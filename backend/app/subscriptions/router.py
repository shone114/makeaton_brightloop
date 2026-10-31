from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.core.database import get_db
from app.models import (
    Subscription,
    SubscriptionLine,
    Plan,
    Product,
    ProductVariant,
    ProductTax,
    TaxRule,
    User,
    QuotationTemplate,
    TemplateLine,
)
from app.schemas import (
    SubscriptionCreate,
    SubscriptionCreateFromTemplate,
    SubscriptionStatusUpdate,
    SubscriptionResponse,
    SubscriptionLineResponse,
    PaginatedResponse,
)
from app.common.dependencies import (
    require_staff_or_admin,
    require_authenticated,
    record_audit_log,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def generate_sub_number(db: Session) -> str:
    count = db.query(func.count(Subscription.id)).scalar() or 0
    return f"SUB-{count + 1:05d}"


def format_sub_response(s: Subscription) -> SubscriptionResponse:
    lines = []
    total_amount = 0.0
    for l in s.lines:
        variant_label = None
        if l.variant:
            variant_label = f"{l.variant.attribute_name}: {l.variant.attribute_value} (+{float(l.variant.price_extra):.2f})"
        
        lines.append(
            SubscriptionLineResponse(
                id=l.id,
                product_id=l.product_id,
                product_name=l.product.name if l.product else None,
                variant_id=l.variant_id,
                variant_label=variant_label,
                quantity=l.quantity,
                unit_price=float(l.unit_price),
                tax_rate=float(l.tax_rate),
                line_total=float(l.line_total),
            )
        )
        total_amount += float(l.line_total)

    return SubscriptionResponse(
        id=s.id,
        number=s.number,
        customer_id=s.customer_id,
        customer_name=s.customer.name if s.customer else None,
        customer_email=s.customer.email if s.customer else None,
        plan_id=s.plan_id,
        plan_name=s.plan.name if s.plan else None,
        billing_period=s.plan.billing_period if s.plan else None,
        status=s.status,
        start_date=s.start_date,
        end_date=s.end_date,
        payment_terms_days=s.payment_terms_days,
        billed_through=s.billed_through,
        created_at=s.created_at,
        lines=lines,
        total_amount=round(total_amount, 2),
    )


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_staff_or_admin)])
def list_subscriptions(
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Subscription)

    if status_filter and isinstance(status_filter, str):
        query = query.filter(Subscription.status == status_filter)
    if customer_id:
        query = query.filter(Subscription.customer_id == customer_id)
    if search:
        search_fmt = f"%{search.lower()}%"
        query = query.join(Subscription.customer).filter(
            or_(
                func.lower(Subscription.number).like(search_fmt),
                func.lower(User.name).like(search_fmt),
                func.lower(User.email).like(search_fmt),
            )
        )

    total = query.count()
    items = query.order_by(Subscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[format_sub_response(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{sub_id}", response_model=SubscriptionResponse, dependencies=[Depends(require_authenticated)])
def get_subscription(sub_id: str, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return format_sub_response(sub)


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreate,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db),
):
    target_customer_id = current_user.id if current_user.role == "customer" else payload.customer_id
    customer = db.query(User).filter(User.id == target_customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")

    plan = db.query(Plan).filter(Plan.id == payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan not found")

    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be on or after start date")

    sub_number = generate_sub_number(db)
    subscription = Subscription(
        number=sub_number,
        customer_id=payload.customer_id,
        plan_id=payload.plan_id,
        status="draft",
        start_date=payload.start_date,
        end_date=payload.end_date,
        payment_terms_days=payload.payment_terms_days,
        billed_through=None,
    )
    db.add(subscription)
    db.flush()

    for item in payload.lines:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        if not prod:
            continue

        unit_price = item.unit_price
        if unit_price is None:
            unit_price = float(prod.sales_price)
            if item.variant_id:
                var = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
                if var:
                    unit_price += float(var.price_extra)

        tax_rate = sum(float(pt.tax_rule.rate) for pt in prod.tax_rules if pt.tax_rule and pt.tax_rule.is_active)
        subtotal = unit_price * item.quantity
        line_total = subtotal + (subtotal * tax_rate / 100.0)

        s_line = SubscriptionLine(
            subscription_id=subscription.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=unit_price,
            tax_rate=tax_rate,
            line_total=round(line_total, 2),
        )
        db.add(s_line)

    record_audit_log(
        db,
        entity_type="subscription",
        entity_id=subscription.id,
        action="created",
        new_value={"number": subscription.number, "status": "draft"},
        user_id=current_user.id,
    )
    db.commit()
    db.refresh(subscription)
    return format_sub_response(subscription)


@router.post("/from-template", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_from_template(
    payload: SubscriptionCreateFromTemplate,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    template = db.query(QuotationTemplate).filter(QuotationTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation template not found")

    sub_number = generate_sub_number(db)
    subscription = Subscription(
        number=sub_number,
        customer_id=payload.customer_id,
        plan_id=template.plan_id,
        status="draft",
        start_date=payload.start_date,
        end_date=payload.end_date,
        payment_terms_days=payload.payment_terms_days,
        billed_through=None,
    )
    db.add(subscription)
    db.flush()

    for t_line in template.lines:
        prod = t_line.product
        tax_rate = sum(float(pt.tax_rule.rate) for pt in prod.tax_rules if pt.tax_rule and pt.tax_rule.is_active)
        unit_price = float(t_line.unit_price)
        subtotal = unit_price * t_line.quantity
        line_total = subtotal + (subtotal * tax_rate / 100.0)

        s_line = SubscriptionLine(
            subscription_id=subscription.id,
            product_id=t_line.product_id,
            variant_id=t_line.variant_id,
            quantity=t_line.quantity,
            unit_price=unit_price,
            tax_rate=tax_rate,
            line_total=round(line_total, 2),
        )
        db.add(s_line)

    record_audit_log(
        db,
        entity_type="subscription",
        entity_id=subscription.id,
        action="created_from_template",
        new_value={"number": subscription.number, "template_id": template.id},
        user_id=current_user.id,
    )
    db.commit()
    db.refresh(subscription)
    return format_sub_response(subscription)


@router.patch("/{sub_id}/status", response_model=SubscriptionResponse)
def update_subscription_status(
    sub_id: str,
    payload: SubscriptionStatusUpdate,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    if current_user.role == "customer" and sub.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update another customer's subscription.")

    target = payload.status.lower()
    current = sub.status.lower()

    if target == current:
        return format_sub_response(sub)

    if current == "draft":
        if target != "quotation":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot transition directly from Draft to {target}. Must be Quotation.")
        if len(sub.lines) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription must have at least one product line to move to Quotation.")

    elif current == "quotation":
        if target != "confirmed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot transition from Quotation to {target}. Must be Confirmed.")

    elif current == "confirmed":
        if target != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot transition from Confirmed to {target}. Must be Active.")

    elif current == "active":
        if target == "paused":
            if not sub.plan.pausable:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This plan does not permit pausing subscriptions.")
        elif target == "closed":
            if not sub.plan.closable_early and sub.end_date > date.today():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This plan cannot be closed early before its end date.")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid transition from Active to {target}.")

    elif current == "paused":
        if target != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paused subscriptions can only be resumed to Active.")

    elif current == "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Closed subscriptions cannot be modified. Please create a renewal subscription.")

    old_status = sub.status
    sub.status = target
    record_audit_log(
        db,
        entity_type="subscription",
        entity_id=sub.id,
        action="status_change",
        old_value={"status": old_status},
        new_value={"status": target},
        user_id=current_user.id,
    )
    db.commit()
    db.refresh(sub)
    return format_sub_response(sub)
