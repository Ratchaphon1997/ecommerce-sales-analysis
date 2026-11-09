"""
generate_data.py
Generates realistic synthetic e-commerce dataset for portfolio demonstration.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

np.random.seed(42)
random.seed(42)

# ─── Constants ────────────────────────────────────────────────────────────────
N_CUSTOMERS    = 2_000
N_PRODUCTS     = 150
N_ORDERS       = 15_000
START_DATE     = datetime(2023, 1, 1)
END_DATE       = datetime(2024, 12, 31)
OUTPUT_DIR     = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

CATEGORIES = {
    "Electronics":   {"weight": 0.25, "price_range": (500, 50_000)},
    "Fashion":       {"weight": 0.20, "price_range": (100, 5_000)},
    "Home & Living": {"weight": 0.18, "price_range": (150, 15_000)},
    "Beauty":        {"weight": 0.15, "price_range": (50, 3_000)},
    "Sports":        {"weight": 0.12, "price_range": (200, 8_000)},
    "Books":         {"weight": 0.10, "price_range": (99, 999)},
}

REGIONS = ["Bangkok", "Central", "North", "Northeast", "South"]
CHANNELS = ["Website", "Mobile App", "Marketplace", "In-store"]
PAYMENT_METHODS = ["Credit Card", "QR Code", "Bank Transfer", "Cash on Delivery"]
STATUSES = ["Completed", "Completed", "Completed", "Returned", "Cancelled"]


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    # Simulate seasonality: higher orders in Nov–Dec
    weights = []
    for _ in range(delta.days + 1):
        d = start + timedelta(days=len(weights))
        month_weight = 1.5 if d.month in (11, 12) else (1.2 if d.month in (6, 7) else 1.0)
        weights.append(month_weight)
    total = sum(weights)
    probs = [w / total for w in weights]
    day_offset = np.random.choice(range(delta.days + 1), p=probs)
    return start + timedelta(days=int(day_offset))


# ─── Customers ────────────────────────────────────────────────────────────────
def generate_customers() -> pd.DataFrame:
    first_names = ["Somchai", "Nida", "Krit", "Ploy", "Anan", "Suda",
                   "Tanaka", "Mira", "Ben", "Fon", "Win", "Pim"]
    last_names  = ["Jaidee", "Phonsri", "Rattana", "Kasem", "Siriporn",
                   "Boonsong", "Thongsuk", "Lertpong", "Nualchawee"]

    customers = pd.DataFrame({
        "customer_id": [f"C{str(i).zfill(5)}" for i in range(1, N_CUSTOMERS + 1)],
        "name":        [f"{random.choice(first_names)} {random.choice(last_names)}"
                        for _ in range(N_CUSTOMERS)],
        "age":         np.random.randint(18, 65, N_CUSTOMERS),
        "gender":      np.random.choice(["Male", "Female", "Not Specified"],
                                        N_CUSTOMERS, p=[0.45, 0.50, 0.05]),
        "region":      np.random.choice(REGIONS, N_CUSTOMERS,
                                        p=[0.40, 0.25, 0.15, 0.12, 0.08]),
        "signup_date": [random_date(datetime(2020, 1, 1), START_DATE)
                        .strftime("%Y-%m-%d") for _ in range(N_CUSTOMERS)],
        "loyalty_tier": np.random.choice(["Bronze", "Silver", "Gold", "Platinum"],
                                         N_CUSTOMERS, p=[0.50, 0.28, 0.15, 0.07]),
    })
    return customers


# ─── Products ─────────────────────────────────────────────────────────────────
def generate_products() -> pd.DataFrame:
    cat_names  = list(CATEGORIES.keys())
    cat_weights = [CATEGORIES[c]["weight"] for c in cat_names]

    products = []
    for i in range(1, N_PRODUCTS + 1):
        cat = random.choices(cat_names, weights=cat_weights)[0]
        lo, hi = CATEGORIES[cat]["price_range"]
        cost_price  = round(random.uniform(lo * 0.4, hi * 0.5), 2)
        sell_price  = round(cost_price * random.uniform(1.3, 2.5), 2)
        products.append({
            "product_id":   f"P{str(i).zfill(4)}",
            "product_name": f"{cat} Product {i}",
            "category":     cat,
            "cost_price":   cost_price,
            "sell_price":   sell_price,
            "stock":        random.randint(0, 500),
            "rating":       round(random.uniform(2.5, 5.0), 1),
        })
    return pd.DataFrame(products)


# ─── Orders & Order Items ──────────────────────────────────────────────────────
def generate_orders(customers: pd.DataFrame, products: pd.DataFrame):
    orders, order_items = [], []
    item_id = 1

    for i in range(1, N_ORDERS + 1):
        order_date = random_date(START_DATE, END_DATE)
        customer   = customers.sample(1).iloc[0]
        status     = random.choice(STATUSES)
        channel    = random.choice(CHANNELS)
        payment    = random.choice(PAYMENT_METHODS)
        discount   = round(random.choice([0, 0, 0, 5, 10, 15, 20]) / 100, 2)
        n_items    = random.randint(1, 5)
        order_products = products.sample(n_items)

        order_total = 0
        for _, prod in order_products.iterrows():
            qty      = random.randint(1, 3)
            subtotal = round(prod["sell_price"] * qty * (1 - discount), 2)
            order_total += subtotal
            order_items.append({
                "item_id":    f"I{str(item_id).zfill(6)}",
                "order_id":   f"O{str(i).zfill(6)}",
                "product_id": prod["product_id"],
                "quantity":   qty,
                "unit_price": prod["sell_price"],
                "discount":   discount,
                "subtotal":   subtotal,
            })
            item_id += 1

        orders.append({
            "order_id":    f"O{str(i).zfill(6)}",
            "customer_id": customer["customer_id"],
            "order_date":  order_date.strftime("%Y-%m-%d"),
            "status":      status,
            "channel":     channel,
            "payment":     payment,
            "discount":    discount,
            "total_amount": round(order_total, 2),
            "region":      customer["region"],
        })

    return pd.DataFrame(orders), pd.DataFrame(order_items)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Generating data...")

    customers = generate_customers()
    products  = generate_products()
    orders, order_items = generate_orders(customers, products)

    customers.to_csv(os.path.join(OUTPUT_DIR, "customers.csv"), index=False)
    products.to_csv(os.path.join(OUTPUT_DIR, "products.csv"), index=False)
    orders.to_csv(os.path.join(OUTPUT_DIR, "orders.csv"), index=False)
    order_items.to_csv(os.path.join(OUTPUT_DIR, "order_items.csv"), index=False)

    print(f"[OK] customers   : {len(customers):,} rows")
    print(f"[OK] products    : {len(products):,} rows")
    print(f"[OK] orders      : {len(orders):,} rows")
    print(f"[OK] order_items : {len(order_items):,} rows")
    print(f"\nSaved to: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
