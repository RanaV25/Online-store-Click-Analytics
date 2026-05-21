"""SQLAlchemy models for ShopPulse Store.

ML/MLOps note:
    `ClickEvent` and `CartEvent` are designed to be exportable as the raw
    feature stream for a future Azure pipeline:
        Browser  ->  Flask /api/track-event
                 ->  (future) Azure Event Hubs
                 ->  Azure Data Lake Storage Gen2 (raw parquet/CSV)
                 ->  Azure ML pipeline (feature engineering + training)
                 ->  Model: P(product becomes high-demand in next 30/60 min).
    Every column captured here was chosen to be useful as a model feature
    (timestamps, session/user, product/category, traffic source, device,
    cart context, search behavior).
"""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False, index=True)
    subcategory = db.Column(db.String(80))
    brand = db.Column(db.String(80))
    description = db.Column(db.Text)
    short_description = db.Column(db.String(300))
    price = db.Column(db.Float, nullable=False)
    compare_at_price = db.Column(db.Float)
    discount_percent = db.Column(db.Integer, default=0)
    stock_quantity = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(400))
    rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "slug": self.slug,
            "category": self.category,
            "subcategory": self.subcategory,
            "brand": self.brand,
            "description": self.description,
            "short_description": self.short_description,
            "price": self.price,
            "compare_at_price": self.compare_at_price,
            "discount_percent": self.discount_percent,
            "stock_quantity": self.stock_quantity,
            "image_url": self.image_url,
            "rating": self.rating,
            "review_count": self.review_count,
            "is_featured": self.is_featured,
            "is_active": self.is_active,
        }


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(400))
    is_active = db.Column(db.Boolean, default=True)


class ClickEvent(db.Model):
    __tablename__ = "click_events"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(64), index=True)
    cart_id = db.Column(db.String(64), index=True)
    session_id = db.Column(db.String(64), index=True)
    user_id = db.Column(db.String(64), index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    page_url = db.Column(db.String(500))
    page_title = db.Column(db.String(300))
    referrer = db.Column(db.String(500))
    product_id = db.Column(db.Integer, index=True)
    product_sku = db.Column(db.String(64))
    category = db.Column(db.String(80))
    search_query = db.Column(db.String(300))
    filter_name = db.Column(db.String(80))
    filter_value = db.Column(db.String(200))
    cart_value = db.Column(db.Float)
    cart_items_count = db.Column(db.Integer)
    traffic_source = db.Column(db.String(80))
    device_type = db.Column(db.String(40))
    browser = db.Column(db.String(80))
    city = db.Column(db.String(80))
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class CartEvent(db.Model):
    __tablename__ = "cart_events"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.String(64), index=True)
    session_id = db.Column(db.String(64), index=True)
    user_id = db.Column(db.String(64), index=True)
    event_type = db.Column(db.String(40), nullable=False, index=True)
    product_id = db.Column(db.Integer, index=True)
    product_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Float)
    cart_total = db.Column(db.Float)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    session_id = db.Column(db.String(64), index=True)
    user_id = db.Column(db.String(64), index=True)
    status = db.Column(db.String(40), default="active", index=True)
    total_items = db.Column(db.Integer, default=0)
    total_amount = db.Column(db.Float, default=0.0)
    converted_order_code = db.Column(db.String(40), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )
    checkout_started_at = db.Column(db.DateTime)
    customer_details_submitted_at = db.Column(db.DateTime)
    whatsapp_clicked_at = db.Column(db.DateTime)
    converted_at = db.Column(db.DateTime)
    cleared_at = db.Column(db.DateTime)


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.String(64), index=True, nullable=False)
    product_id = db.Column(db.Integer, index=True, nullable=False)
    product_name = db.Column(db.String(200))
    product_sku = db.Column(db.String(64))
    category = db.Column(db.String(80))
    subcategory = db.Column(db.String(80))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    line_total = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    removed_at = db.Column(db.DateTime)


class OrderIntent(db.Model):
    __tablename__ = "order_intents"

    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    cart_id = db.Column(db.String(64), index=True)
    session_id = db.Column(db.String(64), index=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(40), nullable=False)
    customer_city = db.Column(db.String(80))
    customer_notes = db.Column(db.Text)
    cart_json = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    total_items = db.Column(db.Integer, nullable=False)
    whatsapp_message = db.Column(db.Text)
    status = db.Column(db.String(40), default="pending_whatsapp", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class SearchQuery(db.Model):
    __tablename__ = "search_queries"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), index=True)
    query = db.Column(db.String(300), nullable=False)
    results_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class RetrainingTrigger(db.Model):
    __tablename__ = "retraining_triggers"

    id = db.Column(db.Integer, primary_key=True)
    trigger_type = db.Column(db.String(60), nullable=False, index=True)
    category_id = db.Column(db.Integer, index=True)
    category_name = db.Column(db.String(120), nullable=False, index=True)
    reason = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    active_until = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(40), default="active", index=True)
    last_checked_at = db.Column(db.DateTime)
    last_training_run_id = db.Column(db.Integer, index=True)


class TrainingRun(db.Model):
    __tablename__ = "training_runs"

    id = db.Column(db.Integer, primary_key=True)
    model_version = db.Column(db.String(120), unique=True, nullable=False, index=True)
    model_type = db.Column(db.String(80), default="random_forest", index=True)
    status = db.Column(db.String(40), default="started", index=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    finished_at = db.Column(db.DateTime)
    source_db_backup = db.Column(db.String(500))
    metrics_json = db.Column(db.Text)
    artifact_path = db.Column(db.String(500))
    github_release_url = db.Column(db.String(500))
    promoted_to_latest = db.Column(db.Boolean, default=False, index=True)
    created_by = db.Column(db.String(120), default="system")
    error_message = db.Column(db.Text)


class ModelDeployment(db.Model):
    __tablename__ = "model_deployments"

    id = db.Column(db.Integer, primary_key=True)
    model_version = db.Column(db.String(120), nullable=False, index=True)
    source_release_url = db.Column(db.String(500))
    deployed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    deployed_by = db.Column(db.String(120), default="system")
    status = db.Column(db.String(40), default="deployed", index=True)
    notes = db.Column(db.Text)


class PredictionJob(db.Model):
    __tablename__ = "prediction_jobs"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    event_id = db.Column(db.String(64), index=True)
    product_id = db.Column(db.Integer, index=True)
    event_type = db.Column(db.String(64), default="product_view", index=True)
    payload_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), default="queued", index=True)
    attempts = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
