from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models import Payment, Invoice, User
from app.schemas import PaymentCreate, PaymentResponse, PaginatedResponse
from app.common.dependencies import (
    require_staff_or_admin,
    require_authenticated,
    record_audit_log,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


def format_payment_response(p: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=p.id,
        invoice_id=p.invoice_id,
        invoice_number=p.invoice.number if p.invoice else None,
        customer_name=p.invoice.customer.name if (p.invoice and p.invoice.customer) else None,
        method=p.method,
        amount=float(p.amount),
        payment_date=p.payment_date,
        note=p.note,
        created_at=p.created_at,
    )


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_staff_or_admin)])
def list_payments(
    invoice_id: Optional[str] = None,
    method: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Payment)
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)
    if method:
        query = query.filter(Payment.method == method)

    total = query.count()
    items = query.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[format_payment_response(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    payload: PaymentCreate,
    user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == payload.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    if invoice.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot record payments for a cancelled invoice.")

    payment = Payment(
        invoice_id=payload.invoice_id,
        method=payload.method,
        amount=payload.amount,
        payment_date=payload.payment_date,
        note=payload.note,
    )
    db.add(payment)
    db.flush()

    current_paid = sum(float(p.amount) for p in invoice.payments) + float(payload.amount)
    if current_paid >= float(invoice.total):
        old_status = invoice.status
        invoice.status = "paid"
        record_audit_log(
            db,
            entity_type="invoice",
            entity_id=invoice.id,
            action="status_change_auto_paid",
            old_value={"status": old_status},
            new_value={"status": "paid"},
            user_id=user.id,
        )

    record_audit_log(
        db,
        entity_type="payment",
        entity_id=payment.id,
        action="payment_recorded",
        new_value={"invoice_number": invoice.number, "amount": float(payment.amount), "method": payment.method},
        user_id=user.id,
    )
    db.commit()
    db.refresh(payment)

    return format_payment_response(payment)
