# Brightloop Software — Backend API & Integration Context


---

## 1. Authentication & Role-Based Access Control (RBAC)

All endpoints (except `/auth/register` and `/auth/login`) require a Bearer token in the request header:
```http
Authorization: Bearer <access_token>
```

### User Roles & Permissions Matrix
| Feature / Route | Admin (`role: "admin"`) | Staff (`role: "staff"`) | Customer (`role: "customer"`) |
| :--- | :---: | :---: | :---: |
| **Finance Dashboard (MRR, ARR, Overdue)** | Full Access | Full Access | No (403) |
| **Manage Tax Rules (`/taxes`)** | Create, Update, Delete | Read Only | No (403) |
| **Manage Discount Rules (`/discounts`)** | Create, Update, Delete | Read Only | No (403) |
| **Manage Products & Plans** | Create, Update | Create, Update | Read Only (Active only) |
| **Manage Subscriptions (Any Customer)** | Full Access | Full Access | No (Own account only) |
| **Generate Bulk Invoices** | Full Access | Full Access | No (403) |
| **Record Payments** | Full Access | Full Access | No (403) |
| **Customer Portal (`/portal/*`)** | Admin View | Staff View | Full Access (Self-Service) |
| **Audit Logs (`/audit`)** | Full Access | Full Access | No (403) |
| **Export Data (CSV / Excel)** | Full Access | Full Access | No (403) |

### Pre-Seeded Demo Logins
For immediate testing without manual signup:
- **Admin:** `admin@brightloop.com` / `Admin@123!`
- **Staff:** `staff@brightloop.com` / `Staff@123!`
- **Customer:** `customer@brightloop.com` / `Cust@1234!`

---

## 2. API Endpoints Reference

### 2.1 Authentication (`/auth`)

#### `POST /auth/register`
Registers a new customer account.
- **Request Body:**
  ```json
  {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "password": "Password123!"
  }
  ```
  *Password Validation Rule:* Length > 8 characters, at least 1 uppercase, 1 lowercase, and 1 special character.
- **Response (201 Created):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": "uuid-here",
      "name": "Jane Doe",
      "email": "jane@example.com",
      "role": "customer",
      "is_active": true,
      "created_at": "2026-10-31T09:00:00Z"
    }
  }
  ```

#### `POST /auth/login`
- **Request Body:**
  ```json
  {
    "email": "admin@brightloop.com",
    "password": "Admin@123!"
  }
  ```
- **Response (200 OK):** Same `TokenResponse` as register.

#### `GET /auth/me`
Fetches current logged-in user profile.
- **Response (200 OK):**
  ```json
  {
    "id": "uuid-here",
    "name": "Alice Admin",
    "email": "admin@brightloop.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-10-31T09:00:00Z"
  }
  ```

---

### 2.2 Executive Dashboard & Finance Analytics (`/dashboard`)
*Access: Admin, Staff*

#### `GET /dashboard/stats`
Returns aggregated business metrics calculated server-side in under 100ms.
- **Response (200 OK):**
  ```json
  {
    "mrr": 58450.00,
    "arr": 701400.00,
    "active_subscriptions": 1470,
    "total_paid_revenue": 1845200.50,
    "unpaid_invoices_count": 84,
    "unpaid_invoices_amount": 95200.00,
    "overdue_invoices_count": 28,
    "overdue_invoices_amount": 34100.00,
    "revenue_by_period": {
      "monthly": 45200.00,
      "yearly": 12000.00,
      "weekly": 850.00,
      "daily": 400.00
    },
    "subscriptions_by_status": {
      "active": 1470,
      "confirmed": 210,
      "quotation": 105,
      "draft": 105,
      "closed": 147,
      "paused": 63
    }
  }
  ```

---

### 2.3 Products & Variants (`/products`)

#### `GET /products`
- **Query Params:** `?type=software|addon|service&is_active=true&page=1&page_size=25`
- **Response (200 OK):**
  ```json
  {
    "items": [
      {
        "id": "prod-uuid-1",
        "name": "Brightloop CRM",
        "type": "software",
        "sales_price": 1200.00,
        "cost_price": 400.00,
        "notes": "Full CRM suite with pipeline tracking.",
        "is_active": true,
        "variants": [
          {
            "id": "var-uuid-1",
            "attribute_name": "Brand",
            "attribute_value": "Odoo Integration Edition",
            "price_extra": 560.00
          },
          {
            "id": "var-uuid-2",
            "attribute_name": "Tier",
            "attribute_value": "Enterprise Multi-tenant",
            "price_extra": 1200.00
          }
        ],
        "taxes": [
          {
            "id": "tax-uuid-1",
            "name": "GST",
            "rate": 18.0
          }
        ]
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 25,
    "pages": 1
  }
  ```

---

### 2.4 Billing Plans (`/plans`)

#### `GET /plans`
- **Query Params:** `?billing_period=daily|weekly|monthly|yearly&is_active=true`
- **Response (200 OK):**
  ```json
  {
    "items": [
      {
        "id": "plan-uuid-1",
        "name": "CRM Monthly",
        "product_id": "prod-uuid-1",
        "product_name": "Brightloop CRM",
        "billing_period": "monthly",
        "amount": 1200.00,
        "min_quantity": 1,
        "available_from": "2025-01-01",
        "available_to": "2030-12-31",
        "closable_early": true,
        "pausable": true,
        "auto_close": false,
        "renewable": false,
        "is_active": true
      }
    ],
    "total": 14,
    "page": 1,
    "page_size": 25,
    "pages": 1
  }
  ```

---

### 2.5 Subscriptions (`/subscriptions`)

#### Status Machine Rules
The subscription status must strictly follow this flow:
```
Draft ──> Quotation ──> Confirmed ──> Active ──> Paused / Closed
```
- **Draft &rarr; Quotation:** Subscription must have at least 1 line item.
- **Quotation &rarr; Confirmed:** Customer accepts terms.
- **Confirmed &rarr; Active:** Starts service / activates recurring billing.
- **Active &rarr; Paused:** Only if plan allows `pausable: true`.
- **Active &rarr; Closed:** Can be closed early only if plan allows `closable_early: true`, or when term ends (`auto_close: true`).

#### `GET /subscriptions`
- **Query Params:** `?status=active&search=Acme&page=1&page_size=25`
- **Response (200 OK):**
  ```json
  {
    "items": [
      {
        "id": "sub-uuid-1",
        "number": "SUB-00042",
        "customer_id": "cust-uuid-1",
        "customer_name": "Acme Corp Client 5",
        "customer_email": "customer5@example.com",
        "plan_id": "plan-uuid-1",
        "plan_name": "CRM Monthly",
        "billing_period": "monthly",
        "status": "active",
        "start_date": "2026-01-01",
        "end_date": "2027-01-01",
        "payment_terms_days": 15,
        "billed_through": "2026-03-31",
        "total_amount": 1416.00,
        "lines": [
          {
            "id": "line-uuid-1",
            "product_id": "prod-uuid-1",
            "product_name": "Brightloop CRM",
            "variant_id": "var-uuid-1",
            "variant_label": "Brand: Odoo Integration Edition (+560.00)",
            "quantity": 1,
            "unit_price": 1760.00,
            "tax_rate": 18.0,
            "line_total": 2076.80
          }
        ]
      }
    ],
    "total": 2100,
    "page": 1,
    "page_size": 25,
    "pages": 84
  }
  ```

#### `POST /subscriptions`
Creates a new subscription in `draft` status.
- **Request Body:**
  ```json
  {
    "customer_id": "cust-uuid-1",
    "plan_id": "plan-uuid-1",
    "start_date": "2026-11-01",
    "end_date": "2027-11-01",
    "payment_terms_days": 15,
    "lines": [
      {
        "product_id": "prod-uuid-1",
        "variant_id": "var-uuid-1",
        "quantity": 1
      }
    ]
  }
  ```

#### `PATCH /subscriptions/{id}/status`
Transitions the subscription status.
- **Request Body:**
  ```json
  {
    "status": "quotation" 
  }
  ```
  *(Allowed values: `"quotation"`, `"confirmed"`, `"active"`, `"paused"`, `"closed"`)*

---

### 2.6 Invoices (`/invoices`)

#### `GET /invoices`
- **Query Params:** `?status=draft|confirmed|paid|cancelled&is_overdue=true&page=1&page_size=25`
- **Response (200 OK):**
  ```json
  {
    "items": [
      {
        "id": "inv-uuid-1",
        "number": "INV-00128",
        "subscription_id": "sub-uuid-1",
        "subscription_number": "SUB-00042",
        "customer_id": "cust-uuid-1",
        "customer_name": "Acme Corp Client 5",
        "customer_email": "customer5@example.com",
        "status": "confirmed",
        "invoice_date": "2026-10-01",
        "due_date": "2026-10-16",
        "period_start": "2026-10-01",
        "period_end": "2026-10-31",
        "subtotal": 1760.00,
        "tax_total": 316.80,
        "discount_total": 176.00,
        "total": 1900.80,
        "paid_amount": 0.00,
        "balance_due": 1900.80,
        "is_overdue": true,
        "sent_at": "2026-10-01T10:00:00Z",
        "lines": [
          {
            "id": "inv-line-1",
            "product_name": "Brightloop CRM",
            "variant_label": "Brand: Odoo Integration Edition",
            "quantity": 1,
            "unit_price": 1760.00,
            "tax_rate": 18.0,
            "tax_amount": 316.80,
            "subtotal": 1760.00,
            "total": 2076.80
          }
        ],
        "discounts": [
          {
            "id": "disc-uuid-1",
            "description": "Volume Discount 10% (Percentage 10.0)",
            "discount_amount": 176.00
          }
        ]
      }
    ],
    "total": 7113,
    "page": 1,
    "page_size": 25,
    "pages": 285
  }
  ```

#### `POST /invoices/generate/{subscription_id}`
Generates the next invoice for an active subscription with **idempotent double-billing protection**.
- If called when an invoice is already billed through the current period, returns **HTTP 400 Bad Request** (`No invoice is currently due for this subscription, or subscription is not active.`).

#### `POST /invoices/generate-bulk`
*Staff / Admin only.* Iterates over all active subscriptions and generates catch-up invoices.
- **Response (200 OK):**
  ```json
  {
    "generated_count": 14,
    "skipped_count": 1456,
    "details": ["Generated INV-07114 for subscription SUB-00010"]
  }
  ```

#### `GET /invoices/{id}/pdf`
Downloads the official branded PDF invoice as `application/pdf`.
- Can be opened directly in an `<iframe>` or downloaded via `<a href="..." download>`.

#### `POST /invoices/{id}/send`
Dispatches the invoice with the PDF attached directly to the customer's email via **Resend**. Updates status to `confirmed`.

---

### 2.7 Payments (`/payments`)

#### `POST /payments`
*Staff / Admin only.* Records customer payment against an invoice.
- **Request Body:**
  ```json
  {
    "invoice_id": "inv-uuid-1",
    "method": "credit_card",
    "amount": 1900.80,
    "payment_date": "2026-10-31",
    "note": "Settled via customer portal"
  }
  ```
  *(Allowed methods: `"credit_card"`, `"bank_transfer"`, `"check"`, `"other"`)*
- When total payments equal or exceed invoice `total`, the invoice status automatically changes to `"paid"`.

---

### 2.8 Customer Self-Service Portal (`/portal`)
*Access: Customer role (returns only the logged-in customer's own data)*

#### `GET /portal/stats`
- **Response (200 OK):**
  ```json
  {
    "customer_name": "Charlie Customer",
    "customer_email": "customer@brightloop.com",
    "active_subscriptions": 2,
    "total_paid": 4500.00,
    "balance_due": 0.00
  }
  ```

#### `GET /portal/subscriptions`
Returns array of the logged-in customer's subscriptions.

#### `GET /portal/invoices`
Returns array of the logged-in customer's invoices with payment statuses and due dates.

---

### 2.9 Taxes & Discounts Management

#### `GET /taxes` & `POST /taxes` *(Admin only for create)*
- **POST Body:**
  ```json
  {
    "name": "State VAT",
    "rate": 14.5,
    "is_active": true
  }
  ```

#### `GET /discounts` & `POST /discounts` *(Admin only for create)*
- **POST Body:**
  ```json
  {
    "name": "Holiday Special 20% Off",
    "type": "percentage",
    "value": 20.0,
    "scope": "subscription",
    "min_purchase_amount": 500.0,
    "min_quantity": 1,
    "start_date": "2026-11-01",
    "end_date": "2026-12-31",
    "usage_limit": 500,
    "is_active": true
  }
  ```

---

### 2.10 Data Export & Audit Log

#### `GET /export/subscriptions?format=csv`
#### `GET /export/invoices?format=csv`
Downloads live report as a `.csv` spreadsheet.

#### `GET /audit`
*Staff / Admin only.* Returns chronological log of all changes:
```json
{
  "items": [
    {
      "id": "audit-uuid-1",
      "entity_type": "subscription",
      "entity_id": "sub-uuid-1",
      "action": "status_change",
      "old_value": {"status": "quotation"},
      "new_value": {"status": "confirmed"},
      "user_name": "Alice Admin",
      "created_at": "2026-10-31T09:15:00Z"
    }
  ],
  "total": 45
}
```

---

## 3. Recommended Frontend Page Hierarchy

```
/
├── login                   --> Tabs: Customer / Staff / Admin (with quick "Fill Demo Credentials" buttons)
├── register                --> Customer self-signup with live password rule badges
│
├── dashboard               --> (Admin & Staff) KPI cards (MRR, ARR, Overdue), Revenue Chart, Status Distribution
│
├── subscriptions
│   ├── page.tsx            --> Filterable table with status badges (Draft, Quotation, Confirmed, Active, Closed)
│   ├── new                 --> Quotation Builder (Customer picker, Plan picker, Variant selection, Add lines)
│   └── [id]                --> Subscription detail page (Action buttons: "Send Quote", "Confirm", "Generate Invoice", "Pause", "Close")
│
├── invoices
│   ├── page.tsx            --> Filterable invoice list (Overdue flag badge, Status: Draft/Confirmed/Paid)
│   └── [id]                --> Invoice detail (Line items breakdown, Tax summary, "Send PDF Email" button, "Record Payment" modal)
│
├── portal                  --> (Customer view) My Subscriptions, Invoices history, Download PDF, Outstanding balance
│
├── settings
│   ├── products            --> Product catalog with variant price extra management
│   ├── plans               --> Billing plan configuration (daily, weekly, monthly, yearly, flags)
│   ├── taxes               --> Tax rules table
│   └── discounts           --> Discount rules with usage counter & date windows
│
└── audit                   --> Searchable audit trail table
```

---



