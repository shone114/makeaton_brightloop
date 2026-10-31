from datetime import datetime, date
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Auth Schemas
# ============================================================================

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class StaffCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================================================
# Tax Schemas
# ============================================================================

class TaxRuleBase(BaseModel):
    name: str
    rate: float = Field(..., ge=0, le=100)
    is_active: bool = True


class TaxRuleCreate(TaxRuleBase):
    pass


class TaxRuleUpdate(BaseModel):
    name: Optional[str] = None
    rate: Optional[float] = None
    is_active: Optional[bool] = None


class TaxRuleResponse(TaxRuleBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Product & Variant Schemas
# ============================================================================

class ProductVariantBase(BaseModel):
    attribute_name: str  # e.g. "Brand"
    attribute_value: str  # e.g. "Odoo"
    price_extra: float = 0.0


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantResponse(ProductVariantBase):
    id: str
    product_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    type: str = "software"  # software, addon, service
    sales_price: float = Field(..., ge=0)
    cost_price: float = 0.0
    notes: Optional[str] = None
    is_active: bool = True


class ProductCreate(ProductBase):
    variants: List[ProductVariantCreate] = []
    tax_rule_ids: List[str] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    sales_price: Optional[float] = None
    cost_price: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    tax_rule_ids: Optional[List[str]] = None


class ProductResponse(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime
    variants: List[ProductVariantResponse] = []
    tax_rates: List[float] = []
    total_tax_rate: float = 0.0

    class Config:
        from_attributes = True


# ============================================================================
# Plan Schemas
# ============================================================================

class PlanBase(BaseModel):
    name: str
    product_id: str
    billing_period: str  # daily, weekly, monthly, yearly
    amount: float = Field(..., ge=0)
    min_quantity: int = Field(1, ge=1)
    available_from: date
    available_to: Optional[date] = None
    auto_close: bool = False
    closable_early: bool = False
    pausable: bool = False
    renewable: bool = False
    is_active: bool = True


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    billing_period: Optional[str] = None
    amount: Optional[float] = None
    min_quantity: Optional[int] = None
    available_from: Optional[date] = None
    available_to: Optional[date] = None
    auto_close: Optional[bool] = None
    closable_early: Optional[bool] = None
    pausable: Optional[bool] = None
    renewable: Optional[bool] = None
    is_active: Optional[bool] = None


class PlanResponse(PlanBase):
    id: str
    product_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Quotation Template Schemas
# ============================================================================

class TemplateLineCreate(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = Field(1, ge=1)
    unit_price: float = Field(..., ge=0)


class TemplateLineResponse(BaseModel):
    id: str
    product_id: str
    product_name: Optional[str] = None
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True


class QuotationTemplateCreate(BaseModel):
    name: str
    plan_id: str
    validity_days: int = 30
    lines: List[TemplateLineCreate] = []


class QuotationTemplateResponse(BaseModel):
    id: str
    name: str
    plan_id: str
    plan_name: Optional[str] = None
    validity_days: int
    is_active: bool
    created_at: datetime
    lines: List[TemplateLineResponse] = []

    class Config:
        from_attributes = True


# ============================================================================
# Subscription Schemas
# ============================================================================

class SubscriptionLineCreate(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = Field(1, ge=1)
    unit_price: Optional[float] = None  # If omitted, auto-calculated from product + variant


class SubscriptionLineResponse(BaseModel):
    id: str
    product_id: str
    product_name: Optional[str] = None
    variant_id: Optional[str] = None
    variant_label: Optional[str] = None
    quantity: int
    unit_price: float
    tax_rate: float
    line_total: float

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    customer_id: str
    plan_id: str
    start_date: date
    end_date: date
    payment_terms_days: int = 30
    lines: List[SubscriptionLineCreate] = []


class SubscriptionCreateFromTemplate(BaseModel):
    customer_id: str
    template_id: str
    start_date: date
    end_date: date
    payment_terms_days: int = 30


class SubscriptionStatusUpdate(BaseModel):
    status: str  # draft, quotation, confirmed, active, paused, closed


class SubscriptionResponse(BaseModel):
    id: str
    number: str
    customer_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    plan_id: str
    plan_name: Optional[str] = None
    billing_period: Optional[str] = None
    status: str
    start_date: date
    end_date: date
    payment_terms_days: int
    billed_through: Optional[date] = None
    created_at: datetime
    lines: List[SubscriptionLineResponse] = []
    total_amount: float = 0.0

    class Config:
        from_attributes = True


# ============================================================================
# Invoice Schemas
# ============================================================================

class InvoiceLineResponse(BaseModel):
    id: str
    product_id: str
    product_name: Optional[str] = None
    variant_label: Optional[str] = None
    description: str
    quantity: int
    unit_price: float
    tax_rate: float
    tax_amount: float
    subtotal: float
    total: float

    class Config:
        from_attributes = True


class InvoiceDiscountResponse(BaseModel):
    id: str
    discount_rule_id: str
    description: str
    type: str
    value: float
    discount_amount: float

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: str
    number: str
    subscription_id: str
    subscription_number: Optional[str] = None
    customer_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: str
    invoice_date: date
    due_date: date
    period_start: date
    period_end: date
    subtotal: float
    tax_total: float
    discount_total: float
    total: float
    payment_terms_days: int
    sent_at: Optional[datetime] = None
    created_at: datetime
    is_overdue: bool = False
    lines: List[InvoiceLineResponse] = []
    discounts: List[InvoiceDiscountResponse] = []
    paid_amount: float = 0.0
    balance_due: float = 0.0

    class Config:
        from_attributes = True


class InvoiceStatusUpdate(BaseModel):
    status: str  # draft, confirmed, paid, cancelled


class BulkInvoiceResponse(BaseModel):
    generated_count: int
    skipped_count: int
    details: List[str] = []


# ============================================================================
# Payment Schemas
# ============================================================================

class PaymentCreate(BaseModel):
    invoice_id: str
    method: str = "bank_transfer"  # bank_transfer, credit_card, cash, check, other
    amount: float = Field(..., gt=0)
    payment_date: date
    note: Optional[str] = None


class PaymentResponse(BaseModel):
    id: str
    invoice_id: str
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    method: str
    amount: float
    payment_date: date
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Discount Schemas
# ============================================================================

class DiscountRuleCreate(BaseModel):
    name: str
    type: str  # fixed, percentage
    value: float = Field(..., gt=0)
    scope: str = "subscription"  # product, subscription
    min_purchase_amount: Optional[float] = None
    min_quantity: Optional[int] = None
    start_date: date
    end_date: date
    usage_limit: Optional[int] = None
    product_ids: List[str] = []


class DiscountRuleUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    value: Optional[float] = None
    scope: Optional[str] = None
    min_purchase_amount: Optional[float] = None
    min_quantity: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    usage_limit: Optional[int] = None
    is_active: Optional[bool] = None
    product_ids: Optional[List[str]] = None


class DiscountRuleResponse(BaseModel):
    id: str
    name: str
    type: str
    value: float
    scope: str
    min_purchase_amount: Optional[float] = None
    min_quantity: Optional[int] = None
    start_date: date
    end_date: date
    usage_limit: Optional[int] = None
    usage_count: int
    is_active: bool
    created_at: datetime
    product_ids: List[str] = []

    class Config:
        from_attributes = True


# ============================================================================
# Dashboard & Analytics Schemas
# ============================================================================

class DashboardStatsResponse(BaseModel):
    mrr: float = 0.0
    arr: float = 0.0
    active_subscriptions: int
    total_revenue: float
    total_paid_revenue: float = 0.0
    outstanding_amount: float
    unpaid_invoices_count: int = 0
    unpaid_invoices_amount: float = 0.0
    overdue_invoices_count: int = 0
    overdue_invoices_amount: float = 0.0
    # Trend deltas vs prior period
    active_subs_delta: float = 0.0
    revenue_delta: float = 0.0
    outstanding_delta: float = 0.0
    overdue_delta: float = 0.0


class RevenueChartPoint(BaseModel):
    month: str  # e.g. "2026-05" or "May 2026"
    revenue: float
    invoice_count: int


class SubscriptionDistributionItem(BaseModel):
    name: str
    value: int


class OverdueAgingBucket(BaseModel):
    bucket: str  # "1-30 days", "31-60 days", "61-90 days", "90+ days"
    invoice_count: int
    total_amount: float


# ============================================================================
# Generic Paginated Response
# ============================================================================

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int

