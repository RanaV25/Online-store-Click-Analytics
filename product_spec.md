You are a senior full-stack Flask developer, data engineer, and MLOps project architect.

 

Build a complete demo e-commerce store called “ShopPulse Store” using:

 

- Python Flask
- SQLite
- SQLAlchemy
- Bootstrap 5
- Jinja templates
- Vanilla JavaScript
- LocalStorage for cart
- WhatsApp-based order submission
- No payment gateway
- No user login required in v1

 

The main purpose of this store is NOT real commerce. It is to generate realistic clickstream, cart, product, search, and order-intent data for a future Azure MLOps project.

 

The final app should help teach:
1. Web event tracking
2. Product catalog management
3. Cart behavior tracking
4. WhatsApp order flow
5. Batch data storage
6. Streaming-style click analytics simulation
7. Future ML model training using collected events

 

==================================================
CORE GOAL
==================================================

 

Create a working Flask + SQLite store where users can:

 

- View a landing page
- Browse categories
- View product listing pages
- View product detail pages
- Search products
- Filter products
- Add products to cart
- Update cart quantity
- Remove products from cart
- Go to checkout page
- Enter name, phone, city, and notes
- Click “Order on WhatsApp”
- Generate a prefilled WhatsApp message with cart details
- Store order intent in SQLite before redirecting to WhatsApp
- Track all major clickstream events in the database

 

No online payment is needed.

 

==================================================
TECH STACK
==================================================

 

Use this stack:

 

- Flask
- SQLAlchemy
- SQLite
- Bootstrap 5
- Jinja2
- Vanilla JavaScript
- LocalStorage
- Chart.js for basic analytics charts
- python-dotenv
- Flask-Migrate optional but not required

 

Do not use React.
Do not use external paid APIs.
Do not use complex authentication.
Do not build admin login in v1 unless time allows.

 

==================================================
PROJECT STRUCTURE
==================================================

 

Create this folder structure:

 

shoppulse_store/
│
├── app.py
├── config.py
├── models.py
├── seed.py
├── requirements.txt
├── README.md
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── analytics.js
│   │   ├── cart.js
│   │   └── main.js
│   └── images/
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── products.html
│   ├── product_detail.html
│   ├── category.html
│   ├── cart.html
│   ├── checkout.html
│   ├── order_success.html
│   ├── analytics_dashboard.html
│   └── partials/
│       ├── navbar.html
│       ├── footer.html
│       └── product_card.html
│
└── data/
    └── shoppulse.db

 

==================================================
DATABASE TABLES
==================================================

 

Create these SQLite tables using SQLAlchemy.

 

1. Product

 

Fields:

 

- id
- sku
- name
- slug
- category
- subcategory
- brand
- description
- short_description
- price
- compare_at_price
- discount_percent
- stock_quantity
- image_url
- rating
- review_count
- is_featured
- is_active
- created_at
- updated_at

 

2. Category

 

Fields:

 

- id
- name
- slug
- description
- image_url
- is_active

 

3. ClickEvent

 

This is very important.

 

Fields:

 

- id
- event_id
- session_id
- user_id
- event_type
- page_url
- page_title
- referrer
- product_id
- product_sku
- category
- search_query
- filter_name
- filter_value
- cart_value
- cart_items_count
- traffic_source
- device_type
- browser
- city
- metadata_json
- created_at

 

Track all meaningful events here.

 

4. CartEvent

 

Fields:

 

- id
- session_id
- event_type
- product_id
- product_name
- quantity
- unit_price
- cart_total
- created_at

 

Event types:

 

- add_to_cart
- remove_from_cart
- update_quantity
- clear_cart
- checkout_started

 

5. OrderIntent

 

Fields:

 

- id
- order_code
- customer_name
- customer_phone
- customer_city
- customer_notes
- cart_json
- total_amount
- total_items
- whatsapp_message
- status
- created_at

 

Status options:

 

- pending_whatsapp
- whatsapp_clicked
- manually_confirmed
- cancelled

 

6. SearchQuery

 

Fields:

 

- id
- session_id
- query
- results_count
- created_at

 

==================================================
SEED DATA
==================================================

 

Create a seed.py file that inserts at least 40 products across 8 categories.

 

Categories:

 

1. Fitness
2. Wellness
3. Kitchen
4. Home Office
5. Skincare
6. Pet Care
7. Electronics Accessories
8. Healthy Snacks

 

Each product should have realistic Indian pricing between ₹299 and ₹2499.

 

Add example products like:

 

Fitness:
- Yoga Mat Pro
- Resistance Band Set
- Foam Roller
- Digital Skipping Rope
- Adjustable Hand Grip

 

Wellness:
- Copper Water Bottle
- Herbal Sleep Tea
- Aromatherapy Diffuser
- Posture Corrector
- Acupressure Slippers

 

Kitchen:
- Portable Blender
- Steel Lunch Box
- Air Fryer Liners
- Spice Organizer
- Oil Spray Bottle

 

Home Office:
- Laptop Stand
- Desk Organizer
- Ergonomic Mouse Pad
- LED Desk Lamp
- Cable Management Box

 

Skincare:
- Aloe Vera Gel
- Vitamin C Face Serum
- Sunscreen SPF 50
- Under Eye Gel
- Clay Face Mask

 

Pet Care:
- Dog Grooming Glove
- Pet Water Bottle
- Anti-Skid Pet Bowl
- Dog Chew Toy
- Pet Hair Remover

 

Electronics Accessories:
- Phone Stand
- Fast Charging Cable
- Bluetooth Tracker
- Laptop Cleaning Kit
- Wireless Mouse

 

Healthy Snacks:
- Protein Trail Mix
- Roasted Makhana
- Millet Cookies
- Peanut Butter
- Granola Bars

 

Seed data should include:

 

- Product name
- Slug
- Category
- Brand
- Price
- Discount
- Stock
- Rating
- Short description
- Long description
- Image URL placeholder

 

Use placeholder images from a safe placeholder service or local static placeholders.

 

==================================================
PAGES TO BUILD
==================================================

 

1. Landing Page: /

 

Purpose:
- Show hero section
- Featured categories
- Featured products
- Search bar
- Trending products
- “Order via WhatsApp” explanation
- CTA buttons

 

Track events:
- page_view
- hero_cta_click
- category_click
- featured_product_click
- search_submit

 

2. Product Listing Page: /products

 

Features:
- Product grid
- Category filter
- Price filter
- Sort by price, rating, discount
- Search query support
- Add to cart button
- View details button

 

Track events:
- page_view
- product_impression
- product_click
- filter_used
- sort_used
- add_to_cart

 

3. Category Page: /category/<slug>

 

Features:
- Show all products in that category
- Category description
- Filters
- Add to cart

 

Track events:
- category_view
- product_click
- add_to_cart
- filter_used

 

4. Product Detail Page: /product/<slug>

 

Features:
- Product image
- Product name
- Price
- Compare-at price
- Discount
- Stock status
- Rating
- Description
- Quantity selector
- Add to cart button
- Buy via WhatsApp button
- Related products

 

Track events:
- product_view
- add_to_cart
- whatsapp_buy_click
- related_product_click

 

5. Cart Page: /cart

 

Cart must be handled with LocalStorage.

 

Features:
- Show cart items
- Update quantity
- Remove item
- Clear cart
- Cart total
- Continue shopping
- Proceed to checkout

 

Track events:
- cart_view
- update_quantity
- remove_from_cart
- clear_cart
- checkout_click

 

6. Checkout Page: /checkout

 

No payment.

 

Fields:
- Name
- Phone
- City
- Notes

 

Features:
- Show cart summary from LocalStorage
- Submit order intent to Flask
- Save OrderIntent in SQLite
- Generate WhatsApp message
- Redirect/open WhatsApp link

 

Track events:
- checkout_view
- checkout_form_started
- checkout_form_submit
- whatsapp_order_click

 

7. Order Success Page: /order-success/<order_code>

 

Features:
- Thank the user
- Show order code
- Show WhatsApp next-step message
- Show “Continue Shopping” button

 

Track events:
- order_success_view

 

8. Analytics Dashboard: /analytics

 

Simple internal analytics page.

 

Show:
- Total page views
- Total product views
- Total add-to-cart events
- Total checkout starts
- Total WhatsApp order clicks
- Top viewed products
- Top added-to-cart products
- Top searched terms
- Conversion funnel:
  page_view → product_view → add_to_cart → checkout_started → whatsapp_order_click
- Recent click events table
- Recent order intents table

 

Use Chart.js for:
- Event count by type
- Top products by views
- Funnel chart
- Events over time

 

No login needed for v1, but add a note in README that this should be protected before production.

 

==================================================
LOCALSTORAGE CART REQUIREMENTS
==================================================

 

Create static/js/cart.js.

 

Cart object format:

 

{
  "items": [
    {
      "product_id": 1,
      "sku": "FIT-YOGA-001",
      "name": "Yoga Mat Pro",
      "slug": "yoga-mat-pro",
      "price": 999,
      "quantity": 2,
      "image_url": "/static/images/yoga-mat.jpg",
      "category": "Fitness"
    }
  ],
  "updated_at": "2026-05-07T12:30:00"
}

 

cart.js should include:

 

- getCart()
- saveCart(cart)
- addToCart(product)
- removeFromCart(productId)
- updateQuantity(productId, quantity)
- clearCart()
- getCartTotal()
- getCartItemsCount()
- renderCart()
- updateCartBadge()

 

Whenever cart changes, send analytics event to backend.

 

==================================================
ANALYTICS TRACKING REQUIREMENTS
==================================================

 

Create static/js/analytics.js.

 

It should:

 

1. Generate or retrieve session_id from LocalStorage.
2. Generate or retrieve anonymous user_id from LocalStorage.
3. Capture page URL, referrer, title, device type, browser.
4. Send events to /api/track-event using fetch POST.
5. Fail silently if analytics endpoint fails.
6. Support custom metadata.

 

Functions:

 

- getSessionId()
- getAnonymousUserId()
- trackEvent(eventType, payload = {})
- trackPageView()
- detectDeviceType()
- getTrafficSource()

 

Example event payload:

 

{
  "event_type": "product_view",
  "product_id": 12,
  "product_sku": "FIT-YOGA-001",
  "category": "Fitness",
  "page_url": "/product/yoga-mat-pro",
  "metadata": {
    "price": 999,
    "discount_percent": 20,
    "stock_quantity": 35
  }
}

 

Every page should automatically track page_view.

 

==================================================
BACKEND API ROUTES
==================================================

 

Create these Flask routes:

 

Frontend routes:

 

- GET /
- GET /products
- GET /category/<slug>
- GET /product/<slug>
- GET /cart
- GET /checkout
- GET /order-success/<order_code>
- GET /analytics

 

API routes:

 

- POST /api/track-event
- POST /api/cart-event
- POST /api/create-order-intent
- GET /api/products
- GET /api/analytics/summary
- GET /api/analytics/funnel
- GET /api/analytics/top-products
- GET /api/analytics/recent-events

 

==================================================
WHATSAPP ORDER FLOW
==================================================

 

On checkout submit:

 

1. Read cart from LocalStorage.
2. Validate cart is not empty.
3. Collect customer details.
4. POST to /api/create-order-intent.
5. Backend saves the order intent.
6. Backend returns:
   - order_code
   - whatsapp_url
7. Frontend opens WhatsApp URL.

 

Use this WhatsApp number as placeholder:

 

+919999999999

 

Keep it configurable in config.py.

 

WhatsApp message format:

 

Hello ShopPulse Store,

 

I want to place an order.

 

Order Code: SP-20260507-001

 

Customer Details:
Name: Rahul Sharma
Phone: 9876543210
City: Delhi

 

Products:
1. Yoga Mat Pro x 2 = ₹1998
2. Copper Water Bottle x 1 = ₹799

 

Total Items: 3
Total Amount: ₹2797

 

Notes:
Please confirm availability.

 

The user will manually complete the order on WhatsApp.

 

==================================================
ML/MLOPS-FRIENDLY DATA DESIGN
==================================================

 

Design the analytics data so it can later be exported for ML.

 

The future model will predict:

 

“Will a product become high demand in the next 30 or 60 minutes?”

 

Therefore, capture data useful for ML:

 

- product views
- add-to-cart events
- search events
- category views
- traffic source
- hour of day
- day of week
- product price
- discount
- stock quantity
- cart value
- device type
- session behavior
- checkout intent

 

Add comments in the code explaining how ClickEvent and CartEvent can later be sent to:

 

- Azure Event Hubs
- Azure Data Lake Storage
- Azure Machine Learning pipeline

 

==================================================
BATCH EXPORT REQUIREMENTS
==================================================

 

Add a simple export route or CLI function to export data as CSV.

 

Exports:

 

- products.csv
- click_events.csv
- cart_events.csv
- order_intents.csv
- search_queries.csv

 

Save exported files under:

 

exports/YYYY-MM-DD/

 

This will later simulate batch data ingestion into Azure Data Lake.

 

==================================================
STREAMING SIMULATION REQUIREMENT
==================================================

 

Create a Python script called simulate_events.py.

 

It should generate fake clickstream events and POST them to /api/track-event.

 

Simulate:

 

- 20 anonymous users
- Product views
- Category views
- Searches
- Add to cart
- Checkout starts
- WhatsApp clicks

 

This script will be useful before real traffic exists.

 

==================================================
DESIGN STYLE
==================================================

 

Use Bootstrap 5.

 

Design should be:

 

- Clean
- Modern
- Mobile responsive
- Good enough for demo
- Not overly complex

 

Use simple colors:

 

- White background
- Dark navy text
- Light gray sections
- Green CTA buttons for WhatsApp
- Blue accents for analytics

 

Landing page should clearly say:

 

“Demo store for real-time demand prediction and MLOps analytics.”

 

But keep it looking like a real store.

 

==================================================
README REQUIREMENTS
==================================================

 

Create a detailed README.md with:

 

1. Project overview
2. Setup instructions
3. How to create database
4. How to run seed.py
5. How to start Flask app
6. How cart works
7. How analytics tracking works
8. How WhatsApp order flow works
9. How to use simulate_events.py
10. How to export data
11. Future Azure architecture

 

Include commands:

 

python -m venv venv
source venv/bin/activate or venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python app.py
python simulate_events.py

 

==================================================
QUALITY REQUIREMENTS
==================================================

 

Important:

 

- Write clean, modular code.
- Do not leave TODO placeholders for core features.
- Make the app runnable locally.
- Include all required files.
- Include complete code, not partial snippets.
- Use environment variables for WhatsApp number and Flask secret.
- Handle empty cart gracefully.
- Handle missing products gracefully.
- Prevent duplicate seed insertion where possible.
- Validate checkout form.
- Use JSON fields carefully.
- Add basic error handling.
- Add comments only where useful.

 

==================================================
ACCEPTANCE CRITERIA
==================================================

 

The project is complete only if:

 

1. Flask app runs locally.
2. SQLite database is created.
3. Seed products are inserted.
4. Landing page loads.
5. Product listing works.
6. Product detail page works.
7. Cart works using LocalStorage.
8. Cart badge updates.
9. Checkout page reads cart from LocalStorage.
10. Order intent is saved to SQLite.
11. WhatsApp message is generated correctly.
12. Analytics events are stored in ClickEvent table.
13. Add-to-cart events are stored.
14. Analytics dashboard shows event counts.
15. simulate_events.py can generate fake events.
16. CSV export works.
17. README explains setup clearly.

 

Build the complete project now.

