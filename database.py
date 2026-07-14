"""
database.py
SQLite persistence layer for the Personal Financial Tracking Dashboard.

This mirrors the PostgreSQL schema defined in the project's Technical Brief.
SQLite is used here for a zero-config, single-file local database. The same
table structure maps directly onto PostgreSQL for production deployment:
  - TEXT ids            -> UUID (gen_random_uuid())
  - REAL amounts         -> NUMERIC(19,4)
  - TEXT dates            -> DATE / TIMESTAMPTZ
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "finance_dashboard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    account_type    TEXT NOT NULL CHECK (account_type IN
                        ('checking','savings','credit_card','brokerage',
                         'retirement','crypto_wallet','loan','other')),
    institution     TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category_type   TEXT NOT NULL CHECK (category_type IN ('income','expense'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id                  TEXT PRIMARY KEY,
    account_id          TEXT NOT NULL REFERENCES accounts(id),
    category_id         TEXT REFERENCES categories(id),
    amount              REAL NOT NULL,      -- positive = income, negative = expense
    description         TEXT,
    transaction_date    TEXT NOT NULL,      -- ISO date string YYYY-MM-DD
    source              TEXT NOT NULL DEFAULT 'manual'
);

CREATE TABLE IF NOT EXISTS portfolios (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    portfolio_type  TEXT NOT NULL CHECK (portfolio_type IN
                        ('brokerage','retirement','crypto','physical_asset'))
);

CREATE TABLE IF NOT EXISTS assets (
    id              TEXT PRIMARY KEY,
    symbol          TEXT,
    name            TEXT NOT NULL,
    asset_class     TEXT NOT NULL CHECK (asset_class IN
                        ('equity','etf','crypto','bond','commodity',
                         'real_estate','collectible','vehicle','other_physical'))
);

CREATE TABLE IF NOT EXISTS holdings (
    id              TEXT PRIMARY KEY,
    portfolio_id    TEXT NOT NULL REFERENCES portfolios(id),
    asset_id        TEXT NOT NULL REFERENCES assets(id),
    quantity        REAL NOT NULL,
    avg_cost        REAL NOT NULL,
    current_price   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS savings_goals (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    target_amount   REAL NOT NULL,
    current_amount  REAL NOT NULL DEFAULT 0,
    target_date     TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key             TEXT PRIMARY KEY,
    value           TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> sqlite3.Connection:
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


@contextmanager
def get_cursor(conn: sqlite3.Connection):
    """Context manager that commits on success and always closes the cursor."""
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    finally:
        cur.close()


def is_empty(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()
    return row["n"] == 0
