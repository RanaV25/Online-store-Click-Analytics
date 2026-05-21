# Advanced MLOps Strategy and Implementation Specs

This document describes the ambitious target architecture for ShopPulse.

The goal is to move from a local/demo ML workflow to a deployed MLOps workflow with:

- PythonAnywhere-hosted Flask app
- Central production database
- Automated event collection
- Queue-based prediction
- External training system
- Automated model retraining triggers
- Versioned model registry using GitHub Actions + GitHub Releases
- Prediction monitoring dashboard
- Safe database backups before training

## Target Architecture

```text
Users
  -> PythonAnywhere Flask app
  -> production database
  -> event queue
  -> prediction worker
  -> prediction database/table
  -> prediction analytics dashboard

Production database
  -> scheduled backup/export
  -> external ML training system
  -> model training
  -> GitHub Actions validation
  -> GitHub Release model version
  -> approved latest model
  -> PythonAnywhere app downloads latest model
```

## System Responsibilities

### 1. PythonAnywhere Web App

Responsibilities:

- Serve storefront pages
- Capture click/cart/order events
- Store raw events
- Create retraining triggers when categories are added
- Send product-view events to a queue for prediction
- Display prediction analytics
- Load the latest automatically promoted model

### 2. Production Database

Chosen production database:

- SQLite

Current SQLite files:

- `data/shoppulse.db`
- `data/prediction_analytics.db`

Future recommended database layout:

```text
main app DB:
  products
  categories
  click_events
  cart_events
  carts
  cart_items
  order_intents
  retraining_triggers
  model_deployments

prediction DB/table:
  product_view_predictions
  prediction_jobs
```

### 3. Event Queue

Chosen queue:

```text
Redis Queue + worker
```

Prediction flow:

```text
product_view event
  -> write raw event to DB
  -> enqueue prediction job
  -> worker consumes job
  -> worker loads latest model
  -> worker builds feature row
  -> worker predicts cart/order probabilities
  -> worker writes prediction row
```

## Automated Retraining Trigger

Requirement:

```text
Any new category creation must trigger automated retraining every hour for the next 3 days.
```

Implementation design:

Do not create 72 separate jobs. Instead:

1. Create one persistent trigger row when a category is created.
2. Run one hourly scheduled retraining check.
3. The hourly job retrains only if an active trigger exists.

Required table:

```text
retraining_triggers
- id
- trigger_type
- category_id
- category_name
- reason
- created_at
- active_until
- status
- last_checked_at
- last_training_run_id
```

Example row:

```text
trigger_type = "new_category"
category_name = "Footwear"
created_at = 2026-05-19 22:00:00
active_until = 2026-05-22 22:00:00
status = "active"
```

Hourly retraining logic:

```text
every hour:
  find active triggers where now < active_until
  if none:
      exit
  backup production DB
  train model from backup
  save timestamped model version
  evaluate metrics
  publish model version
  optionally promote to latest
  update trigger last_training_run_id
  expire old triggers where now >= active_until
```

## Database Backup Before Training

Requirement:

```text
Saving the PythonAnywhere DB file should happen automatically as part of model retraining.
```

Rule:

```text
Never train directly on the live SQLite DB file.
```

Safe flow:

```text
live DB
  -> timestamped backup DB
  -> train from backup DB
```

Backup folder:

```text
data/backups/
  shoppulse_20260519_230000.db
  prediction_analytics_20260519_230000.db
```

Training run should store the backup path in metadata:

```text
training_summary.json:
  source_db_backup: data/backups/shoppulse_20260519_230000.db
```

## Model Versioning

Model versions are created only during training.

Predictions do not create model versions.

Version format:

```text
category_rf_YYYYMMDD_HHMMSS
```

Example:

```text
category_rf_20260519_230000
```

This means:

```text
category Random Forest model trained at 2026-05-19 23:00:00
```

## Model Registry

Use GitHub Actions + GitHub Releases as a lightweight model registry.

GitHub Actions is the automation layer.

GitHub Releases is the model registry storage.

Each model release should be named:

```text
category_rf_20260519_230000
```

Each release should contain:

```text
model.joblib
features.json
metrics.json
training_summary.json
model_card.md
```

Recommended local folder structure before upload:

```text
models/
  latest/
    model.joblib
    features.json
    metrics.json
    training_summary.json

  runs/
    category_rf_20260519_230000/
      model.joblib
      features.json
      metrics.json
      training_summary.json
      model_card.md
```

Meaning:

```text
models/runs/ = model history
models/latest/ = currently deployed model
GitHub Releases = remote model registry
```

## Model Promotion Rules

Training and promotion should be automatic, with manual override available.

Automatically promote a model to latest only if:

- Feature columns match expected schema
- Training completed successfully
- Metrics are valid
- New MAE is better than current latest model, or a configured override permits promotion
- Predictions are within expected range

Promotion flow:

```text
train candidate model
  -> save candidate run
  -> compare metrics to current latest
  -> if accepted:
        copy candidate to models/latest/
        upload release to GitHub
        PythonAnywhere downloads latest
        reload app
```

## Code Change Specs

This section lists required code changes only. It does not include implementation code.

## Code Implementation Design

This section describes how the code should be organized when the advanced MLOps design is implemented.

### 1. App Configuration

Update:

```text
config.py
```

Add configuration values:

```text
MODEL_REGISTRY_MODE
MODEL_LATEST_DIR
MODEL_RUNS_DIR
PREDICTION_DB_URL
BACKUP_DIR
QUEUE_BACKEND
GITHUB_REPO
GITHUB_TOKEN
```

Purpose:

- Keep local, PythonAnywhere, and training-machine settings separate.
- Avoid hardcoded model paths.
- Let the app always load the current deployed model from `models/latest/`.

### 2. Database Models

Update:

```text
models.py
```

Add SQLAlchemy models:

```text
RetrainingTrigger
TrainingRun
ModelDeployment
PredictionJob
```

Purpose:

- `RetrainingTrigger` controls hourly retraining after category creation.
- `TrainingRun` records each model training attempt.
- `ModelDeployment` records which model version is currently deployed.
- `PredictionJob` is a database-backed fallback queue if Redis is unavailable.

### 3. Category Creation Flow

Update:

```text
app.py
```

Add or extend category creation logic.

Runtime behavior:

```text
admin/user creates new category
  -> category row is inserted
  -> retraining trigger row is inserted
  -> active_until = now + 3 days
```

Implementation functions:

```text
create_category(...)
create_retraining_trigger(...)
```

The category creation endpoint should not train the model directly. It should only create the trigger.

### 4. Product View Prediction Flow

Current flow:

```text
product_view event
  -> raw event saved
  -> prediction generated immediately
```

Target flow:

```text
product_view event
  -> raw event saved
  -> prediction job created
  -> worker processes prediction job
  -> prediction result saved
```

Files:

```text
app.py
prediction_store.py
prediction_worker.py
```

Implementation functions:

```text
enqueue_prediction_job(payload)
process_prediction_job(job_id)
load_latest_model()
build_prediction_features(product_id)
save_prediction_result(...)
```

Why this design:

- The website remains fast.
- Model prediction failures do not break user browsing.
- Prediction can later move to another machine.

### 5. Prediction Worker

Create:

```text
prediction_worker.py
```

Responsibilities:

```text
poll queue
load latest model
build features
run prediction
save prediction result
mark job complete/failed
```

Use Redis:

```text
Redis queue -> prediction_worker.py
```

Optional fallback only if Redis is unavailable:

```text
prediction_jobs table -> prediction_worker.py polling loop
```

The worker should always load:

```text
models/latest/model.joblib
```

It should not load random timestamped model folders.

### 6. Feature Pipeline

Update:

```text
train_category_models.py
```

Split feature creation into reusable functions:

```text
load_tables(database_url)
build_category_dataframe(tables)
create_train_test(category_df)
```

Future improvement:

Create:

```text
feature_pipeline.py
```

Move reusable feature logic there so both training and prediction can import the same code.

Target design:

```text
feature_pipeline.py
  -> used by train_category_models.py
  -> used by prediction_worker.py
```

This prevents training/prediction feature mismatch.

### 7. Database Backup Before Training

Create:

```text
backup_database.py
```

Runtime behavior:

```text
hourly job starts
  -> backup live DB
  -> verify backup exists
  -> pass backup path to training script
```

Implementation functions:

```text
create_db_backup(source_db_path, backup_dir)
verify_backup(backup_path)
```

The training script should train from the backup:

```text
python train_category_models.py --db-path data/backups/shoppulse_YYYYMMDD_HHMMSS.db
```

### 8. Hourly Retraining Job

Create:

```text
hourly_retraining_job.py
```

Runtime behavior:

```text
load active retraining triggers
if no active triggers:
    exit
backup DB
train model
save model run
compare metrics
publish release
promote if accepted
update trigger/training metadata
```

Implementation functions:

```text
get_active_retraining_triggers()
expire_old_triggers()
run_training_from_backup(...)
compare_with_latest(...)
promote_model_if_accepted(...)
```

This script is what PythonAnywhere scheduled tasks or GitHub Actions should run hourly.

### 9. Model Training Script

Update:

```text
train_category_models.py
```

New arguments:

```text
--db-path
--database-url
--output-dir
--promote
--model-type
```

Runtime output:

```text
models/runs/<model_version>/
  model.joblib
  features.json
  metrics.json
  training_summary.json
  model_card.md
```

If `--promote` is passed and metrics are accepted:

```text
models/runs/<model_version>/ -> models/latest/
```

The script should write a `TrainingRun` row with:

```text
model_version
status
metrics
artifact_path
source_db_backup
```

### 10. Model Registry Publishing

Create:

```text
publish_model_release.py
```

Responsibilities:

```text
read model run folder
create GitHub Release
upload artifacts
save release URL
```

GitHub Release assets:

```text
model.joblib
features.json
metrics.json
training_summary.json
model_card.md
```

Only trained models create releases.

Predictions never create releases.

### 11. Latest Model Sync

Create:

```text
sync_latest_model.py
```

Runtime behavior:

```text
check latest approved GitHub Release
download artifacts
replace models/latest/
record deployment
reload app if needed
```

The Flask app and prediction worker should load only:

```text
models/latest/model.joblib
```

### 12. Prediction Analytics

Update:

```text
prediction_store.py
templates/prediction_analytics.html
```

Prediction rows should include:

```text
product_name
category_name
event_time
event_type
predicted_cart_probability
predicted_order_probability
model_version
prediction_time
feature_snapshot_json
```

Dashboard should show:

- Recent predictions
- Model version used
- Prediction probabilities
- Category/product context
- Actual outcome when available

### 13. Monitoring and Metrics

Create:

```text
monitor_model_performance.py
```

Responsibilities:

```text
join predictions with later cart/order events
calculate actual outcomes
calculate MAE over time
flag drift or poor performance
```

Basic monitoring output:

```text
prediction_count
avg_predicted_cart_probability
actual_cart_rate
avg_predicted_order_probability
actual_order_rate
mae_cart
mae_order
```

### 14. GitHub Actions Workflow

Create:

```text
.github/workflows/model-training.yml
```

Workflow steps:

```text
checkout repo
setup Python
install dependencies
download or receive DB backup
run train_category_models.py
run validation checks
publish GitHub Release
optionally notify PythonAnywhere
```

Manual trigger:

```text
workflow_dispatch
```

Scheduled trigger:

```text
cron hourly
```

### 15. PythonAnywhere Scheduled Tasks

Create scheduled tasks:

```text
hourly_retraining_job.py
sync_latest_model.py
prediction_worker.py or prediction job poller
```

Recommended schedule:

```text
hourly_retraining_job.py -> hourly
sync_latest_model.py -> hourly or after release
prediction_worker.py -> always-on task if available, otherwise every minute polling
```

## End-to-End Code Flow

### New Category Flow

```text
category created
  -> app.py inserts Category
  -> app.py inserts RetrainingTrigger
  -> hourly_retraining_job.py sees active trigger
  -> backup_database.py copies DB
  -> train_category_models.py trains model from backup
  -> publish_model_release.py publishes model version
  -> sync_latest_model.py updates models/latest/
```

### Product View Prediction Flow

```text
user opens product detail page
  -> frontend sends product_view
  -> app.py saves ClickEvent
  -> app.py creates PredictionJob
  -> prediction_worker.py processes job
  -> prediction_worker.py loads models/latest/model.joblib
  -> feature_pipeline.py builds feature row
  -> prediction_store.py saves prediction result
  -> /prediction-analytics displays result
```

### Model Deployment Flow

```text
new model trained
  -> metrics checked
  -> model released on GitHub
  -> selected model promoted
  -> models/latest/ updated
  -> model_deployments row inserted
  -> app/worker uses new latest model
```

### 1. Category Creation Trigger

Add a proper category creation endpoint or admin flow.

When a new category is created:

- Insert category into `categories`
- Insert row into `retraining_triggers`
- Set `active_until = now + 3 days`
- Set `status = active`

Files likely affected:

```text
models.py
app.py
templates/admin_categories.html
```

New model/table:

```text
RetrainingTrigger
```

### 2. Retraining Trigger Table

Add table:

```text
retraining_triggers
```

Columns:

```text
id
trigger_type
category_id
category_name
reason
created_at
active_until
status
last_checked_at
last_training_run_id
```

### 3. Training Run Metadata Table

Add table:

```text
training_runs
```

Columns:

```text
id
model_version
model_type
status
started_at
finished_at
source_db_backup
metrics_json
artifact_path
github_release_url
promoted_to_latest
created_by
```

### 4. Database Backup Script

Create script:

```text
backup_database.py
```

Responsibilities:

- Locate production DB
- Create timestamped backup directory
- Copy `shoppulse.db`
- Copy `prediction_analytics.db`
- Verify backup file exists
- Return backup path to training script

### 5. Hourly Retraining Job

Create script:

```text
hourly_retraining_job.py
```

Responsibilities:

- Check `retraining_triggers`
- Exit if no active trigger
- Expire old triggers
- Run database backup
- Run model training using backup DB
- Save model version
- Compare metrics
- Promote if accepted
- Update `training_runs`
- Update trigger metadata

### 6. Training Script Upgrade

Update:

```text
train_category_models.py
```

Required changes:

- Accept `--database-url` or `--db-path`
- Accept `--output-dir`
- Generate timestamped `model_version`
- Save artifacts into `models/runs/<model_version>/`
- Save:
  - `model.joblib`
  - `features.json`
  - `metrics.json`
  - `training_summary.json`
  - `model_card.md`
- Optionally copy accepted model into `models/latest/`

### 7. GitHub Release Publisher

Create script:

```text
publish_model_release.py
```

Responsibilities:

- Read model run folder
- Create GitHub Release with model version tag
- Upload model artifacts
- Save release URL into training metadata

Can use:

```text
GitHub CLI
GitHub API
GitHub Actions upload-release-asset action
```

### 8. GitHub Actions Workflow

Create workflow:

```text
.github/workflows/model-training.yml
```

Responsibilities:

- Run on schedule or manual dispatch
- Install dependencies
- Fetch or receive production DB backup
- Run training
- Save model artifacts
- Create GitHub Release
- Optionally notify PythonAnywhere

Triggers:

```text
workflow_dispatch
schedule
```

Schedule example:

```text
hourly
```

### 9. PythonAnywhere Model Sync

Create script:

```text
sync_latest_model.py
```

Responsibilities:

- Check latest approved GitHub Release
- Download model artifacts
- Replace `models/latest/`
- Clear model cache if needed
- Log deployment in `model_deployments`

### 10. Prediction Worker

Create worker:

```text
prediction_worker.py
```

Responsibilities:

- Read product-view jobs from queue
- Load `models/latest/model.joblib`
- Build category features
- Predict probabilities
- Save prediction row

### 11. Prediction Job Queue

Modify product-view handling:

Current:

```text
product_view -> immediate prediction
```

Target:

```text
product_view -> save event -> enqueue prediction job -> worker predicts
```

Queue payload:

```json
{
  "event_id": "...",
  "event_type": "product_view",
  "product_id": 1,
  "category": "Fitness",
  "session_id": "...",
  "cart_id": "...",
  "created_at": "..."
}
```

### 12. Prediction Table Upgrade

Upgrade prediction table to include model version:

```text
product_view_predictions
- id
- product_id
- product_name
- category_name
- event_time
- event_type
- predicted_cart_probability
- predicted_order_probability
- model_name
- model_version
- prediction_time
- feature_snapshot_json
- source_event_id
```

### 13. Monitoring Dashboard Upgrade

Upgrade prediction analytics page to show:

- Model version
- Prediction time
- Product name
- Category
- Predicted cart probability
- Predicted order probability
- Actual add-to-cart outcome if known
- Actual order outcome if known

### 14. Model Deployment Log

Add table:

```text
model_deployments
```

Columns:

```text
id
model_version
source_release_url
deployed_at
deployed_by
status
notes
```

## Deployment Guide

### Phase 1: Prepare PythonAnywhere

1. Create PythonAnywhere web app.
2. Upload project files.
3. Create virtual environment.
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Configure `.env`:

```text
FLASK_SECRET_KEY=...
WHATSAPP_NUMBER=...
DATABASE_URL=sqlite:////home/<username>/Online-store-Click-Analytics/data/shoppulse.db
FLASK_DEBUG=0
```

6. Run seed script once if needed:

```bash
python seed.py
```

7. Configure WSGI file to import Flask app from `app.py`.

8. Reload PythonAnywhere web app.

### Phase 2: Configure Model Artifacts

Create folders:

```bash
mkdir -p models/latest
mkdir -p models/runs
mkdir -p data/backups
```

Train initial model:

```bash
python train_category_models.py
```

Copy or sync selected model into:

```text
models/latest/
```

Reload web app.

### Phase 3: Configure Hourly Retraining

Add PythonAnywhere scheduled task:

```bash
cd /home/<username>/Online-store-Click-Analytics
source venv/bin/activate
python hourly_retraining_job.py
```

Schedule:

```text
Every hour
```

The script should exit quickly if no active retraining trigger exists.

### Phase 4: Configure GitHub Model Registry

1. Create GitHub repository secrets:

```text
GH_TOKEN
PYTHONANYWHERE_API_TOKEN
PYTHONANYWHERE_USERNAME
```

2. Add GitHub Actions workflow:

```text
.github/workflows/model-training.yml
```

3. Use GitHub Releases for model versions.

4. Confirm each release includes:

```text
model.joblib
features.json
metrics.json
training_summary.json
model_card.md
```

### Phase 5: Configure Model Sync

On PythonAnywhere, create scheduled task:

```bash
cd /home/<username>/Online-store-Click-Analytics
source venv/bin/activate
python sync_latest_model.py
```

Schedule:

```text
Every hour or after training workflow completes
```

After syncing a new latest model, reload the web app.

### Phase 6: Configure Queue-Based Prediction

Recommended:

```text
Redis Queue
```

Deploy:

```text
prediction_worker.py
```

Flow:

```text
Flask product_view event
  -> enqueue job
  -> worker predicts
  -> prediction table updated
```

Fallback only if Redis is unavailable:

```text
database-backed prediction_jobs table
```

The worker can poll pending jobs every minute.

### Phase 7: Operational Checks

After deployment, verify:

- Product views are recorded
- Prediction jobs are created
- Prediction rows are created
- Prediction dashboard loads
- Category creation creates retraining trigger
- Hourly job detects active trigger
- DB backup is created before training
- Model version folder is created
- GitHub Release is created
- Latest model can be synced
- App uses latest model version

## Final Target Flow

```text
new category created
  -> retraining trigger active for 3 days
  -> hourly job runs
  -> backup production DB
  -> train timestamped model version
  -> evaluate model
  -> publish GitHub Release
  -> promote to latest if accepted
  -> PythonAnywhere syncs latest model
  -> product_view events use latest model for prediction
```
