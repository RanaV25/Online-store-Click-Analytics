"""ShopPulse Store - Flask application factory and routes.

ML/MLOps note:
    The /api/track-event and /api/cart-event endpoints are the system of
    record for user behaviour today. In production these would dual-write
    (or stream) into Azure Event Hubs, land in ADLS Gen2 as Parquet, and
    feed an Azure ML training pipeline that predicts whether a product
    will become high-demand in the next 30-60 minutes.
"""
import csv
import json
import os
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask, abort, jsonify, render_template, request, send_from_directory,
)
from sqlalchemy import desc, func

from config import Config
from models import (
    CartEvent, Category, ClickEvent, OrderIntent, Product, SearchQuery, db,
)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure data dir exists for SQLite.
    Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")).parent.mkdir(
        parents=True, exist_ok=True
    )

    db.init_app(app)
    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _request_meta():
    """Pull lightweight client metadata off the request."""
    return {
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        "user_agent": request.headers.get("User-Agent", ""),
        "referrer": request.referrer or "",
    }


def _next_order_code():
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"SP-{today}-"
    last = (
        OrderIntent.query.filter(OrderIntent.order_code.like(f"{prefix}%"))
        .order_by(OrderIntent.id.desc())
        .first()
    )
    n = 1
    if last:
        try:
            n = int(last.order_code.split("-")[-1]) + 1
        except ValueError:
            n = 1
    return f"{prefix}{n:03d}"


def _build_whatsapp_message(order_code, customer, items, total_items, total_amount):
    lines = [
        "Hello ShopPulse Store,",
        "",
        "I want to place an order.",
        "",
        f"Order Code: {order_code}",
        "",
        "Customer Details:",
        f"Name: {customer['name']}",
        f"Phone: {customer['phone']}",
    ]
    if customer.get("city"):
        lines.append(f"City: {customer['city']}")
    lines.append("")
    lines.append("Products:")
    for i, it in enumerate(items, start=1):
        line_total = it["unit_price"] * it["quantity"]
        lines.append(f"{i}. {it['name']} x {it['quantity']} = ₹{int(line_total)}")
    lines.append("")
    lines.append(f"Total Items: {total_items}")
    lines.append(f"Total Amount: ₹{int(total_amount)}")
    if customer.get("notes"):
        lines.append("")
        lines.append("Notes:")
        lines.append(customer["notes"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def register_routes(app):

    # ---- Health ----------------------------------------------------------
    @app.route("/healthz")
    def healthz():
        return jsonify(ok=True, service="shoppulse", time=datetime.utcnow().isoformat())

    # ---- Frontend pages --------------------------------------------------
    @app.route("/")
    def index():
        featured_products = (
            Product.query.filter_by(is_featured=True, is_active=True).limit(8).all()
        )
        trending_products = (
            Product.query.filter_by(is_active=True)
            .order_by(desc(Product.rating))
            .limit(8)
            .all()
        )
        categories = Category.query.filter_by(is_active=True).all()
        return render_template(
            "index.html",
            featured_products=featured_products,
            trending_products=trending_products,
            categories=categories,
        )

    @app.route("/products")
    def products():
        q = request.args.get("q", "", type=str).strip()
        category = request.args.get("category", "", type=str).strip()
        sort = request.args.get("sort", "featured", type=str)
        min_price = request.args.get("min_price", type=float)
        max_price = request.args.get("max_price", type=float)

        query = Product.query.filter_by(is_active=True)
        if q:
            like = f"%{q}%"
            query = query.filter(
                (Product.name.ilike(like)) | (Product.description.ilike(like))
            )
        if category:
            query = query.filter(Product.category == category)
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        if sort == "price_asc":
            query = query.order_by(Product.price.asc())
        elif sort == "price_desc":
            query = query.order_by(Product.price.desc())
        elif sort == "rating":
            query = query.order_by(Product.rating.desc())
        elif sort == "discount":
            query = query.order_by(Product.discount_percent.desc())
        else:
            query = query.order_by(Product.is_featured.desc(), Product.rating.desc())

        items = query.all()
        if q:
            try:
                db.session.add(
                    SearchQuery(session_id=request.cookies.get("sp_sid"), query=q,
                                results_count=len(items))
                )
                db.session.commit()
            except Exception:
                db.session.rollback()

        categories = Category.query.filter_by(is_active=True).all()
        return render_template(
            "products.html",
            products=items,
            categories=categories,
            q=q,
            current_category=category,
            current_sort=sort,
            min_price=min_price,
            max_price=max_price,
        )

    @app.route("/category/<slug>")
    def category(slug):
        cat = Category.query.filter_by(slug=slug, is_active=True).first()
        if not cat:
            abort(404)
        items = (
            Product.query.filter_by(category=cat.name, is_active=True)
            .order_by(Product.rating.desc())
            .all()
        )
        return render_template("category.html", category=cat, products=items)

    @app.route("/product/<slug>")
    def product_detail(slug):
        p = Product.query.filter_by(slug=slug, is_active=True).first()
        if not p:
            abort(404)
        related = (
            Product.query.filter(
                Product.category == p.category,
                Product.id != p.id,
                Product.is_active.is_(True),
            )
            .order_by(Product.rating.desc())
            .limit(4)
            .all()
        )
        return render_template("product_detail.html", product=p, related=related,
                               whatsapp_number=app.config["WHATSAPP_NUMBER"])

    @app.route("/cart")
    def cart():
        return render_template("cart.html")

    @app.route("/checkout")
    def checkout():
        return render_template("checkout.html")

    @app.route("/order-success/<order_code>")
    def order_success(order_code):
        order = OrderIntent.query.filter_by(order_code=order_code).first()
        if not order:
            abort(404)
        return render_template("order_success.html", order=order)

    @app.route("/analytics")
    def analytics_dashboard():
        # NOTE: protect this route in production (e.g. basic auth, IP allowlist).
        return render_template("analytics_dashboard.html")

    # ---- Tracking API ----------------------------------------------------

    @app.route("/api/track-event", methods=["POST"])
    def api_track_event():
        # Silent-fail contract: never break the UX on tracking errors.
        try:
            payload = request.get_json(force=True, silent=True) or {}
            meta = _request_meta()
            extra = payload.get("metadata") or {}
            ev = ClickEvent(
                event_id=payload.get("event_id"),
                session_id=payload.get("session_id"),
                user_id=payload.get("user_id"),
                event_type=payload.get("event_type", "unknown"),
                page_url=payload.get("page_url"),
                page_title=payload.get("page_title"),
                referrer=payload.get("referrer") or meta["referrer"],
                product_id=payload.get("product_id"),
                product_sku=payload.get("product_sku"),
                category=payload.get("category"),
                search_query=payload.get("search_query"),
                filter_name=payload.get("filter_name"),
                filter_value=payload.get("filter_value"),
                cart_value=payload.get("cart_value"),
                cart_items_count=payload.get("cart_items_count"),
                traffic_source=payload.get("traffic_source"),
                device_type=payload.get("device_type"),
                browser=payload.get("browser"),
                city=payload.get("city"),
                metadata_json=json.dumps(extra) if extra else None,
            )
            db.session.add(ev)

            if ev.event_type == "search_submit" and payload.get("search_query"):
                db.session.add(
                    SearchQuery(
                        session_id=ev.session_id,
                        query=payload["search_query"],
                        results_count=int(extra.get("results_count", 0) or 0),
                    )
                )

            db.session.commit()
            return ("", 204)
        except Exception:
            db.session.rollback()
            return ("", 204)

    @app.route("/api/cart-event", methods=["POST"])
    def api_cart_event():
        try:
            payload = request.get_json(force=True, silent=True) or {}
            ev = CartEvent(
                session_id=payload.get("session_id"),
                event_type=payload.get("event_type", "unknown"),
                product_id=payload.get("product_id"),
                product_name=payload.get("product_name"),
                quantity=payload.get("quantity"),
                unit_price=payload.get("unit_price"),
                cart_total=payload.get("cart_total"),
            )
            db.session.add(ev)
            db.session.commit()
            return ("", 204)
        except Exception:
            db.session.rollback()
            return ("", 204)

    @app.route("/api/products")
    def api_products():
        items = Product.query.filter_by(is_active=True).all()
        return jsonify([p.to_dict() for p in items])

    # ---- Order intent ----------------------------------------------------

    @app.route("/api/create-order-intent", methods=["POST"])
    def api_create_order_intent():
        data = request.get_json(force=True, silent=True) or {}
        customer = data.get("customer") or {}
        cart_items = data.get("items") or []

        if not customer.get("name") or not customer.get("phone"):
            return jsonify(ok=False, error="Name and phone are required."), 400
        if not cart_items:
            return jsonify(ok=False, error="Cart is empty."), 400

        # Recompute totals server-side from authoritative product rows.
        verified_items = []
        total_amount = 0.0
        total_items = 0
        for it in cart_items:
            pid = it.get("product_id")
            qty = max(1, int(it.get("quantity") or 1))
            product = Product.query.get(pid) if pid else None
            if not product or not product.is_active:
                return jsonify(ok=False, error=f"Product {pid} not available."), 400
            line = {
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "slug": product.slug,
                "unit_price": product.price,
                "quantity": qty,
            }
            total_amount += product.price * qty
            total_items += qty
            verified_items.append(line)

        order_code = _next_order_code()
        msg = _build_whatsapp_message(order_code, customer, verified_items,
                                      total_items, total_amount)

        order = OrderIntent(
            order_code=order_code,
            customer_name=customer["name"],
            customer_phone=customer["phone"],
            customer_city=customer.get("city"),
            customer_notes=customer.get("notes"),
            cart_json=json.dumps(verified_items),
            total_amount=total_amount,
            total_items=total_items,
            whatsapp_message=msg,
            status="pending_whatsapp",
        )
        db.session.add(order)
        db.session.commit()

        wa_number = app.config["WHATSAPP_NUMBER"].lstrip("+")
        whatsapp_url = f"https://wa.me/{wa_number}?text={urllib.parse.quote(msg)}"

        return jsonify(
            ok=True,
            order_code=order_code,
            whatsapp_url=whatsapp_url,
            redirect_url=f"/order-success/{order_code}",
            total_items=total_items,
            total_amount=total_amount,
        )

    # ---- Analytics aggregation API --------------------------------------

    def _count(event_type):
        return (
            db.session.query(func.count(ClickEvent.id))
            .filter(ClickEvent.event_type == event_type)
            .scalar()
            or 0
        )

    @app.route("/api/analytics/summary")
    def api_analytics_summary():
        return jsonify(
            page_views=_count("page_view"),
            product_views=_count("product_view"),
            add_to_cart=_count("add_to_cart"),
            checkout_started=_count("checkout_started"),
            whatsapp_order_clicks=_count("whatsapp_order_click"),
            total_events=db.session.query(func.count(ClickEvent.id)).scalar() or 0,
            total_orders=db.session.query(func.count(OrderIntent.id)).scalar() or 0,
            total_searches=db.session.query(func.count(SearchQuery.id)).scalar() or 0,
        )

    @app.route("/api/analytics/funnel")
    def api_analytics_funnel():
        steps = [
            ("page_view", "Page View"),
            ("product_view", "Product View"),
            ("add_to_cart", "Add to Cart"),
            ("checkout_started", "Checkout Started"),
            ("whatsapp_order_click", "WhatsApp Order Click"),
        ]
        return jsonify([
            {"step": label, "event_type": et, "count": _count(et)}
            for et, label in steps
        ])

    @app.route("/api/analytics/top-products")
    def api_analytics_top_products():
        def _top(event_type, limit=5):
            rows = (
                db.session.query(
                    ClickEvent.product_id,
                    func.count(ClickEvent.id).label("c"),
                )
                .filter(ClickEvent.event_type == event_type)
                .filter(ClickEvent.product_id.isnot(None))
                .group_by(ClickEvent.product_id)
                .order_by(desc("c"))
                .limit(limit)
                .all()
            )
            out = []
            for pid, c in rows:
                p = Product.query.get(pid)
                out.append({
                    "product_id": pid,
                    "name": p.name if p else f"#{pid}",
                    "category": p.category if p else None,
                    "count": c,
                })
            return out

        # Top searches
        searches = (
            db.session.query(SearchQuery.query, func.count(SearchQuery.id).label("c"))
            .group_by(SearchQuery.query)
            .order_by(desc("c"))
            .limit(10)
            .all()
        )
        return jsonify(
            top_viewed=_top("product_view"),
            top_added_to_cart=_top("add_to_cart"),
            top_searched=[{"query": q, "count": c} for q, c in searches],
        )

    @app.route("/api/analytics/recent-events")
    def api_analytics_recent_events():
        n = int(request.args.get("n", 25))
        events = ClickEvent.query.order_by(ClickEvent.id.desc()).limit(n).all()
        orders = OrderIntent.query.order_by(OrderIntent.id.desc()).limit(n).all()

        # Events grouped by hour for the last 24h.
        since = datetime.utcnow() - timedelta(hours=24)
        rows = (
            db.session.query(
                func.strftime("%Y-%m-%d %H:00", ClickEvent.created_at).label("hour"),
                func.count(ClickEvent.id).label("c"),
            )
            .filter(ClickEvent.created_at >= since)
            .group_by("hour")
            .order_by("hour")
            .all()
        )
        timeseries = [{"hour": h, "count": c} for h, c in rows]

        # Events by type (overall distribution).
        type_rows = (
            db.session.query(ClickEvent.event_type, func.count(ClickEvent.id))
            .group_by(ClickEvent.event_type)
            .order_by(desc(func.count(ClickEvent.id)))
            .all()
        )

        return jsonify(
            recent_events=[
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "session_id": e.session_id,
                    "product_id": e.product_id,
                    "page_url": e.page_url,
                    "device_type": e.device_type,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
            recent_orders=[
                {
                    "order_code": o.order_code,
                    "customer_name": o.customer_name,
                    "city": o.customer_city,
                    "total_items": o.total_items,
                    "total_amount": o.total_amount,
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ],
            timeseries=timeseries,
            event_types=[{"event_type": t, "count": c} for t, c in type_rows],
        )

    # ---- CSV export ------------------------------------------------------

    @app.route("/api/export/csv", methods=["POST", "GET"])
    def api_export_csv():
        path = export_all_csv(app)
        return jsonify(ok=True, path=str(path))

    @app.cli.command("export-csv")
    def cli_export_csv():
        """Export all tables to exports/YYYY-MM-DD/ as CSV."""
        path = export_all_csv(app)
        print(f"Exported to: {path}")

    # ---- Static file fallback (favicon noise) ---------------------------
    @app.route("/favicon.ico")
    def favicon():
        return ("", 204)

    # Inject WhatsApp number for templates that want it.
    @app.context_processor
    def inject_globals():
        return {"whatsapp_number": app.config["WHATSAPP_NUMBER"]}


# ---------------------------------------------------------------------------
# CSV export helper
# ---------------------------------------------------------------------------

def export_all_csv(app):
    """Dump all tables into exports/YYYY-MM-DD/.

    Future: replace local-disk write with an upload to Azure Data Lake Storage
    Gen2 (e.g. via `azure-storage-file-datalake`) so the same files become the
    raw layer of the Azure ML training pipeline.
    """
    out_dir = Path(app.config["EXPORT_DIR"]) / datetime.utcnow().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    def dump(filename, rows, headers):
        path = out_dir / filename
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for r in rows:
                w.writerow(r)

    with app.app_context():
        dump(
            "products.csv",
            [
                (p.id, p.sku, p.name, p.slug, p.category, p.brand, p.price,
                 p.compare_at_price, p.discount_percent, p.stock_quantity,
                 p.rating, p.review_count, p.is_featured, p.is_active,
                 p.created_at)
                for p in Product.query.all()
            ],
            ["id", "sku", "name", "slug", "category", "brand", "price",
             "compare_at_price", "discount_percent", "stock_quantity",
             "rating", "review_count", "is_featured", "is_active", "created_at"],
        )
        dump(
            "click_events.csv",
            [
                (e.id, e.event_id, e.session_id, e.user_id, e.event_type,
                 e.page_url, e.product_id, e.product_sku, e.category,
                 e.search_query, e.filter_name, e.filter_value,
                 e.cart_value, e.cart_items_count, e.traffic_source,
                 e.device_type, e.browser, e.city, e.metadata_json,
                 e.created_at)
                for e in ClickEvent.query.all()
            ],
            ["id", "event_id", "session_id", "user_id", "event_type",
             "page_url", "product_id", "product_sku", "category",
             "search_query", "filter_name", "filter_value", "cart_value",
             "cart_items_count", "traffic_source", "device_type", "browser",
             "city", "metadata_json", "created_at"],
        )
        dump(
            "cart_events.csv",
            [
                (e.id, e.session_id, e.event_type, e.product_id,
                 e.product_name, e.quantity, e.unit_price, e.cart_total,
                 e.created_at)
                for e in CartEvent.query.all()
            ],
            ["id", "session_id", "event_type", "product_id", "product_name",
             "quantity", "unit_price", "cart_total", "created_at"],
        )
        dump(
            "order_intents.csv",
            [
                (o.id, o.order_code, o.customer_name, o.customer_phone,
                 o.customer_city, o.customer_notes, o.total_items,
                 o.total_amount, o.status, o.created_at)
                for o in OrderIntent.query.all()
            ],
            ["id", "order_code", "customer_name", "customer_phone",
             "customer_city", "customer_notes", "total_items", "total_amount",
             "status", "created_at"],
        )
        dump(
            "search_queries.csv",
            [
                (s.id, s.session_id, s.query, s.results_count, s.created_at)
                for s in db.session.query(SearchQuery).all()
            ],
            ["id", "session_id", "query", "results_count", "created_at"],
        )
    return out_dir


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=app.config["DEBUG"])
