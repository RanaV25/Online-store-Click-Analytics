"""Shared feature-building utilities for category demand models."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'shoppulse.db'}",
)


def make_engine(database_url=None, db_path=None):
    if db_path:
        database_url = f"sqlite:///{Path(db_path).resolve()}"
    return create_engine(database_url or DEFAULT_DATABASE_URL)


def load_tables(database_url=None, db_path=None):
    """Load all analytics tables as dataframes."""
    engine = make_engine(database_url=database_url, db_path=db_path)
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
            columns=["category", "checkout_started_count", "whatsapp_order_count"]
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
        "product_views", "unique_sessions", "unique_users",
        "add_to_cart_events", "carts_with_add_to_cart",
        "checkout_started_count", "whatsapp_order_count", "total_products",
        "featured_product_count",
    ]
    for col in count_cols:
        if col in category_df.columns:
            category_df[col] = category_df[col].fillna(0).astype(int)

    category_df = category_df.fillna(0)
    total_views = category_df["product_views"].sum()
    total_add_to_cart = category_df["add_to_cart_events"].sum()

    category_df["view_share_pct"] = (
        100 * category_df["product_views"] / total_views if total_views else 0
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
        "avg_price", "avg_discount_pct", "avg_rating", "avg_stock_quantity",
        "view_share_pct", "add_to_cart_share_pct",
        "view_vs_cart_share_gap_pct", "product_view_to_cart_ratio_pct",
        "product_view_to_checkout_ratio_pct",
        "product_view_to_whatsapp_ratio_pct", "cart_to_checkout_ratio_pct",
        "checkout_to_whatsapp_ratio_pct", "cart_to_whatsapp_click_ratio_pct",
        "avg_product_views_per_session", "avg_product_views_per_user",
        "target_cart_probability", "target_order_probability",
    ]
    category_df[round_cols] = category_df[round_cols].round(4)
    return category_df
