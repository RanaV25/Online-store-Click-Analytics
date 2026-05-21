# SLICING.md

## 1. Purpose

This file guides AI coding agents to implement the advanced ShopPulse MLOps roadmap safely in small, reviewable slices. Each slice should be independently testable, avoid unrelated rewrites, and preserve the current Flask/Jinja/SQLite architecture unless the slice explicitly changes it.

## 2. Project Summary

ShopPulse is a demo Flask e-commerce app that captures clickstream, cart, checkout, WhatsApp order-intent, and product-view prediction data. The current app uses server-rendered Jinja templates, vanilla JavaScript, SQLAlchemy with SQLite, localStorage carts, and scikit-learn model artifacts. The advanced target adds PythonAnywhere deployment, model versioning, GitHub Releases as a lightweight registry, scheduled retraining, DB backups, and queued prediction jobs.

## 3. Current Codebase Status

### Exists

- Flask app factory and routes in `app.py`.
- SQLAlchemy models in `models.py`.
- SQLite main DB at `data/shoppulse.db`.
- Separate prediction SQLite DB at `data/prediction_analytics.db`.
- Product/category seeding in `seed.py`.
- Click/cart tracking JS in `static/js/analytics.js` and `static/js/cart.js`.
- Storefront pages in `templates/`.
- Analytics dashboard at `/analytics`.
- Prediction dashboard at `/prediction-analytics`.
- Category-level training in `train_category_models.py`.
- Saved Random Forest artifact in `models/category_random_forest_model.joblib`.
- Browser automation script in `automate_clicks.py`.

### Incomplete

- No admin category management pages yet.
- No migration framework; schema compatibility is handled manually in `app.py`.
- No queue/worker implementation.
- No retraining trigger table.
- No model deployment table.
- No model registry folder layout with `latest/` and `runs/`.
- No GitHub Actions workflow.
- No PythonAnywhere deployment config.
- No automated tests. A file named `test` exists but no test suite was found.

### Owner Decisions

- Production will keep SQLite.
- Prediction jobs should use Redis.
- No auth method is required for now.
- Category creation will happen through admin pages.
- Model training and promotion should be automatic, with manual override available.

### Do Not Change Without Confirmation

- Checkout/WhatsApp business flow.
- Existing route URLs used by README/manual tests.
- Existing localStorage cart key `sp_cart_v1`.
- Database file locations unless deployment slice requires it.
- Model target definitions.

## 4. Chosen Slicing Strategy

Use a hybrid strategy:

- Foundation-first for config, tests, and schema safety.
- Vertical slices for prediction and retraining flows.
- Risk-first for schema safety, backups, Redis queueing, and deployment.

This fits because the app already works as a vertical demo, but advanced MLOps adds operational risk. AI agents should first stabilize foundations, then add one complete workflow at a time.

## 5. Implementation Rules for AI Agents

- Do not rewrite unrelated files.
- Do not perform large unrequested refactors.
- Preserve the current Flask/Jinja/SQLAlchemy architecture unless the slice explicitly changes it.
- Keep each slice small and testable.
- Add or update tests for changed behavior.
- Update docs when behavior changes.
- Verify locally after each slice.
- Stop and ask if database ownership, queue, or deployment assumptions conflict.
- Do not introduce new dependencies unless the slice justifies them.
- Do not change deployment assumptions unless requested.
- Do not commit generated DB files unless explicitly requested.
- Do not remove existing notebooks, archives, or user-created files.

## 6. Slice Dependency Map

```text
Foundation:
  SLICE-00 -> SLICE-01 -> SLICE-02 -> SLICE-03

Core MLOps:
  SLICE-04 -> SLICE-05 -> SLICE-06 -> SLICE-07

Prediction Pipeline:
  SLICE-08 -> SLICE-09 -> SLICE-10

Training and Registry:
  SLICE-11 -> SLICE-12 -> SLICE-13 -> SLICE-14

Deployment Hardening:
  SLICE-15 -> SLICE-16 -> SLICE-17
```

## 7. Detailed Work Slices

### SLICE-00

### Slice Name

Repository and Runtime Baseline

### Goal

Document and verify the current runtime, commands, routes, and existing DB files.

### Why this slice exists

Later agents need a stable baseline before changing schema, training, or deployment.

### Dependencies

None.

### Files likely involved

- `README.md`
- `MLOPS_STRATEGY.md`
- `ADVANCED_MLOPS_STRATEGY.md`
- proposed `docs/CURRENT_STATE.md`

### Tasks

- Record Python version target.
- Record app start command.
- Record all existing routes.
- Record current env vars.
- Record existing DB files.
- Record known missing pieces.

### AI implementation instructions

Prefer documentation-only changes. Do not modify runtime code.

### Acceptance criteria

- A current-state doc exists.
- It lists stack, routes, env vars, DB files, and missing components.

### Manual verification steps

Run:

```bash
venv/bin/python app.py
curl http://localhost:5000/healthz
```

### Tests to add/update

None.

### Risks

Low.

### Do-not-touch list

- `app.py`
- `models.py`
- DB files

### Done definition

The baseline is documented and no behavior changes were made.

### SLICE-01

### Slice Name

Test Harness Setup

### Goal

Add a minimal automated test framework.

### Why this slice exists

Current code has no real test suite. Later agents need regression checks.

### Dependencies

SLICE-00.

### Files likely involved

- `requirements.txt`
- proposed `tests/`
- proposed `pytest.ini`

### Tasks

- Add `pytest`.
- Add app fixture using temporary SQLite DB.
- Add health route test.
- Add basic page-render tests.

### AI implementation instructions

Use temporary DB paths under `/private/tmp` or pytest temp dirs. Do not use production `data/shoppulse.db`.

### Acceptance criteria

- `venv/bin/python -m pytest` runs.
- Health, home, products, analytics, prediction analytics routes return 200 or expected status.

### Manual verification steps

```bash
venv/bin/python -m pytest
```

### Tests to add/update

- `tests/test_health.py`
- `tests/test_pages.py`

### Risks

Medium: importing `app.py` currently creates app/global DB side effects.

### Do-not-touch list

- Storefront UI styling.
- Training logic.

### Done definition

Basic pytest suite passes.

### SLICE-02

### Slice Name

Configuration Consolidation

### Goal

Centralize current and proposed env vars without changing behavior.

### Why this slice exists

Deployment and workers need consistent paths for DB, models, backups, and queues.

### Dependencies

SLICE-01.

### Files likely involved

- `config.py`
- `.env.example`
- tests

### Tasks

- Add config values for model dirs, prediction DB path, backup dir, queue mode, and debug.
- Keep existing defaults compatible.
- Update `.env.example`.

### AI implementation instructions

Add values only. Do not require new env vars for local runs.

### Acceptance criteria

- Existing local run still works with current `.env`.
- Tests pass.
- `.env.example` documents new optional values.

### Manual verification steps

```bash
venv/bin/python -c "from config import Config; print(Config.SQLALCHEMY_DATABASE_URI)"
venv/bin/python -m pytest
```

### Tests to add/update

- Config default test.

### Risks

Low.

### Do-not-touch list

- Secrets.
- Real `.env` values.

### Done definition

Config supports future pieces without breaking current app.

### SLICE-03

### Slice Name

Schema Safety and Migration Decision

### Goal

Prepare for schema changes without unsafe ad hoc alterations.

### Why this slice exists

Advanced MLOps requires new tables. Current schema changes are manual.

### Dependencies

SLICE-01, SLICE-02.

### Files likely involved

- `models.py`
- `app.py`
- proposed `migrations/` or `schema_migrations.py`

### Tasks

- Decide whether to use Flask-Migrate/Alembic or a small SQLite migration helper.
- Add versioned schema migration mechanism.
- Preserve existing `_ensure_sqlite_schema()` behavior until replaced safely.

### AI implementation instructions

Do not remove existing compatibility migration until tests prove replacement works.

### Acceptance criteria

- Fresh DB creation works.
- Existing DB upgrade path works.
- Tests validate new and existing DB startup.

### Manual verification steps

```bash
mv data/shoppulse.db data/shoppulse.backup.db
venv/bin/python seed.py
venv/bin/python app.py
```

### Tests to add/update

- Fresh DB schema test.
- Existing DB migration test, if feasible.

### Risks

High: migration mistakes can corrupt SQLite files.

### Do-not-touch list

- Production/live DB without backup.

### Done definition

Schema changes can be applied repeatably.

### SLICE-04

### Slice Name

Admin Category Creation Foundation

### Goal

Add a controlled backend path for category creation.

### Why this slice exists

Retraining triggers depend on detecting new categories.

### Dependencies

SLICE-03.

### Files likely involved

- `models.py`
- `app.py`
- proposed `templates/admin_categories.html`
- tests

### Tasks

- Add category creation route or API.
- Validate name and slug uniqueness.
- Add basic admin UI or API-only route.

### AI implementation instructions

Because no auth exists, mark the route internal/demo-only and avoid exposing destructive actions broadly.

### Acceptance criteria

- Creating a category inserts a `Category`.
- Duplicate slug/name is rejected.
- Existing category pages still work.

### Manual verification steps

- Create category.
- Visit `/category/<slug>`.

### Tests to add/update

- Category creation success.
- Duplicate category rejection.

### Risks

High: no auth exists.

### Do-not-touch list

- Product seed data.
- Public category browsing behavior.

### Done definition

Category creation works and is tested.

### SLICE-05

### Slice Name

Retraining Trigger Model

### Goal

Add `RetrainingTrigger` table and create a trigger when a category is added.

### Why this slice exists

New category creation must start hourly retraining for three days.

### Dependencies

SLICE-04.

### Files likely involved

- `models.py`
- `app.py`
- tests

### Tasks

- Add `RetrainingTrigger`.
- On category creation, insert active trigger.
- Set `active_until = created_at + 3 days`.

### AI implementation instructions

Do not run training inside the request.

### Acceptance criteria

- New category creates one active trigger.
- Duplicate category does not create a duplicate trigger.
- Trigger has correct `active_until`.

### Manual verification steps

Query DB:

```sql
SELECT category_name, status, active_until FROM retraining_triggers;
```

### Tests to add/update

- Trigger creation test.

### Risks

Medium.

### Do-not-touch list

- Existing click/cart event flow.

### Done definition

Category creation and retraining trigger creation are linked.

### SLICE-06

### Slice Name

Training Run Metadata

### Goal

Add `TrainingRun` and `ModelDeployment` tables.

### Why this slice exists

Training and deployment need auditable metadata.

### Dependencies

SLICE-03.

### Files likely involved

- `models.py`
- proposed migration/helper
- tests

### Tasks

- Add `TrainingRun`.
- Add `ModelDeployment`.
- Add helper functions for creating/updating run rows.

### AI implementation instructions

Keep helpers independent of model training code for testability.

### Acceptance criteria

- Tables are created.
- A test can insert/update a training run.

### Manual verification steps

Use SQLite browser or SQL query to inspect tables.

### Tests to add/update

- Metadata table tests.

### Risks

Low-medium.

### Do-not-touch list

- Training algorithm.

### Done definition

Model lifecycle metadata can be stored.

### SLICE-07

### Slice Name

Feature Pipeline Extraction

### Goal

Move reusable feature building from `train_category_models.py` into a dedicated module.

### Why this slice exists

Training and prediction must use the same feature logic.

### Dependencies

SLICE-01.

### Files likely involved

- proposed `feature_pipeline.py`
- `train_category_models.py`
- `predict_category_models.py`
- `prediction_store.py`
- tests

### Tasks

- Extract `load_tables`, `safe_ratio`, and `build_category_dataframe`.
- Keep imports backward compatible where practical.
- Add tests for dataframe columns.

### AI implementation instructions

This is a refactor slice. Do not change model outputs intentionally.

### Acceptance criteria

- Training script still runs.
- Prediction script still runs.
- Feature dataframe columns match before/after extraction.

### Manual verification steps

```bash
venv/bin/python train_category_models.py
venv/bin/python predict_category_models.py
```

### Tests to add/update

- Feature column contract test.

### Risks

Medium: import cycles.

### Do-not-touch list

- Model hyperparameters.
- Templates.

### Done definition

Shared feature pipeline exists and current behavior is preserved.

### SLICE-08

### Slice Name

Redis Prediction Queue

### Goal

Add Redis-backed prediction jobs for product-view prediction.

### Why this slice exists

The owner chose Redis for queue-based prediction. Product-view prediction should move out of the request path and into a Redis-backed worker flow.

### Dependencies

SLICE-03, SLICE-07.

### Files likely involved

- `models.py` or `prediction_store.py`
- `app.py`
- proposed `queue_client.py`
- tests

### Tasks

- Add Redis connection configuration.
- Add a queue helper for enqueue/dequeue.
- On `product_view`, enqueue a prediction job instead of synchronous prediction.
- Optionally write a lightweight prediction job audit row in SQLite if desired.
- Preserve current prediction path only behind a config flag if needed.

### AI implementation instructions

Do not block `/api/track-event` on model inference.

### Acceptance criteria

- Product view creates raw `ClickEvent`.
- Product view creates a Redis prediction job.
- Request still returns 204.

### Manual verification steps

Post `/api/track-event` with `product_view`, then verify the Redis queue length increases.

### Tests to add/update

- API product-view enqueue test with mocked Redis.

### Risks

Medium: current synchronous prediction behavior changes; Redis must be reachable in deployed environments.

### Do-not-touch list

- Frontend tracking payloads.

### Done definition

Product-view prediction is queued.

### SLICE-09

### Slice Name

Prediction Worker

### Goal

Create worker script that processes pending prediction jobs.

### Why this slice exists

Prediction should run out of request path.

### Dependencies

SLICE-08.

### Files likely involved

- proposed `prediction_worker.py`
- `prediction_store.py`
- tests

### Tasks

- Load pending jobs.
- Load latest model.
- Build features.
- Save prediction row.
- Mark job complete or failed.

### AI implementation instructions

Make worker runnable once for tests and loop mode for deployment.

### Acceptance criteria

- One pending job becomes completed.
- Prediction row is inserted.
- Failed job records error message.

### Manual verification steps

```bash
venv/bin/python prediction_worker.py --once
```

### Tests to add/update

- Worker success test.
- Worker missing model test.

### Risks

Medium: model path and feature consistency.

### Do-not-touch list

- Training script outputs unless needed for model path compatibility.

### Done definition

Prediction jobs can be processed outside Flask request cycle.

### SLICE-10

### Slice Name

Prediction Analytics Upgrade

### Goal

Show queued prediction status and model version in `/prediction-analytics`.

### Why this slice exists

Operators need visibility into prediction health.

### Dependencies

SLICE-09.

### Files likely involved

- `templates/prediction_analytics.html`
- `app.py`
- `prediction_store.py`

### Tasks

- Add model version column.
- Add prediction status counts.
- Add recent failed jobs section.

### AI implementation instructions

Keep table simple. Do not add a frontend framework.

### Acceptance criteria

- Page loads.
- Recent predictions show model version.
- Failed jobs are visible.

### Manual verification steps

Visit `/prediction-analytics`.

### Tests to add/update

- Template renders with predictions and no predictions.

### Risks

Low.

### Do-not-touch list

- Existing `/analytics` charts.

### Done definition

Prediction page reflects queued inference state.

### SLICE-11

### Slice Name

Backup Database Script

### Goal

Create a safe timestamped backup before model training.

### Why this slice exists

Training must not read a mutating live SQLite DB.

### Dependencies

SLICE-02.

### Files likely involved

- proposed `backup_database.py`
- tests

### Tasks

- Copy main DB to `data/backups/`.
- Copy prediction DB if present.
- Verify copied files exist and are non-empty.
- Return machine-readable backup metadata.

### AI implementation instructions

Never delete old backups in this slice.

### Acceptance criteria

- Backup file is created.
- Backup metadata includes source and destination.

### Manual verification steps

```bash
venv/bin/python backup_database.py
ls data/backups
```

### Tests to add/update

- Backup creation test with temp DB.

### Risks

Medium: file paths on PythonAnywhere.

### Do-not-touch list

- Live DB contents.

### Done definition

Training can use a copied DB snapshot.

### SLICE-12

### Slice Name

Versioned Training Outputs

### Goal

Save training artifacts into `models/runs/<model_version>/` and optionally `models/latest/`.

### Why this slice exists

Model versions must be auditable and rollback-friendly.

### Dependencies

SLICE-07, SLICE-11.

### Files likely involved

- `train_category_models.py`
- tests

### Tasks

- Add CLI args: `--db-path`, `--output-dir`, `--promote`.
- Generate `category_rf_YYYYMMDD_HHMMSS`.
- Save `model.joblib`, `features.json`, `metrics.json`, `training_summary.json`.
- Copy to `models/latest/` only when promoted.

### AI implementation instructions

Keep old artifact path compatibility or update consumers in same slice.

### Acceptance criteria

- Training creates a run folder.
- Training metadata includes DB backup path and metrics.
- Prediction can load latest model after promotion.

### Manual verification steps

```bash
venv/bin/python train_category_models.py --promote
ls models/runs
ls models/latest
```

### Tests to add/update

- Training output path test.
- Artifact metadata test.

### Risks

Medium-high: current prediction code uses old model path.

### Do-not-touch list

- Model target definitions.

### Done definition

Versioned training artifacts exist and latest model can be loaded.

### SLICE-13

### Slice Name

Hourly Retraining Job

### Goal

Run retraining only while active triggers exist.

### Why this slice exists

New categories require hourly retraining for three days.

### Dependencies

SLICE-05, SLICE-06, SLICE-11, SLICE-12.

### Files likely involved

- proposed `hourly_retraining_job.py`
- training metadata helpers
- tests

### Tasks

- Find active triggers.
- Expire old triggers.
- Backup DB.
- Run training from backup.
- Write/update `TrainingRun`.
- Automatically promote if acceptance checks pass.
- Support manual override for promote/rollback.

### AI implementation instructions

Make dry-run and once modes available.

### Acceptance criteria

- No active trigger exits with no training.
- Active trigger creates backup and training run.
- Passing model is promoted automatically.
- Manual override can force promote or rollback.
- Expired trigger is marked expired.

### Manual verification steps

```bash
venv/bin/python hourly_retraining_job.py --dry-run
venv/bin/python hourly_retraining_job.py --once
```

### Tests to add/update

- No-trigger test.
- Active-trigger test.

### Risks

High: scheduled task can create many artifacts if logic is wrong.

### Do-not-touch list

- GitHub publishing.

### Done definition

Hourly retraining can be safely scheduled and can auto-promote approved models.

### SLICE-14

### Slice Name

GitHub Release Publisher

### Goal

Publish a model run folder as a GitHub Release.

### Why this slice exists

GitHub Releases are the lightweight model registry.

### Dependencies

SLICE-12.

### Files likely involved

- proposed `publish_model_release.py`
- proposed `.github/workflows/model-training.yml`
- docs

### Tasks

- Create release from run folder.
- Upload model artifacts.
- Record release URL in metadata.

### AI implementation instructions

Support dry-run mode. Do not require secrets for local tests.

### Acceptance criteria

- Dry run lists intended release and assets.
- Missing artifact fails clearly.

### Manual verification steps

```bash
venv/bin/python publish_model_release.py --run-dir models/runs/<version> --dry-run
```

### Tests to add/update

- Artifact validation test.

### Risks

High: credentials and release immutability.

### Do-not-touch list

- Model training code unless metadata handoff requires it.

### Done definition

Model artifacts can be published as a release.

### SLICE-15

### Slice Name

Latest Model Sync

### Goal

Download the automatically promoted latest model artifacts into `models/latest/`, with a manual override path for rollback or forced promotion.

### Why this slice exists

PythonAnywhere app should use a single approved model.

### Dependencies

SLICE-14.

### Files likely involved

- proposed `sync_latest_model.py`
- `prediction_store.py`
- `predict_category_models.py`
- tests

### Tasks

- Locate latest automatically approved release.
- Download artifacts.
- Replace `models/latest/` atomically.
- Clear model cache.
- Record `ModelDeployment`.
- Allow manual override to sync a specific version.

### AI implementation instructions

Use temp download directory and rename into place only after validation.

### Acceptance criteria

- Sync dry run works.
- Local file sync test works.
- Prediction loads synced model.
- Specific-version manual override sync works in dry-run mode.

### Manual verification steps

```bash
venv/bin/python sync_latest_model.py --dry-run
```

### Tests to add/update

- Model artifact validation test.

### Risks

High: bad model can break predictions.

### Do-not-touch list

- Storefront routes.

### Done definition

App can consume latest model from registry workflow.

### SLICE-16

### Slice Name

Admin Pages and Manual Overrides

### Goal

Add admin pages for category creation, retraining visibility, and manual model promotion override.

### Why this slice exists

The owner does not require an auth method now, but the project needs admin pages for category creation and model operations.

### Dependencies

SLICE-04, SLICE-10.

### Files likely involved

- `app.py`
- templates
- model/retraining helper modules
- tests

### Tasks

- Add admin category creation page.
- Add admin retraining trigger list.
- Add admin training run list.
- Add manual promote/rollback action for model versions.
- Label pages as internal/demo until auth is added in the future.

### AI implementation instructions

Do not add an auth system in this slice. Keep admin routes simple and clearly documented as internal/demo routes.

### Acceptance criteria

- Admin page can create a category.
- Category creation creates a retraining trigger.
- Admin page can show training runs/model versions.
- Manual model promotion override is available.

### Manual verification steps

Visit admin pages, create a category, inspect retraining trigger, and test manual promotion in dry-run mode.

### Tests to add/update

- Admin category creation test.
- Manual model promotion dry-run test.

### Risks

High: admin pages are unprotected by owner decision; do not expose sensitive controls beyond intended demo environment.

### Do-not-touch list

- Customer checkout form behavior.

### Done definition

Admin category creation and manual model override flows exist.

### SLICE-17

### Slice Name

PythonAnywhere Deployment Readiness

### Goal

Prepare scripts and docs for manual PythonAnywhere deployment.

### Why this slice exists

Manual deployer needs reliable commands and checks.

### Dependencies

SLICE-02, SLICE-11, SLICE-12, SLICE-16.

### Files likely involved

- `DEPLOYMENT.md`
- proposed `wsgi.py` example or docs
- `.env.example`

### Tasks

- Document PythonAnywhere setup.
- Document env vars.
- Document scheduled tasks.
- Document model sync/retraining tasks.
- Add health/smoke checklist.

### AI implementation instructions

Do not include real secrets or account-specific paths.

### Acceptance criteria

- Human can deploy from docs.
- Commands are copy/paste friendly with placeholders.

### Manual verification steps

Follow `DEPLOYMENT.md`.

### Tests to add/update

None required.

### Risks

Medium: platform limits may block workers/Redis.

### Do-not-touch list

- Runtime code unless docs reveal blocker.

### Done definition

Deployment guide is complete and platform assumptions are explicit.

## 8. Suggested Slice Order

1. SLICE-00
2. SLICE-01
3. SLICE-02
4. SLICE-03
5. SLICE-04
6. SLICE-05
7. SLICE-06
8. SLICE-07
9. SLICE-08
10. SLICE-09
11. SLICE-10
12. SLICE-11
13. SLICE-12
14. SLICE-13
15. SLICE-14
16. SLICE-15
17. SLICE-16
18. SLICE-17

## 9. Parallelization Plan

Can run in parallel after SLICE-01:

- SLICE-02 config cleanup and SLICE-07 feature extraction planning.
- SLICE-10 UI improvements and SLICE-11 backup script after their dependencies.
- SLICE-14 GitHub release dry-run tooling and SLICE-16 admin page design after model artifact structure is agreed.

Must not run in parallel:

- SLICE-03 with any schema-changing slice.
- SLICE-08 and SLICE-09 unless job schema is finalized.
- SLICE-12 and SLICE-15 unless model artifact contract is finalized.

## 10. Review Checklist

- Does the slice change only expected files?
- Are DB changes repeatable and backed by tests?
- Does local startup still work?
- Does `venv/bin/python -m pytest` pass?
- Are routes backward compatible?
- Are env vars documented?
- Are secrets excluded?
- Are model artifacts generated outside source code unless intended?
- Are failures handled without breaking shopper UX?
- Are docs updated?

## 11. Testing Strategy

- Unit tests: feature pipeline, safe ratios, backup helpers, trigger helpers.
- Integration tests: Flask routes, DB writes, prediction job lifecycle.
- API tests: `/api/track-event`, `/api/cart-event`, `/api/create-order-intent`.
- UI smoke tests: home, products, product detail, cart, checkout, analytics, predictions.
- Worker tests: one-shot prediction worker and retraining job dry-run.
- Regression tests: existing checkout and cart behavior.

## 12. Rollback / Recovery Notes

- For code slices, revert the slice commit.
- For DB slices, restore from timestamped DB backup.
- For model slices, copy the previous `models/runs/<version>/` into `models/latest/`.
- For GitHub Releases, mark bad release as not approved; do not delete unless owner confirms.
- For failed scheduled jobs, disable the PythonAnywhere scheduled task first, then inspect logs.

## 13. Open Questions

### Resolved Owner Decisions

- Production will keep SQLite.
- Redis will be used for prediction queueing.
- No auth method is required for now.
- Admin pages will be used for category creation.
- Model training and model promotion should be automatic.
- Manual override must exist for model promotion and rollback.

### Remaining Open Questions

- Should GitHub Releases store DB-derived artifacts, or only model artifacts?
- What retention policy should apply to DB backups and model versions?
- Which Redis provider/account will be used with PythonAnywhere?
