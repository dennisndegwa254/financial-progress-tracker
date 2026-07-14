"""
seed_data.py
Populates the database with realistic sample data on first run, generated
relative to today's date so the Day/Week/Year/Lifetime views are always
populated with something meaningful.
"""

import random
import uuid
from datetime import date, timedelta

from database import get_cursor, is_empty


def uid() -> str:
    return str(uuid.uuid4())


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


CATEGORIES = [
    ("cat_salary", "Salary", "income"),
    ("cat_freelance", "Freelance", "income"),
    ("cat_groceries", "Groceries", "expense"),
    ("cat_rent", "Rent", "expense"),
    ("cat_dining", "Dining Out", "expense"),
    ("cat_transport", "Transport", "expense"),
    ("cat_utilities", "Utilities", "expense"),
    ("cat_entertainment", "Entertainment", "expense"),
    ("cat_health", "Health", "expense"),
]

ACCOUNTS = [
    ("acc_checking", "Everyday Checking", "checking", "Chase"),
    ("acc_savings", "High-Yield Savings", "savings", "Ally"),
]

# (amount, description, category_id, account_id)
TX_TEMPLATE = [
    (175, "Salary", "cat_salary", "acc_checking"),
    (420, "Freelance project", "cat_freelance", "acc_checking"),
    (-1450, "Monthly rent", "cat_rent", "acc_checking"),
    (-86.40, "Whole Foods", "cat_groceries", "acc_checking"),
    (-52.10, "Trader Joe's", "cat_groceries", "acc_checking"),
    (-38.75, "Ramen night", "cat_dining", "acc_checking"),
    (-64.20, "Sushi dinner", "cat_dining", "acc_checking"),
    (-45.00, "Gas station", "cat_transport", "acc_checking"),
    (-120.00, "Electric + water", "cat_utilities", "acc_checking"),
    (-18.99, "Streaming bundle", "cat_entertainment", "acc_checking"),
    (-72.50, "Pharmacy", "cat_health", "acc_checking"),
    (-29.40, "Uber rides", "cat_transport", "acc_checking"),
    (500, "Savings transfer", "cat_salary", "acc_savings"),
    (-95.30, "Costco run", "cat_groceries", "acc_checking"),
    (-22.00, "Movie night", "cat_entertainment", "acc_checking"),
]

DAY_OFFSETS = [1, 2, 4, 6, 8, 9, 11, 13, 15, 17, 19, 21, 23, 26, 29,
               33, 36, 40, 45, 50, 55, 60, 65, 70, 78, 85]

PORTFOLIOS = [
    ("pf_brokerage", "Brokerage", "brokerage"),
    ("pf_physical", "Physical & Digital Assets", "physical_asset"),
]

# (id, symbol, name, asset_class)
ASSETS = [
    ("as_aapl", "AAPL", "Apple Inc.", "equity"),
    ("as_vti", "VTI", "Vanguard Total Stock Mkt ETF", "etf"),
    ("as_btc", "BTC", "Bitcoin", "crypto"),
    ("as_gold", None, "1oz Gold Bar", "commodity"),
    ("as_car", None, "2019 Toyota Camry", "vehicle"),
]

# (id, portfolio_id, asset_id, quantity, avg_cost, current_price)
HOLDINGS = [
    ("hl_aapl", "pf_brokerage", "as_aapl", 22, 148.30, 211.40),
    ("hl_vti", "pf_brokerage", "as_vti", 15, 224.10, 291.70),
    ("hl_btc", "pf_brokerage", "as_btc", 0.18, 41200, 96500),
    ("hl_gold", "pf_physical", "as_gold", 2, 1890, 2385),
    ("hl_car", "pf_physical", "as_car", 1, 24500, 17800),
]

INITIAL_BALANCE = 4200.0


def _goals():
    return [
        ("g_emergency", "Emergency Fund", 15000, 9200, days_ago(-180)),
        ("g_downpayment", "House Down Payment", 60000, 21000, days_ago(-540)),
    ]


def seed(conn):
    with get_cursor(conn) as cur:
        cur.executemany(
            "INSERT INTO accounts (id, name, account_type, institution) VALUES (?,?,?,?)",
            ACCOUNTS,
        )
        cur.executemany(
            "INSERT INTO categories (id, name, category_type) VALUES (?,?,?)",
            CATEGORIES,
        )
        cur.executemany(
            "INSERT INTO portfolios (id, name, portfolio_type) VALUES (?,?,?)",
            PORTFOLIOS,
        )
        cur.executemany(
            "INSERT INTO assets (id, symbol, name, asset_class) VALUES (?,?,?,?)",
            ASSETS,
        )
        cur.executemany(
            "INSERT INTO holdings (id, portfolio_id, asset_id, quantity, avg_cost, current_price) "
            "VALUES (?,?,?,?,?,?)",
            HOLDINGS,
        )
        cur.executemany(
            "INSERT INTO savings_goals (id, name, target_amount, current_amount, target_date) "
            "VALUES (?,?,?,?,?)",
            _goals(),
        )
        cur.execute(
            "INSERT INTO settings (key, value) VALUES ('initial_balance', ?)",
            (str(INITIAL_BALANCE),),
        )

        transactions = []
        for i, off in enumerate(DAY_OFFSETS):
            amount, desc, cat_id, acc_id = TX_TEMPLATE[i % len(TX_TEMPLATE)]
            jitter = amount * (0.85 + random.random() * 0.3) if amount < 0 else amount
            transactions.append(
                (uid(), acc_id, cat_id, round(jitter, 2), desc, days_ago(off), "manual")
            )

        # biweekly salary across the last ~90 days
        off = 3
        while off < 90:
            transactions.append(
                (uid(), "acc_checking", "cat_salary", 3400.0, "Biweekly salary", days_ago(off), "manual")
            )
            off += 14

        # monthly rent across the last ~90 days
        off = 5
        while off < 90:
            transactions.append(
                (uid(), "acc_checking", "cat_rent", -1450.0, "Monthly rent", days_ago(off), "manual")
            )
            off += 30

        # a transaction dated today so the "Day" view is never empty
        transactions.append(
            (uid(), "acc_checking", "cat_dining", -14.50, "Coffee + bagel", days_ago(0), "manual")
        )

        cur.executemany(
            "INSERT INTO transactions "
            "(id, account_id, category_id, amount, description, transaction_date, source) "
            "VALUES (?,?,?,?,?,?,?)",
            transactions,
        )


def ensure_seeded(conn):
    if is_empty(conn):
        seed(conn)
