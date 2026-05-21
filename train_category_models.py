"""Build category features and compare models for cart/order probability.

Run from the project root:
    venv/bin/python train_category_models.py

The script loads the SQLite database configured in .env, builds a category
modeling dataframe from products, click_events, cart_events, carts,
cart_items, order_intents, and search_queries, then trains/evaluates several
regression models.
"""
import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from feature_pipeline import (
    build_category_dataframe, load_tables, make_engine, safe_ratio,
)
from mlops_utils import copy_tree_contents, utc_version, write_json


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "category_random_forest_model.joblib"
FEATURES_PATH = MODEL_DIR / "category_random_forest_features.joblib"
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'shoppulse.db'}",
)

engine = create_engine(DATABASE_URL)


def load_tables():
    """Load all analytics tables as dataframes."""
    tables = {
        "products": pd.read_sql("SELECT * FROM products", engine),
        "categories": pd.read_sql("SELECT * FROM categories", engine),
        "click_events": pd.read_sql("SELECT * FROM click_events", engine),
        "cart_events": pd.read_sql("SELECT * FROM cart_events", engine),
        "carts": pd.read_sql("SELECT * FROM carts", engine),
        "cart_items": pd.read_sql("SELECT * FROM cart_items", engine),
        "order_intents": pd.read_sql("SELECT * FROM order_intents", engine),
        "search_queries": pd.read_sql("SELECT * FROM search_queries", engine),
    }

    for df in tables.values():
        for col in ["created_at", "updated_at", "added_at", "removed_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    return tables


def safe_ratio(numerator, denominator, multiplier=1.0):
    return (
        multiplier * numerator / denominator.replace(0, np.nan)
    ).replace([np.inf, -np.inf], 0).fillna(0)


def build_category_dataframe(tables):
    products_df = tables["products"]
    click_events_df = tables["click_events"]
    cart_events_df = tables["cart_events"]

    product_lookup = products_df[
        [
            "id", "category", "subcategory", "price", "discount_percent",
            "rating", "review_count", "stock_quantity", "is_featured",
            "is_active",
        ]
    ].rename(columns={"id": "product_id"})

    clicks_enriched_df = click_events_df.merge(
        product_lookup,
        on="product_id",
        how="left",
        suffixes=("", "_product"),
    )
    clicks_enriched_df["final_category"] = clicks_enriched_df["category"].fillna(
        clicks_enriched_df["category_product"]
    )

    cart_events_enriched_df = cart_events_df.merge(
        product_lookup,
        on="product_id",
        how="left",
    )
    cart_events_enriched_df["final_category"] = cart_events_enriched_df["category"]

    product_views_df = (
        clicks_enriched_df[clicks_enriched_df["event_type"] == "product_view"]
        .groupby("final_category", dropna=False)
        .agg(
            product_views=("id", "count"),
            unique_sessions=("session_id", "nunique"),
            unique_users=("user_id", "nunique"),
        )
        .reset_index()
        .rename(columns={"final_category": "category"})
    )

    add_to_cart_df = (
        cart_events_enriched_df[
            cart_events_enriched_df["event_type"] == "add_to_cart"
        ]
        .groupby("final_category", dropna=False)
        .agg(
            add_to_cart_events=("id", "count"),
            carts_with_add_to_cart=("cart_id", "nunique"),
        )
        .reset_index()
        .rename(columns={"final_category": "category"})
    )

    category_carts_df = (
        cart_events_enriched_df[
            (cart_events_enriched_df["event_type"] == "add_to_cart")
            & (cart_events_enriched_df["cart_id"].notna())
        ][["final_category", "cart_id"]]
        .drop_duplicates()
        .rename(columns={"final_category": "category"})
    )

    checkout_whatsapp_df = category_carts_df.merge(
        cart_events_df[["cart_id", "event_type"]],
        on="cart_id",
        how="left",
    )

    if checkout_whatsapp_df.empty:
        checkout_whatsapp_df = pd.DataFrame(
            columns=[
                "category",
                "checkout_started_count",
                "whatsapp_order_count",
            ]
        )
    else:
        checkout_whatsapp_df = (
            checkout_whatsapp_df.groupby("category", dropna=False)
            .agg(
                checkout_started_count=(
                    "event_type",
                    lambda x: int((x == "checkout_started").sum()),
                ),
                whatsapp_order_count=(
                    "event_type",
                    lambda x: int((x == "whatsapp_order_click").sum()),
                ),
            )
            .reset_index()
        )

    product_features_df = (
        products_df[products_df["is_active"] == 1]
        .groupby("category", dropna=False)
        .agg(
            total_products=("id", "count"),
            avg_price=("price", "mean"),
            avg_discount_pct=("discount_percent", "mean"),
            avg_rating=("rating", "mean"),
            total_reviews=("review_count", "sum"),
            avg_stock_quantity=("stock_quantity", "mean"),
            featured_product_count=("is_featured", "sum"),
        )
        .reset_index()
    )

    category_df = (
        product_views_df.merge(add_to_cart_df, on="category", how="left")
        .merge(checkout_whatsapp_df, on="category", how="left")
        .merge(product_features_df, on="category", how="left")
    )

    count_cols = [
        "product_views",
        "unique_sessions",
        "unique_users",
        "add_to_cart_events",
        "carts_with_add_to_cart",
        "checkout_started_count",
        "whatsapp_order_count",
        "total_products",
        "featured_product_count",
    ]
    for col in count_cols:
        if col in category_df.columns:
            category_df[col] = category_df[col].fillna(0).astype(int)

    category_df = category_df.fillna(0)

    total_views = category_df["product_views"].sum()
    total_add_to_cart = category_df["add_to_cart_events"].sum()

    category_df["view_share_pct"] = (
        100 * category_df["product_views"] / total_views
        if total_views else 0
    )
    category_df["add_to_cart_share_pct"] = (
        100 * category_df["add_to_cart_events"] / total_add_to_cart
        if total_add_to_cart else 0
    )
    category_df["view_vs_cart_share_gap_pct"] = (
        category_df["view_share_pct"] - category_df["add_to_cart_share_pct"]
    )

    category_df["product_view_to_cart_ratio_pct"] = safe_ratio(
        category_df["add_to_cart_events"], category_df["product_views"], 100
    )
    category_df["product_view_to_checkout_ratio_pct"] = safe_ratio(
        category_df["checkout_started_count"], category_df["product_views"], 100
    )
    category_df["product_view_to_whatsapp_ratio_pct"] = safe_ratio(
        category_df["whatsapp_order_count"], category_df["product_views"], 100
    )
    category_df["cart_to_checkout_ratio_pct"] = safe_ratio(
        category_df["checkout_started_count"], category_df["add_to_cart_events"], 100
    )
    category_df["checkout_to_whatsapp_ratio_pct"] = safe_ratio(
        category_df["whatsapp_order_count"], category_df["checkout_started_count"], 100
    )
    category_df["cart_to_whatsapp_click_ratio_pct"] = safe_ratio(
        category_df["whatsapp_order_count"], category_df["add_to_cart_events"], 100
    )
    category_df["avg_product_views_per_session"] = safe_ratio(
        category_df["product_views"], category_df["unique_sessions"]
    )
    category_df["avg_product_views_per_user"] = safe_ratio(
        category_df["product_views"], category_df["unique_users"]
    )

    category_df["target_cart_probability"] = safe_ratio(
        category_df["add_to_cart_events"], category_df["product_views"]
    ).clip(0, 1)
    category_df["target_order_probability"] = safe_ratio(
        category_df["whatsapp_order_count"], category_df["product_views"]
    ).clip(0, 1)

    round_cols = [
        "avg_price",
        "avg_discount_pct",
        "avg_rating",
        "avg_stock_quantity",
        "view_share_pct",
        "add_to_cart_share_pct",
        "view_vs_cart_share_gap_pct",
        "product_view_to_cart_ratio_pct",
        "product_view_to_checkout_ratio_pct",
        "product_view_to_whatsapp_ratio_pct",
        "cart_to_checkout_ratio_pct",
        "checkout_to_whatsapp_ratio_pct",
        "cart_to_whatsapp_click_ratio_pct",
        "avg_product_views_per_session",
        "avg_product_views_per_user",
        "target_cart_probability",
        "target_order_probability",
    ]
    category_df[round_cols] = category_df[round_cols].round(4)

    return category_df


# Keep the shared feature module as the source of truth while preserving older
# imports from this script.
from feature_pipeline import build_category_dataframe, load_tables, safe_ratio  # noqa: E402,F811


def create_train_test(category_df):
    target_cols = ["target_cart_probability", "target_order_probability"]

    leakage_cols = [
        "add_to_cart_events",
        "checkout_started_count",
        "whatsapp_order_count",
        "product_view_to_cart_ratio_pct",
        "product_view_to_checkout_ratio_pct",
        "product_view_to_whatsapp_ratio_pct",
        "cart_to_checkout_ratio_pct",
        "checkout_to_whatsapp_ratio_pct",
        "cart_to_whatsapp_click_ratio_pct",
        "target_cart_probability",
        "target_order_probability",
    ]

    feature_cols = [col for col in category_df.columns if col not in leakage_cols]
    X = category_df[feature_cols]
    y = category_df[target_cols]

    if len(category_df) < 2:
        raise ValueError("Need at least 2 category rows to create train/test data.")

    test_size = 0.4 if len(category_df) < 10 else 0.25
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=42,
    )

    training_df = X_train.copy()
    training_df[target_cols] = y_train
    testing_df = X_test.copy()
    testing_df[target_cols] = y_test

    return X, y, X_train, X_test, y_train, y_test, training_df, testing_df


def build_preprocessor(X):
    categorical_features = X.select_dtypes(include=["object"]).columns.tolist()
    numeric_features = X.select_dtypes(
        include=["int64", "float64", "int32", "float32"]
    ).columns.tolist()

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, numeric_features),
            ("categorical", categorical_transformer, categorical_features),
        ]
    )

    return preprocessor, numeric_features, categorical_features


def build_models(preprocessor):
    return {
        "baseline_mean": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", DummyRegressor(strategy="mean")),
            ]
        ),
        "ridge_regression": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", Ridge(alpha=1.0)),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=300,
                        max_depth=5,
                        min_samples_leaf=1,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "gradient_boosting": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    MultiOutputRegressor(
                        GradientBoostingRegressor(
                            n_estimators=150,
                            learning_rate=0.05,
                            max_depth=3,
                            random_state=42,
                        )
                    ),
                ),
            ]
        ),
    }


def evaluate_models(models, X_train, X_test, y_train, y_test):
    results = []

    for model_name, pipeline in models.items():
        print("\n" + "=" * 80)
        print(f"Training model: {model_name}")
        print("Parameters:")
        print(pipeline.get_params())

        pipeline.fit(X_train, y_train)
        preds = np.clip(pipeline.predict(X_test), 0, 1)

        mae_cart = mean_absolute_error(y_test["target_cart_probability"], preds[:, 0])
        mae_order = mean_absolute_error(y_test["target_order_probability"], preds[:, 1])
        rmse_cart = mean_squared_error(
            y_test["target_cart_probability"], preds[:, 0], squared=False
        )
        rmse_order = mean_squared_error(
            y_test["target_order_probability"], preds[:, 1], squared=False
        )

        if len(y_test) >= 2:
            r2_cart = r2_score(y_test["target_cart_probability"], preds[:, 0])
            r2_order = r2_score(y_test["target_order_probability"], preds[:, 1])
        else:
            r2_cart = np.nan
            r2_order = np.nan

        output_df = X_test[["category"]].copy()
        output_df["actual_cart_probability"] = y_test[
            "target_cart_probability"
        ].values
        output_df["predicted_cart_probability"] = preds[:, 0]
        output_df["actual_order_probability"] = y_test[
            "target_order_probability"
        ].values
        output_df["predicted_order_probability"] = preds[:, 1]

        print("Model output:")
        print(output_df.to_string(index=False))

        results.append(
            {
                "model": model_name,
                "mae_cart_probability": mae_cart,
                "mae_order_probability": mae_order,
                "avg_mae": np.mean([mae_cart, mae_order]),
                "rmse_cart_probability": rmse_cart,
                "rmse_order_probability": rmse_order,
                "avg_rmse": np.mean([rmse_cart, rmse_order]),
                "r2_cart_probability": r2_cart,
                "r2_order_probability": r2_order,
            }
        )

    results_df = pd.DataFrame(results).sort_values("avg_mae")
    return results_df


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", help="Train from a specific SQLite DB backup.")
    parser.add_argument("--database-url", default=DATABASE_URL)
    parser.add_argument("--output-dir", default=str(MODEL_DIR / "runs"))
    parser.add_argument("--promote", action="store_true",
                        help="Copy the trained run to models/latest.")
    parser.add_argument("--model-version", default=None)
    return parser.parse_args()


def main(args=None):
    args = args or parse_args()
    database_url = args.database_url
    if args.db_path:
        database_url = f"sqlite:///{Path(args.db_path).resolve()}"

    print(f"Using database: {database_url}")
    tables = load_tables(database_url=database_url)

    print("\nTables loaded:")
    for name, df in tables.items():
        print(f"{name}: {df.shape}")

    category_df = build_category_dataframe(tables)
    if category_df.empty:
        raise ValueError("No category data available. Generate events first.")

    print("\nCategory modeling dataframe:")
    print(category_df.to_string(index=False))

    (
        X,
        y,
        X_train,
        X_test,
        y_train,
        y_test,
        training_df,
        testing_df,
    ) = create_train_test(category_df)

    print("\nTraining dataframe:")
    print(training_df.to_string(index=False))
    print("\nTesting dataframe:")
    print(testing_df.to_string(index=False))

    preprocessor, numeric_features, categorical_features = build_preprocessor(X)
    print("\nNumeric features:")
    print(numeric_features)
    print("\nCategorical features:")
    print(categorical_features)

    models = build_models(preprocessor)
    results_df = evaluate_models(models, X_train, X_test, y_train, y_test)

    print("\nModel performance:")
    print(results_df.to_string(index=False))

    best_by_metric_name = results_df.iloc[0]["model"]
    production_model_name = "random_forest"
    production_model = models[production_model_name]

    print("\n" + "=" * 80)
    print(f"Best model by validation metric: {best_by_metric_name}")
    print("Selection metric: lowest avg_mae")
    print(results_df.iloc[0].to_string())
    print("\nProduction model selected for saving: random_forest")
    print("Reason: user-selected model for this project stage.")

    print("\nTraining final Random Forest model on all category rows...")
    production_model.fit(X, y)

    model_version = args.model_version or utc_version("category_rf")
    run_dir = Path(args.output_dir) / model_version
    run_dir.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_artifact = {
        "model_name": production_model_name,
        "model_version": model_version,
        "model": production_model,
        "feature_columns": X.columns.tolist(),
        "target_columns": y.columns.tolist(),
        "database_url": database_url,
        "source_db_path": str(Path(args.db_path).resolve()) if args.db_path else None,
        "training_rows": len(X),
        "metrics": results_df.to_dict(orient="records"),
    }
    joblib.dump(model_artifact, run_dir / "model.joblib")
    metadata = {
        "model_version": model_version,
        "model_name": production_model_name,
        "feature_columns": X.columns.tolist(),
        "target_columns": y.columns.tolist(),
        "category_dataframe_columns": category_df.columns.tolist(),
    }
    write_json(run_dir / "features.json", metadata)
    write_json(run_dir / "metrics.json", results_df.to_dict(orient="records"))
    write_json(run_dir / "training_summary.json", {
        "model_version": model_version,
        "trained_at": datetime.utcnow().isoformat(),
        "database_url": database_url,
        "source_db_path": str(Path(args.db_path).resolve()) if args.db_path else None,
        "training_rows": len(X),
        "promoted": bool(args.promote),
    })
    (run_dir / "model_card.md").write_text(
        f"# {model_version}\n\n"
        f"- Model: RandomForestRegressor\n"
        f"- Training rows: {len(X)}\n"
        f"- Targets: {', '.join(y.columns)}\n",
        encoding="utf-8",
    )

    # Keep legacy paths working for the current app and notebooks.
    joblib.dump(model_artifact, MODEL_PATH)
    joblib.dump(metadata, FEATURES_PATH)

    if args.promote:
        copy_tree_contents(run_dir, BASE_DIR / "models" / "latest")

    print(f"Saved versioned model run to: {run_dir}")
    print(f"Saved legacy model artifact to: {MODEL_PATH}")
    if args.promote:
        print(f"Promoted model to: {BASE_DIR / 'models' / 'latest'}")

    final_preds = np.clip(production_model.predict(X), 0, 1)
    final_output_df = category_df.copy()
    final_output_df["predicted_cart_probability"] = final_preds[:, 0]
    final_output_df["predicted_order_probability"] = final_preds[:, 1]

    print("\nFinal predictions on all categories:")
    print(
        final_output_df[
            [
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
        ]
        .sort_values("predicted_order_probability", ascending=False)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
