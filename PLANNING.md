# ShopPulse Store - Planning & Phases

This document breaks down the implementation of the **ShopPulse Store** demo
e-commerce application (per `product_spec.md`) into clear, sequential phases.
Each phase has a goal, scope, deliverables, and exit criteria so progress is
verifiable.

---

## 1. Project Overview

**Name:** ShopPulse Store
**Purpose:** A Flask + SQLite demo e-commerce store whose primary goal is to
generate realistic clickstream, cart, search, and order-intent data for a
future Azure MLOps project that predicts short-horizon (30-60 minute) product
demand.

**Stack:** Flask, SQLAlchemy, SQLite, Bootstrap 5, Jinja2, vanilla JS,
LocalStorage cart, Chart.js, python-dotenv. WhatsApp link is the order
submission channel (no payments, no auth in v1).

**Top-level deliverables:**
1. Runnable Flask app with seeded catalog (40+ products / 8 categories).
2. Browse / search / cart / checkout flow ending in a WhatsApp deep link.
3. Click and cart event capture into SQLite via `/api/track-event`.
4. Internal analytics dashboard with funnel + Chart.js visualizations.
5. `simulate_events.py` traffic generator + CSV batch export.
6. README explaining setup, flow, and future Azure architecture.

---

## 2. Architecture Snapshot

```
Browser (Bootstrap + JS + LocalStorage cart)
   │  fetch POST /api/track-event, /api/cart-event, /api/create-order-intent
   ▼
Flask app (app.py)
   ├── Frontend routes  → Jinja templates
   ├── API routes       → JSON
   └── SQLAlchemy models (models.py)
            │
            ▼
       SQLite (data/shoppulse.db)
            │
            ▼
   CSV exports (exports/YYYY-MM-DD/) ──► future: Azure ADLS / Event Hubs / AML
```

---

## 3. Phase Breakdown

Phases are ordered to keep the app runnable end-to-end as early as possible.
Phases 1-4 give a usable store; phases 5-7 add analytics, simulation, and
polish.

### Phase 0 - Repository scaffolding
**Goal:** Empty but installable project skeleton.

**Tasks:**
- Create folder tree from spec: `static/{css,js,images}`, `templates/partials`,
  `data/`, `exports/`.
- Add `requirements.txt` (Flask, Flask-SQLAlchemy, python-dotenv, requests,
  faker for simulator).
- Add `.env.example` with `FLASK_SECRET_KEY`, `WHATSAPP_NUMBER`,
  `DATABASE_URL`.
- Add `.gitignore` for `venv/`, `__pycache__/`, `data/*.db`, `exports/`,
  `.env`.
- Stub `config.py` reading env vars; stub `app.py` with `create_app()` and a
  health route.

**Exit criteria:** `pip install -r requirements.txt && python app.py` boots
and serves a 200 on `/healthz`.

---

### Phase 1 - Data model & seed
**Goal:** Persisted catalog ready to render.

**Tasks:**
- Implement `models.py` with all six tables exactly per spec:
  `Product`, `Category`, `ClickEvent`, `CartEvent`, `OrderIntent`,
  `SearchQuery`. Use `db.JSON` (or `Text` JSON-serialized) for
  `metadata_json` and `cart_json`.
- Add helpful indexes: `ClickEvent(event_type, created_at)`,
  `ClickEvent(session_id)`, `Product(slug)`, `Product(category)`.
- Implement `seed.py`:
  - 8 categories from spec.
  - 40+ products (5 per category from the named examples), realistic
    Indian pricing (₹299-₹2499), discount %, stock 10-200, rating 3.5-5.
  - Generate slug + SKU (`<CAT>-<NAME>-<NNN>`).
  - Idempotent: skip insert if SKU/slug already exists.
- Use placeholder image URLs (e.g. `picsum.photos/seed/<sku>/600/600`)
  served via product `image_url`.

**Exit criteria:** `python seed.py` populates DB; re-running it does not
duplicate rows; row counts match spec (>=40 products, 8 categories).

---

### Phase 2 - Storefront pages (read-only)
**Goal:** All browse pages render real data; no cart/analytics yet.

**Tasks:**
- `templates/base.html` with Bootstrap 5 CDN, navbar partial, footer partial,
  search bar, cart badge placeholder.
- Partials: `navbar.html`, `footer.html`, `product_card.html`.
- Routes + templates:
  - `GET /` (`index.html`): hero, featured categories, featured products,
    trending products, "Order via WhatsApp" explainer, demo banner
    ("Demo store for real-time demand prediction and MLOps analytics.").
  - `GET /products` (`products.html`): grid + category/price filters + sort
    (price/rating/discount) + search via `?q=`.
  - `GET /category/<slug>` (`category.html`): filtered listing + description.
  - `GET /product/<slug>` (`product_detail.html`): image, price, compare-at,
    discount %, stock, rating, qty selector, related products
    (same-category).
- Apply design system: white bg, dark navy text, light gray sections, green
  WhatsApp CTA, blue analytics accents (in `static/css/style.css`).
- Graceful 404 for missing slug.

**Exit criteria:** Each page reachable, mobile-responsive, shows seeded data.

---

### Phase 3 - LocalStorage cart + checkout + WhatsApp flow
**Goal:** End-to-end purchase intent leaves the app via WhatsApp.

**Tasks:**
- `static/js/cart.js` exporting all required functions: `getCart`,
  `saveCart`, `addToCart`, `removeFromCart`, `updateQuantity`, `clearCart`,
  `getCartTotal`, `getCartItemsCount`, `renderCart`, `updateCartBadge`.
  Cart object matches spec shape; `updated_at` is ISO-8601.
- Wire "Add to cart" buttons on listing, category, and detail pages.
- `GET /cart` (`cart.html`): renders entirely from LocalStorage on page load
  via `renderCart()`; supports qty edit, remove, clear, totals.
- `GET /checkout` (`checkout.html`): name / phone / city / notes form, cart
  summary from LocalStorage, client-side validation (phone digits, name
  required, cart non-empty).
- `POST /api/create-order-intent`:
  - Validates payload + cart (recomputes totals server-side from
    `Product` rows by id to prevent tampering).
  - Generates `order_code` `SP-YYYYMMDD-NNN` (daily counter).
  - Builds WhatsApp message exactly per spec template.
  - Saves `OrderIntent` with `status='pending_whatsapp'`, returns
    `{ order_code, whatsapp_url }` where url is
    `https://wa.me/<NUMBER>?text=<urlencoded>`.
- Frontend opens `whatsapp_url` in new tab, then redirects to
  `/order-success/<order_code>` and clears cart.
- `GET /order-success/<order_code>` (`order_success.html`): thanks user,
  shows code + next-step note + Continue Shopping CTA.

**Exit criteria:** A user can add items, check out, click "Order on
WhatsApp", land on order-success, and see the row in `OrderIntent`.

---

### Phase 4 - Click & cart event tracking
**Goal:** Every meaningful interaction is captured.

**Tasks:**
- `static/js/analytics.js` implementing `getSessionId`,
  `getAnonymousUserId` (UUID v4 in LocalStorage; session_id rotates on
  ~30 min idle), `detectDeviceType` (UA-based mobile/tablet/desktop),
  `getTrafficSource` (utm_source > document.referrer host > "direct"),
  `trackEvent(eventType, payload)`, `trackPageView()`. Use
  `navigator.sendBeacon` when available, fallback to `fetch` with
  `keepalive: true`. Fail silently.
- `POST /api/track-event` accepts the spec payload, fills
  `ClickEvent.metadata_json` with extras, sets `created_at` server-side.
- `POST /api/cart-event` writes `CartEvent` rows for `add_to_cart`,
  `remove_from_cart`, `update_quantity`, `clear_cart`, `checkout_started`.
- Wire required events on each page (per spec sections "Track events"):
  landing CTAs, product impressions/clicks, filter/sort, product_view,
  whatsapp_buy_click, cart_view, checkout_view/form_started/form_submit,
  whatsapp_order_click, order_success_view.
- Search submissions also write a `SearchQuery` row with `results_count`.
- Add code comments noting how `ClickEvent` / `CartEvent` rows can be
  forwarded to **Azure Event Hubs** and persisted to **ADLS Gen2** for an
  **Azure ML** training pipeline.

**Exit criteria:** Browsing the site populates `ClickEvent`, `CartEvent`,
`SearchQuery` with correct types and session attribution.

---

### Phase 5 - Analytics dashboard
**Goal:** Internal `/analytics` page summarizes behavior.

**Tasks:**
- Aggregation API routes (all read-only, JSON):
  - `GET /api/analytics/summary` - totals: page_views, product_views,
    add_to_cart, checkout_started, whatsapp_order_click.
  - `GET /api/analytics/funnel` - 5-step funnel counts in order.
  - `GET /api/analytics/top-products` - top viewed and top added-to-cart.
  - `GET /api/analytics/recent-events` - last N click events + last N
    order intents.
- `GET /analytics` (`analytics_dashboard.html`):
  - KPI cards (totals).
  - Chart.js: bar (events by type), bar (top products by views), funnel
    (horizontal bars), line (events over time, hourly bucket).
  - Tables: top searched terms, recent click events, recent order intents.
- README note that this route must be auth-protected before production.

**Exit criteria:** Dashboard renders charts populated from real DB data.

---

### Phase 6 - Simulator & batch export
**Goal:** Generate data without humans, and dump it for downstream ML.

**Tasks:**
- `simulate_events.py`:
  - 20 synthetic anonymous users (stable UUIDs).
  - Each runs a randomized session: page_view -> category_view ->
    product_view(s) -> optional search -> optional add_to_cart ->
    optional checkout_started -> optional whatsapp_order_click.
  - POSTs to `/api/track-event` (and `/api/cart-event` where applicable)
    with realistic timing jitter; configurable target URL and total events.
- CSV export (Flask CLI + `GET /api/export/csv` admin route):
  - Writes `products.csv`, `click_events.csv`, `cart_events.csv`,
    `order_intents.csv`, `search_queries.csv` to `exports/YYYY-MM-DD/`.
  - Header row + UTF-8; safely serializes JSON columns.
- Comments in export module describe future ADLS upload step.

**Exit criteria:** Running the simulator visibly grows analytics counts; CSV
export produces 5 files with correct row counts.

---

### Phase 7 - Polish, docs, and acceptance
**Goal:** Meet every line of the spec's Acceptance Criteria.

**Tasks:**
- README.md sections: overview, setup, DB creation, seeding, running,
  cart explanation, analytics tracking, WhatsApp flow, simulator usage,
  CSV export, future Azure architecture (Event Hubs -> ADLS -> AML
  pipeline -> model serving -> back into store), security caveats.
- Empty-cart and missing-product handling reviewed on every page.
- Manual smoke test of all 17 acceptance items (checklist below).
- Lint pass; remove dead code; verify no TODOs in core paths.

**Exit criteria:** All 17 acceptance items pass on a fresh clone.

---

## 4. Cross-cutting Concerns

- **Config:** `config.py` reads `WHATSAPP_NUMBER`, `FLASK_SECRET_KEY`,
  `DATABASE_URL` from env via `python-dotenv`. Defaults are dev-safe.
- **Security (v1 scope):** No auth; analytics dashboard and CSV export are
  open - README flags this. Server recomputes order totals from DB to
  prevent client-side price tampering.
- **Performance:** Indexes on hot lookup columns; analytics queries
  aggregated server-side, not in JS.
- **Error handling:** API endpoints return JSON `{ "ok": false, "error": ... }`
  with appropriate status; tracking endpoints always 204 on bad input
  (silent-fail contract for the frontend).
- **ML readiness:** Every `ClickEvent` row carries enough columns
  (timestamps, session, product, category, traffic source, device, cart
  context) to derive features for the future "high demand in next
  30/60 min" model. Hour-of-day / day-of-week are derived at query time.

---

## 5. File-by-file Ownership Map

| File / Folder | Phase | Notes |
|---|---|---|
| `app.py` | 0, then grows each phase | factory + route registration |
| `config.py` | 0 | env vars, WhatsApp number |
| `models.py` | 1 | all 6 tables + indexes |
| `seed.py` | 1 | idempotent catalog seed |
| `templates/base.html` + partials | 2 | layout, navbar, footer, card |
| `templates/index.html` | 2 | landing |
| `templates/products.html` | 2 | listing |
| `templates/category.html` | 2 | category page |
| `templates/product_detail.html` | 2 | PDP |
| `templates/cart.html` | 3 | LocalStorage cart UI |
| `templates/checkout.html` | 3 | checkout form |
| `templates/order_success.html` | 3 | thank-you page |
| `templates/analytics_dashboard.html` | 5 | KPI + Chart.js |
| `static/js/cart.js` | 3 | cart API |
| `static/js/analytics.js` | 4 | tracking client |
| `static/js/main.js` | 2-4 | shared init, page-view auto-track |
| `static/css/style.css` | 2 | design tokens |
| `simulate_events.py` | 6 | traffic generator |
| `exports/` writer (CLI + route) | 6 | CSV batch dump |
| `README.md` | 7 | full setup + Azure roadmap |

---

## 6. Acceptance Checklist (from spec)

- [ ] Flask app runs locally
- [ ] SQLite DB is created
- [ ] Seed products inserted
- [ ] Landing page loads
- [ ] Product listing works
- [ ] Product detail page works
- [ ] Cart works using LocalStorage
- [ ] Cart badge updates
- [ ] Checkout reads cart from LocalStorage
- [ ] Order intent saved to SQLite
- [ ] WhatsApp message generated correctly
- [ ] Analytics events stored in `ClickEvent`
- [ ] Add-to-cart events stored in `CartEvent`
- [ ] Analytics dashboard shows event counts
- [ ] `simulate_events.py` generates fake events
- [ ] CSV export works
- [ ] README explains setup clearly

---

## 7. Out of Scope for v1

- User accounts / login
- Real payments
- Admin product management UI
- Live Azure pipeline wiring (only documented + structurally prepared)
- Internationalization
