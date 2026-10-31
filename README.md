# Brightloop

Brightloop is a full-stack subscription billing system built for the Odoo
hackathon brief. It covers the catalogue, plans, quotations, subscription
lifecycle, recurring invoices, taxes, discounts, payments, finance reporting and
a customer self-service portal.

The backend is FastAPI + SQLAlchemy 2 + SQLite. The frontend is SvelteKit 5 with
Svelte runes, Tailwind CSS and a static SPA build served by FastAPI.

## Quick start

Prerequisites: Python 3.11+, Node.js 20+.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend ci
```

### One command demo

```powershell
.\scripts\demo.ps1
```

This builds the frontend, starts FastAPI and serves the app at
<http://127.0.0.1:8000>. Add `-SkipBuild` to reuse the existing frontend build.

### Development mode

Run the API and Vite in separate terminals:

```powershell
# terminal 1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# terminal 2
npm --prefix frontend run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to the backend on port 8000.
Swagger remains available at <http://127.0.0.1:8000/docs>.

On first boot the app creates `brightloop.db` and seeds a demo catalogue,
customers, subscriptions and billing history. Set `SEED_DEMO_DATA=false` to
disable it.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@brightloop.io` | `Admin@1234` |
| Staff | `sales@brightloop.io` | `Staff@1234` |
| Customer (Acme) | `billing@acme-retail.com` | `Customer@1234` |
| Customer (Northwind) | `finance@northwind.com` | `Customer@1234` |

Admin sees the full workspace. Staff gets the same operational screens without
staff-management access. Customers only see their own subscriptions, invoices
and payments.

## Demo walkthrough

1. Sign in as the admin and open **Invoices**.
2. Choose **Run billing**.
3. Select **Next 30 days**, then **Preview**. The preview is a dry run and writes
   nothing.
4. Keep **Issue invoices immediately** enabled and choose **Run billing**.
5. Open one of the generated invoices and record a full or partial payment.
6. Sign out and sign in as the Acme customer to see the same invoice in the
   portal.
7. Sign in as staff to confirm the operational workspace and restricted
   staff-management access.

The seeded dataset is already billed through roughly the current date, so
running billing for today may legitimately produce zero invoices. Use a future
date to demonstrate the next billing cycle.

## Billing behavior

- `POST /api/v1/invoices/run-billing` selects active subscriptions whose
  `next_billing_date` is on or before `as_of`.
- Each due period is invoiced once. Missed periods are caught up in order, capped
  at 60 periods per run.
- A unique constraint on `(subscription_id, period_start)` and the billing
  cursor make retries and repeated runs safe.
- `dry_run: true` returns the due counts without writing invoices.
- `auto_confirm: false` creates draft invoices for review.
- Invoice totals are computed per line: quantity, unit price, discount, tax and
  total. Tax rates and lifecycle settings are snapshotted so later catalogue
  changes do not rewrite history.
- Subscriptions close automatically at term end when the plan allows it,
  otherwise billing stops for a human decision.
- Payments may be partial. An invoice becomes `paid` when payments cover the
  total; overpayments are rejected.

The same flow can be triggered for one subscription with
`POST /api/v1/subscriptions/{id}/invoices`.

## Main API areas

All routes are under `/api/v1` and require a bearer token unless noted.

| Area | Endpoints |
| --- | --- |
| Auth | `/auth/login`, `/auth/register`, `/auth/me`, password reset/change |
| Customers | `/customers`, `/customers/me`, customer detail/update |
| Catalogue | `/taxes`, `/products`, product variants, `/plans` |
| Sales | `/quotation-templates`, `/discounts`, `/subscriptions` |
| Billing | `/invoices`, `/invoices/run-billing`, invoice actions, `/payments` |
| Reporting | `/reports/summary`, `/reports/revenue`, `/reports/overdue` |

List endpoints return `{ "items": [], "total": 0, "page": 1, "page_size": 20,
"pages": 0 }` and support pagination plus area-specific filters.

## Configuration

Copy `.env.example` to `.env` when you need to override defaults.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Set to `production` for production checks |
| `SECRET_KEY` | dev value | JWT signing key; production requires 32+ random characters |
| `DATABASE_URL` | `sqlite:///./brightloop.db` | Database connection |
| `CORS_ORIGINS` | localhost:3000, localhost:5173 | Comma-separated browser origins |
| `FRONTEND_URL` | `http://localhost:5173` | Password-reset link base |
| `SEED_DEMO_DATA` | `true` | Seed demo data on first boot |
| `SERVE_FRONTEND` | `true` | Serve the built SPA from FastAPI |
| `FRONTEND_BUILD_DIR` | `frontend/build` | Static build directory |

In production, set a random `SECRET_KEY` and a real `DATABASE_URL`. Startup
rejects the default or short secret when `ENVIRONMENT=production`.

## Tests and checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run check
npm --prefix frontend run build
```

The backend suite covers authentication, tenant isolation, subscription state
transitions, invoice generation, billing-run idempotency and catch-up, dry runs,
discount limits, payments and reporting math. The frontend check runs
`svelte-check`; the build produces `frontend/build/index.html` plus hashed
`_app` assets.

## Project layout

```text
app/
  main.py                 FastAPI app, lifespan, API and SPA serving
  core/                   settings, security, money helpers
  db/                     engine, session, migrations, demo seed
  models/                 users, products, plans, subscriptions, invoices
  schemas/                Pydantic request/response models
  services/               lifecycle, billing, payments, reporting, email
  api/v1/                 versioned routers
frontend/
  src/routes/             SvelteKit pages
  src/lib/components/     UI components, including RunBillingModal
  src/lib/data/           backend mappers, API repositories, reactive store
  build/                  generated static SPA
tests/                    backend test suite
scripts/demo.ps1          build + serve demo launcher
```

## Production notes

- Replace `create_all` with Alembic before production schema changes.
- Schedule `run_billing` once a day; retries are safe.
- Implement `services/email.py` against a real email provider.
- `/invoices/{id}/print` returns HTML; render it to PDF if attachments are
  needed.
- SQLite is suitable for a demo and small deployments. Point `DATABASE_URL` at
  PostgreSQL when you need concurrent writers.
- Add login rate limiting, refresh-token revocation, audit logging and dunning
  for a hardened deployment.
