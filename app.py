"""
app.py
Personal Financial Tracking Dashboard -- Streamlit application.

Implements the four required views from the Product Requirement Document:
  1. Core tracking:  savings, expenses, investments
  2. Timeframes:      Day / Week / Year / Lifetime
  3. Portfolios:      shares & stocks, plus physical/digital assets

Run with:
    pip install -r requirements.txt
    streamlit run app.py
"""

import uuid
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import init_db, get_cursor
from seed_data import ensure_seeded
from finance_logic import (
    get_transactions_df,
    get_holdings_df,
    get_trend,
    get_period_totals,
    get_category_breakdown,
    get_net_worth,
    timeframe_start,
)

# ---------------------------------------------------------------- Setup ----
st.set_page_config(page_title="Ledger | Financial Dashboard", layout="wide", page_icon="\U0001F4BC")

ACCENT = "#C7A24C"
POSITIVE = "#5FAE7A"
NEGATIVE = "#C1614A"
BG = "#0E1216"
SURFACE = "#161B21"
BORDER = "#2A323C"
TEXT_MUTED = "#8A93A0"

st.markdown(
    f"""
    <style>
        .stApp {{ background-color: {BG}; }}
        section[data-testid="stSidebar"] {{ background-color: {SURFACE}; }}
        div[data-testid="stMetric"] {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 14px 16px;
        }}
        div[data-testid="stMetricLabel"] {{ color: {TEXT_MUTED}; }}
        h1, h2, h3 {{ font-family: Georgia, serif; }}
        hr {{ border-color: {BORDER}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

conn = init_db()
ensure_seeded(conn)


# ---------------------------------------------------------------- Helpers --
def fmt_money(n: float) -> str:
    sign = "-" if n < 0 else ""
    return f"{sign}${abs(n):,.2f}"


def fmt_compact(n: float) -> str:
    sign = "-" if n < 0 else ""
    a = abs(n)
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:.2f}M"
    if a >= 1_000:
        return f"{sign}${a / 1_000:.1f}K"
    return fmt_money(n)


def uid() -> str:
    return str(uuid.uuid4())


def timeframe_selector(key: str) -> str:
    label = st.radio(
        "Timeframe", ["Day", "Week", "Year", "Lifetime"],
        index=2, horizontal=True, key=key, label_visibility="collapsed",
    )
    return label.lower()


def styled_chart_layout(fig, height=260):
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=TEXT_MUTED),
        legend=dict(font=dict(color=TEXT_MUTED)),
    )
    return fig


# ---------------------------------------------------------------- Sidebar --
st.sidebar.markdown("## \U0001F4BC LEDGER")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Transactions", "Portfolios", "Assets", "Goals"],
    label_visibility="collapsed",
)

net_worth = get_net_worth(conn)
st.sidebar.markdown("---")
st.sidebar.caption("NET WORTH")
st.sidebar.markdown(f"### {fmt_compact(net_worth['net_worth'])}")


# ============================================================== OVERVIEW ==
def render_overview():
    st.caption("OVERVIEW")
    st.title("Net Worth")
    tf = timeframe_selector("tf_overview")

    totals = get_period_totals(conn, tf)
    trend = get_trend(conn, tf)

    st.metric(
        "Total Net Worth",
        fmt_money(net_worth["net_worth"]),
        delta=f"{fmt_money(totals['net'])} net this period",
    )

    if not trend.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=trend["date"], y=trend["balance"], mode="lines", fill="tozeroy",
                line=dict(color=ACCENT, width=2), fillcolor="rgba(199,162,76,0.15)",
                name="Balance",
            )
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor=BORDER)
        st.plotly_chart(styled_chart_layout(fig, 280), use_container_width=True)
    else:
        st.info("No transaction history yet.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Income", fmt_money(totals["income"]))
    c2.metric("Expenses", fmt_money(totals["expense"]))
    c3.metric(
        "Portfolio Value",
        fmt_money(net_worth["portfolio_value"]),
        delta=fmt_money(net_worth["portfolio_value"] - net_worth["portfolio_cost"]),
    )

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Spending by Category")
        cat = get_category_breakdown(conn, tf)
        if cat.empty:
            st.caption("No expenses recorded in this period.")
        else:
            fig = px.bar(
                cat, x="amount", y="category_name", orientation="h",
                color_discrete_sequence=[ACCENT],
            )
            fig.update_layout(yaxis_title="", xaxis_title="")
            st.plotly_chart(styled_chart_layout(fig), use_container_width=True)

    with right:
        st.subheader("Portfolio Mix")
        holdings = get_holdings_df(conn)
        if holdings.empty:
            st.caption("No holdings yet.")
        else:
            fig = px.pie(
                holdings, values="market_value", names="symbol", hole=0.5,
                color_discrete_sequence=px.colors.sequential.Sunset,
            )
            st.plotly_chart(styled_chart_layout(fig), use_container_width=True)


# =========================================================== TRANSACTIONS ==
def render_transactions():
    st.caption("LEDGER")
    st.title("Transactions")
    tf = timeframe_selector("tf_transactions")

    with st.expander("\u2795 Add transaction"):
        with st.form("add_tx", clear_on_submit=True):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Description")
            amount = c2.number_input("Amount ($)", min_value=0.0, step=1.0, format="%.2f")

            c3, c4 = st.columns(2)
            kind = c3.selectbox("Type", ["Expense", "Income"])
            tx_date = c4.date_input("Date", value=date.today())

            accounts = pd.read_sql_query("SELECT id, name FROM accounts", conn)
            categories = pd.read_sql_query("SELECT id, name FROM categories", conn)
            c5, c6 = st.columns(2)
            account_id = c5.selectbox(
                "Account", accounts["id"],
                format_func=lambda i: accounts.set_index("id").loc[i, "name"],
            )
            category_id = c6.selectbox(
                "Category", categories["id"],
                format_func=lambda i: categories.set_index("id").loc[i, "name"],
            )

            submitted = st.form_submit_button("Save transaction")
            if submitted and desc and amount:
                signed = -amount if kind == "Expense" else amount
                with get_cursor(conn) as cur:
                    cur.execute(
                        "INSERT INTO transactions "
                        "(id, account_id, category_id, amount, description, transaction_date, source) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (uid(), account_id, category_id, signed, desc, tx_date.isoformat(), "manual"),
                    )
                st.rerun()

    df = get_transactions_df(conn)
    if df.empty:
        st.caption("No transactions yet.")
        return

    start = timeframe_start(tf)
    windowed = df[df["date"] >= start].sort_values("date", ascending=False)

    if windowed.empty:
        st.caption("No transactions in this timeframe.")
        return

    header = st.columns([1.2, 3, 1.6, 1.6, 1.4, 0.6])
    for col, label in zip(header, ["Date", "Description", "Category", "Account", "Amount", ""]):
        col.caption(label.upper())

    for _, row in windowed.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1.2, 3, 1.6, 1.6, 1.4, 0.6])
        c1.caption(row["date"].strftime("%b %d"))
        c2.write(row["description"])
        c3.caption(row["category_name"] or "\u2014")
        c4.caption(row["account_name"] or "\u2014")
        color = POSITIVE if row["amount"] >= 0 else NEGATIVE
        sign = "+" if row["amount"] >= 0 else ""
        c5.markdown(f"<span style='color:{color}'>{sign}{fmt_money(row['amount'])}</span>", unsafe_allow_html=True)
        if c6.button("\U0001F5D1", key=f"del_tx_{row['id']}"):
            with get_cursor(conn) as cur:
                cur.execute("DELETE FROM transactions WHERE id = ?", (row["id"],))
            st.rerun()


# ============================================================= PORTFOLIOS ==
def render_portfolios():
    st.caption("INVESTMENTS")
    st.title("Shares & Stocks Portfolio")

    with st.expander("\u2795 Add holding"):
        with st.form("add_holding", clear_on_submit=True):
            c1, c2 = st.columns(2)
            symbol = c1.text_input("Symbol").upper()
            asset_class = c2.selectbox("Asset Class", ["equity", "etf", "crypto", "bond"])
            name = st.text_input("Name")
            c3, c4, c5 = st.columns(3)
            qty = c3.number_input("Quantity", min_value=0.0, step=1.0)
            avg_cost = c4.number_input("Avg Cost", min_value=0.0, step=1.0)
            price = c5.number_input("Current Price", min_value=0.0, step=1.0)

            submitted = st.form_submit_button("Save holding")
            if submitted and name and qty and avg_cost:
                asset_id = uid()
                with get_cursor(conn) as cur:
                    cur.execute(
                        "INSERT INTO assets (id, symbol, name, asset_class) VALUES (?,?,?,?)",
                        (asset_id, symbol or None, name, asset_class),
                    )
                    cur.execute(
                        "INSERT INTO holdings "
                        "(id, portfolio_id, asset_id, quantity, avg_cost, current_price) "
                        "VALUES (?,?,?,?,?,?)",
                        (uid(), "pf_brokerage", asset_id, qty, avg_cost, price or avg_cost),
                    )
                st.rerun()

    holdings = get_holdings_df(conn)
    tradeable = holdings[holdings["portfolio_type"] == "brokerage"] if not holdings.empty else holdings

    if tradeable.empty:
        st.caption("No brokerage holdings yet.")
        return

    total_value = tradeable["market_value"].sum()
    total_cost = tradeable["cost_basis"].sum()
    gain = total_value - total_cost

    c1, c2, c3 = st.columns(3)
    c1.metric("Portfolio Value", fmt_money(total_value))
    c2.metric("Cost Basis", fmt_money(total_cost))
    c3.metric("Unrealized Gain", fmt_money(gain), delta=f"{(gain / total_cost * 100 if total_cost else 0):.1f}%")

    header = st.columns([1, 2, 1, 1, 1, 1.3, 1.3, 0.6])
    for col, label in zip(header, ["Symbol", "Name", "Qty", "Avg Cost", "Price", "Value", "Gain/Loss", ""]):
        col.caption(label.upper())

    for _, row in tradeable.iterrows():
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1, 2, 1, 1, 1, 1.3, 1.3, 0.6])
        c1.markdown(f"**{row['symbol'] or '\u2014'}**")
        c2.write(row["asset_name"])
        c3.caption(f"{row['quantity']:g}")
        c4.caption(fmt_money(row["avg_cost"]))

        new_price = c5.number_input(
            "price", value=float(row["current_price"]), key=f"price_{row['id']}",
            label_visibility="collapsed", step=1.0,
        )
        if new_price != row["current_price"]:
            with get_cursor(conn) as cur:
                cur.execute("UPDATE holdings SET current_price = ? WHERE id = ?", (new_price, row["id"]))
            st.rerun()

        c6.write(fmt_money(row["market_value"]))
        color = POSITIVE if row["gain_loss"] >= 0 else NEGATIVE
        sign = "+" if row["gain_loss"] >= 0 else ""
        c7.markdown(f"<span style='color:{color}'>{sign}{fmt_money(row['gain_loss'])}</span>", unsafe_allow_html=True)

        if c8.button("\U0001F5D1", key=f"del_hold_{row['id']}"):
            with get_cursor(conn) as cur:
                cur.execute("DELETE FROM holdings WHERE id = ?", (row["id"],))
            st.rerun()


# ================================================================= ASSETS ==
def render_assets():
    st.caption("TANGIBLE & DIGITAL")
    st.title("Physical & Digital Assets")

    with st.expander("\u2795 Add asset"):
        with st.form("add_asset", clear_on_submit=True):
            name = st.text_input("Name")
            asset_class = st.selectbox(
                "Asset Class", ["real_estate", "collectible", "vehicle", "commodity", "other_physical"]
            )
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
            purchase_price = c2.number_input("Purchase Price", min_value=0.0, step=1.0)
            current_value = c3.number_input("Current Value", min_value=0.0, step=1.0)

            submitted = st.form_submit_button("Save asset")
            if submitted and name and current_value:
                asset_id = uid()
                with get_cursor(conn) as cur:
                    cur.execute(
                        "INSERT INTO assets (id, symbol, name, asset_class) VALUES (?,?,?,?)",
                        (asset_id, None, name, asset_class),
                    )
                    cur.execute(
                        "INSERT INTO holdings "
                        "(id, portfolio_id, asset_id, quantity, avg_cost, current_price) "
                        "VALUES (?,?,?,?,?,?)",
                        (uid(), "pf_physical", asset_id, qty, purchase_price or current_value, current_value),
                    )
                st.rerun()

    holdings = get_holdings_df(conn)
    physical = holdings[holdings["portfolio_type"] == "physical_asset"] if not holdings.empty else holdings

    if physical.empty:
        st.caption("No physical or digital assets yet.")
        return

    cols = st.columns(3)
    for i, (_, row) in enumerate(physical.iterrows()):
        with cols[i % 3]:
            st.markdown(f"**{row['asset_name']}**")
            st.caption(f"{row['asset_class'].replace('_', ' ').title()} \u00b7 Qty {row['quantity']:g}")
            st.write(fmt_money(row["market_value"]))
            color = POSITIVE if row["gain_loss"] >= 0 else NEGATIVE
            sign = "+" if row["gain_loss"] >= 0 else ""
            st.markdown(f"<span style='color:{color}'>{sign}{fmt_money(row['gain_loss'])}</span>", unsafe_allow_html=True)
            if st.button("Remove", key=f"del_asset_{row['id']}"):
                with get_cursor(conn) as cur:
                    cur.execute("DELETE FROM holdings WHERE id = ?", (row["id"],))
                st.rerun()
            st.markdown("---")


# ================================================================= GOALS ===
def render_goals():
    st.caption("PLANNING")
    st.title("Savings Goals")

    with st.expander("\u2795 Add goal"):
        with st.form("add_goal", clear_on_submit=True):
            name = st.text_input("Goal Name")
            c1, c2 = st.columns(2)
            target = c1.number_input("Target Amount", min_value=0.0, step=100.0)
            current = c2.number_input("Current Amount", min_value=0.0, step=100.0)
            target_date = st.date_input("Target Date")

            submitted = st.form_submit_button("Save goal")
            if submitted and name and target:
                with get_cursor(conn) as cur:
                    cur.execute(
                        "INSERT INTO savings_goals "
                        "(id, name, target_amount, current_amount, target_date) VALUES (?,?,?,?,?)",
                        (uid(), name, target, current, target_date.isoformat()),
                    )
                st.rerun()

    goals = pd.read_sql_query("SELECT * FROM savings_goals", conn)
    if goals.empty:
        st.caption("No goals yet.")
        return

    cols = st.columns(2)
    for i, (_, g) in enumerate(goals.iterrows()):
        with cols[i % 2]:
            pct = min(100, (g["current_amount"] / g["target_amount"]) * 100) if g["target_amount"] else 0
            days_left = None
            if g["target_date"]:
                days_left = max(0, (pd.to_datetime(g["target_date"]) - pd.Timestamp(date.today())).days)

            st.markdown(f"**\U0001F416 {g['name']}**")
            st.caption(f"{fmt_money(g['current_amount'])} of {fmt_money(g['target_amount'])}")
            st.progress(pct / 100)

            note = f"{pct:.0f}% funded"
            if days_left is not None:
                note += f" \u00b7 {days_left}d left"
            st.caption(note)

            if st.button("Remove", key=f"del_goal_{g['id']}"):
                with get_cursor(conn) as cur:
                    cur.execute("DELETE FROM savings_goals WHERE id = ?", (g["id"],))
                st.rerun()
            st.markdown("---")


# ---------------------------------------------------------------- Router ---
PAGES = {
    "Overview": render_overview,
    "Transactions": render_transactions,
    "Portfolios": render_portfolios,
    "Assets": render_assets,
    "Goals": render_goals,
}
PAGES[page]()
