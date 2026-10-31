import uuid
from datetime import datetime, timezone, date
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Numeric,
    Text,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="customer", index=True)  # admin, staff, customer
    is_active = Column(Boolean, nullable=False, default=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    subscriptions = relationship("Subscription", back_populates="customer", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="customer")


class TaxRule(Base):
    __tablename__ = "tax_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 2), nullable=False)  # e.g. 18.00 = 18%
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    products = relationship("ProductTax", back_populates="tax_rule")


class ProductTax(Base):
    __tablename__ = "product_taxes"

    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    tax_rule_id = Column(String(36), ForeignKey("tax_rules.id", ondelete="CASCADE"), primary_key=True)

    product = relationship("Product", back_populates="tax_rules")
    tax_rule = relationship("TaxRule", back_populates="products")


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, default="software", index=True)  # software, addon, service
    sales_price = Column(Numeric(12, 2), nullable=False)
    cost_price = Column(Numeric(12, 2), nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    tax_rules = relationship("ProductTax", back_populates="product", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="product")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_name = Column(String(100), nullable=False)   # e.g. "Brand"
    attribute_value = Column(String(100), nullable=False)  # e.g. "Odoo"
    price_extra = Column(Numeric(12, 2), nullable=False, default=0.0)  # e.g. +560.00
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    product = relationship("Product", back_populates="variants")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    billing_period = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly, yearly
    amount = Column(Numeric(12, 2), nullable=False)
    min_quantity = Column(Integer, nullable=False, default=1)
    available_from = Column(Date, nullable=False)
    available_to = Column(Date, nullable=True)
    
    # Behaviour flags per statement:
    auto_close = Column(Boolean, nullable=False, default=False)
    closable_early = Column(Boolean, nullable=False, default=False)
    pausable = Column(Boolean, nullable=False, default=False)
    renewable = Column(Boolean, nullable=False, default=False)
    
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    product = relationship("Product", back_populates="plans")
    subscriptions = relationship("Subscription", back_populates="plan")
    templates = relationship("QuotationTemplate", back_populates="plan")


class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    plan_id = Column(String(36), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    validity_days = Column(Integer, nullable=False, default=30)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    plan = relationship("Plan", back_populates="templates")
    lines = relationship("TemplateLine", back_populates="template", cascade="all, delete-orphan")


class TemplateLine(Base):
    __tablename__ = "template_lines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    template_id = Column(String(36), ForeignKey("quotation_templates.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    variant_id = Column(String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)

    template = relationship("QuotationTemplate", back_populates="lines")
    product = relationship("Product")
    variant = relationship("ProductVariant")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    number = Column(String(50), unique=True, nullable=False, index=True)  # SUB-XXXXX
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Status flow: Draft -> Quotation -> Confirmed -> Active -> Closed (or Paused)
    status = Column(String(30), nullable=False, default="draft", index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False, index=True)
    payment_terms_days = Column(Integer, nullable=False, default=30)
    
    # Idempotency anchor: tracks date through which subscription has been invoiced
    billed_through = Column(Date, nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    customer = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    lines = relationship("SubscriptionLine", back_populates="subscription", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="subscription")

    __table_args__ = (
        Index("idx_sub_status_billed", "status", "billed_through"),
    )


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    variant_id = Column(String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=False, default=0.0)  # combined tax percentage snapshot
    line_total = Column(Numeric(12, 2), nullable=False)

    subscription = relationship("Subscription", back_populates="lines")
    product = relationship("Product")
    variant = relationship("ProductVariant")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    number = Column(String(50), unique=True, nullable=False, index=True)  # INV-XXXXX
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Status flow: Draft -> Confirmed -> Paid, plus Cancelled
    status = Column(String(30), nullable=False, default="draft", index=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    subtotal = Column(Numeric(12, 2), nullable=False, default=0.0)
    tax_total = Column(Numeric(12, 2), nullable=False, default=0.0)
    discount_total = Column(Numeric(12, 2), nullable=False, default=0.0)
    total = Column(Numeric(12, 2), nullable=False, default=0.0)
    payment_terms_days = Column(Integer, nullable=False, default=30)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    subscription = relationship("Subscription", back_populates="invoices")
    customer = relationship("User", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    discounts = relationship("InvoiceDiscount", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    # Double billing guard at DB level:
    __table_args__ = (
        UniqueConstraint("subscription_id", "period_start", name="uq_invoice_sub_period_start"),
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    variant_id = Column(String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    subtotal = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("Product")
    variant = relationship("ProductVariant")


class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)  # fixed, percentage
    value = Column(Numeric(12, 2), nullable=False)
    scope = Column(String(20), nullable=False, default="subscription", index=True)  # product, subscription
    min_purchase_amount = Column(Numeric(12, 2), nullable=True)
    min_quantity = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    usage_limit = Column(Integer, nullable=True)  # None = unlimited
    usage_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    products = relationship("DiscountProduct", back_populates="discount_rule", cascade="all, delete-orphan")


class DiscountProduct(Base):
    __tablename__ = "discount_products"

    discount_rule_id = Column(String(36), ForeignKey("discount_rules.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)

    discount_rule = relationship("DiscountRule", back_populates="products")
    product = relationship("Product")


class InvoiceDiscount(Base):
    __tablename__ = "invoice_discounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    discount_rule_id = Column(String(36), ForeignKey("discount_rules.id", ondelete="RESTRICT"), nullable=False)
    description = Column(String(500), nullable=False)
    type = Column(String(20), nullable=False)  # fixed, percentage
    value = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="discounts")
    discount_rule = relationship("DiscountRule")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    method = Column(String(50), nullable=False)  # bank_transfer, credit_card, cash, check, other
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(Date, nullable=False, index=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    invoice = relationship("Invoice", back_populates="payments")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(50), nullable=False, index=True)  # subscription, invoice, payment, etc.
    entity_id = Column(String(36), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # created, status_change, payment_recorded, etc.
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    user_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

