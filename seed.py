"""Idempotent catalog seed for ShopPulse Store.

Run:
    python seed.py
"""
import re
import random

from app import create_app
from models import Category, Product, db


CATEGORIES = [
    ("Fitness", "Gear for home workouts and active lifestyles."),
    ("Wellness", "Self-care, mindfulness, and recovery essentials."),
    ("Kitchen", "Smart, compact, and useful kitchen tools."),
    ("Home Office", "Make working from home comfortable and productive."),
    ("Skincare", "Daily skincare picks with quality formulations."),
    ("Pet Care", "Comfort and care for your furry companions."),
    ("Electronics Accessories", "Cables, stands, and gadgets that just work."),
    ("Healthy Snacks", "Better-for-you snacks with honest ingredients."),
]

# (name, brand, price, discount, stock, rating, short_desc, long_desc)
PRODUCTS = {
    "Fitness": [
        ("Yoga Mat Pro", "FlexFit", 1299, 20, 120, 4.6,
         "Anti-skid, 6mm thick yoga mat for daily practice.",
         "A premium 6mm TPE yoga mat with non-slip texture, sweat-resistant surface and a carry strap. Built for hot yoga, pilates, and floor workouts."),
        ("Resistance Band Set", "FlexFit", 799, 25, 200, 4.4,
         "5-piece latex bands with door anchor.",
         "Five colour-coded resistance bands (10-50 lb), door anchor, ankle straps and handles. Full-body strength training in a pouch."),
        ("Foam Roller", "RollEase", 999, 15, 80, 4.5,
         "High-density EVA foam roller for muscle recovery.",
         "33cm high-density foam roller for myofascial release. Reduces soreness and improves mobility post-workout."),
        ("Digital Skipping Rope", "JumpIQ", 699, 30, 150, 4.3,
         "Jump-count display with adjustable cable length.",
         "Smart skipping rope with built-in counter, adjustable nylon cable and ergonomic handles. Track jumps and calories on the LCD display."),
        ("Adjustable Hand Grip", "GripMax", 499, 20, 220, 4.2,
         "10-60kg adjustable resistance hand grip.",
         "Forearm and wrist trainer with adjustable resistance from 10 to 60 kg. Built with a durable steel spring and silicone-padded handles."),
    ],
    "Wellness": [
        ("Copper Water Bottle", "PureSip", 899, 25, 180, 4.5,
         "1L pure copper bottle for ayurvedic hydration.",
         "Hand-finished 1-litre pure copper bottle. Leak-proof cap, polished exterior, ayurveda-recommended for daily hydration."),
        ("Herbal Sleep Tea", "CalmLeaf", 449, 15, 250, 4.4,
         "Chamomile and ashwagandha sleep blend, 30 sachets.",
         "Caffeine-free herbal infusion of chamomile, ashwagandha, lavender and tulsi. Sip 30 minutes before bed for deeper rest."),
        ("Aromatherapy Diffuser", "Aurora", 1599, 20, 90, 4.6,
         "300ml ultrasonic diffuser with 7 LED colours.",
         "300ml ultrasonic essential oil diffuser with whisper-quiet operation, auto shut-off and 7 ambient LED colours."),
        ("Posture Corrector", "AlignFit", 999, 30, 140, 4.1,
         "Adjustable upper-back posture support.",
         "Breathable shoulder-strap posture corrector. Trains your back to sit and stand straighter through gentle reminder pull."),
        ("Acupressure Slippers", "ReflexStep", 599, 20, 160, 4.0,
         "Reflexology slippers for daily foot massage.",
         "Acupressure slippers with strategically placed nodes that target reflex zones to relieve fatigue and improve circulation."),
    ],
    "Kitchen": [
        ("Portable Blender", "MixGo", 1899, 25, 110, 4.4,
         "USB-rechargeable 400ml personal blender.",
         "Cordless 400ml blender with 6 stainless steel blades. USB-C charging, ideal for smoothies, protein shakes, and travel."),
        ("Steel Lunch Box", "TiffinPro", 899, 15, 200, 4.5,
         "3-tier insulated steel lunch box, 1L.",
         "Three-tier insulated stainless-steel tiffin with leak-proof seal. Keeps meals warm for up to 4 hours."),
        ("Air Fryer Liners", "CrispCo", 399, 20, 300, 4.3,
         "100 disposable parchment liners, 8-inch.",
         "Pack of 100 perforated parchment liners that fit most 4-7L air fryers. Non-stick, oil-resistant, and food-safe."),
        ("Spice Organizer", "RackIt", 1199, 20, 120, 4.4,
         "Rotating 16-jar spice carousel.",
         "Sturdy 360° rotating carousel with 16 airtight glass spice jars, label stickers and a chalk marker."),
        ("Oil Spray Bottle", "MistKitchen", 499, 15, 250, 4.2,
         "200ml glass oil sprayer for healthy cooking.",
         "Glass oil mister with adjustable nozzle. Use less oil for healthier sautéing, salads and air-frying."),
    ],
    "Home Office": [
        ("Laptop Stand", "DeskRise", 1499, 20, 130, 4.6,
         "Ergonomic aluminium laptop riser, foldable.",
         "Heat-dissipating aluminium laptop stand. Foldable, height adjustable and supports up to 17-inch laptops."),
        ("Desk Organizer", "Tidyo", 999, 25, 150, 4.4,
         "Mesh metal desk organiser with drawer.",
         "Premium mesh metal organiser with pen slots, file rack, sticky-note pad and a small drawer for clips and cables."),
        ("Ergonomic Mouse Pad", "WristEase", 599, 15, 200, 4.3,
         "Memory-foam wrist-rest mouse pad.",
         "Memory-foam wrist-support mouse pad with smooth fabric surface and non-slip rubber base."),
        ("LED Desk Lamp", "BrightDesk", 1799, 25, 95, 4.5,
         "Eye-care LED desk lamp with 3 modes.",
         "Flicker-free LED desk lamp with three colour modes, touch dimmer, and a USB charging port. Reduces eye strain on long work sessions."),
        ("Cable Management Box", "WireCalm", 899, 20, 180, 4.4,
         "Heat-resistant cable management box, large.",
         "Large heat-resistant ABS box that hides power strips and tangled cables. Keeps your workspace clean and child-safe."),
    ],
    "Skincare": [
        ("Aloe Vera Gel", "BotanicaDaily", 349, 10, 300, 4.3,
         "99% pure aloe vera gel, 200g.",
         "Cold-processed aloe vera gel sourced from organic farms. Lightweight, fast-absorbing, and great for face, hair and after-sun care."),
        ("Vitamin C Face Serum", "GlowLab", 899, 30, 180, 4.6,
         "10% Vitamin C brightening serum, 30ml.",
         "Stable 10% L-ascorbic acid serum with hyaluronic acid and vitamin E. Brightens, evens tone, and boosts skin radiance."),
        ("Sunscreen SPF 50", "ShieldSun", 699, 20, 220, 4.5,
         "SPF 50 PA+++ matte-finish sunscreen, 50g.",
         "Lightweight, non-greasy SPF 50 PA+++ broad-spectrum sunscreen. Matte finish, no white cast, suitable for all skin types."),
        ("Under Eye Gel", "GlowLab", 599, 20, 170, 4.4,
         "Caffeine + niacinamide under-eye gel.",
         "Cooling under-eye gel with caffeine, niacinamide and cucumber extract. Reduces puffiness and dark circles with daily use."),
        ("Clay Face Mask", "BotanicaDaily", 549, 15, 200, 4.3,
         "Bentonite + kaolin detox clay mask, 100g.",
         "Deep-cleansing clay mask blend of bentonite and kaolin with rosehip oil. Detoxifies pores without over-drying."),
    ],
    "Pet Care": [
        ("Dog Grooming Glove", "PawCare", 599, 20, 150, 4.4,
         "Silicone deshedding glove for dogs and cats.",
         "Soft-tip silicone grooming glove that gently removes loose hair while massaging your pet. Machine-washable."),
        ("Pet Water Bottle", "PawCare", 699, 25, 180, 4.5,
         "Leak-proof travel water bottle for pets, 400ml.",
         "Portable 400ml pet water bottle with built-in trough and one-handed operation. Perfect for walks and road trips."),
        ("Anti-Skid Pet Bowl", "FurFeast", 499, 15, 200, 4.3,
         "Stainless steel bowl with rubber base.",
         "Heavy-gauge stainless steel pet bowl with anti-skid silicone base. Dishwasher-safe and rust-resistant."),
        ("Dog Chew Toy", "PlayPup", 449, 20, 220, 4.2,
         "Natural rubber chew toy for aggressive chewers.",
         "Durable natural rubber chew toy designed for strong chewers. Helps clean teeth and reduce anxiety."),
        ("Pet Hair Remover", "FurFeast", 899, 25, 140, 4.5,
         "Reusable pet hair lint roller.",
         "Reusable self-cleaning pet hair roller. No tape, no batteries — just twist and empty. Works on sofas, beds and clothes."),
    ],
    "Electronics Accessories": [
        ("Phone Stand", "DockMate", 399, 20, 280, 4.3,
         "Aluminium adjustable phone and tablet stand.",
         "Foldable aluminium stand for phones and tablets up to 12.9 inches. Adjustable angle, anti-scratch silicone pads."),
        ("Fast Charging Cable", "BoltLink", 499, 25, 320, 4.4,
         "1.5m braided USB-C to USB-C cable, 60W.",
         "Nylon-braided 1.5m USB-C to USB-C cable supporting 60W PD fast charging and 480Mbps data."),
        ("Bluetooth Tracker", "FindIt", 1299, 20, 130, 4.5,
         "Slim Bluetooth tracker tag for keys and wallets.",
         "Coin-cell Bluetooth tracker with 1-year battery, finder ring, and replaceable battery. Works with iOS and Android."),
        ("Laptop Cleaning Kit", "PixelPure", 599, 15, 200, 4.2,
         "5-in-1 screen and keyboard cleaning kit.",
         "Includes screen spray, microfibre cloth, brush, cleaning gel and air blower. Safe for laptops, phones and TVs."),
        ("Wireless Mouse", "ClickEdge", 999, 20, 180, 4.5,
         "2.4GHz silent wireless mouse with USB receiver.",
         "Ergonomic silent-click wireless mouse with 1600 DPI, 18-month battery and a nano USB receiver."),
    ],
    "Healthy Snacks": [
        ("Protein Trail Mix", "FuelBite", 549, 15, 250, 4.4,
         "Roasted nuts, seeds and berries, 250g.",
         "Power-packed mix of almonds, cashews, pumpkin seeds, cranberries and dark chocolate chips. 12g protein per 40g serving."),
        ("Roasted Makhana", "DesiCrunch", 299, 20, 320, 4.5,
         "Pink himalayan salt roasted makhana, 100g.",
         "Light, crunchy roasted fox-nuts seasoned with pink himalayan salt. A guilt-free, low-calorie evening snack."),
        ("Millet Cookies", "DesiCrunch", 349, 15, 220, 4.3,
         "Ragi and bajra cookies with jaggery, 200g.",
         "Wholesome cookies baked with ragi, bajra and jaggery. No refined sugar, no maida — perfect for tea-time munching."),
        ("Peanut Butter", "FuelBite", 599, 20, 180, 4.6,
         "Crunchy 100% peanut butter, 500g, no sugar.",
         "Stone-ground crunchy peanut butter made with 100% roasted peanuts. No sugar, no palm oil — just real ingredients."),
        ("Granola Bars", "FuelBite", 449, 25, 240, 4.4,
         "Oats and honey granola bars, pack of 12.",
         "Soft-baked granola bars with oats, honey, almonds and dark chocolate. A balanced on-the-go snack for busy days."),
    ],
}


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def sku_for(category: str, name: str, idx: int) -> str:
    cat_part = "".join(w[0] for w in category.split()).upper()[:3]
    name_part = "".join(w[0] for w in name.split()).upper()[:4]
    return f"{cat_part}-{name_part}-{idx:03d}"


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Categories
        cat_objs = {}
        for name, desc in CATEGORIES:
            slug = slugify(name)
            cat = Category.query.filter_by(slug=slug).first()
            if not cat:
                cat = Category(
                    name=name,
                    slug=slug,
                    description=desc,
                    image_url=f"https://picsum.photos/seed/{slug}/600/400",
                    is_active=True,
                )
                db.session.add(cat)
            cat_objs[name] = cat
        db.session.commit()

        # Products
        random.seed(42)
        added = 0
        idx_global = 0
        for category, items in PRODUCTS.items():
            for i, (name, brand, price, discount, stock, rating,
                    short_desc, long_desc) in enumerate(items, start=1):
                idx_global += 1
                slug = slugify(name)
                sku = sku_for(category, name, idx_global)
                if Product.query.filter((Product.sku == sku) | (Product.slug == slug)).first():
                    continue
                compare_at = round(price / (1 - discount / 100), 0) if discount else None
                p = Product(
                    sku=sku,
                    name=name,
                    slug=slug,
                    category=category,
                    subcategory=None,
                    brand=brand,
                    description=long_desc,
                    short_description=short_desc,
                    price=float(price),
                    compare_at_price=compare_at,
                    discount_percent=discount,
                    stock_quantity=stock,
                    image_url=f"https://picsum.photos/seed/{sku}/600/600",
                    rating=rating,
                    review_count=random.randint(20, 500),
                    is_featured=(i <= 2),
                    is_active=True,
                )
                db.session.add(p)
                added += 1
        db.session.commit()
        total = Product.query.count()
        print(f"Seed complete. Inserted {added} new products. Total products: {total}.")
        print(f"Categories: {Category.query.count()}.")


if __name__ == "__main__":
    seed()
