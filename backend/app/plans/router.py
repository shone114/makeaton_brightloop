from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Plan, Product, User
from app.schemas import PlanCreate, PlanUpdate, PlanResponse, PaginatedResponse
from app.common.dependencies import (
    require_admin,
    require_authenticated,
    record_audit_log,
)

router = APIRouter(prefix="/plans", tags=["Subscription Plans"])


def format_plan_response(p: Plan) -> PlanResponse:
    return PlanResponse(
        id=p.id,
        name=p.name,
        product_id=p.product_id,
        product_name=p.product.name if p.product else None,
        billing_period=p.billing_period,
        amount=float(p.amount),
        min_quantity=p.min_quantity,
        available_from=p.available_from,
        available_to=p.available_to,
        auto_close=p.auto_close,
        closable_early=p.closable_early,
        pausable=p.pausable,
        renewable=p.renewable,
        is_active=p.is_active,
        created_at=p.created_at,
    )


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_authenticated)])
def list_plans(
    billing_period: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Plan)
    if billing_period:
        query = query.filter(Plan.billing_period == billing_period)
    if is_active is not None:
        query = query.filter(Plan.is_active == is_active)

    total = query.count()
    items = query.order_by(Plan.name.asc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[format_plan_response(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/all", response_model=List[PlanResponse], dependencies=[Depends(require_authenticated)])
def get_all_active_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.is_active == True).order_by(Plan.name.asc()).all()
    return [format_plan_response(p) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse, dependencies=[Depends(require_authenticated)])
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return format_plan_response(plan)


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    prod = db.query(Product).filter(Product.id == payload.product_id).first()
    if not prod:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected product does not exist")

    plan = Plan(
        name=payload.name,
        product_id=payload.product_id,
        billing_period=payload.billing_period,
        amount=payload.amount,
        min_quantity=payload.min_quantity,
        available_from=payload.available_from,
        available_to=payload.available_to,
        auto_close=payload.auto_close,
        closable_early=payload.closable_early,
        pausable=payload.pausable,
        renewable=payload.renewable,
        is_active=payload.is_active,
    )
    db.add(plan)
    record_audit_log(
        db,
        entity_type="plan",
        entity_id=plan.id,
        action="created",
        new_value={"name": plan.name, "amount": float(plan.amount), "billing_period": plan.billing_period},
        user_id=admin.id,
    )
    db.commit()
    db.refresh(plan)
    return format_plan_response(plan)


@router.put("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: str,
    payload: PlanUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, val)

    record_audit_log(
        db,
        entity_type="plan",
        entity_id=plan.id,
        action="updated",
        new_value={"name": plan.name, "amount": float(plan.amount)},
        user_id=admin.id,
    )
    db.commit()
    db.refresh(plan)
    return format_plan_response(plan)
