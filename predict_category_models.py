"""Load the saved category Random Forest model and run predictions.

Run from the project root after training:
    venv/bin/python predict_category_models.py

This script reuses the feature-building code from train_category_models.py,
loads models/category_random_forest_model.joblib, and predicts:
    - target_cart_probability
    - target_order_probability
for each product category in the current database.
"""
from pathlib import Path

import joblib
import numpy as np

from feature_pipeline import BASE_DIR, build_category_dataframe, load_tables
from mlops_utils import current_model_path


MODEL_PATH = current_model_path()


def load_model_artifact(model_path=MODEL_PATH):
    if not Path(model_path).exists():
        raise FileNotFoundError(
            f"Model file not found: {model_path}\n"
            "Train and save it first with: venv/bin/python train_category_models.py"
        )
    return joblib.load(model_path)


def main():
    artifact = load_model_artifact()

    model = artifact["model"]
    feature_columns = artifact["feature_columns"]
    target_columns = artifact["target_columns"]

    print(f"Loaded model: {artifact['model_name']}")
    print(f"Model file: {MODEL_PATH}")
    print(f"Training rows used when saved: {artifact['training_rows']}")
    print(f"Targets: {target_columns}")

    tables = load_tables()
    category_df = build_category_dataframe(tables)

    missing_columns = [
        col for col in feature_columns
        if col not in category_df.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing required feature columns: {missing_columns}")

    X = category_df[feature_columns]
    predictions = np.clip(model.predict(X), 0, 1)

    output_df = category_df.copy()
    output_df["predicted_cart_probability"] = predictions[:, 0]
    output_df["predicted_order_probability"] = predictions[:, 1]

    display_cols = [
        "category",
        "product_views",
        "add_to_cart_events",
        "checkout_started_count",
        "whatsapp_order_count",
        "target_cart_probability",
        "predicted_cart_probability",
        "target_order_probability",
        "predicted_order_probability",
    ]

    print("\nPredictions:")
    print(
        output_df[display_cols]
        .sort_values("predicted_order_probability", ascending=False)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
