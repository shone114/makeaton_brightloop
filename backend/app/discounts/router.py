from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import DiscountRule, DiscountProduct, User
from app.schemas import DiscountRuleCreate, DiscountRuleUpdate, DiscountRuleResponse
from app.common.dependencies import require_admin, require_authenticated, record_audit_log

router = APIRouter(prefix="/discounts", tags=["Discounts"])


def format_discount_response(d: DiscountRule) -> DiscountRuleResponse:
    prod_ids = [dp.product_id for dp in d.products]
    return DiscountRuleResponse(
        id=d.id,
        name=d.name,
        type=d.type,
        value=float(d.value),
        scope=d.scope,
        min_purchase_amount=float(d.min_purchase_amount) if d.min_purchase_amount else None,
        min_quantity=d.min_quantity,
        start_date=d.start_date,
        end_date=d.end_date,
        usage_limit=d.usage_limit,
        usage_count=d.usage_count,
        is_active=d.is_active,
        created_at=d.created_at,
        product_ids=prod_ids,
    )


@router.get("", response_model=List[DiscountRuleResponse], dependencies=[Depends(require_authenticated)])
def list_discounts(db: Session = Depends(get_db)):
    discounts = db.query(DiscountRule).order_by(DiscountRule.created_at.desc()).all()
    return [format_discount_response(d) for d in discounts]


@router.post("", response_model=DiscountRuleResponse, status_code=status.HTTP_201_CREATED)
def create_discount(
    payload: DiscountRuleCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be on or after start date")

    discount = DiscountRule(
        name=payload.name,
        type=payload.type,
        value=payload.value,
        scope=payload.scope,
        min_purchase_amount=payload.min_purchase_amount,
        min_quantity=payload.min_quantity,
        start_date=payload.start_date,
        end_date=payload.end_date,
        usage_limit=payload.usage_limit,
        usage_count=0,
        is_active=True,
    )
    db.add(discount)
    db.flush()

    if payload.scope == "product":
        for pid in payload.product_ids:
            dp = DiscountProduct(discount_rule_id=discount.id, product_id=pid)
            db.add(dp)

    record_audit_log(
        db,
        entity_type="discount_rule",
        entity_id=discount.id,
        action="created",
        new_value={"name": discount.name, "type": discount.type, "value": float(discount.value)},
        user_id=admin.id,
    )
    db.commit()
    db.refresh(discount)

    return format_discount_response(discount)


@router.put("/{discount_id}", response_model=DiscountRuleResponse)
def update_discount(
    discount_id: str,
    payload: DiscountRuleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    discount = db.query(DiscountRule).filter(DiscountRule.id == discount_id).first()
    if not discount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount rule not found")

    for field, val in payload.model_dump(exclude_unset=True, exclude={"product_ids"}).items():
        setattr(discount, field, val)

    if payload.product_ids is not None:
        db.query(DiscountProduct).filter(DiscountProduct.discount_rule_id == discount_id).delete()
        for pid in payload.product_ids:
            db.add(DiscountProduct(discount_rule_id=discount_id, product_id=pid))

    record_audit_log(
        db,
        entity_type="discount_rule",
        entity_id=discount.id,
        action="updated",
        new_value={"name": discount.name, "is_active": discount.is_active},
        user_id=admin.id,
    )
    db.commit()
    db.refresh(discount)

    return format_discount_response(discount)
