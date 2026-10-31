# Backend architecture

Brightloop Subscription Management API — FastAPI + SQLAlchemy 2 + SQLite.
This document is the map of the running system: layers, request flow, data
model, subscription lifecycle and the billing run.

> Mermaid diagrams render on GitHub, GitLab and in the VS Code Markdown
> preview (extension: *Markdown Preview Mermaid Support*).

---

## 1. Layered architecture

```mermaid
flowchart TB
    subgraph Clients["Clients"]
        swagger["Swagger UI<br/>/docs · /redoc"]
        apiClient["HTTP client / SPA<br/>Bearer JWT"]
        ops["Cron / ops job<br/>billing run"]
    end

    subgraph ASGI["ASGI layer — app/main.py"]
        uvicorn["Uvicorn<br/>127.0.0.1:8000"]
        app["FastAPI app<br/>CORS middleware<br/>IntegrityError to 409<br/>/ · /health · /docs"]
    end

    subgraph Routers["Routers — /api/v1"]
        authR["auth<br/>register · login · token · reset"]
        userR["users · customers"]
        catalogR["taxes · products · plans<br/>quotation-templates"]
        billingR["subscriptions · discounts<br/>invoices · payments"]
        reportsR["reports<br/>summary · revenue · overdue"]
    end

    subgraph Cross["Cross-cutting — app/api"]
        dbDep["get_db<br/>one Session per request"]
        jwtDep["get_current_user<br/>JWT sub to User row"]
        roleDep["require_roles<br/>admin · staff · customer"]
        scopeDep["ensure_customer_access<br/>per-customer scoping"]
        pageDep["paginate<br/>page · page_size"]
    end

    subgraph Services["Domain services — app/services"]
        subSvc["subscriptions<br/>create · transition · renew"]
        billSvc["billing<br/>periods · pricing · run"]
        invSvc["invoices<br/>confirm · cancel · pay"]
        repSvc["reporting<br/>MRR · revenue · overdue"]
        numSvc["numbering<br/>SUB- · INV-"]
        mailSvc["email<br/>console / SMTP"]
    end

    subgraph Persistence["Persistence — app/db · app/models"]
        orm["SQLAlchemy 2.0 ORM<br/>Money / Rate type decorators"]
        sess["Engine + SessionLocal<br/>WAL · foreign_keys=ON"]
        sqlite[("SQLite<br/>brightloop.db")]
    end

    subgraph Core["Configuration and security — app/core"]
        cfg["Settings (.env)<br/>SECRET_KEY · TTLs · CORS · seed"]
        sec["PBKDF2-SHA256 hashing<br/>PyJWT HS256 tokens"]
        money["Money helpers<br/>amounts stored as cents"]
    end

    swagger --> uvicorn
    apiClient --> uvicorn
    ops --> uvicorn
    uvicorn --> app
    app --> authR
    app --> userR
    app --> catalogR
    app --> billingR
    app --> reportsR

    authR --> dbDep
    userR --> jwtDep
    catalogR --> roleDep
    billingR --> scopeDep
    reportsR --> pageDep

    Cross --> Services
    Services --> orm
    orm --> sess
    sess --> sqlite

    cfg -.-> Cross
    cfg -.-> Services
    sec -.-> jwtDep
    sec -.-> authR
    money -.-> billSvc
```

**Rules of the layers**

| Layer | Owns | Must not |
| --- | --- | --- |
| `app/api/v1/*` | HTTP verbs, status codes, auth gates, response models | contain pricing or state-machine logic |
| `app/api/deps.py` | token decoding, role checks, customer scoping, pagination | touch domain tables beyond `users` |
| `app/services/*` | business rules, transactions, calculations | import FastAPI or raise `HTTPException` |
| `app/models/*` | schema, relationships, enums, cheap `@property` helpers | perform I/O |
| `app/schemas/*` | request/response contracts and validation | import services |

---

## 2. Request lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant F as FastAPI
    participant D as deps.py
    participant R as Router
    participant S as Service
    participant O as SQLAlchemy
    participant DB as SQLite

    C->>F: GET /api/v1/reports/summary<br/>Authorization: Bearer <token>
    F->>F: CORS, route match,<br/>request body validation
    F->>D: Depends(get_db) · Depends(get_current_user)
    D->>D: decode JWT (HS256), read sub
    D->>O: db.get(User, sub)
    O->>DB: SELECT users WHERE id = ?
    DB-->>O: row
    O-->>D: User

    alt token invalid, user missing or inactive
        D-->>C: 401 Unauthorized
    else role not allowed by require_roles
        D-->>C: 403 Forbidden
    else customer touches another account
        D-->>C: 403 Forbidden
    else allowed
        D->>R: inject User + Session
        R->>S: summary(db, as_of)
        S->>O: aggregate queries
        O->>DB: SELECT ... GROUP BY ...
        DB-->>O: rows
        O-->>S: scalars
        S-->>R: plain dict
        R-->>C: 200 JSON validated by response_model
    end
```

Notes:

* The **role is read from the database on every request**, not trusted from the
  token claim, so demotions and `is_active = false` take effect immediately.
* `IntegrityError` is translated once, globally, into `409 Conflict`
  (`app/main.py`).
* Every route writes through one `Session`; services never commit, routers do.

---

## 3. Data model

```mermaid
erDiagram
    CUSTOMERS {
        int id PK
        string name
        string email UK
        string phone
        text billing_address
        string tax_id
        bool is_active
    }

    USERS {
        int id PK
        string email UK
        string hashed_password
        string full_name
        enum role "admin | staff | customer"
        bool is_active
        int customer_id FK
        datetime last_login_at
    }

    PASSWORD_RESET_TOKENS {
        int id PK
        int user_id FK
        string token_hash UK
        datetime expires_at
        datetime used_at
    }

    TAXES {
        int id PK
        string name UK
        decimal rate "percent"
        bool is_active
    }

    PRODUCTS {
        int id PK
        string name
        enum type "service | addon | module | support"
        decimal sales_price
        decimal cost_price
        int tax_id FK
        bool is_active
    }

    PRODUCT_VARIANTS {
        int id PK
        int product_id FK
        string name
        decimal price_delta
        bool is_active
    }

    PLANS {
        int id PK
        string code UK
        string name
        int product_id FK
        decimal price
        enum interval "daily | weekly | monthly | yearly"
        int min_quantity
        int tax_id FK
        bool auto_close_on_expiry
        bool allow_early_close
        bool allow_pause
        bool allow_renew
        bool is_active
    }

    QUOTATION_TEMPLATES {
        int id PK
        string name UK
        int plan_id FK
        int validity_days
        int payment_terms_days
        bool is_active
    }

    QUOTATION_TEMPLATE_LINES {
        int id PK
        int template_id FK
        int product_id FK
        int variant_id FK
        int quantity
        decimal unit_price
    }

    DISCOUNTS {
        int id PK
        string name
        string code UK
        enum type "fixed | percentage"
        decimal value
        enum scope "subscription | product"
        int product_id FK
        decimal min_purchase_amount
        int min_quantity
        date start_date
        date end_date
        int max_uses
        int used_count
        bool is_active
    }

    SUBSCRIPTIONS {
        int id PK
        string number UK
        int customer_id FK
        int plan_id FK
        int quotation_template_id FK
        enum status "draft | quotation | confirmed | active | paused | closed"
        date start_date
        date expiry_date
        int payment_terms_days
        date current_period_start
        date current_period_end
        date next_billing_date
        datetime closed_at
        int renewed_from_id FK
        int created_by_id FK
    }

    SUBSCRIPTION_LINES {
        int id PK
        int subscription_id FK
        int product_id FK
        int variant_id FK
        int quantity
        decimal unit_price
        int tax_id FK
        decimal tax_rate
        decimal amount
    }

    SUBSCRIPTION_STATUS_HISTORY {
        int id PK
        int subscription_id FK
        enum from_status
        enum to_status
        int changed_by_id FK
        datetime created_at
    }

    SUBSCRIPTION_DISCOUNTS {
        int id PK
        int subscription_id FK
        int discount_id FK
        datetime applied_at
        datetime removed_at
    }

    INVOICES {
        int id PK
        string number UK
        int subscription_id FK
        int customer_id FK
        enum status "draft | confirmed | paid | cancelled"
        date issue_date
        date due_date
        date period_start
        date period_end
        decimal subtotal
        decimal discount_total
        decimal tax_total
        decimal total
        decimal amount_paid
        datetime confirmed_at
        datetime cancelled_at
    }

    INVOICE_LINES {
        int id PK
        int invoice_id FK
        int product_id FK
        string description
        int quantity
        decimal unit_price
        decimal tax_rate
        decimal discount_amount
        decimal tax_amount
        decimal total
    }

    PAYMENTS {
        int id PK
        int invoice_id FK
        enum method "card | bank_transfer | cash | paypal | direct_debit | other"
        decimal amount
        date paid_on
        string reference
        int recorded_by_id FK
    }

    DISCOUNT_REDEMPTIONS {
        int id PK
        int discount_id FK
        int subscription_id FK
        int invoice_id FK
        decimal amount
        datetime created_at
    }

    CUSTOMERS |o--o{ USERS : "portal logins"
    CUSTOMERS ||--o{ SUBSCRIPTIONS : "owns"
    CUSTOMERS ||--o{ INVOICES : "is billed"
    USERS ||--o{ PASSWORD_RESET_TOKENS : "requests"
    USERS |o--o{ SUBSCRIPTIONS : "created_by"
    USERS |o--o{ PAYMENTS : "recorded_by"
    USERS |o--o{ SUBSCRIPTION_STATUS_HISTORY : "changed_by"

    TAXES |o--o{ PRODUCTS : "default tax"
    TAXES |o--o{ PLANS : "plan tax"
    TAXES |o--o{ SUBSCRIPTION_LINES : "line tax"

    PRODUCTS ||--o{ PRODUCT_VARIANTS : "sells as"
    PRODUCTS ||--o{ PLANS : "underlies"
    PRODUCTS ||--o{ QUOTATION_TEMPLATE_LINES : "offered in"
    PRODUCTS |o--o{ SUBSCRIPTION_LINES : "subscribed as"
    PRODUCTS |o--o{ INVOICE_LINES : "snapshot of"
    PRODUCT_VARIANTS |o--o{ SUBSCRIPTION_LINES : "variant"
    PRODUCT_VARIANTS |o--o{ QUOTATION_TEMPLATE_LINES : "variant"

    PLANS ||--o{ QUOTATION_TEMPLATES : "templated by"
    PLANS ||--o{ SUBSCRIPTIONS : "priced by"
    QUOTATION_TEMPLATES ||--o{ QUOTATION_TEMPLATE_LINES : "contains"
    QUOTATION_TEMPLATES |o--o{ SUBSCRIPTIONS : "started from"

    SUBSCRIPTIONS ||--o{ SUBSCRIPTION_LINES : "contains"
    SUBSCRIPTIONS ||--o{ SUBSCRIPTION_STATUS_HISTORY : "audited by"
    SUBSCRIPTIONS ||--o{ SUBSCRIPTION_DISCOUNTS : "has active"
    SUBSCRIPTIONS |o--o{ INVOICES : "billed as"
    SUBSCRIPTIONS |o--o{ DISCOUNT_REDEMPTIONS : "consumes"

    DISCOUNTS ||--o{ SUBSCRIPTION_DISCOUNTS : "applied via"
    DISCOUNTS ||--o{ DISCOUNT_REDEMPTIONS : "redeemed as"

    INVOICES ||--o{ INVOICE_LINES : "snapshots"
    INVOICES ||--o{ PAYMENTS : "settled by"
    INVOICES |o--o{ DISCOUNT_REDEMPTIONS : "discounted by"
```

Key constraints:

* `invoices (subscription_id, period_start)` is **unique** — the hard guarantee
  that a billing period is never invoiced twice.
* `subscriptions.expiry_date` + `next_billing_date` drive the billing cursor.
* `discounts.used_count` guards `max_uses`; rows in `discount_redemptions` are
  written only when an invoice is confirmed.
* Money is stored as integer cents (`Money`) and tax rates as basis points
  (`Rate`); API payloads use decimal numbers.

---

## 4. Subscription lifecycle

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> QUOTATION : send quote
    QUOTATION --> DRAFT : revise
    DRAFT --> CONFIRMED : direct sale
    QUOTATION --> CONFIRMED : accepted
    CONFIRMED --> ACTIVE : activate
    ACTIVE --> PAUSED : pause
    PAUSED --> ACTIVE : resume
    ACTIVE --> CLOSED : early close
    PAUSED --> CLOSED : close
    CONFIRMED --> CLOSED : cancel
    QUOTATION --> CLOSED : lost
    DRAFT --> CLOSED : discard
    CLOSED --> [*]

    note right of ACTIVE
        Only ACTIVE rows are billed.
        Expiry with auto_close_on_expiry
        closes the subscription.
    end note
```

Transitions are declared once in `app/models/subscription.py`
(`STATUS_TRANSITIONS`) and enforced by `app/services/subscriptions.py`; an
invalid move raises `ValueError`, which the router maps to `409`.

`activate` sets `current_period_start` / `current_period_end` /
`next_billing_date`, so the first billing run can pick the subscription up.

---

## 5. Billing run

`POST /api/v1/invoices/run-billing` (admin or staff) → `run_billing()`.

```mermaid
flowchart TD
    A["POST /invoices/run-billing<br/>as_of · auto_confirm · dry_run"] --> B["Load subscriptions<br/>status = ACTIVE<br/>next_billing_date <= as_of"]
    B --> C{"Any due?"}
    C -->|no| Z["Return counts<br/>scanned · invoiced · skipped · closed"]
    C -->|yes| D{"next_billing_date<br/>after expiry_date?"}
    D -->|yes| E["Stop billing<br/>auto_close_on_expiry ? CLOSED"]
    E --> Z
    D -->|no| F["next_period(plan, cursor)"]
    F --> G{"dry_run?"}
    G -->|yes| H["Report period,<br/>write nothing, rollback"]
    H --> Z
    G -->|no| I["build_invoice<br/>price lines · apply discounts<br/>compute taxes · totals"]
    I --> J{"Period already invoiced?<br/>unique (subscription, period_start)"}
    J -->|yes| K["Skip: ValueError<br/>errors + skipped"]
    J -->|no| L["Persist invoice<br/>DRAFT, or CONFIRMED when auto_confirm"]
    L --> M["advance_subscription<br/>move billing cursor"]
    K --> M
    M --> N{"More missed periods?<br/>max 60 per subscription"}
    N -->|yes| D
    N -->|no| C
```

Behaviour worth knowing:

* **Catch-up billing**: a subscription that was offline for months produces one
  invoice per missed period, capped at `max_cycles = 60`.
* **Idempotent**: re-running for the same `as_of` never duplicates invoices.
* **Dry run** rolls the whole transaction back and returns what *would* happen.
* Discounts are re-evaluated at invoice time against their date window,
  minimum quantity/amount and remaining `max_uses`.

---

## 6. Module map

```
app/
  main.py              FastAPI app, lifespan (create_all + seed), CORS, 409 handler
  core/
    config.py          env-driven Settings
    security.py        PBKDF2 hashing, JWT encode/decode, password policy
    money.py           cents/Decimal helpers
  db/
    base.py            Declarative Base, TimestampMixin, Money, Rate, enum_column
    session.py         engine, SQLite PRAGMAs, SessionLocal, get_db
    seed.py            demo users, customers, catalogue, subscriptions, invoices
  models/              users/customers, products/taxes, plans, quotations,
                       discounts, subscriptions, invoices/payments
  schemas/             Pydantic request/response contracts
  services/            subscriptions, billing, invoices, reporting, numbering, email
  api/
    deps.py            auth, role gates, pagination, customer scoping
    pagination.py      page/page_size helpers
    v1/                one router per resource, wired in v1/router.py
docs/
  architecture.md      this document
tests/                 pytest suite against an in-memory SQLite database
```

Runtime entry point: `uvicorn app.main:app --reload` — API under `/api/v1`,
docs at `/docs`, health at `/health`.
