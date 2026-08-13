"""Synthetic data generator — fallback used when the live MySQL DB is unreachable.
Produces the same 6 tables/schema as the real database tables.
"""
import random
import datetime as dt
import polars as pl


def generate_synthetic_data(seed: int = 42):
    """Fallback generator: creates the same 6 tables locally when the DB is unreachable.

    `seed` controls the exact data produced — pass a value derived from the
    current date (e.g. int(datetime.date.today().strftime("%Y%m%d"))) to get
    a dataset that's stable through a given day but changes on the next,
    giving a genuine once-a-day data refresh for the synthetic fallback.
    """
    import random as _random_local
    _random_local.seed(seed)

    from faker import Faker

    fake = Faker("en_IN")
    Faker.seed(seed)

    N_USERS = 800
    N_RESTAURANTS = 120
    N_RIDERS = 60
    N_ORDERS = 4000
    START_DATE = dt.date(2025, 1, 1)
    END_DATE = dt.date(2025, 12, 31)
    DAYS_RANGE = (END_DATE - START_DATE).days

    CITIES = ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Pune", "Chennai"]
    CUISINES = ["North Indian", "South Indian", "Chinese", "Italian", "Fast Food",
                "Desserts", "Biryani", "Healthy", "Beverages", "Bakery"]
    CHANNELS = ["Organic", "Paid Search", "Social Media Ad", "Referral", "Influencer", "Push Notification"]
    DEVICES = ["Android", "iOS"]
    PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Wallet", "Cash on Delivery", "Net Banking"]
    CANCEL_REASONS = ["Restaurant too busy", "Customer changed mind", "Payment failed",
                       "Item unavailable", "Delivery partner unavailable", "Long wait time", None]
    GENDERS = ["Male", "Female", "Other"]
    PROFESSIONS = ["Student", "Salaried Employee", "Self-Employed", "Business Owner", "Homemaker", "Retired"]
    INCOME_BRACKETS = ["Low (<3L)", "Mid (3-8L)", "High (8-15L)", "Premium (15L+)"]

    def pick_profession(age):
        # Loosely age-correlated so the demographic cuts look realistic, not random noise
        if age <= 22:
            return random.choices(PROFESSIONS, weights=[55, 20, 10, 5, 8, 2])[0]
        elif age <= 30:
            return random.choices(PROFESSIONS, weights=[5, 50, 20, 10, 10, 5])[0]
        elif age <= 45:
            return random.choices(PROFESSIONS, weights=[1, 40, 25, 20, 12, 2])[0]
        else:
            return random.choices(PROFESSIONS, weights=[0, 25, 20, 25, 15, 15])[0]

    def pick_income(profession):
        # Loosely profession-correlated income bracket
        weights_by_profession = {
            "Student": [70, 25, 4, 1], "Homemaker": [40, 40, 15, 5], "Retired": [30, 40, 20, 10],
            "Salaried Employee": [10, 45, 35, 10], "Self-Employed": [15, 35, 30, 20],
            "Business Owner": [5, 20, 35, 40],
        }
        return random.choices(INCOME_BRACKETS, weights=weights_by_profession[profession])[0]

    def random_date(start=START_DATE, days_range=DAYS_RANGE):
        return start + dt.timedelta(days=random.randint(0, days_range))

    # ---------------- USERS ----------------
    users = []
    for uid in range(1, N_USERS + 1):
        signup_date = random_date()
        channel = random.choices(CHANNELS, weights=[35, 20, 15, 15, 10, 5])[0]
        city = random.choice(CITIES)
        device = random.choice(DEVICES)
        age = random.randint(18, 55)
        profession = pick_profession(age)
        income_bracket = pick_income(profession)
        gender = random.choices(GENDERS, weights=[48, 48, 4])[0]
        city_dirty = city.upper() if random.random() < 0.1 else (f" {city} " if random.random() < 0.1 else city)
        device_dirty = device if random.random() > 0.05 else None
        gender_dirty = gender.lower() if random.random() < 0.08 else (None if random.random() < 0.02 else gender)
        profession_dirty = profession.lower() if random.random() < 0.08 else (None if random.random() < 0.02 else profession)
        users.append({
            "user_id": f"U{uid:05d}",
            "user_name": fake.name(),
            "signup_date": signup_date.isoformat() if random.random() > 0.03 else signup_date.strftime("%d/%m/%Y"),
            "acquisition_channel": channel,
            "city": city_dirty,
            "device_type": device_dirty,
            "age": age if random.random() > 0.02 else None,
            "gender": gender_dirty,
            "profession": profession_dirty,
            "income_bracket": income_bracket,
            "is_subscriber": random.random() < 0.22,   # membership/subscription feature flag (Feature Adoption)
            "ab_test_group": random.choice(["Control", "Treatment"]),  # Checkout-Redesign A/B test assignment
        })
    users += random.sample(users, 15)  # inject duplicates
    users_df = pl.DataFrame(users)

    # ---------------- RESTAURANTS ----------------
    restaurants = []
    for rid in range(1, N_RESTAURANTS + 1):
        restaurants.append({
            "restaurant_id": f"R{rid:04d}",
            "restaurant_name": fake.company() + " " + random.choice(["Kitchen", "Restaurant", "Cafe", "Eatery", "Diner"]),
            "cuisine_type": random.choice(CUISINES),
            "city": random.choice(CITIES),
            "onboarded_date": random_date(dt.date(2023, 1, 1), 1095).isoformat(),
            "commission_rate": round(random.uniform(0.12, 0.25), 3),
            "base_rating": round(random.uniform(3.2, 4.9), 1),
        })
    restaurants_df = pl.DataFrame(restaurants)

    # ---------------- DELIVERY PARTNERS ----------------
    riders = []
    for did in range(1, N_RIDERS + 1):
        riders.append({
            "delivery_partner_id": f"D{did:04d}",
            "partner_name": fake.name(),
            "city": random.choice(CITIES),
            "joined_date": random_date(dt.date(2023, 1, 1), 1095).isoformat(),
            "vehicle_type": random.choice(["Bike", "Bicycle", "Scooter"]),
        })
    riders_df = pl.DataFrame(riders)

    # ---------------- ORDERS (main fact table) ----------------
    user_ids = users_df["user_id"].to_list()
    user_signup = dict(zip(users_df["user_id"], users_df["signup_date"]))
    user_ab_group = dict(zip(users_df["user_id"], users_df["ab_test_group"]))
    restaurant_ids = restaurants_df["restaurant_id"].to_list()
    restaurant_commission = dict(zip(restaurants_df["restaurant_id"], restaurants_df["commission_rate"]))
    rider_ids = riders_df["delivery_partner_id"].to_list()
    user_weights = [random.paretovariate(1.2) for _ in user_ids]

    orders = []
    order_counter = 1
    user_order_dates = {u: [] for u in user_ids}

    for _ in range(N_ORDERS):
        uid = random.choices(user_ids, weights=user_weights, k=1)[0]
        try:
            su = dt.date.fromisoformat(user_signup[uid])
        except Exception:
            su = START_DATE
        lo = max(su, START_DATE)
        if lo >= END_DATE:
            lo = START_DATE
        order_date = lo + dt.timedelta(days=random.randint(0, max((END_DATE - lo).days, 1)))
        order_time = dt.datetime.combine(order_date, dt.time(
            hour=random.choices(range(24), weights=[1,1,1,1,1,1,2,4,6,5,4,5,7,6,4,4,5,6,8,9,8,6,4,2])[0],
            minute=random.randint(0, 59)))

        rid = random.choice(restaurant_ids)
        partner = random.choice(rider_ids)
        is_treatment = user_ab_group[uid] == "Treatment"   # Checkout-Redesign A/B test: Treatment = new one-click checkout
        items_count = random.randint(1, 8)
        base_item_price = random.uniform(80, 350)
        order_value = round(items_count * base_item_price * random.uniform(0.8, 1.2), 2)
        if is_treatment:
            order_value = round(order_value * 1.06, 2)   # simulated uplift: smoother checkout nudges slightly bigger baskets
        discount_amount = round(order_value * random.choice([0, 0, 0, 0.1, 0.15, 0.2]), 2)
        delivery_fee = round(random.uniform(0, 60), 2)
        commission_rate = restaurant_commission[rid]

        status_weights = [91, 6, 3] if is_treatment else [88, 9, 3]  # Treatment: fewer drop-offs/cancellations
        status = random.choices(["Delivered", "Cancelled", "Failed"], weights=status_weights)[0]
        accepted_delay = random.randint(1, 8)
        prep_time = random.randint(10, 35)
        pickup_delay = random.randint(2, 15)
        distance_km = round(random.uniform(0.8, 12.0), 2)
        travel_time = round(distance_km * random.uniform(3.0, 6.0))

        placed_time = order_time
        accepted_time = placed_time + dt.timedelta(minutes=accepted_delay)
        promised_time = placed_time + dt.timedelta(minutes=random.choice([30, 35, 40, 45]))

        ready_time = accepted_time + dt.timedelta(minutes=prep_time)  # food-ready timestamp (prep complete)

        if status == "Delivered":
            pickup_time = ready_time + dt.timedelta(minutes=pickup_delay)
            delivered_time = pickup_time + dt.timedelta(minutes=travel_time)
            cancel_reason = None
            rating = random.choices([5,4,3,2,1], weights=[45,30,15,7,3])[0]
            refund_amount = 0.0
            complaint_flag = random.random() < 0.06
            if complaint_flag and random.random() < 0.5:
                refund_amount = round(order_value * random.uniform(0.1, 0.5), 2)
            wrong_item_flag = random.random() < 0.035   # Order Accuracy Rate driver
        elif status == "Cancelled":
            pickup_time = None; delivered_time = None; ready_time = None
            cancel_reason = random.choice(CANCEL_REASONS[:-1])
            rating = None
            refund_amount = round(order_value * random.uniform(0.5, 1.0), 2) if random.random() < 0.7 else 0.0
            complaint_flag = random.random() < 0.3
            wrong_item_flag = False
        else:
            pickup_time = None; delivered_time = None; ready_time = None
            cancel_reason = "Payment failed"
            rating = None
            refund_amount = round(order_value, 2)
            complaint_flag = random.random() < 0.2
            wrong_item_flag = False

        payment_method = random.choice(PAYMENT_METHODS)
        payment_status = "Success" if status != "Failed" else "Failed"
        is_promo_used = discount_amount > 0
        is_scheduled_order = random.random() < 0.16      # Feature Adoption: scheduled orders
        payment_gateway_fee = round(order_value * random.uniform(0.015, 0.025), 2)   # ~2% gateway fee
        delivery_cost_to_rider = round(18 + distance_km * random.uniform(6, 10), 2)  # platform's actual payout to rider
        user_order_dates[uid].append(order_date)

        orders.append({
            "order_id": f"O{order_counter:06d}",
            "user_id": uid,
            "restaurant_id": rid,
            "delivery_partner_id": partner if status == "Delivered" else (partner if random.random() < 0.5 else None),
            "order_placed_time": placed_time.isoformat(sep=" "),
            "order_accepted_time": accepted_time.isoformat(sep=" ") if status != "Failed" else None,
            "promised_delivery_time": promised_time.isoformat(sep=" "),
            "ready_time": ready_time.isoformat(sep=" ") if ready_time else None,
            "pickup_time": pickup_time.isoformat(sep=" ") if pickup_time else None,
            "delivered_time": delivered_time.isoformat(sep=" ") if delivered_time else None,
            "order_status": status,
            "cancel_reason": cancel_reason,
            "items_count": items_count,
            "order_value": order_value,
            "discount_amount": discount_amount,
            "delivery_fee": delivery_fee,
            "delivery_cost_to_rider": delivery_cost_to_rider,
            "payment_gateway_fee": payment_gateway_fee,
            "commission_rate": commission_rate,
            "payment_method": payment_method,
            "payment_status": payment_status,
            "distance_km": distance_km,
            "rating": rating,
            "complaint_flag": complaint_flag,
            "wrong_item_flag": wrong_item_flag,
            "refund_amount": refund_amount,
            "is_promo_used": is_promo_used,
            "is_scheduled_order": is_scheduled_order,
            "ab_test_group": user_ab_group[uid],
            "device_type": random.choice(DEVICES),
            "city": random.choice(CITIES),
        })
        order_counter += 1

    orders_df = pl.DataFrame(orders)
    orders_df = orders_df.with_columns(
        pl.col("order_placed_time").str.strptime(pl.Datetime, strict=False).alias("_ts")
    ).sort(["user_id", "_ts"]).with_columns(
        (pl.int_range(0, pl.len()).over("user_id") == 0).alias("is_first_order")
    ).drop("_ts")

    # inject data-quality issues
    orders_issues = orders_df.to_dicts()
    for r in orders_issues:
        if random.random() < 0.01:
            r["delivery_fee"] = -abs(r["delivery_fee"])
        if random.random() < 0.005:
            r["order_value"] = None
        if random.random() < 0.05:
            r["payment_method"] = r["payment_method"].lower() if r["payment_method"] else r["payment_method"]
        if random.random() < 0.003 and r["order_value"]:
            r["order_value"] = round(r["order_value"] * 20, 2)
    orders_df = pl.DataFrame(orders_issues)
    dup_rows = random.sample(orders_issues, 40)
    orders_df = pl.concat([orders_df, pl.DataFrame(dup_rows)], how="vertical")

    # ---------------- APP EVENTS (funnel: app_open -> menu_view -> add_to_cart -> checkout -> payment) ----------------
    FUNNEL_STAGES = ["app_open", "menu_view", "add_to_cart", "checkout_started", "payment_completed"]
    events = []
    eid = 1
    N_SESSIONS = 2500
    for s in range(N_SESSIONS):
        uid = random.choices(user_ids, weights=user_weights, k=1)[0]
        session_date = random_date()
        t = dt.datetime.combine(session_date, dt.time(random.randint(7,23), random.randint(0,59)))
        drop_probs = [0.0, 0.15, 0.25, 0.20, 0.10]
        reached = True
        for i, stage in enumerate(FUNNEL_STAGES):
            if i > 0 and random.random() < drop_probs[i]:
                reached = False
            if not reached:
                break
            # each stage takes some active browsing time -> lets us derive avg session duration
            t = t + dt.timedelta(seconds=random.randint(20, 240))
            events.append({
                "event_id": f"E{eid:06d}", "session_id": f"S{s:06d}", "user_id": uid,
                "event_name": stage, "event_time": t.isoformat(sep=" "),
                "device_type": random.choice(DEVICES),
            })
            eid += 1
    events_df = pl.DataFrame(events)

    # ---------------- NPS SURVEY RESPONSES ----------------
    # Sent post-delivery to a sample of users; score 0-10 (Promoters 9-10, Passives 7-8, Detractors 0-6)
    nps_rows = []
    nid = 1
    surveyed_users = random.sample(user_ids, k=min(450, len(user_ids)))
    for uid in surveyed_users:
        resp_date = random_date()
        # bias score loosely using user_weights (heavier/loyal users skew slightly more positive)
        w = user_weights[user_ids.index(uid)] if False else None  # (kept simple/independent below)
        score = random.choices(range(0, 11),
                                weights=[2,1,1,2,3,4,6,10,14,20,17])[0]
        nps_rows.append({
            "response_id": f"N{nid:05d}",
            "user_id": uid,
            "response_date": resp_date.isoformat(),
            "nps_score": score,
        })
        nid += 1
    nps_df = pl.DataFrame(nps_rows)

    return users_df, restaurants_df, riders_df, orders_df, events_df, nps_df
