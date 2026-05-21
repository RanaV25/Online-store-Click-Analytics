# DEPLOYMENT.md

## 1. Purpose

This file is a manual deployment guide for a human deploying ShopPulse. It focuses on PythonAnywhere because the project owner stated that future deployment will be there. It also marks missing production pieces clearly.

## 2. Deployment Overview

### App components

- Flask backend in `app.py`
- Jinja templates in `templates/`
- Static assets in `static/`
- SQLAlchemy models in `models.py`
- Main SQLite DB: `data/shoppulse.db`
- Prediction SQLite DB: `data/prediction_analytics.db`
- ML training script: `train_category_models.py`
- Prediction script/helper: `predict_category_models.py`, `prediction_store.py`
- Optional browser automation: `automate_clicks.py`

### Deployment target

Primary target:

```text
PythonAnywhere
```

### Runtime

Detected from README and venv:

```text
Python 3.10+ required
Python 3.11 used in development
```

### Database

Chosen production DB:

```text
SQLite
```

### External services

Current code uses:

- WhatsApp deep link via `wa.me`
- Bootstrap/Bootstrap Icons CDN
- Chart.js CDN
- Picsum image URLs in seeded data

Proposed advanced MLOps uses:

- GitHub Releases
- GitHub Actions
- Redis queue service

### Authentication

Not found in current codebase.

Internal routes currently unprotected:

- `/analytics`
- `/prediction-analytics`
- `/api/export/csv`

## 3. Prerequisites

### Accounts

- PythonAnywhere account
- GitHub account and repository
- Domain/DNS access if using custom domain

### Local tools

- Git
- Python 3.10 or 3.11
- pip
- virtualenv support

### PythonAnywhere tools

- Bash console
- Web app configuration page
- Files tab or Git clone access
- Scheduled tasks, if using retraining jobs

### Optional future tools

- GitHub CLI or GitHub Actions
- Redis or queue provider
- Redis provider/account

## 4. Environment Variables

| Variable | Required | Used By | Description | Example Format | Where to Get It |
|---|---:|---|---|---|---|
| `FLASK_SECRET_KEY` | Yes | Flask app | Session/signing secret | `long-random-string` | Generate manually |
| `WHATSAPP_NUMBER` | Yes | Checkout | WhatsApp order target | `+919999999999` | Store owner |
| `DATABASE_URL` | Yes | Flask/SQLAlchemy | Main DB connection | `sqlite:////home/user/app/data/shoppulse.db` | PythonAnywhere path |
| `FLASK_DEBUG` | Yes | Flask app | Must be off in prod | `0` | Set manually |
| `PORT` | No | Local only | Local dev port | `5000` | Local preference |
| `MODEL_LATEST_DIR` | Proposed | Prediction | Latest model dir | `/home/user/app/models/latest` | Deployment path |
| `MODEL_RUNS_DIR` | Proposed | Training | Versioned model dir | `/home/user/app/models/runs` | Deployment path |
| `PREDICTION_DB_URL` | Proposed | Prediction | Prediction DB path/URL | `sqlite:////home/user/app/data/prediction_analytics.db` | Deployment path |
| `BACKUP_DIR` | Proposed | Retraining | DB backup dir | `/home/user/app/data/backups` | Deployment path |
| `GITHUB_REPO` | Proposed | Model sync | Registry repo | `owner/repo` | GitHub |
| `GITHUB_TOKEN` | Proposed | Model sync/release | GitHub API token | secret value | GitHub |
| `REDIS_URL` | Proposed | Prediction worker | Redis queue connection | `redis://...` | Redis provider |

Do not commit real `.env` files.

## 5. Local Pre-Deployment Checklist

Run locally before deployment:

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py
python train_category_models.py
python predict_category_models.py
python -m py_compile app.py models.py train_category_models.py prediction_store.py
python app.py
```

Smoke test locally:

```bash
curl http://localhost:5000/healthz
curl -I http://localhost:5000/
curl -I http://localhost:5000/products
curl -I http://localhost:5000/analytics
curl -I http://localhost:5000/prediction-analytics
```

Not found in current codebase:

- lint command
- pytest test suite
- type check command
- build command
- migration command

## 6. Database Setup

### Current SQLite setup

The app creates tables on startup through `db.create_all()` and compatibility logic in `app.py`.

Initial seed:

```bash
python seed.py
```

Expected DB files:

```text
data/shoppulse.db
data/prediction_analytics.db
```

### Backup before deployment

Before uploading/changing DB:

```bash
mkdir -p data/backups
cp data/shoppulse.db data/backups/shoppulse_predeploy_YYYYMMDD_HHMMSS.db
cp data/prediction_analytics.db data/backups/prediction_analytics_predeploy_YYYYMMDD_HHMMSS.db
```

### Migration notes

No formal migration system exists. Schema changes must be handled carefully.

Rollback:

```bash
cp data/backups/shoppulse_predeploy_YYYYMMDD_HHMMSS.db data/shoppulse.db
cp data/backups/prediction_analytics_predeploy_YYYYMMDD_HHMMSS.db data/prediction_analytics.db
```

## 7. Deployment Steps

### Step 1: Clone project on PythonAnywhere

In PythonAnywhere Bash:

```bash
cd ~
git clone <your-repo-url> Online-store-Click-Analytics
cd Online-store-Click-Analytics
```

### Step 2: Create virtualenv

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If PythonAnywhere does not provide Python 3.11, use the closest available Python 3.10+ version.

### Step 3: Create `.env`

```bash
cp .env.example .env
nano .env
```

Production example:

```text
FLASK_SECRET_KEY=<generate-a-long-random-secret>
WHATSAPP_NUMBER=+919999999999
DATABASE_URL=sqlite:////home/<username>/Online-store-Click-Analytics/data/shoppulse.db
FLASK_DEBUG=0
```

### Step 4: Create required folders

```bash
mkdir -p data
mkdir -p data/backups
mkdir -p models
mkdir -p models/latest
mkdir -p models/runs
```

### Step 5: Seed database

Only run this for a new database:

```bash
source venv/bin/activate
python seed.py
```

### Step 6: Train initial model

```bash
source venv/bin/activate
python train_category_models.py
```

Current code saves:

```text
models/category_random_forest_model.joblib
models/category_random_forest_features.joblib
```

If using future `models/latest/` flow, copy selected artifacts there after implementation.

### Step 7: Configure PythonAnywhere web app

In PythonAnywhere Web tab:

1. Create a new web app.
2. Choose manual configuration.
3. Select Python version.
4. Set source code directory:

```text
/home/<username>/Online-store-Click-Analytics
```

5. Set virtualenv:

```text
/home/<username>/Online-store-Click-Analytics/venv
```

6. Edit WSGI file.

Example WSGI content:

```python
import sys
from pathlib import Path

project_home = "/home/<username>/Online-store-Click-Analytics"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application
```

### Step 8: Static files

Current app serves static files through Flask. For PythonAnywhere, configure:

| URL | Directory |
|---|---|
| `/static/` | `/home/<username>/Online-store-Click-Analytics/static/` |

### Step 9: Reload web app

Use PythonAnywhere Web tab:

```text
Reload
```

### Step 10: Optional scheduled tasks

Current code has no hourly retraining job yet.

After implementation, add scheduled tasks:

```bash
cd /home/<username>/Online-store-Click-Analytics
source venv/bin/activate
python hourly_retraining_job.py
```

If using DB-backed prediction jobs:
Prediction queue decision: use Redis. The DB-backed queue should only be treated as a fallback if Redis is unavailable.

If a DB-backed fallback is implemented:

```bash
cd /home/<username>/Online-store-Click-Analytics
source venv/bin/activate
python prediction_worker.py --once
```

## 8. Domain and DNS Setup

For default PythonAnywhere domain:

```text
<username>.pythonanywhere.com
```

For custom domain:

1. Add domain in PythonAnywhere Web tab.
2. Create DNS CNAME:

```text
www -> <username>.pythonanywhere.com
```

3. Configure SSL in PythonAnywhere.
4. Verify HTTPS works.

CORS:

Not configured in current codebase. Not needed for same-origin server-rendered app unless APIs are called from another domain.

## 9. Manual Smoke Test

After deployment:

- Open homepage.
- Open `/healthz`.
- Open `/products`.
- Open a product detail page.
- Confirm a `product_view` event is saved.
- Add product to cart.
- Open cart.
- Proceed to checkout.
- Submit order.
- Confirm WhatsApp tab opens.
- Confirm order success page loads.
- Open `/analytics`.
- Open `/prediction-analytics`.
- Confirm prediction rows appear after product views.

Optional DB checks:

```sql
SELECT event_type, COUNT(*) FROM click_events GROUP BY event_type;
SELECT event_type, COUNT(*) FROM cart_events GROUP BY event_type;
SELECT COUNT(*) FROM order_intents;
```

## 10. Monitoring and Logs

PythonAnywhere logs:

- Error log
- Server log
- Access log

Watch for:

- `ModuleNotFoundError`
- SQLite permission errors
- missing `.env`
- missing model file
- prediction DB write failures
- template errors
- 500 responses on `/api/track-event`

Basic metrics to review:

- Product views per day
- Add-to-cart count
- Checkout started count
- WhatsApp order clicks
- Prediction rows per day
- Failed prediction jobs, after worker implementation

## 11. Backup and Recovery

### Manual backup

```bash
cd /home/<username>/Online-store-Click-Analytics
mkdir -p data/backups
cp data/shoppulse.db data/backups/shoppulse_$(date +%Y%m%d_%H%M%S).db
cp data/prediction_analytics.db data/backups/prediction_analytics_$(date +%Y%m%d_%H%M%S).db
```

### Restore

1. Stop or reload app to reduce writes.
2. Copy backup into place:

```bash
cp data/backups/shoppulse_<timestamp>.db data/shoppulse.db
cp data/backups/prediction_analytics_<timestamp>.db data/prediction_analytics.db
```

3. Reload web app.

### Model rollback

Current code:

```text
models/category_random_forest_model.joblib
```

Future versioned flow:

```bash
rm -rf models/latest
cp -R models/runs/<previous-good-version> models/latest
```

Reload app after rollback.

## 12. Common Deployment Problems

| Problem | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: flask` | Wrong virtualenv or dependencies not installed | Set PythonAnywhere virtualenv and run `pip install -r requirements.txt` |
| App returns 500 | Bad WSGI path or import error | Check PythonAnywhere error log |
| DB connection error | Bad `DATABASE_URL` path | Use absolute SQLite URI with four slashes after `sqlite:` |
| `no such table` | DB not initialized | Run `python seed.py` or start app once |
| Static files not loading | Static mapping missing | Map `/static/` to project `static/` directory |
| Product images broken | External image host blocked | Use local/static images or another image host |
| Prediction page empty | No product views or missing model | Visit product detail page and train model |
| Model load fails | Missing `.joblib` file | Run `python train_category_models.py` |
| SQLite permission error | Directory not writable | Check ownership and write permission for `data/` |
| Debug visible in prod | `FLASK_DEBUG=1` | Set `FLASK_DEBUG=0` |
| Admin/internal pages exposed | No auth required by owner for now | Keep routes internal/demo-only or add auth later if requirements change |
| Scheduled task does nothing | Script not implemented or no active triggers | Check task output and trigger table |
| Domain not resolving | DNS not propagated or wrong CNAME | Verify DNS records |
| SSL issue | Certificate not configured | Enable SSL in PythonAnywhere |

## 13. Production Hardening Checklist

- `FLASK_DEBUG=0`
- Strong `FLASK_SECRET_KEY`
- Admin/internal pages reviewed for exposure risk
- `/api/export/csv` protected
- DB backups enabled
- Error logs monitored
- Static file mapping configured
- HTTPS enabled
- `.env` not committed
- DB files not committed unless intentionally using demo data
- Model file exists before enabling prediction
- Backup before schema change
- Rate limiting considered for event APIs

## 14. Post-Deployment Tasks

- Record deployment URL.
- Record PythonAnywhere username and app path.
- Confirm seed data exists.
- Confirm checkout WhatsApp number is correct.
- Confirm analytics events are written.
- Confirm predictions are written.
- Train and verify initial model.
- Document current model version.
- Create first DB backup.
- Test rollback with a copied DB in a safe environment.

## 15. Open Deployment Questions

### Resolved Owner Decisions

- Production will keep SQLite.
- Prediction jobs will use Redis.
- No auth method is required for now.
- Categories will be created from admin pages.
- Model training and promotion should be automatic.
- Manual override should exist for promotion/rollback.

### Remaining Questions

- Which Redis provider will be used?
- Who has permission to access the admin pages operationally?
- Where should long-term DB backups be stored?
- Should GitHub Releases contain only model artifacts or also metrics/model cards?
