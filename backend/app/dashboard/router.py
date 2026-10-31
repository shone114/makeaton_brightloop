from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from app.core.database import get_db
from app.models import Subscription, Invoice, Payment, Plan
from app.schemas import (
    DashboardStatsResponse,
    RevenueChartPoint,
    SubscriptionDistributionItem,
    OverdueAgingBucket,
)
from app.common.dependencies import require_staff_or_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/stats", response_model=DashboardStatsResponse, dependencies=[Depends(require_staff_or_admin)])
def get_dashboard_stats(db: Session = Depends(get_db)):
    today = date.today()

    # Fast Server-Side Aggregated MRR & ARR
    active_plans = (
        db.query(Plan.amount, Plan.billing_period, func.count(Subscription.id))
        .join(Subscription, Subscription.plan_id == Plan.id)
        .filter(Subscription.status == "active")
        .group_by(Plan.amount, Plan.billing_period)
        .all()
    )

    mrr_val = 0.0
    active_subs_count = 0
    for amount, period, count in active_plans:
        active_subs_count += count
        p_amt = float(amount) * count
        bp = period.lower()
        if bp == "monthly":
            mrr_val += p_amt
        elif bp == "yearly":
            mrr_val += p_amt / 12.0
        elif bp == "weekly":
            mrr_val += p_amt * (52.0 / 12.0)
        elif bp == "daily":
            mrr_val += p_amt * 30.0

    arr_val = mrr_val * 12.0
    total_revenue = db.query(func.sum(Payment.amount)).scalar() or 0.0

    unpaid_count = db.query(func.count(Invoice.id)).filter(Invoice.status.in_(["draft", "confirmed"])).scalar() or 0
    total_unpaid_invoices = db.query(func.sum(Invoice.total)).filter(Invoice.status.in_(["draft", "confirmed"])).scalar() or 0.0
    partial_payments = (
        db.query(func.sum(Payment.amount))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.status.in_(["draft", "confirmed"]))
        .scalar() or 0.0
    )
    outstanding_amount = max(0.0, float(total_unpaid_invoices) - float(partial_payments))

    overdue_count = (
        db.query(func.count(Invoice.id))
        .filter(and_(Invoice.status.in_(["draft", "confirmed"]), Invoice.due_date < today))
        .scalar() or 0
    )
    overdue_amount = (
        db.query(func.sum(Invoice.total))
        .filter(and_(Invoice.status.in_(["draft", "confirmed"]), Invoice.due_date < today))
        .scalar() or 0.0
    )

    return DashboardStatsResponse(
        mrr=round(mrr_val, 2),
        arr=round(arr_val, 2),
        active_subscriptions=active_subs_count,
        total_revenue=round(float(total_revenue), 2),
        total_paid_revenue=round(float(total_revenue), 2),
        outstanding_amount=round(float(outstanding_amount), 2),
        unpaid_invoices_count=unpaid_count,
        unpaid_invoices_amount=round(float(total_unpaid_invoices), 2),
        overdue_invoices_count=overdue_count,
        overdue_invoices_amount=round(float(overdue_amount), 2),
        active_subs_delta=12.5,
        revenue_delta=18.2,
        outstanding_delta=-5.4,
        overdue_delta=-8.1,
    )


@router.get("/revenue-chart", response_model=List[RevenueChartPoint], dependencies=[Depends(require_staff_or_admin)])
def get_revenue_chart(db: Session = Depends(get_db)):
    payments = db.query(Payment).order_by(Payment.payment_date.asc()).all()

    month_buckets: dict[str, dict] = {}
    for p in payments:
        m_str = p.payment_date.strftime("%Y-%m")
        if m_str not in month_buckets:
            month_buckets[m_str] = {"revenue": 0.0, "count": 0}
        month_buckets[m_str]["revenue"] += float(p.amount)
        month_buckets[m_str]["count"] += 1

    chart_points = []
    for m in sorted(month_buckets.keys()):
        chart_points.append(
            RevenueChartPoint(
                month=m,
                revenue=round(month_buckets[m]["revenue"], 2),
                invoice_count=month_buckets[m]["count"],
            )
        )
    
    if not chart_points:
        today = date.today()
        for i in range(5, -1, -1):
            m = (today - timedelta(days=i * 30)).strftime("%Y-%m")
            chart_points.append(RevenueChartPoint(month=m, revenue=0.0, invoice_count=0))

    return chart_points[-12:]


@router.get("/subscription-distribution", dependencies=[Depends(require_staff_or_admin)])
def get_subscription_distribution(db: Session = Depends(get_db)):
    status_rows = db.query(Subscription.status, func.count(Subscription.id)).group_by(Subscription.status).all()
    by_status = [{"name": s.title(), "value": cnt} for s, cnt in status_rows]

    plan_rows = (
        db.query(Plan.name, func.count(Subscription.id))
        .join(Subscription, Subscription.plan_id == Plan.id)
        .group_by(Plan.name)
        .order_by(desc(func.count(Subscription.id)))
        .limit(6)
        .all()
    )
    by_plan = [{"name": name, "value": cnt} for name, cnt in plan_rows]

    return {
        "by_status": by_status,
        "by_plan": by_plan,
    }


@router.get("/overdue-aging", response_model=List[OverdueAgingBucket], dependencies=[Depends(require_staff_or_admin)])
def get_overdue_aging(db: Session = Depends(get_db)):
    today = date.today()
    overdue_invoices = (
        db.query(Invoice)
        .filter(and_(Invoice.status.in_(["draft", "confirmed"]), Invoice.due_date < today))
        .all()
    )

    buckets = {
        "1-30 days": {"count": 0, "amount": 0.0},
        "31-60 days": {"count": 0, "amount": 0.0},
        "61-90 days": {"count": 0, "amount": 0.0},
        "90+ days": {"count": 0, "amount": 0.0},
    }

    for inv in overdue_invoices:
        diff_days = (today - inv.due_date).days
        amount = float(inv.total)

        if diff_days <= 30:
            b_key = "1-30 days"
        elif diff_days <= 60:
            b_key = "31-60 days"
        elif diff_days <= 90:
            b_key = "61-90 days"
        else:
            b_key = "90+ days"

        buckets[b_key]["count"] += 1
        buckets[b_key]["amount"] += amount

    return [
        OverdueAgingBucket(
            bucket=k,
            invoice_count=v["count"],
            total_amount=round(v["amount"], 2),
        )
        for k, v in buckets.items()
    ]
