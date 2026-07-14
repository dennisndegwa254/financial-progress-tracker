"""
finance_logic.py
Derived financial calculations: net worth, timeframe trends, category
breakdowns. Balances are always derived from the transaction ledger and
current holding prices, never stored directly -- the same principle laid
out in the project's Technical Brief.
"""

import pandas as pd
from datetime import date


def get_initial_balance(conn) -> float:
    row = conn.execute("SELECT value FROM settings WHERE key = 'initial_balance'").fetchone()
    return float(row["value"]) if row else 0.0


def get_transactions_df(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT t.id, t.account_id, t.category_id, t.amount, t.description,
               t.transaction_date AS date, t.source,
               a.name AS account_name, c.name AS category_name, c.category_type
        FROM transactions t
        LEFT JOIN accounts a ON a.id = t.account_id
        LEFT JOIN categories c ON c.id = t.category_id
        ORDER BY t.transaction_date ASC
        """,
        conn,
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_holdings_df(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT h.id, h.portfolio_id, h.asset_id, h.quantity, h.avg_cost, h.current_price,
               p.name AS portfolio_name, p.portfolio_type,
               a.symbol, a.name AS asset_name, a.asset_class
        FROM holdings h
        JOIN portfolios p ON p.id = h.portfolio_id
        JOIN assets a ON a.id = h.asset_id
        """,
        conn,
    )
    if not df.empty:
        df["market_value"] = df["quantity"] * df["current_price"]
        df["cost_basis"] = df["quantity"] * df["avg_cost"]
        df["gain_loss"] = df["market_value"] - df["cost_basis"]
    return df


def get_cash_series(conn) -> pd.DataFrame:
    """Running cash balance across the full transaction history."""
    df = get_transactions_df(conn)
    initial = get_initial_balance(conn)
    if df.empty:
        return pd.DataFrame(columns=["date", "balance"])
    df = df.sort_values("date").copy()
    df["balance"] = initial + df["amount"].cumsum()
    return df[["date", "balance"]]


def timeframe_start(timeframe: str) -> pd.Timestamp:
    today = pd.Timestamp(date.today())
    return {
        "day": today - pd.Timedelta(days=1),
        "week": today - pd.Timedelta(days=7),
        "year": today - pd.DateOffset(years=1),
        "lifetime": pd.Timestamp("2000-01-01"),
    }[timeframe]


def get_trend(conn, timeframe: str) -> pd.DataFrame:
    """Resampled balance series for charting: daily points for day/week,
    monthly points for year/lifetime -- mirroring the daily-snapshot +
    resample pattern from the Technical Brief."""
    series = get_cash_series(conn)
    if series.empty:
        return series
    start = timeframe_start(timeframe)
    windowed = series[series["date"] >= start]
    if windowed.empty:
        windowed = series.tail(1)

    indexed = windowed.set_index("date")["balance"]
    if timeframe in ("day", "week"):
        resampled = indexed.resample("D").last().dropna()
    else:
        resampled = indexed.resample("ME").last().dropna()
    return resampled.reset_index()


def get_period_totals(conn, timeframe: str) -> dict:
    df = get_transactions_df(conn)
    if df.empty:
        return {"income": 0.0, "expense": 0.0, "net": 0.0, "count": 0}
    start = timeframe_start(timeframe)
    windowed = df[df["date"] >= start]
    income = windowed.loc[windowed["amount"] > 0, "amount"].sum()
    expense = -windowed.loc[windowed["amount"] < 0, "amount"].sum()
    return {"income": income, "expense": expense, "net": income - expense, "count": len(windowed)}


def get_category_breakdown(conn, timeframe: str) -> pd.DataFrame:
    df = get_transactions_df(conn)
    if df.empty:
        return pd.DataFrame(columns=["category_name", "amount"])
    start = timeframe_start(timeframe)
    windowed = df[(df["date"] >= start) & (df["amount"] < 0)]
    if windowed.empty:
        return pd.DataFrame(columns=["category_name", "amount"])
    grouped = windowed.groupby("category_name")["amount"].sum().abs().sort_values(ascending=False)
    return grouped.reset_index()


def get_net_worth(conn) -> dict:
    cash_series = get_cash_series(conn)
    current_cash = cash_series["balance"].iloc[-1] if not cash_series.empty else get_initial_balance(conn)
    holdings = get_holdings_df(conn)
    portfolio_value = holdings["market_value"].sum() if not holdings.empty else 0.0
    portfolio_cost = holdings["cost_basis"].sum() if not holdings.empty else 0.0
    return {
        "cash": current_cash,
        "portfolio_value": portfolio_value,
        "portfolio_cost": portfolio_cost,
        "net_worth": current_cash + portfolio_value,
    }
