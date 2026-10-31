import uuid
from datetime import date
from app.models import User, Plan, Product, TaxRule, ProductTax, Subscription, SubscriptionLine
from app.invoices.router import generate_invoice_for_subscription, compute_next_period


def test_compute_next_period_monthly():
    start = date(2026, 1, 15)
    p_start, p_end = compute_next_period(start, "monthly")
    assert p_start == date(2026, 1, 15)
    assert p_end == date(2026, 2, 14)


def test_compute_next_period_weekly():
    start = date(2026, 1, 1)
    p_start, p_end = compute_next_period(start, "weekly")
    assert p_start == date(2026, 1, 1)
    assert p_end == date(2026, 1, 7)


def test_compute_next_period_daily():
    start = date(2026, 1, 1)
    p_start, p_end = compute_next_period(start, "daily")
    assert p_start == date(2026, 1, 1)
    assert p_end == date(2026, 1, 1)


def test_invoice_generation_idempotency_no_double_billing(db_session):
    uid = uuid.uuid4().hex[:6]
    customer = User(
        name="Billing Test User",
        email=f"billingtest_{uid}@example.com",
        password_hash="fakehash",
        role="customer",
    )
    db_session.add(customer)
    db_session.flush()

    product = Product(
        name=f"Brightloop Pro Suite {uid}",
        type="software",
        sales_price=1000.0,
        cost_price=300.0,
    )
    db_session.add(product)
    db_session.flush()

    tax = TaxRule(name=f"GST Test {uid}", rate=18.0)
    db_session.add(tax)
    db_session.flush()

    db_session.add(ProductTax(product_id=product.id, tax_rule_id=tax.id))

    plan = Plan(
        name=f"Pro Monthly Test {uid}",
        product_id=product.id,
        billing_period="monthly",
        amount=1000.0,
        min_quantity=1,
        available_from=date(2025, 1, 1),
    )
    db_session.add(plan)
    db_session.flush()

    sub = Subscription(
        number=f"SUB-TEST-{uid}",
        customer_id=customer.id,
        plan_id=plan.id,
        status="active",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        payment_terms_days=30,
        billed_through=None,
    )
    db_session.add(sub)
    db_session.flush()

    sub_line = SubscriptionLine(
        subscription_id=sub.id,
        product_id=product.id,
        quantity=1,
        unit_price=1000.0,
        tax_rate=18.0,
        line_total=1180.0,
    )
    db_session.add(sub_line)
    db_session.commit()

    # First Invoice Generation (Should succeed)
    inv1 = generate_invoice_for_subscription(
        db_session,
        subscription_id=sub.id,
        invoice_date=date(2026, 1, 1),
    )
    assert inv1 is not None
    assert inv1.subtotal == 1000.0
    assert inv1.tax_total == 180.0
    assert inv1.total == 1180.0
    assert sub.billed_through == date(2026, 1, 31)
    db_session.commit()

    # Second Invoice Generation for SAME period (MUST BE PREVENTED - NO DOUBLE BILLING!)
    inv2 = generate_invoice_for_subscription(
        db_session,
        subscription_id=sub.id,
        invoice_date=date(2026, 1, 15),
    )
    assert inv2 is None  # Skipped!

    # Third Invoice Generation after period end (Next period: 2026-02-01)
    inv3 = generate_invoice_for_subscription(
        db_session,
        subscription_id=sub.id,
        invoice_date=date(2026, 2, 5),
    )
    assert inv3 is not None
    assert inv3.period_start == date(2026, 2, 1)
    assert inv3.period_end == date(2026, 2, 28)
    assert sub.billed_through == date(2026, 2, 28)
