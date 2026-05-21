# ShopPulse Store - Deployment & Test Guide (Local)

ShopPulse Store is a **demo Flask + SQLite e-commerce app** whose primary
purpose is to generate realistic clickstream, cart, search, and order-intent
data for a future Azure MLOps demand-prediction pipeline. Orders are placed
via a **WhatsApp deep link** — no payment gateway is involved.

This README covers everything you need to **deploy and test the app on your
local machine**. Implementation phases live in [`PLANNING.md`](PLANNING.md);
the original product brief lives in [`product_spec.md`](product_spec.md).

---

## 1. Prerequisites

| Tool   | Version           | Notes                                        |
|--------|-------------------|----------------------------------------------|
| Python | 3.10 or newer     | 3.11 used in development                     |
| pip    | bundled           | `python -m ensurepip --upgrade` if missing   |
| OS     | macOS/Linux/WSL/Win | Tested on Linux                            |
| Browser| Chrome/Firefox/Safari/Edge | For UI smoke testing                |

No external services, no Docker, no Node toolchain required. Internet access
is needed once for `pip install` (and at runtime for the Bootstrap/Chart.js
CDNs and placeholder product images from `picsum.photos`).

---

## 2. One-time setup

```bash
# 1. Clone and enter the repo
git clone <your-fork-or-this-repo-url>
cd Online-store-Click-Analytics

# 2. Create and activate a virtualenv
python3.11 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows PowerShell

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure environment (optional; sane dev defaults exist)
cp .env.example .env
# edit .env to set FLASK_SECRET_KEY and WHATSAPP_NUMBER
```

### Environment variables (`.env`)

| Variable           | Default                        | What it controls                       |
|--------------------|--------------------------------|----------------------------------------|
| `FLASK_SECRET_KEY` | `dev-secret-change-me`         | Flask session signing                  |
| `WHATSAPP_NUMBER`  | `+919999999999`                | Deep-link target for orders            |
| `DATABASE_URL`     | `sqlite:///data/shoppulse.db`  | SQLAlchemy connection string           |
| `FLASK_DEBUG`      | `1`                            | Auto-reload + verbose errors           |
| `PORT`             | `5000`                         | Override server port                   |

---

## 3. Initialise the database & seed the catalog

```bash
python seed.py
```

What this does:

- Creates `data/shoppulse.db` (SQLite) if absent.
- Creates all tables (`products`, `categories`, `click_events`,
  `cart_events`, `order_intents`, `search_queries`).
- Inserts **8 categories** and **40 products** with realistic Indian pricing.
- Idempotent: re-running it inserts nothing new.

Expected output:

```
Seed complete. Inserted 40 new products. Total products: 40.
Categories: 8.
```

---

## 4. Run the Flask app

```bash
python app.py
```

You should see:

```
 * Running on http://0.0.0.0:5000
```

Open <http://localhost:5000>.

To use a different port:

```bash
PORT=5050 python app.py
```

---

## 5. Manual test plan (mirrors the spec's acceptance criteria)

Open the app in a browser and walk through the following. Each item maps to
one of the 17 acceptance criteria in `product_spec.md`.

### 5.1 Landing & catalog
1. Visit <http://localhost:5000/> — hero, categories, featured + trending
   products are visible. The black "demo store" banner is at the top.
2. Click a category tile (e.g. **Fitness**) — you should land on
   `/category/fitness` with that category's products.
3. Click **All Products** — `/products` lists 40 items. Try the search box,
   category filter, price range, and sort options. Each filter change
   reloads with the correct results.

### 5.2 Product detail
1. Click any product. The detail page shows image, brand, price,
   compare-at price, discount %, stock, rating, related products.
2. Click **Buy via WhatsApp** — a new tab opens `https://wa.me/...` with a
   prefilled single-item message.

### 5.3 Cart (LocalStorage)
1. From listing or detail page, click **Add**. A toast confirms.
2. The cart badge in the navbar updates.
3. Visit `/cart` — items appear, quantity can be edited, items can be
   removed, **Clear cart** empties it. Reload the page; the cart persists
   (LocalStorage).

### 5.4 Checkout & WhatsApp order flow
1. With items in cart, click **Proceed to checkout**.
2. The checkout page shows your cart summary on the right. Fill **Name**,
   **Phone**, **City**, optional **Notes**.
3. Click **Order on WhatsApp**. You should:
   - See a `wa.me/...` URL open in a new tab with a multi-line message
     (order code, customer block, products, totals, notes).
   - Be redirected to `/order-success/SP-YYYYMMDD-NNN`.
   - The cart is cleared.
4. The page shows your order code, total items, total amount, and a
   **Continue shopping** button.

### 5.5 Analytics dashboard
1. Visit `/analytics`. The page renders:
   - 6 KPI cards (page views, product views, add-to-cart, checkout started,
     WhatsApp clicks, total events).
   - Funnel bar chart, events-by-type bar chart, 24-hour line chart, top
     viewed products bar chart.
   - Tables: top added-to-cart, top searched terms, recent order intents,
     recent click events.
2. Click **Export CSV** — an alert shows the `exports/YYYY-MM-DD/` path.

### 5.6 Verify event capture in the DB

```bash
sqlite3 data/shoppulse.db "
  SELECT event_type, COUNT(*) FROM click_events GROUP BY event_type;
  SELECT event_type, COUNT(*) FROM cart_events  GROUP BY event_type;
  SELECT order_code, customer_name, total_amount FROM order_intents;
"
```

You should see rows for the events you triggered (`page_view`,
`product_view`, `add_to_cart`, `checkout_started`, `whatsapp_order_click`,
etc.) and your test order(s).

---

## 6. Generate synthetic traffic (no humans needed)

The `simulate_events.py` script POSTs realistic events directly to the
running server. Useful before any real users exist.

```bash
# Defaults: 20 users, 40 sessions
python simulate_events.py

# Custom: hit a different host, specify session count
python simulate_events.py --base-url http://localhost:5050 --sessions 100
```

Each session walks the funnel: page_view → search/filter →
product_view(s) → maybe add_to_cart → maybe checkout_started → maybe
whatsapp_order_click. Refresh `/analytics` to see counts grow.

---

## 7. Export analytics data as CSV

Two options — both write to `exports/YYYY-MM-DD/`:

**HTTP (used by the dashboard's Export button):**

```bash
curl -X POST http://localhost:5000/api/export/csv
```

**Flask CLI:**

```bash
flask --app app export-csv
```

Files produced:

```
exports/2026-05-07/
├── products.csv
├── click_events.csv
├── cart_events.csv
├── order_intents.csv
└── search_queries.csv
```

In production these CSVs would be uploaded to **Azure Data Lake Storage
Gen2** as the raw layer of the demand-prediction pipeline.

---

## 8. Quick-test cheat sheet (copy/paste)

```bash
# 1. Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Seed
python seed.py

# 3. Run app (terminal A)
python app.py

# 4. Smoke test (terminal B)
curl -s http://localhost:5000/healthz
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5000/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5000/products
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5000/analytics

# 5. Generate traffic
python simulate_events.py --sessions 30

# 6. Export
curl -s -X POST http://localhost:5000/api/export/csv
ls exports/
```

---

## 9. Project layout

```
.
├── app.py                        # Flask factory, routes, API, CSV export
├── config.py                     # env-driven config
├── models.py                     # SQLAlchemy models (6 tables)
├── seed.py                       # idempotent catalog seed
├── simulate_events.py            # synthetic traffic generator
├── requirements.txt
├── PLANNING.md                   # phased implementation plan
├── product_spec.md               # original product brief
├── README.md                     # this file
├── data/
│   └── shoppulse.db              # SQLite (created at first run)
├── exports/
│   └── YYYY-MM-DD/*.csv          # batch dumps
├── static/
│   ├── css/style.css
│   └── js/{analytics.js, cart.js, main.js}
└── templates/
    ├── base.html
    ├── index.html
    ├── products.html
    ├── category.html
    ├── product_detail.html
    ├── cart.html
    ├── checkout.html
    ├── order_success.html
    ├── analytics_dashboard.html
    └── partials/{navbar.html, footer.html, product_card.html}
```

---

## 10. Backend routes reference

| Method | Path                              | Purpose                            |
|--------|-----------------------------------|------------------------------------|
| GET    | `/`                               | Landing page                       |
| GET    | `/products`                       | Listing + search + filters + sort  |
| GET    | `/category/<slug>`                | Category page                      |
| GET    | `/product/<slug>`                 | Product detail                     |
| GET    | `/cart`                           | LocalStorage-driven cart           |
| GET    | `/checkout`                       | Checkout form                      |
| GET    | `/order-success/<order_code>`     | Order confirmation                 |
| GET    | `/analytics`                      | Internal analytics dashboard       |
| GET    | `/healthz`                        | Liveness probe                     |
| POST   | `/api/track-event`                | Click event ingestion (silent-fail)|
| POST   | `/api/cart-event`                 | Cart event ingestion (silent-fail) |
| POST   | `/api/create-order-intent`        | Server-validated order + WA URL    |
| GET    | `/api/products`                   | Catalog JSON (used by simulator)   |
| GET    | `/api/analytics/summary`          | KPI counts                         |
| GET    | `/api/analytics/funnel`           | 5-step funnel counts               |
| GET    | `/api/analytics/top-products`     | Top viewed / added / searched      |
| GET    | `/api/analytics/recent-events`    | Last N events + orders + timeseries|
| GET/POST| `/api/export/csv`                | Dump all tables to disk            |

---

## 11. How the cart works (LocalStorage contract)

`static/js/cart.js` owns a single LocalStorage key, `sp_cart_v1`, shaped:

```json
{
  "items": [
    { "product_id": 1, "sku": "FIT-YMP-001", "name": "Yoga Mat Pro",
      "slug": "yoga-mat-pro", "price": 1299, "quantity": 2,
      "image_url": "...", "category": "Fitness" }
  ],
  "updated_at": "2026-05-07T12:30:00.000Z"
}
```

Every mutation also sends a `cart-event` to the server (best-effort) and
mirrors the action onto the click stream so funnel queries remain simple.

---

## 12. How analytics tracking works

`static/js/analytics.js` runs on every page (loaded by `base.html`):

- **Identity**: anonymous `user_id` (UUID, persistent) and `session_id`
  (UUID, rotates after 30 minutes idle), both kept in LocalStorage.
- **Auto event**: `page_view` on every load.
- **Manual events**: pages call
  `SPAnalytics.trackEvent(eventType, payload)` for `product_view`,
  `category_view`, `add_to_cart`, `checkout_*`, `whatsapp_*`, etc.
- **Transport**: `navigator.sendBeacon` when available; falls back to
  `fetch` with `keepalive`. Failures are silent — UX is never blocked.

---

## 13. WhatsApp order flow (end-to-end)

```
Browser                                Flask                       SQLite
  │                                     │                            │
  │  POST /api/create-order-intent ───► │                            │
  │       { customer, items }            │ recompute totals from DB ─►│
  │                                     │ insert OrderIntent ────────►│
  │ ◄── { order_code, whatsapp_url } ── │                            │
  │                                                                  │
  │ window.open(whatsapp_url)                                        │
  │ window.location = /order-success/<code>                          │
```

The server **never trusts client-side prices** — it recomputes
`total_amount` and `total_items` from the `Product` rows by id. The
generated WhatsApp URL is `https://wa.me/<NUMBER>?text=<urlencoded>`.

---

## 14. Future Azure architecture (where this fits)

```
ShopPulse browsers
      │  POST /api/track-event, /api/cart-event
      ▼
Flask app  ──► Azure Event Hubs  ──► ADLS Gen2 (raw Parquet/CSV)
                                          │
                                          ▼
                          Azure ML pipeline (feature engineering + training)
                                          │
                                          ▼
                       Model: P(product becomes high-demand in next 30/60 min)
                                          │
                                          ▼
                         Real-time scoring → store ranking & alerting
```

The local CSV export already produces the file layout that the future ADLS
upload step would consume.

---

## 15. Troubleshooting

| Symptom                             | Likely cause / fix                                  |
|-------------------------------------|------------------------------------------------------|
| `ModuleNotFoundError: flask`        | venv not activated — `source venv/bin/activate`      |
| `OperationalError: no such table`   | run `python seed.py` first                           |
| `Address already in use`            | another process on port 5000 — `PORT=5050 python app.py` |
| Product images don't load           | `picsum.photos` blocked by network — use a different image host or local files |
| Cart looks empty after refresh      | LocalStorage disabled in browser settings (private mode) |
| `simulate_events.py` 0 products     | seed not run, or wrong `--base-url`                  |

---

## 16. Security caveats (v1 demo)

- **No auth on `/analytics`** or `/api/export/csv` — gate these with basic
  auth, an IP allowlist, or move them behind a VPN before any production use.
- **No CSRF protection** on order-intent submission — fine for a demo, not
  for production.
- WhatsApp number is taken from env, never from the client. Server
  recomputes prices to prevent client-side tampering.

---

## 17. Stopping the app

`Ctrl+C` in the terminal running `python app.py`. The SQLite DB and CSV
exports persist on disk (under `data/` and `exports/`).
