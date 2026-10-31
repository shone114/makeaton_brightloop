import os
import sys
import random
import uuid
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models import (
    User,
    TaxRule,
    Product,
    ProductVariant,
    ProductTax,
    Plan,
    QuotationTemplate,
    TemplateLine,
    Subscription,
    SubscriptionLine,
    Invoice,
    InvoiceLine,
    InvoiceDiscount,
    DiscountRule,
    DiscountProduct,
    Payment,
    AuditLog,
)


def seed_database():
    print("Beginning Brightloop Database Seeding...")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. USERS
        print("Seeding Users...")
        admin = User(
            id=str(uuid.uuid4()),
            name="Alice Admin",
            email="admin@brightloop.com",
            password_hash=get_password_hash("Admin@123!"),
            role="admin",
            is_active=True,
        )
        staff = User(
            id=str(uuid.uuid4()),
            name="Sam Staff",
            email="staff@brightloop.com",
            password_hash=get_password_hash("Staff@123!"),
            role="staff",
            is_active=True,
        )
        demo_customer = User(
            id=str(uuid.uuid4()),
            name="Charlie Customer",
            email="customer@brightloop.com",
            password_hash=get_password_hash("Cust@1234!"),
            role="customer",
            is_active=True,
        )
        db.add_all([admin, staff, demo_customer])

        customer_users = [demo_customer]
        for i in range(1, 51):
            c_user = User(
                id=str(uuid.uuid4()),
                name=f"Acme Corp Client {i}",
                email=f"customer{i}@example.com",
                password_hash=get_password_hash("Test@1234!"),
                role="customer",
                is_active=True,
            )
            customer_users.append(c_user)
            db.add(c_user)

        db.flush()

        # 2. TAX RULES
        print("Seeding Tax Rules...")
        tax_gst = TaxRule(id=str(uuid.uuid4()), name="GST", rate=18.0, is_active=True)
        tax_service = TaxRule(id=str(uuid.uuid4()), name="Service Tax", rate=12.0, is_active=True)
        tax_zero = TaxRule(id=str(uuid.uuid4()), name="Zero Rate", rate=0.0, is_active=True)
        db.add_all([tax_gst, tax_service, tax_zero])
        db.flush()

        # 3. PRODUCTS & VARIANTS
        print("Seeding Products and Variants...")
        products_data = [
            {
                "name": "Brightloop CRM",
                "type": "software",
                "sales_price": 1200.0,
                "cost_price": 400.0,
                "notes": "Full CRM suite with pipeline tracking.",
                "tax": tax_gst,
                "variants": [
                    {"name": "Brand", "val": "Standard Edition", "extra": 0.0},
                    {"name": "Brand", "val": "Odoo Brand Integration", "extra": 560.0},
                    {"name": "Brand", "val": "Salesforce Sync", "extra": 890.0},
                ],
            },
            {
                "name": "Brightloop ERP",
                "type": "software",
                "sales_price": 2500.0,
                "cost_price": 800.0,
                "notes": "Enterprise Resource Planning and inventory management.",
                "tax": tax_gst,
                "variants": [
                    {"name": "Brand", "val": "Standard Core", "extra": 0.0},
                    {"name": "Brand", "val": "Odoo ERP Connector", "extra": 560.0},
                ],
            },
            {
                "name": "Brightloop HR",
                "type": "software",
                "sales_price": 800.0,
                "cost_price": 250.0,
                "notes": "Payroll, leave tracking, and employee profiles.",
                "tax": tax_gst,
                "variants": [],
            },
            {
                "name": "Brightloop POS",
                "type": "software",
                "sales_price": 600.0,
                "cost_price": 200.0,
                "notes": "Point of sale for retail stores and pop-ups.",
                "tax": tax_gst,
                "variants": [],
            },
            {
                "name": "Email Add-on",
                "type": "addon",
                "sales_price": 150.0,
                "cost_price": 30.0,
                "notes": "Transactional and broadcast email capacity.",
                "tax": tax_gst,
                "variants": [
                    {"name": "Tier", "val": "Standard 50k", "extra": 0.0},
                    {"name": "Tier", "val": "Enterprise 250k", "extra": 100.0},
                ],
            },
            {
                "name": "Storage Add-on",
                "type": "addon",
                "sales_price": 200.0,
                "cost_price": 50.0,
                "notes": "Encrypted cloud block storage.",
                "tax": tax_gst,
                "variants": [
                    {"name": "Size", "val": "100 GB", "extra": 0.0},
                    {"name": "Size", "val": "500 GB", "extra": 150.0},
                    {"name": "Size", "val": "1 TB", "extra": 400.0},
                ],
            },
            {
                "name": "API Access",
                "type": "addon",
                "sales_price": 500.0,
                "cost_price": 100.0,
                "notes": "Direct REST/GraphQL endpoints with 10k req/min.",
                "tax": tax_gst,
                "variants": [],
            },
            {
                "name": "Priority Support",
                "type": "addon",
                "sales_price": 300.0,
                "cost_price": 80.0,
                "notes": "24/7 dedicated Slack channel and phone hotline.",
                "tax": tax_gst,
                "variants": [],
            },
            {
                "name": "Implementation Service",
                "type": "service",
                "sales_price": 5000.0,
                "cost_price": 2000.0,
                "notes": "White-glove onboarding and data migration.",
                "tax": tax_service,
                "variants": [],
            },
            {
                "name": "Training Package",
                "type": "service",
                "sales_price": 1500.0,
                "cost_price": 500.0,
                "notes": "Comprehensive team certification workshops.",
                "tax": tax_service,
                "variants": [
                    {"name": "Delivery", "val": "Online Live", "extra": 0.0},
                    {"name": "Delivery", "val": "On-site Workshop", "extra": 1000.0},
                ],
            },
        ]

        created_products: list[Product] = []
        product_variants_map: dict[str, list[ProductVariant]] = {}

        for p_info in products_data:
            p = Product(
                id=str(uuid.uuid4()),
                name=p_info["name"],
                type=p_info["type"],
                sales_price=p_info["sales_price"],
                cost_price=p_info["cost_price"],
                notes=p_info["notes"],
                is_active=True,
            )
            db.add(p)
            created_products.append(p)
            db.flush()

            pt = ProductTax(product_id=p.id, tax_rule_id=p_info["tax"].id)
            db.add(pt)

            v_list = []
            for v_info in p_info["variants"]:
                pv = ProductVariant(
                    id=str(uuid.uuid4()),
                    product_id=p.id,
                    attribute_name=v_info["name"],
                    attribute_value=v_info["val"],
                    price_extra=v_info["extra"],
                )
                db.add(pv)
                v_list.append(pv)
            product_variants_map[p.id] = v_list

        db.flush()

        # 4. PLANS
        print("Seeding Plans...")
        crm_prod = created_products[0]
        erp_prod = created_products[1]
        hr_prod = created_products[2]
        pos_prod = created_products[3]
        email_prod = created_products[4]
        storage_prod = created_products[5]
        api_prod = created_products[6]
        support_prod = created_products[7]
        training_prod = created_products[9]

        plans_data = [
            {"name": "CRM Monthly", "prod": crm_prod, "period": "monthly", "amt": 1200.0, "early": True, "pause": True, "auto_close": False, "renew": False},
            {"name": "CRM Yearly", "prod": crm_prod, "period": "yearly", "amt": 12000.0, "early": False, "pause": False, "auto_close": True, "renew": True},
            {"name": "ERP Monthly", "prod": erp_prod, "period": "monthly", "amt": 2500.0, "early": True, "pause": True, "auto_close": False, "renew": False},
            {"name": "ERP Yearly", "prod": erp_prod, "period": "yearly", "amt": 25000.0, "early": False, "pause": False, "auto_close": True, "renew": True},
            {"name": "HR Monthly", "prod": hr_prod, "period": "monthly", "amt": 800.0, "early": True, "pause": False, "auto_close": False, "renew": False},
            {"name": "HR Yearly", "prod": hr_prod, "period": "yearly", "amt": 8000.0, "early": False, "pause": False, "auto_close": True, "renew": True},
            {"name": "POS Monthly", "prod": pos_prod, "period": "monthly", "amt": 600.0, "early": True, "pause": True, "auto_close": False, "renew": False},
            {"name": "Email Monthly", "prod": email_prod, "period": "monthly", "amt": 150.0, "early": True, "pause": True, "auto_close": False, "renew": False},
            {"name": "Storage Monthly", "prod": storage_prod, "period": "monthly", "amt": 200.0, "early": True, "pause": False, "auto_close": False, "renew": False},
            {"name": "API Weekly", "prod": api_prod, "period": "weekly", "amt": 125.0, "early": True, "pause": False, "auto_close": False, "renew": False},
            {"name": "API Daily", "prod": api_prod, "period": "daily", "amt": 20.0, "early": False, "pause": False, "auto_close": True, "renew": False},
            {"name": "Support Monthly", "prod": support_prod, "period": "monthly", "amt": 300.0, "early": True, "pause": True, "auto_close": False, "renew": False},
            {"name": "Training Yearly", "prod": training_prod, "period": "yearly", "amt": 1500.0, "early": False, "pause": False, "auto_close": True, "renew": True},
            {"name": "CRM Trial (Daily)", "prod": crm_prod, "period": "daily", "amt": 50.0, "early": False, "pause": False, "auto_close": True, "renew": False},
        ]

        created_plans: list[Plan] = []
        for p_info in plans_data:
            plan = Plan(
                id=str(uuid.uuid4()),
                name=p_info["name"],
                product_id=p_info["prod"].id,
                billing_period=p_info["period"],
                amount=p_info["amt"],
                min_quantity=1,
                available_from=date(2025, 1, 1),
                available_to=date(2030, 12, 31),
                closable_early=p_info["early"],
                pausable=p_info["pause"],
                auto_close=p_info["auto_close"],
                renewable=p_info["renew"],
                is_active=True,
            )
            db.add(plan)
            created_plans.append(plan)

        db.flush()

        # 5. DISCOUNT RULES
        print("Seeding Discount Rules...")
        disc_vol = DiscountRule(
            id=str(uuid.uuid4()),
            name="Volume Discount 10%",
            type="percentage",
            value=10.0,
            scope="subscription",
            min_quantity=5,
            start_date=date(2025, 1, 1),
            end_date=date(2030, 12, 31),
            is_active=True,
        )
        disc_early = DiscountRule(
            id=str(uuid.uuid4()),
            name="Early Bird $200 Off",
            type="fixed",
            value=200.0,
            scope="subscription",
            min_purchase_amount=2000.0,
            start_date=date(2025, 1, 1),
            end_date=date(2030, 12, 31),
            is_active=True,
        )
        disc_crm = DiscountRule(
            id=str(uuid.uuid4()),
            name="CRM Special 15%",
            type="percentage",
            value=15.0,
            scope="product",
            start_date=date(2025, 1, 1),
            end_date=date(2030, 12, 31),
            usage_limit=1000,
            usage_count=45,
            is_active=True,
        )
        db.add_all([disc_vol, disc_early, disc_crm])
        db.flush()

        dp = DiscountProduct(discount_rule_id=disc_crm.id, product_id=crm_prod.id)
        db.add(dp)

        # 6. QUOTATION TEMPLATES
        print("Seeding Quotation Templates...")
        t1 = QuotationTemplate(id=str(uuid.uuid4()), name="SMB Starter Kit", plan_id=created_plans[0].id, validity_days=30, is_active=True)
        t2 = QuotationTemplate(id=str(uuid.uuid4()), name="Enterprise Suite", plan_id=created_plans[3].id, validity_days=45, is_active=True)
        db.add_all([t1, t2])
        db.flush()

        t1_l1 = TemplateLine(template_id=t1.id, product_id=crm_prod.id, quantity=1, unit_price=1200.0)
        t1_l2 = TemplateLine(template_id=t1.id, product_id=email_prod.id, quantity=1, unit_price=150.0)
        
        odoo_var = product_variants_map[crm_prod.id][1]
        t2_l1 = TemplateLine(template_id=t2.id, product_id=erp_prod.id, quantity=1, unit_price=2500.0)
        t2_l2 = TemplateLine(template_id=t2.id, product_id=crm_prod.id, variant_id=odoo_var.id, quantity=2, unit_price=1760.0)
        t2_l3 = TemplateLine(template_id=t2.id, product_id=storage_prod.id, quantity=1, unit_price=350.0)
        db.add_all([t1_l1, t1_l2, t2_l1, t2_l2, t2_l3])
        db.flush()

        # 7. SCALE SEEDING: 2,100 SUBSCRIPTIONS & INVOICES
        print("Generating 2,100 Subscriptions, Invoices, and Payments...")
        today = date.today()

        statuses_pool = (
            ["active"] * 70 +
            ["confirmed"] * 10 +
            ["quotation"] * 5 +
            ["draft"] * 5 +
            ["closed"] * 7 +
            ["paused"] * 3
        )

        all_subscriptions = []
        all_sub_lines = []
        all_invoices = []
        all_inv_lines = []
        all_payments = []

        sub_seq = 1
        inv_seq = 1

        for i in range(2100):
            cust = random.choice(customer_users)
            plan = random.choice(created_plans)
            sub_status = random.choice(statuses_pool)

            days_back = random.randint(30, 420)
            start_dt = today - timedelta(days=days_back)
            end_dt = start_dt + timedelta(days=365)
            
            sub_id = str(uuid.uuid4())
            sub_num = f"SUB-{sub_seq:05d}"
            sub_seq += 1

            billed_thru = None
            if sub_status in ("active", "closed", "paused"):
                billed_days = random.randint(15, days_back)
                billed_thru = start_dt + timedelta(days=billed_days)

            sub = Subscription(
                id=sub_id,
                number=sub_num,
                customer_id=cust.id,
                plan_id=plan.id,
                status=sub_status,
                start_date=start_dt,
                end_date=end_dt,
                payment_terms_days=random.choice([15, 30, 45]),
                billed_through=billed_thru,
                created_at=datetime.combine(start_dt, datetime.min.time(), tzinfo=timezone.utc),
            )
            all_subscriptions.append(sub)

            prod = plan.product
            var = None
            price = float(prod.sales_price)
            if prod.id in product_variants_map and product_variants_map[prod.id]:
                if random.random() > 0.5:
                    var = random.choice(product_variants_map[prod.id])
                    price += float(var.price_extra)

            qty = random.randint(1, 3)
            tax_rate = 18.0 if prod.type in ("software", "addon") else 12.0
            line_sub = price * qty
            line_tot = line_sub + (line_sub * tax_rate / 100.0)

            s_line1 = SubscriptionLine(
                id=str(uuid.uuid4()),
                subscription_id=sub_id,
                product_id=prod.id,
                variant_id=var.id if var else None,
                quantity=qty,
                unit_price=price,
                tax_rate=tax_rate,
                line_total=round(line_tot, 2),
            )
            all_sub_lines.append(s_line1)

            if sub_status in ("active", "closed", "paused") and billed_thru:
                num_invoices = min(5, max(1, days_back // 30))
                for inv_idx in range(num_invoices):
                    inv_date = start_dt + timedelta(days=inv_idx * 30)
                    if inv_date > today:
                        break
                    
                    due_date = inv_date + timedelta(days=sub.payment_terms_days)
                    p_start = inv_date
                    p_end = p_start + timedelta(days=29)

                    if due_date < today:
                        inv_status = "paid" if random.random() < 0.75 else "confirmed"
                    else:
                        inv_status = random.choice(["draft", "confirmed"])

                    inv_id = str(uuid.uuid4())
                    inv_num = f"INV-{inv_seq:05d}"
                    inv_seq += 1

                    inv = Invoice(
                        id=inv_id,
                        number=inv_num,
                        subscription_id=sub_id,
                        customer_id=cust.id,
                        status=inv_status,
                        invoice_date=inv_date,
                        due_date=due_date,
                        period_start=p_start,
                        period_end=p_end,
                        subtotal=round(line_sub, 2),
                        tax_total=round(line_sub * tax_rate / 100.0, 2),
                        discount_total=0.0,
                        total=round(line_tot, 2),
                        payment_terms_days=sub.payment_terms_days,
                        sent_at=datetime.combine(inv_date, datetime.min.time(), tzinfo=timezone.utc),
                        created_at=datetime.combine(inv_date, datetime.min.time(), tzinfo=timezone.utc),
                    )
                    all_invoices.append(inv)

                    inv_line = InvoiceLine(
                        id=str(uuid.uuid4()),
                        invoice_id=inv_id,
                        product_id=prod.id,
                        variant_id=var.id if var else None,
                        description=f"{prod.name}{' (' + var.attribute_value + ')' if var else ''}",
                        quantity=qty,
                        unit_price=price,
                        tax_rate=tax_rate,
                        tax_amount=round(line_sub * tax_rate / 100.0, 2),
                        subtotal=round(line_sub, 2),
                        total=round(line_tot, 2),
                    )
                    all_inv_lines.append(inv_line)

                    if inv_status == "paid":
                        pay_dt = inv_date + timedelta(days=random.randint(1, sub.payment_terms_days))
                        if pay_dt > today:
                            pay_dt = today
                        payment = Payment(
                            id=str(uuid.uuid4()),
                            invoice_id=inv_id,
                            method=random.choice(["bank_transfer", "credit_card", "bank_transfer"]),
                            amount=round(line_tot, 2),
                            payment_date=pay_dt,
                            note=f"Payment received for {inv_num}",
                            created_at=datetime.combine(pay_dt, datetime.min.time(), tzinfo=timezone.utc),
                        )
                        all_payments.append(payment)

        print(f"Bulk inserting {len(all_subscriptions)} subscriptions...")
        db.bulk_save_objects(all_subscriptions)
        db.bulk_save_objects(all_sub_lines)
        db.commit()

        print(f"Bulk inserting {len(all_invoices)} invoices...")
        db.bulk_save_objects(all_invoices)
        db.bulk_save_objects(all_inv_lines)
        db.bulk_save_objects(all_payments)
        db.commit()

        admin_log = AuditLog(
            id=str(uuid.uuid4()),
            entity_type="system",
            entity_id=admin.id,
            action="system_seeded",
            new_value={"total_subscriptions": len(all_subscriptions), "total_invoices": len(all_invoices)},
            user_id=admin.id,
        )
        db.add(admin_log)
        db.commit()

        print(f"\n=======================================================")
        print(f"  BRIGHTLOOP DATABASE SEED COMPLETE!")
        print(f"  Subscriptions: {len(all_subscriptions)}")
        print(f"  Invoices:      {len(all_invoices)}")
        print(f"  Payments:      {len(all_payments)}")
        print(f"  Demo Logins:")
        print(f"    Admin:    admin@brightloop.com / Admin@123!")
        print(f"    Staff:    staff@brightloop.com / Staff@123!")
        print(f"    Customer: customer@brightloop.com / Cust@1234!")
        print(f"=======================================================\n")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
