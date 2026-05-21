from pathlib import Path

from app import create_app
from models import Category, Product, RetrainingTrigger, db


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:////private/tmp/shoppulse_pytest.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WHATSAPP_NUMBER = "+10000000000"
    EXPORT_DIR = Path("/private/tmp/shoppulse_exports")
    DEBUG = True
    MODEL_RUNS_DIR = Path("/private/tmp/shoppulse_models/runs")


def make_app():
    app = create_app(TestConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
        cat = Category(name="Fitness", slug="fitness", description="Test", is_active=True)
        db.session.add(cat)
        db.session.add(
            Product(
                sku="FIT-TEST-001",
                name="Test Product",
                slug="test-product",
                category="Fitness",
                price=100.0,
                stock_quantity=10,
                is_active=True,
            )
        )
        db.session.commit()
    return app


def test_healthz():
    client = make_app().test_client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json["ok"] is True


def test_public_pages_render():
    client = make_app().test_client()
    for path in ["/", "/products", "/analytics", "/prediction-analytics", "/admin/categories"]:
        response = client.get(path)
        assert response.status_code == 200


def test_admin_category_creates_retraining_trigger():
    app = make_app()
    client = app.test_client()
    response = client.post(
        "/admin/categories",
        data={"name": "New Category", "description": "Demo"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    with app.app_context():
        category = Category.query.filter_by(name="New Category").first()
        assert category is not None
        assert category.slug == "new-category"
        trigger = RetrainingTrigger.query.filter_by(category_id=category.id).first()
        assert trigger is not None
        assert trigger.reason == "New category created from admin page"
        assert trigger.status == "active"
