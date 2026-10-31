# Brightloop — Subscription Management API

Backend scaffold for the **Subscription Management System** brief: products and
variants, plans, quotation templates, subscriptions, automated invoicing, taxes,
discounts, payments and finance reporting — built with **FastAPI + SQLAlchemy 2 +
SQLite**.

The domain model follows the four scenes in the brief (signup, launching a plan,
billing day, discounts/payments/reporting) rather than a generic CRUD skeleton.

---

## Quickstart

```powershell
# from the repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# optional: customise settings (defaults work out of the box)
Copy-Item .env.example .env

uvicorn app.main:app --reload
```

* Swagger UI: <http://127.0.0.1:8000/docs>
* ReDoc: <http://127.0.0.1:8000/redoc>
* Health: <http://127.0.0.1:8000/health>

On first boot the app creates `brightloop.db` and seeds a demo month of data
(disable with `SEED_DEMO_DATA=false`).

### Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@brightloop.io` | `Admin@1234` |
| Staff (sales) | `sales@brightloop.io` | `Staff@1234` |
| Customer (Acme) | `billing@acme-retail.com` | `Customer@1234` |
| Customer (Northwind) | `finance@northwind.com` | `Customer@1234` |

### Try the billing month

```powershell
$token = (Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/auth/login `
  -ContentType 'application/json' `
  -Body '{"email":"admin@brightloop.io","password":"Admin@1234"}').token.access_token

$h = @{ Authorization = "Bearer $token" }

# finance view
Invoke-RestMethod http://127.0.0.1:8000/api/v1/reports/summary -Headers $h

# bill every due subscription (idempotent)
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/invoices/run-billing `
  -Headers $h -ContentType 'application/json' `
  -Body '{"as_of":"2026-10-31","auto_confirm":true}'
```

---

## Stack

| Concern | Choice |
| --- | --- |
| Web framework | FastAPI (sync SQLAlchemy sessions, async-ready) |
| ORM | SQLAlchemy 2.0 (`Mapped` / `mapped_column`) |
| Database | SQLite, WAL mode, foreign keys enforced |
| Validation | Pydantic v2 + pydantic-settings |
| Auth | JWT access tokens (PyJWT) + PBKDF2-SHA256 password hashing |
| Tests | pytest + FastAPI TestClient, in-memory SQLite |

Money is stored as **integer cents** through a `Money` type decorator and always
handled as `Decimal` in Python, so no float rounding drifts into invoices. Tax
rates are stored as basis points via a `Rate` decorator.

---

## Project layout

```
app/
  main.py                 app factory, lifespan, CORS, error handlers
  core/
    config.py             pydantic-settings (reads .env)
    security.py           hashing, password policy, JWT, reset tokens
    money.py              Decimal helpers + proportional allocation
  db/
    base.py               Base, Money/Rate types, utcnow, enum helper
    session.py            engine, session factory, get_db, SQLite PRAGMAs
    seed.py               demo data for one billing month
  models/                 user, product, plan, quotation, subscription,
                          discount, invoice
  schemas/                request/response models, pagination envelope
  services/
    subscriptions.py      state machine, line pricing, renewals
    billing.py            period math, discount engine, invoice run
    invoices.py           confirm/cancel/send, payments, printable HTML
    reporting.py          MRR, revenue series, overdue
    numbering.py          SUB/YYYY/NNNNN and INV/YYYY/NNNNN
    email.py              pluggable email seam (logs in dev)
  api/
    deps.py               auth, role guards, pagination, tenant scoping
    v1/                   routers: auth, users, customers, taxes, products,
                          plans, quotation-templates, discounts,
                          subscriptions, invoices, payments, reports
tests/                    auth, billing/discount/payment, lifecycle tests
```

---

## Domain model

```
Customer 1─* User            (portal logins; one email = one account)
Customer 1─* Subscription *─1 Plan *─1 Product 1─* ProductVariant
                        │           └─1 Tax
                        ├─* SubscriptionLine *─1 Product / Variant / Tax
                        ├─* SubscriptionDiscount *─1 Discount
                        └─1 QuotationTemplate

Subscription 1─* Invoice 1─* InvoiceLine
                        └─* Payment
Discount 1─* DiscountRedemption
```

Key fields:

* **Product** — name, type, sales/cost price, notes, default tax, variants with
  `price_delta` (e.g. *Odoo brand* adds 560).
* **Plan** — price, interval (`daily|weekly|monthly|yearly`), minimum quantity,
  availability window, and the four lifecycle switches (`auto_close_on_expiry`,
  `allow_early_close`, `allow_pause`, `allow_renew`). Those switches are
  **snapshotted** onto the subscription so changing a plan later does not
  rewrite history.
* **Subscription** — number, customer, plan, start/expiry dates, payment terms,
  lines, discount links, billing cursor (`current_period_start/end`,
  `next_billing_date`), and a full status history.
* **Invoice** — number, customer, period, totals (`subtotal`, `discount_total`,
  `tax_total`, `total`, `amount_paid`), status, and an `amount_due` / `is_overdue`
  pair derived from those numbers.
* **Payment** — method, amount, date, reference and note, always against an
  invoice.

Statuses: `draft → quotation → confirmed → active → paused → closed`, enforced by
a transition map in `app/models/subscription.py`. Closing early is refused when
the plan forbids it.

---

## How billing works

1. Activating a subscription anchors the cursor on its start date.
2. `POST /api/v1/invoices/run-billing` selects every **active** subscription with
   `next_billing_date <= as_of` and bills each period in order, looping so missed
   months are caught up (capped at 60 periods per run).
3. Invoice numbers and lines are generated from the subscription: customer,
   products, quantities, unit prices, tax rates, discounts and totals.
4. A unique constraint on `(subscription_id, period_start)` makes double billing
   impossible even under concurrent runs. `dry_run` lets you preview the run.
5. After invoicing, the cursor moves forward. When the next period would start
   after `expiry_date`, the subscription closes automatically if the plan allows
   it; otherwise billing stops and a human decides.

Amounts are calculated per line:

```
line_subtotal   = quantity × unit_price
line_discount   = discount rules matching the line (product or subscription scope)
line_tax        = (line_subtotal − line_discount) × tax_rate
line_total      = line_subtotal − line_discount + line_tax
invoice_total   = Σ line_total
```

* **Taxes** live on the product (or plan) and are copied onto subscription and
  invoice lines, so a rate change never rewrites past invoices.
* **Discounts** are created by admins only, then attached to a subscription.
  Every invoice re-checks the start/end dates, `min_purchase_amount`,
  `min_quantity` and `max_uses`. A use is consumed only when the invoice is
  confirmed; once the limit is reached the discount silently stops applying.
  Percentage and fixed amounts are both capped at the eligible subtotal.
* **Payments** can be partial; the invoice flips to `paid` when the sum of
  payments covers the total, and overpayments are rejected.

A single subscription can also be billed on demand:
`POST /api/v1/subscriptions/{id}/invoices`.

---

## API surface

All routes are under `/api/v1` and require a bearer token unless noted.

| Area | Endpoints |
| --- | --- |
| Auth | `POST /auth/register`, `/auth/login`, `/auth/token`, `/auth/forgot-password`, `/auth/reset-password`, `GET /auth/me`, `POST /auth/me/password` |
| Users | `GET /users`, `POST /users/staff` *(admin)*, `GET|PATCH /users/{id}` *(admin)* |
| Customers | `GET /customers`, `POST /customers`, `GET /customers/me`, `GET|PATCH /customers/{id}` |
| Taxes | `GET /taxes`, `POST|PATCH|DELETE /taxes/{id}` *(admin writes)* |
| Products | `GET|POST /products`, `GET|PATCH|DELETE /products/{id}`, `POST /products/{id}/variants`, `PATCH|DELETE /products/variants/{id}` |
| Plans | `GET|POST /plans`, `GET|PATCH|DELETE /plans/{id}` |
| Quotation templates | `GET|POST /quotation-templates`, `GET|DELETE /quotation-templates/{id}` *(staff)* |
| Discounts | `GET|POST /discounts`, `GET|PATCH|DELETE /discounts/{id}` *(admin writes)* |
| Subscriptions | `GET|POST /subscriptions`, `GET|PATCH /subscriptions/{id}`, `POST .../status`, `.../confirm`, `.../activate`, `.../pause`, `.../resume`, `.../close`, `.../renew`, `.../discounts`, `GET|POST .../invoices` |
| Invoices | `GET|POST /invoices`, `POST /invoices/run-billing`, `GET|PATCH /invoices/{id}`, `POST .../confirm`, `.../cancel`, `.../send`, `.../payments`, `GET .../print` |
| Payments | `GET /payments`, `GET /payments/{id}`, `GET /payments/{id}/invoice` |
| Reports | `GET /reports/summary`, `/reports/revenue?group_by=month|day`, `/reports/overdue` |

List endpoints accept `page` / `page_size` and return:

```json
{ "items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0 }
```

Useful filters: subscriptions by `status`, `customer_id`, `plan_id`,
`expiring_before`, `q` (number or customer name); invoices by `status`,
`overdue`, `date_from`/`date_to`, `subscription_id`, `q`.

---

## Access control

| Capability | Admin | Staff | Customer |
| --- | --- | --- | --- |
| Products, plans, taxes, discounts | write | read | read |
| Quotation templates | write | write | – |
| Staff management | ✔ | – | – |
| Customers, subscriptions, invoices | all | all | own records only |
| Record payments, billing run, reports | ✔ | ✔ | – |

* Passwords must be longer than 8 characters with upper, lower and special
  characters — checked in one place (`core.security`) and used by every schema.
* Customer-scoped data is filtered in the query **and** guarded per record, so a
  portal user cannot read another customer's subscription or invoice by ID.
* Password reset tokens are random, stored only as SHA-256 hashes, single-use and
  short-lived. Responses never reveal whether an email exists.
* Reset links are emailed through `services/email.py`, which logs to the console
  in dev. Swap in SMTP/SES/Postmark there.

> The scaffold returns the reset token in the response outside production so you
> can test the flow without a mail server.

---

## Tests

```powershell
python -m pytest
```

22 tests cover the parts that are easy to get wrong:

* password policy, signup/login, duplicate emails, reset-token single use,
  user enumeration;
* invoice generation with taxes, billing-run idempotency, catch-up of missed
  periods, dry runs;
* discount auto-application and `max_uses` exhaustion;
* partial → full payments, overpayment and draft-invoice rejection;
* the subscription state machine, minimum quantities, variant pricing, renewals,
  quotation templates;
* customer tenant isolation and admin-only endpoints;
* overdue reporting and MRR/ARR math.

---

## Production checklist

This is a scaffold, so a few seams are deliberately simple:

1. **Migrations** — replace `create_all` with Alembic before the schema changes
   in production. `alembic init` + autogenerate against these models is enough.
2. **Scheduling** — call `run_billing` from a scheduler (APScheduler, cron,
   Celery beat) once a day; it is idempotent, so retries are safe.
3. **Email** — implement `send_email` against a real provider.
4. **PDF** — `/invoices/{id}/print` returns HTML; pipe it through WeasyPrint or a
   browserless renderer when you need attachments.
5. **Scale** — SQLite is fine for thousands of subscriptions (WAL, indexed
   filters, capped pagination). For concurrency beyond a single writer, point
   `DATABASE_URL` at PostgreSQL; the SQL is portable.
6. **Hardening** — JWT refresh tokens and revocation, login rate limiting,
   audit log for admin actions, multi-currency, proration on mid-cycle plan
   changes, and dunning (retry/reminder schedules).
