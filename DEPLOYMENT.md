# DEPLOYMENT.md

## 1. Purpose

This document explains how to deploy the Online Store Click Analytics / ShopPulse Flask application manually.

It is written for a human operator, so the steps are intentionally detailed. The recommended deployment target is PythonAnywhere because that is the planned hosting platform for this project.

## 2. What Will Be Deployed

The project has these main parts:

| Component | Purpose |
|---|---|
| Flask app | Website, product pages, cart, checkout, analytics routes |
| SQLite main DB | Stores products, categories, click events, carts, cart events, orders, model job metadata |
| SQLite prediction DB | Stores product-view prediction results shown in analytics |
| Random Forest model | Predicts cart probability and order probability by category/product-view features |
| Redis queue | Holds prediction jobs created when a user views a product |
| Prediction worker | Pulls jobs from Redis and writes model predictions |
| Hourly retraining job | Retrains/promotes model when active retraining triggers exist |
| Admin pages | Create categories and manually promote models |

Important current decisions:

- Database: SQLite
- Queue: Redis
- Auth: no auth for now
- Hosting target: PythonAnywhere
- Admin pages: enabled
- Model retraining: automatic via scheduled task, with manual promotion override

## 3. Deployment Architecture

Production flow:

```text
User Browser
    |
    v
PythonAnywhere Flask Web App
    |
    +--> SQLite main DB: data/shoppulse.db
    |
    +--> Redis queue: prediction_jobs
    |
    +--> SQLite prediction DB: data/prediction_analytics.db

PythonAnywhere Scheduled Task
    |
    +--> prediction_worker.py --once
    |
    +--> reads Redis jobs
    |
    +--> loads models/latest/model.joblib
    |
    +--> writes prediction rows

PythonAnywhere Scheduled Task
    |
    +--> hourly_retraining_job.py --once
    |
    +--> backs up DB
    |
    +--> retrains model
    |
    +--> promotes latest model
```

## 4. Accounts And Services Needed

You need:

- PythonAnywhere account
- GitHub repository containing this project
- Hosted Redis account
- Optional custom domain/DNS access

Redis options:

- Upstash Redis
- Redis Cloud
- Any external Redis provider that gives you a Redis URL

PythonAnywhere does not provide Redis by default, so you need an external Redis service.

## 5. Local Pre-Deployment Checklist

Run these locally before deploying.

From your local project folder:

```bash
cd Online-store-Click-Analytics
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Compile important Python files:

```bash
python -m py_compile app.py models.py config.py feature_pipeline.py prediction_store.py train_category_models.py predict_category_models.py queue_client.py prediction_worker.py backup_database.py hourly_retraining_job.py publish_model_release.py sync_latest_model.py
```

Run tests:

```bash
python -m pytest
```

Train and promote a model locally:

```bash
python train_category_models.py --promote
```

Confirm prediction model loads:

```bash
python predict_category_models.py
```

Create a backup locally:

```bash
python backup_database.py
```

If all commands pass, continue.

## 6. Files And Folders To Expect

Important folders:

```text
Online-store-Click-Analytics/
├── app.py
├── models.py
├── config.py
├── requirements.txt
├── data/
│   ├── shoppulse.db
│   ├── prediction_analytics.db
│   └── backups/
├── models/
│   ├── latest/
│   │   ├── model.joblib
│   │   ├── features.json
│   │   ├── metrics.json
│   │   ├── training_summary.json
│   │   └── model_card.md
│   └── runs/
│       └── category_rf_<timestamp>/
├── templates/
├── static/
├── prediction_worker.py
├── hourly_retraining_job.py
└── backup_database.py
```

Do not commit real `.env` secrets.

SQLite DB files may or may not be committed depending on whether you want demo data in GitHub. For production, uploading DB files manually is safer.

## 7. Environment Variables

Create these on PythonAnywhere in a `.env` file.

| Variable | Required | Used By | Description | Example |
|---|---:|---|---|---|
| `FLASK_SECRET_KEY` | Yes | Flask | Secret for session/signing | `long-random-string` |
| `FLASK_DEBUG` | Yes | Flask | Must be `0` in production | `0` |
| `DATABASE_URL` | Yes | Flask/SQLAlchemy | Main SQLite DB URL | `sqlite:////home/user/Online-store-Click-Analytics/data/shoppulse.db` |
| `PREDICTION_DB_PATH` | Yes | Prediction store | Prediction SQLite file path | `/home/user/Online-store-Click-Analytics/data/prediction_analytics.db` |
| `WHATSAPP_NUMBER` | Yes | Checkout | WhatsApp order number | `+919999999999` |
| `REDIS_URL` | Yes | Queue/worker | Redis connection URL | `redis://default:password@host:6379/0` |
| `REDIS_PREDICTION_QUEUE` | No | Queue/worker | Redis queue name | `prediction_jobs` |
| `MODEL_RUNS_DIR` | No | Training | Versioned model folder | `/home/user/Online-store-Click-Analytics/models/runs` |
| `MODEL_LATEST_DIR` | No | Prediction | Promoted model folder | `/home/user/Online-store-Click-Analytics/models/latest` |
| `BACKUP_DIR` | No | Backup/retraining | Backup folder | `/home/user/Online-store-Click-Analytics/data/backups` |
| `GITHUB_REPO` | No | Model release helper | GitHub repo name | `owner/repo` |
| `GITHUB_TOKEN` | No | Model release helper | GitHub token | secret value |

Example `.env`:

```env
FLASK_SECRET_KEY=replace-with-a-long-random-secret
FLASK_DEBUG=0
DATABASE_URL=sqlite:////home/<username>/Online-store-Click-Analytics/data/shoppulse.db
PREDICTION_DB_PATH=/home/<username>/Online-store-Click-Analytics/data/prediction_analytics.db
WHATSAPP_NUMBER=+919999999999
REDIS_URL=redis://default:<password>@<host>:6379/0
REDIS_PREDICTION_QUEUE=prediction_jobs
MODEL_RUNS_DIR=/home/<username>/Online-store-Click-Analytics/models/runs
MODEL_LATEST_DIR=/home/<username>/Online-store-Click-Analytics/models/latest
BACKUP_DIR=/home/<username>/Online-store-Click-Analytics/data/backups
```

Replace `<username>`, `<password>`, and `<host>`.

## 8. Prepare Redis

Create a Redis database using Upstash, Redis Cloud, or another provider.

After creating Redis, copy the Redis URL.

The URL usually looks like one of these:

```text
redis://default:<password>@<host>:6379/0
rediss://default:<password>@<host>:6379/0
```

Use `rediss://` if your provider requires TLS.

Add that value to:

```env
REDIS_URL=...
```

The queue name can stay:

```env
REDIS_PREDICTION_QUEUE=prediction_jobs
```

## 9. Push Code To GitHub

From your local machine:

```bash
git status
git add .
git commit -m "Prepare app for PythonAnywhere deployment"
git push
```

Check GitHub and confirm the latest code is visible.

## 10. Create PythonAnywhere Web App

In PythonAnywhere:

1. Log in.
2. Go to the **Web** tab.
3. Click **Add a new web app**.
4. Choose your domain.
5. Choose **Manual configuration**.
6. Choose Python `3.11` if available.
7. Finish the wizard.

Do not reload yet. First clone the project and configure the virtual environment.

## 11. Clone Project On PythonAnywhere

Open a PythonAnywhere Bash console.

Run:

```bash
cd ~
git clone <your-github-repo-url> Online-store-Click-Analytics
cd Online-store-Click-Analytics
```

Example:

```bash
git clone https://github.com/<owner>/<repo>.git Online-store-Click-Analytics
```

Confirm files exist:

```bash
ls
```

You should see files like:

```text
app.py
models.py
requirements.txt
templates
static
```

## 12. Create Virtual Environment On PythonAnywhere

From the project folder:

```bash
cd ~/Online-store-Click-Analytics
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If `python3.11` is not available, use the closest Python 3 version available on PythonAnywhere:

```bash
python3.10 -m venv venv
```

## 13. Create Required Folders

Run:

```bash
cd ~/Online-store-Click-Analytics
mkdir -p data
mkdir -p data/backups
mkdir -p models
mkdir -p models/latest
mkdir -p models/runs
```

## 14. Create `.env` On PythonAnywhere

Run:

```bash
cd ~/Online-store-Click-Analytics
cp .env.example .env
nano .env
```

Paste production values like:

```env
FLASK_SECRET_KEY=replace-with-a-long-random-secret
FLASK_DEBUG=0
DATABASE_URL=sqlite:////home/<username>/Online-store-Click-Analytics/data/shoppulse.db
PREDICTION_DB_PATH=/home/<username>/Online-store-Click-Analytics/data/prediction_analytics.db
WHATSAPP_NUMBER=+919999999999
REDIS_URL=redis://default:<password>@<host>:6379/0
REDIS_PREDICTION_QUEUE=prediction_jobs
MODEL_RUNS_DIR=/home/<username>/Online-store-Click-Analytics/models/runs
MODEL_LATEST_DIR=/home/<username>/Online-store-Click-Analytics/models/latest
BACKUP_DIR=/home/<username>/Online-store-Click-Analytics/data/backups
```

Save and exit:

- Press `Ctrl + O`
- Press `Enter`
- Press `Ctrl + X`

## 15. Prepare The Database

There are two options.

### Option A: Start With A New Database

Use this if you do not need local data.

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
python seed.py
```

This creates the main DB and seed products/categories.

The prediction DB is created automatically when prediction storage is initialized.

### Option B: Upload Existing Local SQLite DBs

Use this if you already have useful local event data.

Upload these local files to PythonAnywhere:

```text
data/shoppulse.db
data/prediction_analytics.db
```

Destination:

```text
/home/<username>/Online-store-Click-Analytics/data/
```

You can upload using:

- PythonAnywhere Files tab
- `scp`
- GitHub release/manual artifact

After upload, confirm:

```bash
ls -lh data
```

## 16. Train And Promote Initial Model

Run:

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
python train_category_models.py --promote
```

Expected result:

```text
models/runs/category_rf_<timestamp>/
models/latest/model.joblib
models/latest/features.json
models/latest/metrics.json
models/latest/training_summary.json
models/latest/model_card.md
```

Verify model loads:

```bash
python predict_category_models.py
```

If this fails, do not continue to web reload yet. Fix model/database issues first.

## 17. Configure PythonAnywhere WSGI

Go to PythonAnywhere **Web** tab.

Find **Code** section.

Click the WSGI config file link.

Replace the content with:

```python
import os
import sys

project_home = "/home/<username>/Online-store-Click-Analytics"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application
```

Replace `<username>` with your PythonAnywhere username.

Save the file.

## 18. Configure PythonAnywhere Virtualenv

In PythonAnywhere **Web** tab:

Find **Virtualenv**.

Set it to:

```text
/home/<username>/Online-store-Click-Analytics/venv
```

Click save/checkmark if needed.

## 19. Configure Static Files

In PythonAnywhere **Web** tab:

Find **Static files**.

Add:

| URL | Directory |
|---|---|
| `/static/` | `/home/<username>/Online-store-Click-Analytics/static/` |

Save the mapping.

## 20. Reload Web App

In PythonAnywhere **Web** tab:

Click:

```text
Reload
```

Open your site:

```text
https://<username>.pythonanywhere.com
```

## 21. First Web Smoke Test

Open these pages in the browser:

```text
/
/healthz
/products
/analytics
/prediction-analytics
/admin/categories
/admin/models
```

Expected:

- `/` loads homepage
- `/healthz` returns OK
- `/products` shows products
- `/analytics` loads analytics dashboard
- `/prediction-analytics` loads prediction table
- `/admin/categories` loads admin category form
- `/admin/models` loads model admin page

If any page gives 500:

1. Go to PythonAnywhere **Web** tab.
2. Open error log.
3. Fix the first error shown.
4. Reload the app.

## 22. Test Product View Event

In the browser:

1. Open `/products`.
2. Click a product.
3. This should create a `product_view` event.
4. It should also create a prediction job record.
5. It should push a job into Redis.

If Redis is unavailable, the job will be marked `queue_failed`.

## 23. Run Prediction Worker Manually

Before scheduling it, test the worker manually.

In PythonAnywhere Bash:

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
python prediction_worker.py --once
```

Then open:

```text
/prediction-analytics
```

Expected:

- A row appears with product name
- category name appears
- event type appears
- cart/order prediction values appear
- model version appears

## 24. Configure Scheduled Prediction Worker

PythonAnywhere may not support always-on background workers depending on your plan.

Use scheduled tasks first.

In PythonAnywhere:

1. Go to **Tasks** tab.
2. Add a scheduled task.
3. Run every 1 to 5 minutes.
4. Command:

```bash
cd /home/<username>/Online-store-Click-Analytics && source venv/bin/activate && python prediction_worker.py --once
```

Recommended:

```text
Every 1 minute for active testing
Every 5 minutes for lighter production usage
```

## 25. Configure Hourly Retraining

When a category is created from `/admin/categories`, the app creates an active retraining trigger for the next 3 days.

The hourly retraining task checks those triggers.

In PythonAnywhere:

1. Go to **Tasks** tab.
2. Add a scheduled task.
3. Run every hour.
4. Command:

```bash
cd /home/<username>/Online-store-Click-Analytics && source venv/bin/activate && python hourly_retraining_job.py --once
```

What this does:

1. Checks active retraining triggers.
2. Backs up the SQLite DB.
3. Trains a new model.
4. Saves a timestamped model version under `models/runs/`.
5. Promotes the new model to `models/latest/`.

## 26. Test Category Retraining Trigger

Open:

```text
/admin/categories
```

Create a new category.

Expected:

- Category is created.
- A retraining trigger is created.
- Trigger remains active for 3 days.

Then manually run:

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
python hourly_retraining_job.py --once
```

Open:

```text
/admin/models
```

Expected:

- New model run appears.
- `models/latest` points to the promoted model.

## 27. Manual Model Promotion

Open:

```text
/admin/models
```

Use the promotion form/button to promote a specific model version.

You can also promote from Bash:

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
python sync_latest_model.py --model-version category_rf_<timestamp>
```

After promotion:

1. Reload the web app.
2. Run `python predict_category_models.py`.
3. Check `/prediction-analytics`.

## 28. Manual Database Backup

Run this before large changes:

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
python backup_database.py
```

Expected:

```text
data/backups/<timestamp>/shoppulse_<timestamp>.db
data/backups/<timestamp>/prediction_analytics_<timestamp>.db
data/backups/<timestamp>/backup_metadata.json
```

## 29. Manual Database Restore

Use restore only when needed.

First, reduce writes:

1. Pause scheduled tasks if possible.
2. Avoid using the website during restore.

Then restore:

```bash
cd ~/Online-store-Click-Analytics
cp data/backups/<timestamp>/shoppulse_<timestamp>.db data/shoppulse.db
cp data/backups/<timestamp>/prediction_analytics_<timestamp>.db data/prediction_analytics.db
```

Reload PythonAnywhere web app.

Run smoke test again.

## 30. Model Rollback

To roll back to a previous model:

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
python sync_latest_model.py --model-version category_rf_<previous_timestamp>
```

Reload the web app.

Verify:

```bash
python predict_category_models.py
```

Open:

```text
/admin/models
/prediction-analytics
```

## 31. GitHub Release Model Registry

The project includes a helper for publishing model artifacts to GitHub Releases.

Dry run:

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
python publish_model_release.py --run-dir models/latest --dry-run
```

Actual release requires GitHub CLI authentication:

```bash
gh auth login
```

Then:

```bash
python publish_model_release.py --run-dir models/latest
```

This publishes:

```text
model.joblib
features.json
metrics.json
training_summary.json
model_card.md
```

This step is optional for the first deployment.

## 32. Domain Setup

For default PythonAnywhere domain:

```text
https://<username>.pythonanywhere.com
```

No DNS setup is needed.

For custom domain:

1. Go to PythonAnywhere **Web** tab.
2. Add custom domain.
3. In your DNS provider, create CNAME:

```text
www -> <username>.pythonanywhere.com
```

4. Wait for DNS propagation.
5. Enable SSL in PythonAnywhere.
6. Test:

```text
https://www.<your-domain>
```

## 33. Final Production Smoke Test

After everything is configured, test this full flow:

1. Open homepage.
2. Open products page.
3. Open product detail page.
4. Confirm product view is tracked.
5. Run prediction worker once.
6. Open prediction analytics.
7. Add product to cart.
8. Open cart.
9. Start checkout.
10. Submit WhatsApp checkout.
11. Open analytics.
12. Create category from admin page.
13. Run hourly retraining once.
14. Open admin model page.
15. Confirm latest model exists.

Optional DB checks:

```sql
SELECT event_type, COUNT(*) FROM click_events GROUP BY event_type;
SELECT event_type, COUNT(*) FROM cart_events GROUP BY event_type;
SELECT COUNT(*) FROM carts;
SELECT COUNT(*) FROM prediction_jobs;
SELECT COUNT(*) FROM retraining_triggers;
```

## 34. Logs To Check

PythonAnywhere logs:

- Error log
- Server log
- Access log
- Scheduled task logs

Common things to watch:

- `ModuleNotFoundError`
- wrong virtualenv path
- bad `.env` path/value
- SQLite permission errors
- Redis connection errors
- missing model file
- failed prediction jobs
- 500 responses on `/api/track-event`

## 35. Common Problems

| Problem | Likely Cause | Fix |
|---|---|---|
| App shows 500 | WSGI import error or missing env var | Check PythonAnywhere error log |
| `ModuleNotFoundError` | Wrong virtualenv | Set virtualenv path in Web tab and reinstall requirements |
| DB connection error | Bad SQLite URL | Use `sqlite:////home/<username>/.../data/shoppulse.db` |
| `no such table` | DB not initialized | Run `python seed.py` or verify uploaded DB |
| Static files missing | Static mapping not configured | Map `/static/` to project `static/` folder |
| Prediction page empty | Worker not running or no product views | View product, run `prediction_worker.py --once` |
| Redis connection error | Bad `REDIS_URL` or provider blocked | Verify Redis URL and TLS setting |
| Model load fails | No promoted model | Run `python train_category_models.py --promote` |
| Scheduled task fails | Wrong path or virtualenv | Use absolute `/home/<username>/...` paths |
| Category retraining not happening | No active trigger or task not scheduled | Create category and run hourly job manually |
| SQLite locked | Too many concurrent writes | Reduce scheduled task overlap and keep tasks short |
| WhatsApp link wrong | Bad `WHATSAPP_NUMBER` | Fix `.env` and reload |
| Debug visible | `FLASK_DEBUG=1` | Set `FLASK_DEBUG=0` |

## 36. Production Hardening Checklist

Before sharing the app widely:

- `FLASK_DEBUG=0`
- Strong `FLASK_SECRET_KEY`
- `.env` not committed
- PythonAnywhere app reloads successfully
- Static files configured
- Redis URL tested
- Prediction worker scheduled
- Hourly retraining scheduled
- DB backup script tested
- Initial model trained and promoted
- Admin pages reviewed for exposure risk
- SQLite backups stored safely
- Error logs checked after deployment
- HTTPS enabled

## 37. Ongoing Operations

Daily:

- Check PythonAnywhere error logs.
- Check prediction analytics page.
- Confirm scheduled tasks are running.

Weekly:

- Download/copy SQLite backups.
- Review model metrics.
- Review failed prediction jobs.

After adding new categories:

- Confirm retraining trigger exists.
- Confirm hourly task creates new model runs.
- Confirm promoted model works.

Before major changes:

- Run `python backup_database.py`.
- Note current model version.
- Keep previous `models/latest` backup or model run.

## 38. Minimal Command Reference

Activate environment:

```bash
cd ~/Online-store-Click-Analytics
source venv/bin/activate
```

Run tests:

```bash
python -m pytest
```

Train and promote model:

```bash
python train_category_models.py --promote
```

Run prediction worker once:

```bash
python prediction_worker.py --once
```

Run retraining job once:

```bash
python hourly_retraining_job.py --once
```

Create DB backup:

```bash
python backup_database.py
```

Rollback model:

```bash
python sync_latest_model.py --model-version category_rf_<timestamp>
```

Check model predictions:

```bash
python predict_category_models.py
```

## 39. Open Deployment Decisions

These still need human decisions:

- Which Redis provider will be used?
- Should admin routes stay public, or should basic admin protection be added later?
- How often should SQLite backups be copied outside PythonAnywhere?
- Should GitHub Releases be used for every promoted model or only major model versions?
- Should prediction worker run every 1 minute or 5 minutes on PythonAnywhere?

