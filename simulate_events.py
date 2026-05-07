"""Generate synthetic clickstream traffic for ShopPulse.

Usage:
    python simulate_events.py                  # default: 20 users, ~600 events
    python simulate_events.py --users 50 --events 2000
    python simulate_events.py --base-url http://localhost:5000

The script POSTs to /api/track-event (and /api/cart-event for cart actions)
exactly the way a real browser would. Useful before any real traffic exists.
"""
import argparse
import json
import random
import time
import uuid
from datetime import datetime

import requests


CITIES = ["Delhi", "Mumbai", "Bengaluru", "Pune", "Chennai", "Hyderabad",
          "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]
DEVICES = ["mobile", "desktop", "tablet"]
BROWSERS = ["Chrome", "Safari", "Firefox", "Edge"]
SOURCES = ["direct", "google", "instagram", "whatsapp", "referral"]
SEARCH_TERMS = ["yoga mat", "blender", "snacks", "lamp", "serum", "dog toy",
                "wireless mouse", "tea", "spice rack", "tracker"]


def get_products(base_url):
    try:
        r = requests.get(f"{base_url}/api/products", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Could not load /api/products from {base_url}: {e}")
        return []


def post(base_url, path, payload):
    try:
        requests.post(f"{base_url}{path}", json=payload, timeout=3)
    except Exception:
        pass


def make_user():
    return {
        "user_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "city": random.choice(CITIES),
        "device_type": random.choice(DEVICES),
        "browser": random.choice(BROWSERS),
        "traffic_source": random.choice(SOURCES),
    }


def base_event(user, event_type, page_url, **extra):
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "session_id": user["session_id"],
        "user_id": user["user_id"],
        "page_url": page_url,
        "page_title": page_url,
        "city": user["city"],
        "device_type": user["device_type"],
        "browser": user["browser"],
        "traffic_source": user["traffic_source"],
    }
    payload.update(extra)
    return payload


def run_session(base_url, products, total_target):
    """One synthetic browsing session for one user."""
    user = make_user()
    cart_value = 0.0
    cart_items_count = 0

    # 1. Landing
    post(base_url, "/api/track-event", base_event(user, "page_view", "/"))
    if random.random() < 0.5:
        post(base_url, "/api/track-event", base_event(user, "hero_cta_click", "/",
              metadata={"cta": "shop_now"}))

    # 2. Browse + maybe search
    post(base_url, "/api/track-event", base_event(user, "page_view", "/products"))
    if random.random() < 0.4:
        q = random.choice(SEARCH_TERMS)
        post(base_url, "/api/track-event", base_event(
            user, "search_submit", "/products", search_query=q,
            metadata={"results_count": random.randint(0, 12)}))

    if random.random() < 0.3:
        post(base_url, "/api/track-event", base_event(
            user, "filter_used", "/products",
            filter_name="category", filter_value=random.choice(
                ["Fitness", "Wellness", "Kitchen", "Skincare"])))

    # 3. View a few products
    viewed = random.sample(products, k=min(len(products), random.randint(2, 5)))
    for p in viewed:
        page = f"/product/{p['slug']}"
        post(base_url, "/api/track-event", base_event(
            user, "product_click", "/products",
            product_id=p["id"], product_sku=p["sku"], category=p["category"]))
        post(base_url, "/api/track-event", base_event(
            user, "product_view", page,
            product_id=p["id"], product_sku=p["sku"], category=p["category"],
            metadata={"price": p["price"], "discount_percent": p["discount_percent"],
                      "stock_quantity": p["stock_quantity"]}))

        # 4. Maybe add to cart
        if random.random() < 0.45:
            qty = random.randint(1, 3)
            cart_items_count += qty
            cart_value += p["price"] * qty
            post(base_url, "/api/cart-event", {
                "session_id": user["session_id"],
                "event_type": "add_to_cart",
                "product_id": p["id"],
                "product_name": p["name"],
                "quantity": qty,
                "unit_price": p["price"],
                "cart_total": cart_value,
            })
            post(base_url, "/api/track-event", base_event(
                user, "add_to_cart", page,
                product_id=p["id"], product_sku=p["sku"], category=p["category"],
                cart_value=cart_value, cart_items_count=cart_items_count))

        time.sleep(random.uniform(0.05, 0.2))

    # 5. Maybe checkout
    if cart_items_count > 0 and random.random() < 0.5:
        post(base_url, "/api/track-event", base_event(
            user, "page_view", "/cart",
            cart_value=cart_value, cart_items_count=cart_items_count))
        post(base_url, "/api/track-event", base_event(
            user, "cart_view", "/cart",
            cart_value=cart_value, cart_items_count=cart_items_count))
        post(base_url, "/api/track-event", base_event(
            user, "checkout_started", "/checkout",
            cart_value=cart_value, cart_items_count=cart_items_count))
        if random.random() < 0.6:
            post(base_url, "/api/track-event", base_event(
                user, "whatsapp_order_click", "/checkout",
                cart_value=cart_value, cart_items_count=cart_items_count))

    return cart_items_count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:5000")
    ap.add_argument("--users", type=int, default=20)
    ap.add_argument("--sessions", type=int, default=None,
                    help="Total sessions to generate (default = users * 2).")
    args = ap.parse_args()

    products = get_products(args.base_url)
    if not products:
        print("No products available. Did you run `python seed.py`?")
        return

    total_sessions = args.sessions or (args.users * 2)
    started = datetime.utcnow()
    print(f"[{started.isoformat()}] Simulating {total_sessions} sessions "
          f"against {args.base_url}…")

    for i in range(total_sessions):
        run_session(args.base_url, products, total_sessions)
        if (i + 1) % 5 == 0:
            print(f"  …{i+1}/{total_sessions} sessions done")

    elapsed = (datetime.utcnow() - started).total_seconds()
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
