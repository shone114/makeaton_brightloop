import uuid
from datetime import date
from app.models import User, Plan, Product, TaxRule, ProductTax, Subscription, SubscriptionLine, DiscountRule, DiscountProduct
from app.invoices.router import generate_invoice_for_subscription


def test_discount_auto_application_and_limits(db_session):
    uid = uuid.uuid4().hex[:6]
    customer = User(
        name="Discount Customer",
        email=f"discount_cust_{uid}@example.com",
        password_hash="fakehash",
        role="customer",
    )
    db_session.add(customer)
    db_session.flush()

    product = Product(
        name=f"Discounted SaaS Suite {uid}",
        type="software",
        sales_price=500.0,
        cost_price=100.0,
    )
    db_session.add(product)
    db_session.flush()

    plan = Plan(
        name=f"Discount Monthly {uid}",
        product_id=product.id,
        billing_period="monthly",
        amount=500.0,
        min_quantity=1,
        available_from=date(2025, 1, 1),
    )
    db_session.add(plan)
    db_session.flush()

    discount = DiscountRule(
        name=f"Special 20% Promo {uid}",
        type="percentage",
        value=20.0,
        scope="subscription",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        usage_limit=1,
        usage_count=0,
        is_active=True,
    )
    db_session.add(discount)
    db_session.flush()

    sub = Subscription(
        number=f"SUB-DISC-{uid}",
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
        unit_price=500.0,
        tax_rate=0.0,
        line_total=500.0,
    )
    db_session.add(sub_line)
    db_session.commit()

    # Invoice 1: Discount should auto-apply
    inv1 = generate_invoice_for_subscription(db_session, sub.id, date(2026, 1, 1))
    assert inv1 is not None
    assert inv1.subtotal == 500.0
    assert inv1.discount_total == 100.0
    assert inv1.total == 400.0
    assert discount.usage_count == 1
    db_session.commit()

    # Invoice 2: Next period, discount limit was 1, so discount should NOT apply
    inv2 = generate_invoice_for_subscription(db_session, sub.id, date(2026, 2, 1))
    assert inv2 is not None
    assert inv2.subtotal == 500.0
    assert inv2.discount_total == 0.0
    assert inv2.total == 500.0
