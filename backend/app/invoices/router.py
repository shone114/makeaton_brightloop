import calendar
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.core.database import get_db
from app.core.config import settings
from app.models import (
    Invoice,
    InvoiceLine,
    InvoiceDiscount,
    Subscription,
    SubscriptionLine,
    DiscountRule,
    DiscountProduct,
    Payment,
    User,
    Plan,
    Product,
    ProductVariant,
)
from app.schemas import (
    InvoiceResponse,
    InvoiceLineResponse,
    InvoiceDiscountResponse,
    InvoiceStatusUpdate,
    BulkInvoiceResponse,
    PaginatedResponse,
)
from app.common.dependencies import (
    require_staff_or_admin,
    require_authenticated,
    record_audit_log,
)
from app.invoices.pdf import generate_invoice_pdf
from app.common.email import send_email

router = APIRouter(prefix="/invoices", tags=["Invoices & Billing Engine"])


def compute_next_period(start: date, billing_period: str) -> tuple[date, date]:
    period = billing_period.lower()
    period_start = start

    if period == "daily":
        period_end = period_start
    elif period == "weekly":
        period_end = period_start + timedelta(days=6)
    elif period == "yearly":
        try:
            target_year = period_start.year + 1
            period_end = date(target_year, period_start.month, period_start.day) - timedelta(days=1)
        except ValueError:
            period_end = period_start + timedelta(days=364)
    else:  # monthly default
        year = period_start.year
        month = period_start.month + 1
        if month > 12:
            month = 1
            year += 1
        max_day = calendar.monthrange(year, month)[1]
        target_day = min(period_start.day, max_day)
        next_month_start = date(year, month, target_day)
        period_end = next_month_start - timedelta(days=1)

    return period_start, period_end


def generate_invoice_number(db: Session) -> str:
    count = db.query(func.count(Invoice.id)).scalar() or 0
    return f"INV-{count + 1:05d}"


def generate_invoice_for_subscription(
    db: Session,
    subscription_id: str,
    invoice_date: Optional[date] = None,
) -> Optional[Invoice]:
    if invoice_date is None:
        invoice_date = date.today()

    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        return None

    if sub.status.lower() != "active":
        return None

    if sub.billed_through is None:
        period_start = sub.start_date
    else:
        period_start = sub.billed_through + timedelta(days=1)

    if period_start > sub.end_date or period_start > invoice_date:
        return None  # Nothing due yet

    period_start, period_end = compute_next_period(period_start, sub.plan.billing_period)
    if period_end > sub.end_date:
        period_end = sub.end_date

    # IDEMPOTENCY GUARD: Check if invoice already exists for this subscription and period_start
    existing = db.query(Invoice).filter(
        and_(
            Invoice.subscription_id == sub.id,
            Invoice.period_start == period_start,
        )
    ).first()
    if existing is not None:
        return None  # Skip duplicate!

    inv_number = generate_invoice_number(db)
    due_date = invoice_date + timedelta(days=sub.payment_terms_days)

    invoice = Invoice(
        number=inv_number,
        subscription_id=sub.id,
        customer_id=sub.customer_id,
        status="draft",
        invoice_date=invoice_date,
        due_date=due_date,
        period_start=period_start,
        period_end=period_end,
        subtotal=0.0,
        tax_total=0.0,
        discount_total=0.0,
        total=0.0,
        payment_terms_days=sub.payment_terms_days,
    )
    db.add(invoice)
    db.flush()

    subtotal_acc = 0.0
    tax_acc = 0.0
    line_models: list[InvoiceLine] = []

    for s_line in sub.lines:
        variant_suffix = ""
        if s_line.variant:
            variant_suffix = f" ({s_line.variant.attribute_name}: {s_line.variant.attribute_value})"
        desc_text = f"{s_line.product.name}{variant_suffix}"

        line_subtotal = float(s_line.unit_price) * s_line.quantity
        line_tax = round(line_subtotal * (float(s_line.tax_rate) / 100.0), 2)
        line_total = line_subtotal + line_tax

        inv_line = InvoiceLine(
            invoice_id=invoice.id,
            product_id=s_line.product_id,
            variant_id=s_line.variant_id,
            description=desc_text,
            quantity=s_line.quantity,
            unit_price=s_line.unit_price,
            tax_rate=s_line.tax_rate,
            tax_amount=line_tax,
            subtotal=line_subtotal,
            total=line_total,
        )
        db.add(inv_line)
        line_models.append(inv_line)

        subtotal_acc += line_subtotal
        tax_acc += line_tax

    # AUTOMATIC DISCOUNT APPLICATION
    available_discounts = db.query(DiscountRule).filter(
        and_(
            DiscountRule.is_active == True,
            DiscountRule.start_date <= invoice_date,
            DiscountRule.end_date >= invoice_date,
            or_(
                DiscountRule.usage_limit == None,
                DiscountRule.usage_count < DiscountRule.usage_limit,
            ),
        )
    ).all()

    total_discount_acc = 0.0
    for disc in available_discounts:
        eligible_subtotal = 0.0
        meets_conditions = True

        if disc.scope == "product":
            target_prod_ids = {dp.product_id for dp in disc.products}
            matched_qty = 0
            for l in line_models:
                if l.product_id in target_prod_ids:
                    eligible_subtotal += float(l.subtotal)
                    matched_qty += l.quantity
            if eligible_subtotal == 0:
                meets_conditions = False
            if disc.min_quantity and matched_qty < disc.min_quantity:
                meets_conditions = False
            if disc.min_purchase_amount and eligible_subtotal < float(disc.min_purchase_amount):
                meets_conditions = False
        else:
            eligible_subtotal = subtotal_acc
            total_qty = sum(l.quantity for l in line_models)
            if disc.min_quantity and total_qty < disc.min_quantity:
                meets_conditions = False
            if disc.min_purchase_amount and eligible_subtotal < float(disc.min_purchase_amount):
                meets_conditions = False

        if meets_conditions and eligible_subtotal > 0:
            if disc.type == "percentage":
                amount = eligible_subtotal * (float(disc.value) / 100.0)
            else:
                amount = float(disc.value)

            amount = min(amount, eligible_subtotal)
            amount = round(amount, 2)

            if amount > 0:
                inv_disc = InvoiceDiscount(
                    invoice_id=invoice.id,
                    discount_rule_id=disc.id,
                    description=f"{disc.name} ({disc.type.title()} {float(disc.value)})",
                    type=disc.type,
                    value=disc.value,
                    discount_amount=amount,
                )
                db.add(inv_disc)
                disc.usage_count += 1
                total_discount_acc += amount

    total_discount_acc = min(total_discount_acc, subtotal_acc)
    grand_total = subtotal_acc + tax_acc - total_discount_acc

    invoice.subtotal = round(subtotal_acc, 2)
    invoice.tax_total = round(tax_acc, 2)
    invoice.discount_total = round(total_discount_acc, 2)
    invoice.total = round(grand_total, 2)

    sub.billed_through = period_end
    return invoice


def format_invoice_response(inv: Invoice) -> InvoiceResponse:
    lines = []
    for l in inv.lines:
        variant_label = None
        if l.variant:
            variant_label = f"{l.variant.attribute_name}: {l.variant.attribute_value}"
        lines.append(
            InvoiceLineResponse(
                id=l.id,
                product_id=l.product_id,
                product_name=l.product.name if l.product else None,
                variant_label=variant_label,
                description=l.description,
                quantity=l.quantity,
                unit_price=float(l.unit_price),
                tax_rate=float(l.tax_rate),
                tax_amount=float(l.tax_amount),
                subtotal=float(l.subtotal),
                total=float(l.total),
            )
        )

    discounts = []
    for d in inv.discounts:
        discounts.append(
            InvoiceDiscountResponse(
                id=d.id,
                discount_rule_id=d.discount_rule_id,
                description=d.description,
                type=d.type,
                value=float(d.value),
                discount_amount=float(d.discount_amount),
            )
        )

    paid_sum = sum(float(p.amount) for p in inv.payments)
    balance_due = max(0.0, float(inv.total) - paid_sum)
    is_overdue = inv.status in ("draft", "confirmed") and date.today() > inv.due_date

    return InvoiceResponse(
        id=inv.id,
        number=inv.number,
        subscription_id=inv.subscription_id,
        subscription_number=inv.subscription.number if inv.subscription else None,
        customer_id=inv.customer_id,
        customer_name=inv.customer.name if inv.customer else None,
        customer_email=inv.customer.email if inv.customer else None,
        status=inv.status,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        period_start=inv.period_start,
        period_end=inv.period_end,
        subtotal=float(inv.subtotal),
        tax_total=float(inv.tax_total),
        discount_total=float(inv.discount_total),
        total=float(inv.total),
        payment_terms_days=inv.payment_terms_days,
        sent_at=inv.sent_at,
        created_at=inv.created_at,
        is_overdue=is_overdue,
        lines=lines,
        discounts=discounts,
        paid_amount=round(paid_sum, 2),
        balance_due=round(balance_due, 2),
    )


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_staff_or_admin)])
def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    overdue_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Invoice)

    if status_filter and isinstance(status_filter, str):
        query = query.filter(Invoice.status == status_filter)
    if overdue_only:
        query = query.filter(
            and_(
                Invoice.status.in_(["draft", "confirmed"]),
                Invoice.due_date < date.today(),
            )
        )
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if search:
        search_fmt = f"%{search.lower()}%"
        query = query.join(Invoice.customer).filter(
            or_(
                func.lower(Invoice.number).like(search_fmt),
                func.lower(User.name).like(search_fmt),
                func.lower(User.email).like(search_fmt),
            )
        )

    total = query.count()
    items = query.order_by(Invoice.invoice_date.desc(), Invoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[format_invoice_response(inv) for inv in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse, dependencies=[Depends(require_authenticated)])
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return format_invoice_response(inv)


@router.post("/generate/{subscription_id}", response_model=InvoiceResponse, dependencies=[Depends(require_staff_or_admin)])
def generate_single_invoice(subscription_id: str, db: Session = Depends(get_db)):
    invoice = generate_invoice_for_subscription(db, subscription_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No invoice is currently due for this subscription, or subscription is not active.",
        )
    db.commit()
    db.refresh(invoice)
    return format_invoice_response(invoice)


@router.post("/generate-bulk", response_model=BulkInvoiceResponse, dependencies=[Depends(require_staff_or_admin)])
def generate_bulk_invoices(db: Session = Depends(get_db)):
    active_subs = db.query(Subscription).filter(Subscription.status == "active").all()

    generated_count = 0
    skipped_count = 0
    details = []

    for sub in active_subs:
        catch_up_iterations = 0
        while catch_up_iterations < 12:
            inv = generate_invoice_for_subscription(db, sub.id)
            if inv:
                generated_count += 1
                details.append(f"Generated {inv.number} for subscription {sub.number}")
                catch_up_iterations += 1
            else:
                if catch_up_iterations == 0:
                    skipped_count += 1
                break

    db.commit()

    return BulkInvoiceResponse(
        generated_count=generated_count,
        skipped_count=skipped_count,
        details=details[:50],
    )


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse, dependencies=[Depends(require_staff_or_admin)])
def update_invoice_status(
    invoice_id: str,
    payload: InvoiceStatusUpdate,
    user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    target = payload.status.lower()
    current = inv.status.lower()

    if target == "cancelled":
        if len(inv.payments) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel an invoice that already has recorded payments.",
            )
    elif target == "confirmed":
        if current not in ("draft", "confirmed"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot confirm invoice in {current} status.")

    old_status = inv.status
    inv.status = target
    record_audit_log(
        db,
        entity_type="invoice",
        entity_id=inv.id,
        action="status_change",
        old_value={"status": old_status},
        new_value={"status": target},
        user_id=user.id,
    )
    db.commit()
    db.refresh(inv)
    return format_invoice_response(inv)


@router.get("/{invoice_id}/pdf", dependencies=[Depends(require_authenticated)])
def download_invoice_pdf(invoice_id: str, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    pdf_bytes = generate_invoice_pdf(inv)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Invoice_{inv.number}.pdf"'},
    )


@router.post("/{invoice_id}/send", response_model=InvoiceResponse, dependencies=[Depends(require_staff_or_admin)])
def send_invoice(invoice_id: str, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    inv.sent_at = datetime.now(timezone.utc)
    if inv.status == "draft":
        inv.status = "confirmed"

    # Send email with attached PDF invoice
    if inv.customer and inv.customer.email:
        pdf_bytes = generate_invoice_pdf(inv)
        html_msg = f"""
        <h2>Your Invoice #{inv.number} is Ready</h2>
        <p>Dear {inv.customer.name},</p>
        <p>Please find attached your invoice for <strong>${float(inv.total):,.2f}</strong> covering period {inv.period_start} to {inv.period_end}.</p>
        <p>Payment is due by <strong>{inv.due_date}</strong>.</p>
        <p>Thank you for choosing Brightloop Software!</p>
        """
        send_email(
            to_email=inv.customer.email,
            subject=f"Invoice {inv.number} from Brightloop Software",
            html_content=html_msg,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"Invoice_{inv.number}.pdf",
        )

    db.commit()
    db.refresh(inv)
    return format_invoice_response(inv)
