from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import TaxRule, User
from app.schemas import TaxRuleCreate, TaxRuleUpdate, TaxRuleResponse
from app.common.dependencies import require_admin, require_authenticated, record_audit_log

router = APIRouter(prefix="/taxes", tags=["Tax Rules"])


@router.get("", response_model=List[TaxRuleResponse], dependencies=[Depends(require_authenticated)])
def list_taxes(db: Session = Depends(get_db)):
    taxes = db.query(TaxRule).order_by(TaxRule.name.asc()).all()
    return [TaxRuleResponse.model_validate(t) for t in taxes]


@router.post("", response_model=TaxRuleResponse, status_code=status.HTTP_201_CREATED)
def create_tax(
    payload: TaxRuleCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tax = TaxRule(
        name=payload.name,
        rate=payload.rate,
        is_active=payload.is_active,
    )
    db.add(tax)
    db.flush()
    record_audit_log(
        db,
        entity_type="tax_rule",
        entity_id=tax.id,
        action="created",
        new_value={"name": tax.name, "rate": float(tax.rate)},
        user_id=admin.id,
    )
    db.commit()
    db.refresh(tax)
    return TaxRuleResponse.model_validate(tax)


@router.put("/{tax_id}", response_model=TaxRuleResponse)
def update_tax(
    tax_id: str,
    payload: TaxRuleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tax = db.query(TaxRule).filter(TaxRule.id == tax_id).first()
    if not tax:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax rule not found")

    old_val = {"name": tax.name, "rate": float(tax.rate), "is_active": tax.is_active}
    if payload.name is not None:
        tax.name = payload.name
    if payload.rate is not None:
        tax.rate = payload.rate
    if payload.is_active is not None:
        tax.is_active = payload.is_active

    record_audit_log(
        db,
        entity_type="tax_rule",
        entity_id=tax.id,
        action="updated",
        old_value=old_val,
        new_value={"name": tax.name, "rate": float(tax.rate), "is_active": tax.is_active},
        user_id=admin.id,
    )
    db.commit()
    db.refresh(tax)
    return TaxRuleResponse.model_validate(tax)
