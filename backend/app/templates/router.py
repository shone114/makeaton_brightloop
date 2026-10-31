from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import QuotationTemplate, TemplateLine, Plan, User
from app.schemas import (
    QuotationTemplateCreate,
    QuotationTemplateResponse,
    TemplateLineResponse,
)
from app.common.dependencies import (
    require_staff_or_admin,
    require_authenticated,
    record_audit_log,
)

router = APIRouter(prefix="/templates", tags=["Quotation Templates"])


def format_template_response(t: QuotationTemplate) -> QuotationTemplateResponse:
    lines = []
    for line in t.lines:
        lines.append(
            TemplateLineResponse(
                id=line.id,
                product_id=line.product_id,
                product_name=line.product.name if line.product else None,
                variant_id=line.variant_id,
                variant_name=f"{line.variant.attribute_name}: {line.variant.attribute_value}" if line.variant else None,
                quantity=line.quantity,
                unit_price=float(line.unit_price),
            )
        )
    return QuotationTemplateResponse(
        id=t.id,
        name=t.name,
        plan_id=t.plan_id,
        plan_name=t.plan.name if t.plan else None,
        validity_days=t.validity_days,
        is_active=t.is_active,
        created_at=t.created_at,
        lines=lines,
    )


@router.get("", response_model=List[QuotationTemplateResponse], dependencies=[Depends(require_authenticated)])
def list_templates(db: Session = Depends(get_db)):
    templates = db.query(QuotationTemplate).order_by(QuotationTemplate.name.asc()).all()
    return [format_template_response(t) for t in templates]


@router.get("/{template_id}", response_model=QuotationTemplateResponse, dependencies=[Depends(require_authenticated)])
def get_template(template_id: str, db: Session = Depends(get_db)):
    t = db.query(QuotationTemplate).filter(QuotationTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return format_template_response(t)


@router.post("", response_model=QuotationTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: QuotationTemplateCreate,
    user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.id == payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected plan does not exist")

    template = QuotationTemplate(
        name=payload.name,
        plan_id=payload.plan_id,
        validity_days=payload.validity_days,
        is_active=True,
    )
    db.add(template)
    db.flush()

    for line in payload.lines:
        t_line = TemplateLine(
            template_id=template.id,
            product_id=line.product_id,
            variant_id=line.variant_id,
            quantity=line.quantity,
            unit_price=line.unit_price,
        )
        db.add(t_line)

    record_audit_log(
        db,
        entity_type="quotation_template",
        entity_id=template.id,
        action="created",
        new_value={"name": template.name},
        user_id=user.id,
    )
    db.commit()
    db.refresh(template)
    return format_template_response(template)
