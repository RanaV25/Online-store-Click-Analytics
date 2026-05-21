"""Prediction storage and scoring helpers for product-view events.

Predictions are intentionally written to a separate SQLite database from the
main storefront DB. The main app records clickstream events; this module turns
new product_view events into category-level model predictions and stores the
result for the prediction analytics page.
"""
import json
import sqlite3
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from feature_pipeline import BASE_DIR, build_category_dataframe, load_tables
from mlops_utils import current_model_path


PREDICTION_DB_PATH = BASE_DIR / "data" / "prediction_analytics.db"
MODEL_PATH = current_model_path()


def init_prediction_db(db_path=PREDICTION_DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_view_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                category_name TEXT NOT NULL,
                event_time TEXT NOT NULL,
                event_type TEXT NOT NULL,
                predicted_cart_probability REAL NOT NULL,
                predicted_order_probability REAL NOT NULL,
                target_cart_probability REAL,
                target_order_probability REAL,
                product_views INTEGER,
                add_to_cart_events INTEGER,
                checkout_started_count INTEGER,
                whatsapp_order_count INTEGER,
                model_name TEXT,
                model_version TEXT,
                model_training_rows INTEGER,
                source_event_id TEXT,
                cart_id TEXT,
                session_id TEXT,
                metadata_json TEXT,
                prediction_time TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(product_view_predictions)")
        }
        if "model_version" not in existing_cols:
            conn.execute("ALTER TABLE product_view_predictions ADD COLUMN model_version TEXT")
        if "prediction_time" not in existing_cols:
            conn.execute("ALTER TABLE product_view_predictions ADD COLUMN prediction_time TEXT")
        conn.commit()


@lru_cache(maxsize=1)
def load_model_artifact():
    model_path = current_model_path()
    if not model_path.exists():
        return None
    return joblib.load(model_path)


def build_prediction_for_product_view(product, event_payload, event_time=None):
    """Score the product's category using the latest category dataframe."""
    artifact = load_model_artifact()
    if artifact is None:
        return None

    category_df = build_category_dataframe(load_tables())
    if category_df.empty:
        return None

    category_rows = category_df[category_df["category"] == product.category]
    if category_rows.empty:
        return None

    feature_columns = artifact["feature_columns"]
    missing_columns = [
        col for col in feature_columns
        if col not in category_rows.columns
    ]
    if missing_columns:
        return None

    model = artifact["model"]
    features = category_rows[feature_columns]
    prediction = np.clip(model.predict(features), 0, 1)[0]
    category_row = category_rows.iloc[0]
    event_time = event_time or datetime.utcnow()

    return {
        "product_id": product.id,
        "product_name": product.name,
        "category_name": product.category,
        "event_time": event_time.isoformat(),
        "event_type": event_payload.get("event_type", "product_view"),
        "predicted_cart_probability": float(prediction[0]),
        "predicted_order_probability": float(prediction[1]),
        "target_cart_probability": float(category_row.get("target_cart_probability", 0)),
        "target_order_probability": float(category_row.get("target_order_probability", 0)),
        "product_views": int(category_row.get("product_views", 0)),
        "add_to_cart_events": int(category_row.get("add_to_cart_events", 0)),
        "checkout_started_count": int(category_row.get("checkout_started_count", 0)),
        "whatsapp_order_count": int(category_row.get("whatsapp_order_count", 0)),
        "model_name": artifact.get("model_name", "unknown"),
        "model_version": artifact.get("model_version", "legacy"),
        "model_training_rows": int(artifact.get("training_rows", 0)),
        "source_event_id": event_payload.get("event_id"),
        "cart_id": event_payload.get("cart_id"),
        "session_id": event_payload.get("session_id"),
        "metadata_json": json.dumps({
            "feature_columns": feature_columns,
            "category_features": category_row.to_dict(),
        }, default=str),
        "prediction_time": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }


def save_prediction_row(row, db_path=PREDICTION_DB_PATH):
    if not row:
        return
    init_prediction_db(db_path)
    columns = [
        "product_id",
        "product_name",
        "category_name",
        "event_time",
        "event_type",
        "predicted_cart_probability",
        "predicted_order_probability",
        "target_cart_probability",
        "target_order_probability",
        "product_views",
        "add_to_cart_events",
        "checkout_started_count",
        "whatsapp_order_count",
        "model_name",
        "model_version",
        "model_training_rows",
        "source_event_id",
        "cart_id",
        "session_id",
        "metadata_json",
        "prediction_time",
        "created_at",
    ]
    placeholders = ", ".join(["?"] * len(columns))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"""
            INSERT INTO product_view_predictions ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            [row.get(col) for col in columns],
        )
        conn.commit()


def get_recent_predictions(limit=100, db_path=PREDICTION_DB_PATH):
    init_prediction_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                id,
                product_id,
                product_name,
                category_name,
                event_time,
                event_type,
                predicted_cart_probability,
                predicted_order_probability,
                target_cart_probability,
                target_order_probability,
                product_views,
                add_to_cart_events,
                checkout_started_count,
                whatsapp_order_count,
                model_name,
                model_version,
                model_training_rows,
                session_id,
                prediction_time,
                created_at
            FROM product_view_predictions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
