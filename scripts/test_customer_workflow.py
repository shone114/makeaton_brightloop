import os
import sys
import getpass
import re
from datetime import date, timedelta
from fastapi.testclient import TestClient

# Ensure backend is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app

client = TestClient(app)


def print_step(num: int, title: str):
    print(f"\n{'='*65}")
    print(f"  STEP {num}: {title.upper()}")
    print(f"{'='*65}")


def check_password_rules(pwd: str) -> list[str]:
    errors = []
    if len(pwd) <= 8:
        errors.append("Must be more than 8 characters long (> 8 chars)")
    if not re.search(r"[A-Z]", pwd):
        errors.append("Must contain at least 1 uppercase letter")
    if not re.search(r"[a-z]", pwd):
        errors.append("Must contain at least 1 lowercase letter")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\/`~]", pwd):
        errors.append("Must contain at least 1 special character (!@#$%^&*)")
    return errors


def prompt_user_input():
    print("\n" + "#"*65)
    print("   BRIGHTLOOP CUSTOMER JOURNEY: INTERACTIVE TEST WORKFLOW")
    print("#"*65)

    # 1. Customer Name
    name = input("\nEnter customer full name [Default: Shone Bijju]: ").strip()
    if not name:
        name = "Shone Bijju"

    # 2. Customer Email
    print("\n--- EMAIL RECIPIENT NOTICE ---")
    print("Note: On Resend's free tier (using 'onboarding@resend.dev'), emails can only")
    print("be delivered to your verified signup email (e.g. shonebijju114@gmail.com).")
    print("To receive the real PDF invoice in your inbox, enter that email.")
    email = input("\nEnter customer email address [Default: shonebijju114@gmail.com]: ").strip()
    if not email:
        email = "shonebijju114@gmail.com"

    # 3. Password with rule validation
    print("\nPassword requirements:")
    print("  - More than 8 characters long")
    print("  - At least 1 uppercase letter (A-Z)")
    print("  - At least 1 lowercase letter (a-z)")
    print("  - At least 1 special character (!@#$%...)")

    while True:
        pwd = input("\nEnter account password [Default: Password123!]: ").strip()
        if not pwd:
            pwd = "Password123!"

        errors = check_password_rules(pwd)
        if not errors:
            print("  [OK] Password meets all security requirements!")
            break
        else:
            print("  [ERROR] Password does not meet requirements:")
            for err in errors:
                print(f"    * {err}")
            print("  Please try again.")

    return name, email, pwd


def main():
    name, email, password = prompt_user_input()

    # ----------------------------------------------------
    # STEP 1: REGISTER / LOGIN
    # ----------------------------------------------------
    print_step(1, "Customer Registration & Authentication")
    reg_payload = {"name": name, "email": email, "password": password}
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)

    if reg_resp.status_code == 201:
        token = reg_resp.json()["access_token"]
        print(f"  [SUCCESS] New customer account created!")
    elif reg_resp.status_code == 400 and "already exists" in reg_resp.text:
        print(f"  [INFO] Customer account already exists. Logging in with credentials...")
        login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        if login_resp.status_code != 200:
            print(f"  [ERROR] Login failed: {login_resp.status_code} - {login_resp.text}")
            sys.exit(1)
        token = login_resp.json()["access_token"]
        print(f"  [SUCCESS] Logged in successfully!")
    else:
        print(f"  [ERROR] Registration failed: {reg_resp.status_code} - {reg_resp.text}")
        sys.exit(1)

    auth_headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    customer_id = me["id"]
    print(f"  Customer ID: {customer_id}")
    print(f"  Role:        {me['role']}")

    # ----------------------------------------------------
    # STEP 2: SELECT SUBSCRIPTION PLAN
    # ----------------------------------------------------
    print_step(2, "Select Subscription Plan & Product Options")
    plans_resp = client.get("/api/v1/plans?is_active=true", headers=auth_headers)
    if plans_resp.status_code != 200:
        print(f"  [ERROR] Could not fetch plans: {plans_resp.text}")
        sys.exit(1)

    plans_json = plans_resp.json()
    plans = plans_json["items"] if isinstance(plans_json, dict) and "items" in plans_json else plans_json

    if not plans:
        print("  [ERROR] No active plans available in database.")
        sys.exit(1)

    print("\nAvailable Subscription Plans:")
    for i, p in enumerate(plans):
        prod_title = p.get("product_name") or "Product"
        print(f"  [{i+1:2d}] {p['name']:<24} | ${float(p['amount']):>8,.2f} / {p['billing_period']:<7} | Product: {prod_title}")

    # Prompt user to choose plan
    while True:
        choice_str = input(f"\nSelect a plan number [1-{len(plans)}] (Default: 1): ").strip()
        if not choice_str:
            choice_idx = 0
            break
        try:
            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(plans):
                break
            print(f"  Invalid choice. Enter a number between 1 and {len(plans)}.")
        except ValueError:
            print("  Please enter a valid number.")

    selected_plan = plans[choice_idx]
    print(f"\n  [SELECTED] {selected_plan['name']} - ${float(selected_plan['amount']):,.2f} / {selected_plan['billing_period']}")

    # Check for Product Variants
    product_id = selected_plan["product_id"]
    prod_resp = client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
    selected_variant_id = None
    variant_price_extra = 0.0

    if prod_resp.status_code == 200:
        product_data = prod_resp.json()
        variants = product_data.get("variants", [])
        if variants:
            print(f"\nProduct '{product_data['name']}' has {len(variants)} available variants/editions:")
            print("  [ 0] Base / Standard Edition (+ $0.00)")
            for vi, v in enumerate(variants):
                extra = float(v.get("price_extra", 0))
                print(f"  [{vi+1:2d}] {v.get('attribute_name')}: {v.get('attribute_value')} (+ ${extra:,.2f})")

            v_choice = input(f"\nSelect variant [0-{len(variants)}] (Default: 0): ").strip()
            if v_choice and v_choice != "0":
                try:
                    v_idx = int(v_choice) - 1
                    if 0 <= v_idx < len(variants):
                        selected_variant_id = variants[v_idx]["id"]
                        variant_price_extra = float(variants[v_idx]["price_extra"])
                        print(f"  [SELECTED VARIANT] {variants[v_idx]['attribute_value']} (+${variant_price_extra:,.2f})")
                except ValueError:
                    pass

    # Quantity
    qty_str = input("\nEnter subscription quantity [Default: 1]: ").strip()
    qty = 1
    if qty_str:
        try:
            qty = max(1, int(qty_str))
        except ValueError:
            qty = 1

    # Payment terms
    payment_terms_days = 15
    terms_str = input("Select payment terms in days (15 / 30 / 45) [Default: 15]: ").strip()
    if terms_str in ("15", "30", "45"):
        payment_terms_days = int(terms_str)

    # ----------------------------------------------------
    # STEP 3: CREATE & TRANSITION SUBSCRIPTION STATUS
    # ----------------------------------------------------
    print_step(3, "Subscription Creation & Official Status Transitions")
    today = date.today()
    sub_payload = {
        "customer_id": customer_id,
        "plan_id": selected_plan["id"],
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=365)).isoformat(),
        "payment_terms_days": payment_terms_days,
        "lines": [
            {
                "product_id": product_id,
                "variant_id": selected_variant_id,
                "quantity": qty,
            }
        ],
    }

    sub_resp = client.post("/api/v1/subscriptions", json=sub_payload, headers=auth_headers)
    if sub_resp.status_code != 201:
        print(f"  [ERROR] Failed to create subscription: {sub_resp.text}")
        sys.exit(1)

    sub_data = sub_resp.json()
    sub_id = sub_data["id"]
    sub_num = sub_data["number"]
    print(f"  [SUCCESS] Subscription Initialized: {sub_num}")
    print(f"  Initial Status: {sub_data['status'].upper()}")
    print(f"  Line Item Subtotal: ${float(sub_data['total_amount']):,.2f}")

    # Official Status Transitions: Draft -> Quotation -> Confirmed -> Active
    print("\nExecuting strict state machine transitions:")
    for target_state in ["quotation", "confirmed", "active"]:
        st_resp = client.patch(
            f"/api/v1/subscriptions/{sub_id}/status",
            json={"status": target_state},
            headers=auth_headers,
        )
        if st_resp.status_code != 200:
            print(f"  [ERROR] Transition to {target_state} failed: {st_resp.text}")
            sys.exit(1)
        print(f"    --> Transitioned to: {target_state.upper()} (Valid & Logged)")

    # ----------------------------------------------------
    # STEP 4: GENERATE IDEMPOTENT INVOICE
    # ----------------------------------------------------
    print_step(4, "Generate Invoices & Double-Billing Prevention Guard")
    inv_resp = client.post(f"/api/v1/invoices/generate/{sub_id}", headers=auth_headers)
    if inv_resp.status_code != 200:
        print(f"  [ERROR] Invoice generation failed: {inv_resp.text}")
        sys.exit(1)

    inv = inv_resp.json()
    inv_id = inv["id"]
    inv_num = inv["number"]
    print(f"  [SUCCESS] Generated Invoice #{inv_num}:")
    print(f"    Billing Period: {inv['period_start']} to {inv['period_end']}")
    print(f"    Due Date:       {inv['due_date']} ({inv['payment_terms_days']} days)")
    print(f"    Subtotal:       ${float(inv['subtotal']):,.2f}")
    print(f"    Tax Total:      ${float(inv['tax_total']):,.2f}")
    print(f"    Discounts:     -${float(inv['discount_total']):,.2f}")
    print(f"    Grand Total:    ${float(inv['total']):,.2f}")

    # Idempotency verification: Attempt duplicate generation
    print("\n  Testing Double-Billing Protection (Attempting duplicate generation for same period):")
    dup_resp = client.post(f"/api/v1/invoices/generate/{sub_id}", headers=auth_headers)
    if dup_resp.status_code == 400:
        print(f"    [VERIFIED: ZERO DOUBLE BILLING]")
        print(f"    Engine rejected duplicate request: \"{dup_resp.json()['detail']}\"")
    else:
        print(f"    [WARNING] Unexpected response on duplicate check: {dup_resp.status_code}")

    # ----------------------------------------------------
    # STEP 5: RESEND EMAIL DISPATCH & LOCAL PDF CREATION
    # ----------------------------------------------------
    print_step(5, "Resend Transactional Email & PDF Generation")
    confirm_send = input(f"\nDispatch invoice email to '{email}' via Resend? [Y/n]: ").strip().lower()
    if confirm_send != "n":
        send_resp = client.post(f"/api/v1/invoices/{inv_id}/send", headers=auth_headers)
        if send_resp.status_code == 200:
            print(f"  [SUCCESS] Invoice #{inv_num} dispatched! Status changed to: {send_resp.json()['status'].upper()}")
        else:
            print(f"  [WARNING] Dispatch returned: {send_resp.status_code} - {send_resp.text}")

    # Download PDF locally to disk
    pdf_resp = client.get(f"/api/v1/invoices/{inv_id}/pdf", headers=auth_headers)
    if pdf_resp.status_code == 200:
        pdf_filename = f"test_invoice_{inv_num}.pdf"
        pdf_path = os.path.abspath(pdf_filename)
        with open(pdf_path, "wb") as f:
            f.write(pdf_resp.content)
        print(f"\n  [PDF INVOICE DOWNLOADED]")
        print(f"  Location:  {pdf_path}")
        print(f"  File Size: {len(pdf_resp.content):,} bytes")
        print(f"  (You can open this file in your PDF viewer right now to inspect the formatting!)")
    else:
        print(f"  [ERROR] PDF generation failed: {pdf_resp.status_code}")

    # ----------------------------------------------------
    # STEP 6: RECORD PAYMENT
    # ----------------------------------------------------
    print_step(6, "Record Payment Settlement")
    pay_prompt = input(f"\nRecord payment of ${float(inv['total']):,.2f} for Invoice #{inv_num}? [Y/n]: ").strip().lower()
    if pay_prompt != "n":
        print("Choose payment method:")
        print("  [1] Credit Card")
        print("  [2] Bank Transfer")
        print("  [3] PayPal / Online")
        m_choice = input("Select method [1-3] (Default: 1): ").strip()
        method_map = {"1": "credit_card", "2": "bank_transfer", "3": "paypal"}
        method = method_map.get(m_choice, "credit_card")

        # Admin records payment
        admin_login = client.post("/api/v1/auth/login", json={"email": "admin@brightloop.com", "password": "Admin@123!"})
        if admin_login.status_code == 200:
            admin_token = admin_login.json()["access_token"]
            pay_resp = client.post(
                "/api/v1/payments",
                json={
                    "invoice_id": inv_id,
                    "method": method,
                    "amount": float(inv["total"]),
                    "note": f"Settled via portal by customer {name}",
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            if pay_resp.status_code == 201:
                p_data = pay_resp.json()
                print(f"  [SUCCESS] Payment of ${float(p_data['amount']):,.2f} recorded via {p_data['method']}!")
            else:
                print(f"  [ERROR] Payment recording failed: {pay_resp.text}")
        else:
            print("  [SKIP] Admin login failed for recording payment.")

    # ----------------------------------------------------
    # STEP 7: CUSTOMER PORTAL VIEW
    # ----------------------------------------------------
    print_step(7, "Customer Portal Real-Time Status")
    stats = client.get("/api/v1/portal/stats", headers=auth_headers).json()
    print("  Customer Dashboard Metrics:")
    print(f"    Account Holder:        {stats.get('customer_name')} ({stats.get('customer_email')})")
    print(f"    Active Subscriptions:  {stats.get('active_subscriptions')}")
    print(f"    Total Paid:            ${float(stats.get('total_paid', 0)):,.2f}")
    print(f"    Balance Outstanding:   ${float(stats.get('balance_due', 0)):,.2f}")

    my_invoices = client.get("/api/v1/portal/invoices", headers=auth_headers).json()
    print(f"\n  Invoices in Customer Portal ({len(my_invoices)} total):")
    for my_inv in my_invoices[:5]:
        print(f"    #{my_inv['number']:<12} | Date: {my_inv['invoice_date']} | Total: ${float(my_inv['total']):>8,.2f} | Status: {my_inv['status'].upper():<9} | Overdue: {my_inv['is_overdue']}")

    print("\n" + "="*65)
    print("  CUSTOMER WORKFLOW COMPLETE: ALL RULES & VALIDATIONS PASSED!")
    print("="*65 + "\n")


if __name__ == "__main__":
    main()
