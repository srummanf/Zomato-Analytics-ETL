"""Step 2: Synthetic Data Generation — customers, orders, order items, payments,
deliveries for one simulated day, anchored to real restaurant signals
(rating, votes, cost-for-two) so volumes/values stay plausible.

Customers use a fixed random seed, so the pool is identical every run (acts
like a stable dimension without needing a "does this file exist" check).
Transactional tables (orders/items/payments/deliveries) are seeded by the
--date argument and appended to their CSV, simulating one new day of data.
"""
import argparse
import random
import re
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from faker import Faker

DATA_DIR = Path(__file__).parent / "data"
RESTAURANTS_FILE = DATA_DIR / "raw_restaurants.csv"

CUSTOMER_POOL_SIZE = 5000
DELIVERY_PARTNER_POOL_SIZE = 300
MENU_ITEMS = ["Combo Meal", "Starter", "Main Course", "Dessert", "Beverage", "Biryani", "Thali"]
PAYMENT_METHODS = ["UPI", "Card", "Cash on Delivery", "Wallet"]


def load_restaurants():
    df = pd.read_csv(RESTAURANTS_FILE)
    df["restaurant_id"] = df.index

    def parse_rate(value):
        if not isinstance(value, str):
            return None
        match = re.search(r"(\d\.\d)", value)
        return float(match.group(1)) if match else None

    def parse_cost(value):
        if not isinstance(value, str):
            return None
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None

    df["rate_parsed"] = df["rate"].apply(parse_rate)
    df["cost_parsed"] = df["approx_cost(for two people)"].apply(parse_cost)
    df["rate_parsed"] = df["rate_parsed"].fillna(df["rate_parsed"].mean())
    df["cost_parsed"] = df["cost_parsed"].fillna(df["cost_parsed"].median())
    df["weight"] = (df["votes"] + 1) * df["rate_parsed"]
    return df


def build_customer_pool():
    fake = Faker()
    Faker.seed(7)
    random.seed(7)
    return pd.DataFrame([
        {
            "customer_id": f"CUST{i:06d}",
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "signup_date": fake.date_between(start_date="-2y", end_date="-1d"),
        }
        for i in range(CUSTOMER_POOL_SIZE)
    ])


def build_delivery_partner_pool():
    fake = Faker()
    Faker.seed(13)
    return pd.DataFrame([
        {
            "delivery_partner_id": f"PARTNER{i:04d}",
            "delivery_partner_name": fake.name(),
            "delivery_partner_rating": round(random.Random(i).uniform(3.5, 5.0), 1),
        }
        for i in range(DELIVERY_PARTNER_POOL_SIZE)
    ])


def generate_orders(order_date, num_orders, restaurants, customers, rng):
    restaurant_ids = restaurants["restaurant_id"].tolist()
    weights = restaurants["weight"].tolist()
    cost_by_restaurant = restaurants.set_index("restaurant_id")["cost_parsed"]

    orders = []
    for _ in range(num_orders):
        restaurant_id = rng.choices(restaurant_ids, weights=weights, k=1)[0]
        party_size = rng.randint(1, 4)
        order_total = round(cost_by_restaurant[restaurant_id] / 2 * party_size * rng.uniform(0.8, 1.2), 2)
        order_status = rng.choices(["Delivered", "Cancelled"], weights=[95, 5], k=1)[0]
        orders.append({
            "order_id": str(uuid.uuid4()),
            "customer_id": rng.choice(customers["customer_id"].tolist()),
            "restaurant_id": restaurant_id,
            "order_date": order_date.isoformat(),
            "order_time": f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}",
            "party_size": party_size,
            "order_total": order_total,
            "order_status": order_status,
        })
    return pd.DataFrame(orders)


def generate_order_items(orders, rng):
    items = []
    for _, order in orders.iterrows():
        num_items = rng.randint(1, 4)
        remaining = order["order_total"]
        for i in range(num_items):
            price = round(remaining / (num_items - i) * rng.uniform(0.85, 1.15), 2) if i < num_items - 1 else round(remaining, 2)
            remaining -= price
            items.append({
                "order_item_id": str(uuid.uuid4()),
                "order_id": order["order_id"],
                "item_name": rng.choice(MENU_ITEMS),
                "item_price": price,
            })
    return pd.DataFrame(items)


def generate_payments(orders, rng):
    payments = []
    for _, order in orders.iterrows():
        status = rng.choices(["Success", "Failed", "Refunded"], weights=[93, 3, 4], k=1)[0]
        payments.append({
            "payment_id": str(uuid.uuid4()),
            "order_id": order["order_id"],
            "payment_method": rng.choices(PAYMENT_METHODS, weights=[45, 30, 15, 10], k=1)[0],
            "amount": order["order_total"],
            "payment_status": status,
        })
    return pd.DataFrame(payments)


def generate_deliveries(orders, delivery_partners, rng):
    deliveries = []
    partner_records = delivery_partners.to_dict("records")
    for _, order in orders.iterrows():
        if order["order_status"] == "Cancelled":
            continue
        partner = rng.choice(partner_records)
        delivery_time = max(10, round(rng.gauss(31, 7)))
        deliveries.append({
            "delivery_id": str(uuid.uuid4()),
            "order_id": order["order_id"],
            "delivery_partner_id": partner["delivery_partner_id"],
            "delivery_partner_name": partner["delivery_partner_name"],
            "delivery_time_minutes": delivery_time,
            "delivery_status": rng.choices(["Delivered", "Delayed"], weights=[88, 12], k=1)[0],
        })
    return pd.DataFrame(deliveries)


def append_csv(df, path):
    df.to_csv(path, mode="a", header=not path.exists(), index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--num-orders", type=int, default=500)
    args = parser.parse_args()
    order_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    restaurants = load_restaurants()
    customers = build_customer_pool()
    delivery_partners = build_delivery_partner_pool()
    customers.to_csv(DATA_DIR / "raw_customers.csv", index=False)

    rng = random.Random(order_date.toordinal())
    orders = generate_orders(order_date, args.num_orders, restaurants, customers, rng)
    order_items = generate_order_items(orders, rng)
    payments = generate_payments(orders, rng)
    deliveries = generate_deliveries(orders, delivery_partners, rng)

    append_csv(orders, DATA_DIR / "raw_orders.csv")
    append_csv(order_items, DATA_DIR / "raw_order_items.csv")
    append_csv(payments, DATA_DIR / "raw_payments.csv")
    append_csv(deliveries, DATA_DIR / "raw_deliveries.csv")

    print(f"Generated {len(orders)} orders for {order_date} "
          f"({len(order_items)} items, {len(payments)} payments, {len(deliveries)} deliveries)")


if __name__ == "__main__":
    main()
