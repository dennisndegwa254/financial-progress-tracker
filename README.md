# financial-progress-tracker
# Personal Financial Tracking Dashboard (Python)

A Python/Streamlit implementation of the Personal Financial Tracking
Dashboard PRD: savings, expenses, and investment tracking with Day / Week /
Year / Lifetime views, plus dedicated portfolio tracking for shares/stocks
and physical/digital assets.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. On first run it creates a local
SQLite database (`finance_dashboard.db`) and seeds it with sample data.

## Project structure

```
finance_dashboard_python/
├── app.py            # Streamlit UI: pages, charts, forms
├── database.py        # SQLite schema + connection helpers
├── seed_data.py        # Sample data generator (first run only)
├── finance_logic.py    # Net worth, trends, timeframe/category calculations
├── requirements.txt
└── README.md
```

## Notes on moving to production (PostgreSQL)

The schema in `database.py` mirrors the PostgreSQL schema from the project's
Technical Brief. To move from the local SQLite file to Postgres:

1. Swap `sqlite3.connect(...)` for `psycopg2.connect(...)` (or use
   SQLAlchemy for a database-agnostic layer).
2. Change `TEXT` primary keys to `UUID DEFAULT gen_random_uuid()`.
3. Change `REAL` monetary columns to `NUMERIC(19,4)` and use `decimal.Decimal`
   in Python instead of native floats to avoid floating-point rounding
   errors in financial calculations.
4. Replace the manual "current_price" field on holdings with a scheduled
   job (e.g. APScheduler or a cron-triggered script) that pulls live prices
   from a market data API (Alpha Vantage, CoinGecko, etc.) as described in
   the Technical Brief.
