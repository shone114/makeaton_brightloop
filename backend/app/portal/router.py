from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc, and_
from app.core.database import get_db
from app.models import Subscription, SubscriptionLine, Invoice, InvoiceLine, Payment, User
from app.schemas import (
    SubscriptionResponse,
    InvoiceResponse,
)
from app.common.dependencies import get_current_user
from app.subscriptions.router import format_sub_response
from app.invoices.router import format_invoice_response

router = APIRouter(prefix="/portal", tags=["Customer Portal"])


@router.get("/stats")
def get_portal_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    active_subs = (
        db.query(func.count(Subscription.id))
        .filter(and_(Subscription.customer_id == current_user.id, Subscription.status == "active"))
        .scalar() or 0
    )

    total_paid = (
        db.query(func.sum(Payment.amount))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.customer_id == current_user.id)
        .scalar() or 0.0
    )

    unpaid_invoices_sum = (
        db.query(func.sum(Invoice.total))
        .filter(and_(Invoice.customer_id == current_user.id, Invoice.status.in_(["draft", "confirmed"])))
        .scalar() or 0.0
    )

    partial_payments = (
        db.query(func.sum(Payment.amount))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(and_(Invoice.customer_id == current_user.id, Invoice.status.in_(["draft", "confirmed"])))
        .scalar() or 0.0
    )

    balance_due = max(0.0, float(unpaid_invoices_sum) - float(partial_payments))

    return {
        "customer_name": current_user.name,
        "customer_email": current_user.email,
        "active_subscriptions": active_subs,
        "total_paid": round(float(total_paid), 2),
        "balance_due": round(float(balance_due), 2),
    }


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
def get_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subs = (
        db.query(Subscription)
        .options(
            joinedload(Subscription.customer),
            joinedload(Subscription.plan),
            selectinload(Subscription.lines).joinedload(SubscriptionLine.product),
            selectinload(Subscription.lines).joinedload(SubscriptionLine.variant),
        )
        .filter(Subscription.customer_id == current_user.id)
        .order_by(desc(Subscription.created_at))
        .all()
    )
    return [format_sub_response(s) for s in subs]


@router.get("/invoices", response_model=List[InvoiceResponse])
def get_my_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoices = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.customer),
            joinedload(Invoice.subscription),
            selectinload(Invoice.lines).joinedload(InvoiceLine.product),
            selectinload(Invoice.lines).joinedload(InvoiceLine.variant),
            selectinload(Invoice.discounts),
            selectinload(Invoice.payments),
        )
        .filter(Invoice.customer_id == current_user.id)
        .order_by(desc(Invoice.invoice_date))
        .all()
    )
    return [format_invoice_response(inv) for inv in invoices]
