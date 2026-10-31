from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models import AuditLog
from app.schemas import PaginatedResponse
from app.common.dependencies import require_admin

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_audit_logs(
    entity_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    total = query.count()
    items = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[
            {
                "id": log.id,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "action": log.action,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "user_id": log.user_id,
                "created_at": log.created_at,
            }
            for log in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )
