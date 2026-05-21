"""Generate ShopPulse analytics data by driving real browser clicks.

Run the Flask app first:
    venv/bin/python app.py

Then run this script in another terminal:
    venv/bin/python automate_clicks.py --sessions 50

This is intentionally different from simulate_events.py. It uses Playwright
to click through the storefront, so frontend tracking, localStorage cart IDs,
cart rotation, checkout form submission, and browser metadata are exercised.
"""
import argparse
import random
import time
from urllib.parse import urljoin

import requests

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    raise SystemExit(
        "Playwright is required for browser-click automation.\n"
        "Install it with:\n"
        "  venv/bin/python -m pip install playwright\n"
        "  venv/bin/python -m playwright install chromium"
    ) from exc


SEARCH_TERMS = [
    "yoga mat", "blender", "snacks", "lamp", "serum", "wireless mouse",
    "tea", "spice rack", "tracker", "kitchen",
]
CUSTOMERS = [
    ("Aarav Sharma", "9876543210", "Delhi"),
    ("Maya Rao", "9988776655", "Bengaluru"),
    ("Rohan Mehta", "9123456780", "Mumbai"),
    ("Nisha Patel", "9012345678", "Ahmedabad"),
    ("Kabir Singh", "9898989898", "Pune"),
]
VIEWPORTS = [
    {"width": 390, "height": 844},
    {"width": 768, "height": 1024},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
]


def check_server(base_url):
    try:
        response = requests.get(urljoin(base_url, "/healthz"), timeout=5)
        response.raise_for_status()
    except Exception as exc:
        raise SystemExit(
            f"Could not reach {base_url}. Start the app first with "
            "`venv/bin/python app.py`."
        ) from exc


def maybe_sleep(min_ms, max_ms):
    time.sleep(random.uniform(min_ms, max_ms) / 1000.0)


def count(page, selector):
    return page.locator(selector).count()


def click_random(page, selector, timeout=5000):
    locator = page.locator(selector)
    total = locator.count()
    if total == 0:
        return False
    item = locator.nth(random.randrange(total))
    item.scroll_into_view_if_needed(timeout=timeout)
    item.click(timeout=timeout)
    return True


def browse_products(page, base_url):
    if random.random() < 0.45:
        page.goto(base_url, wait_until="networkidle")
        term = random.choice(SEARCH_TERMS)
        page.locator("#heroSearch").fill(term)
        page.locator("form").first.locator("button[type='submit']").click()
        page.wait_for_load_state("networkidle")
    else:
        page.goto(urljoin(base_url, "/products"), wait_until="networkidle")

    if random.random() < 0.35 and count(page, "select[name='category']") > 0:
        category_select = page.locator("select[name='category']")
        options = category_select.locator("option").all_inner_texts()
        options = [option.strip() for option in options if option.strip() and option != "All"]
        if options:
            category_select.select_option(label=random.choice(options))
            page.locator("button:has-text('Apply')").click()
            page.wait_for_load_state("networkidle")

    if random.random() < 0.3 and count(page, "select[name='sort']") > 0:
        page.locator("select[name='sort']").select_option(
            random.choice(["price_asc", "price_desc", "rating", "discount"])
        )
        page.locator("button:has-text('Apply')").click()
        page.wait_for_load_state("networkidle")


def add_products(page, base_url):
    added = 0
    product_clicks = random.randint(1, 5)
    for _ in range(product_clicks):
        page.goto(urljoin(base_url, "/products"), wait_until="networkidle")
        if not click_random(page, "[data-track-product-click]"):
            break
        page.wait_for_load_state("networkidle")
        maybe_sleep(250, 900)

        if random.random() < 0.75 and count(page, "[data-add-to-cart]") > 0:
            if count(page, "#qty") > 0:
                page.locator("#qty").fill(str(random.randint(1, 3)))
            page.locator("[data-add-to-cart]").first.click()
            added += 1
            maybe_sleep(300, 900)

        if random.random() < 0.25:
            page.go_back(wait_until="networkidle")

    return added


def maybe_edit_cart(page, base_url):
    page.goto(urljoin(base_url, "/cart"), wait_until="networkidle")
    maybe_sleep(250, 700)

    if random.random() < 0.2 and count(page, "[data-cart-qty]") > 0:
        qty = page.locator("[data-cart-qty]").first
        qty.fill(str(random.randint(1, 4)))
        qty.dispatch_event("change")
        maybe_sleep(250, 700)

    if random.random() < 0.15 and count(page, "[data-cart-remove]") > 0:
        page.locator("[data-cart-remove]").first.click()
        maybe_sleep(250, 700)

    if random.random() < 0.12 and count(page, "#clearCartBtn") > 0:
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#clearCartBtn").click()
        maybe_sleep(250, 700)
        return "cleared"

    return "active"


def checkout(page, base_url):
    page.goto(urljoin(base_url, "/checkout"), wait_until="networkidle")
    if "checkout" not in page.url:
        return "skipped"

    name, phone, city = random.choice(CUSTOMERS)
    page.locator("input[name='name']").fill(name)
    page.locator("input[name='phone']").fill(phone)
    page.locator("input[name='city']").fill(city)
    if random.random() < 0.35:
        page.locator("textarea[name='notes']").fill("Please confirm availability.")

    page.locator("#submitOrderBtn").click()
    try:
        page.wait_for_url("**/order-success/**", timeout=10000)
        return "converted"
    except PlaywrightTimeoutError:
        return "checkout_attempted"


def run_browser_session(browser, base_url, session_num):
    context = browser.new_context(
        viewport=random.choice(VIEWPORTS),
        locale="en-IN",
    )
    context.route("**://wa.me/**", lambda route: route.abort())
    context.on("page", lambda popup: popup.close() if "wa.me" in popup.url else None)
    page = context.new_page()

    try:
        browse_products(page, base_url)
        added_count = add_products(page, base_url)
        if added_count == 0:
            context.close()
            return "browsed_only"

        cart_state = maybe_edit_cart(page, base_url)
        if cart_state == "cleared":
            context.close()
            return "cleared"

        if random.random() < 0.65:
            result = checkout(page, base_url)
        else:
            result = "abandoned_cart"
        context.close()
        return result
    except Exception as exc:
        context.close()
        print(f"Session {session_num} failed: {exc}")
        return "failed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--sessions", type=int, default=25)
    parser.add_argument("--headful", action="store_true",
                        help="Show the browser instead of running headless.")
    parser.add_argument("--slow-mo", type=int, default=0,
                        help="Delay each browser action by N milliseconds.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    check_server(base_url)

    results = {}
    started = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful, slow_mo=args.slow_mo)
        for i in range(1, args.sessions + 1):
            result = run_browser_session(browser, base_url, i)
            results[result] = results.get(result, 0) + 1
            if i % 5 == 0 or i == args.sessions:
                print(f"{i}/{args.sessions} sessions complete: {results}")
        browser.close()

    elapsed = time.time() - started
    print(f"Done in {elapsed:.1f}s. Final results: {results}")


if __name__ == "__main__":
    main()
