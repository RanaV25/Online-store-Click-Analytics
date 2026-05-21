# Basic MLOps Strategy

This project can use a simple, explainable MLOps flow:

```text
collect events -> build features -> train model -> save model -> serve predictions -> monitor results -> retrain
```

## 1. Data Collection

The core event and business tables are:

- `click_events`
- `cart_events`
- `carts`
- `cart_items`
- `order_intents`
- `products`
- `categories`

Important events to keep capturing:

- `product_view`
- `add_to_cart`
- `checkout_started`
- `whatsapp_order_click`
- `cart_converted`

Each important event should include:

- `created_at` or event time
- `product_id`
- `category`
- `session_id`
- `cart_id`
- `user_id`
- `device_type`
- `traffic_source`

## 2. Feature Store Lite

For now, `train_category_models.py` acts as the feature pipeline. It builds category-level features from the raw event tables.

A future improvement is to persist engineered features into tables such as:

- `category_features_hourly`
- `category_features_daily`

Example feature columns:

- `category`
- `window_start`
- `product_views`
- `add_to_cart_events`
- `checkout_started_count`
- `whatsapp_order_count`
- `view_to_cart_rate`
- `avg_price`
- `avg_discount`
- `target_cart_probability`
- `target_order_probability`

## 3. Training Pipeline

The current training command is:

```bash
venv/bin/python train_category_models.py
```

The training script should continue to:

- Load data
- Build features
- Create train/test splits
- Train multiple candidate models
- Compare metrics
- Save the selected model
- Save feature columns and metadata

Current saved artifacts:

- `models/category_random_forest_model.joblib`
- `models/category_random_forest_features.joblib`

Recommended next artifacts:

- `models/metrics.json`
- `models/training_run.json`

## 4. Model Registry Lite

Instead of a full model registry, use a folder-based registry:

```text
models/
  latest/
    model.joblib
    features.json
    metrics.json
  runs/
    2026-05-19_223000/
      model.joblib
      features.json
      metrics.json
      training_data_summary.json
```

This allows simple model comparison and rollback.

## 5. Prediction Serving

The current prediction flow is:

```text
product_view event -> rebuild category features -> load saved model -> predict -> save prediction
```

Predictions are stored separately in:

```text
data/prediction_analytics.db
```

Prediction records should include:

- `product_name`
- `category_name`
- `event_time`
- `event_type`
- `predicted_cart_probability`
- `predicted_order_probability`
- `model_name`
- `model_version`
- Feature snapshot or metadata

This allows later comparison of predicted behavior vs actual behavior.

## 6. Monitoring

Basic model monitoring should track:

- Number of predictions per day
- Average predicted cart probability
- Average predicted order probability
- Actual add-to-cart rate
- Actual WhatsApp order rate
- Prediction vs actual difference
- Model MAE over time

Basic data-quality monitoring should track:

- Missing `product_id`
- Missing `category`
- New unseen category
- Zero product views
- Very low event volume

## 7. Retraining Strategy

Start with manual retraining:

```bash
venv/bin/python train_category_models.py
```

Then move to scheduled retraining.

Suggested schedule:

- Daily if event volume is high
- Weekly if event volume is low

Retrain when:

- New categories or products are added
- MAE gets worse
- Traffic behavior changes
- More than a defined number of new events are collected

## 8. Evaluation Before Deployment

Before replacing the saved production model, compare:

- Current model MAE
- New model MAE
- Cart probability MAE
- Order probability MAE

Only replace the saved model if the new model performs better or is intentionally selected.

## 9. Versioning

Every saved model should include metadata:

- `model_version`
- `trained_at`
- `training_rows`
- `feature_columns`
- `target_columns`
- `metrics`
- `git_commit`, if available
- `data_start_time`
- `data_end_time`

Simple model version format:

```text
category_rf_20260519_223000
```

## 10. Highest-Value Improvement

The most important modeling improvement is changing the dataset from:

```text
one row = one category
```

to:

```text
one row = one category per hour/day
```

That creates more training examples and supports future-looking targets:

```text
features from this hour -> target in next hour
```

Example target:

```text
target_cart_probability_next_hour
target_order_probability_next_hour
```

## Basic Architecture

```text
Flask app
  -> SQLite event tables
  -> feature pipeline script
  -> model training script
  -> saved model artifact
  -> prediction service inside Flask
  -> prediction analytics SQLite DB
  -> prediction dashboard
```

This is simple, explainable, and strong enough for a portfolio/demo MLOps project.
