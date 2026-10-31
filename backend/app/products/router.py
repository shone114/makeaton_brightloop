from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models import Product, ProductVariant, ProductTax, TaxRule, User
from app.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductVariantCreate,
    ProductVariantResponse,
    PaginatedResponse,
)
from app.common.dependencies import (
    require_admin,
    require_authenticated,
    record_audit_log,
)

router = APIRouter(prefix="/products", tags=["Products & Variants"])


def format_product_response(p: Product) -> ProductResponse:
    variants = [ProductVariantResponse.model_validate(v) for v in p.variants]
    tax_rates = [float(pt.tax_rule.rate) for pt in p.tax_rules if pt.tax_rule and pt.tax_rule.is_active]
    return ProductResponse(
        id=p.id,
        name=p.name,
        type=p.type,
        sales_price=float(p.sales_price),
        cost_price=float(p.cost_price),
        notes=p.notes,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
        variants=variants,
        tax_rates=tax_rates,
        total_tax_rate=sum(tax_rates),
    )


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_authenticated)])
def list_products(
    search: Optional[str] = None,
    product_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if search:
        query = query.filter(func.lower(Product.name).like(f"%{search.lower()}%"))
    if product_type:
        query = query.filter(Product.type == product_type)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    total = query.count()
    items = query.order_by(Product.name.asc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[format_product_response(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/all", response_model=List[ProductResponse], dependencies=[Depends(require_authenticated)])
def get_all_active_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active == True).order_by(Product.name.asc()).all()
    return [format_product_response(p) for p in products]


@router.get("/{product_id}", response_model=ProductResponse, dependencies=[Depends(require_authenticated)])
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return format_product_response(p)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = Product(
        name=payload.name,
        type=payload.type,
        sales_price=payload.sales_price,
        cost_price=payload.cost_price,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(product)
    db.flush()

    for v in payload.variants:
        variant = ProductVariant(
            product_id=product.id,
            attribute_name=v.attribute_name,
            attribute_value=v.attribute_value,
            price_extra=v.price_extra,
        )
        db.add(variant)

    for tax_id in payload.tax_rule_ids:
        pt = ProductTax(product_id=product.id, tax_rule_id=tax_id)
        db.add(pt)

    record_audit_log(
        db,
        entity_type="product",
        entity_id=product.id,
        action="created",
        new_value={"name": product.name, "sales_price": float(product.sales_price)},
        user_id=admin.id,
    )
    db.commit()
    db.refresh(product)
    return format_product_response(product)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if payload.name is not None:
        product.name = payload.name
    if payload.type is not None:
        product.type = payload.type
    if payload.sales_price is not None:
        product.sales_price = payload.sales_price
    if payload.cost_price is not None:
        product.cost_price = payload.cost_price
    if payload.notes is not None:
        product.notes = payload.notes
    if payload.is_active is not None:
        product.is_active = payload.is_active

    if payload.tax_rule_ids is not None:
        db.query(ProductTax).filter(ProductTax.product_id == product_id).delete()
        for tax_id in payload.tax_rule_ids:
            db.add(ProductTax(product_id=product.id, tax_rule_id=tax_id))

    record_audit_log(
        db,
        entity_type="product",
        entity_id=product.id,
        action="updated",
        new_value={"name": product.name, "sales_price": float(product.sales_price)},
        user_id=admin.id,
    )
    db.commit()
    db.refresh(product)
    return format_product_response(product)


@router.post("/{product_id}/variants", response_model=ProductVariantResponse)
def add_variant(
    product_id: str,
    payload: ProductVariantCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    variant = ProductVariant(
        product_id=product_id,
        attribute_name=payload.attribute_name,
        attribute_value=payload.attribute_value,
        price_extra=payload.price_extra,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return ProductVariantResponse.model_validate(variant)
