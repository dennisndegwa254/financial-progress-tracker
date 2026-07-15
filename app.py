import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Apex Wealth Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Dark-Mode-Friendly CSS
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; }
        .stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; }
        div[data-testid="metric-container"] { color: #f8fafc; }
    </style>
""", unsafe_allow_html=True)

# --- 1. INITIALIZE DEFAULT STATE DATA ---
if "expenses" not in st.session_state:
    st.session_state.expenses = [
        {"date": "2026-07-01", "category": "Rent", "amount": 1200.0, "note": "Monthly rent"},
        {"date": "2026-07-03", "category": "Groceries", "amount": 350.0, "note": "Weekly restock"},
        {"date": "2026-07-05", "category": "Utilities", "amount": 150.0, "note": "Electric & Internet"},
        {"date": "2026-07-08", "category": "Dining Out", "amount": 120.0, "note": "Team dinner"},
        {"date": "2026-07-12", "category": "Entertainment", "amount": 80.0, "note": "Movie night"},
    ]

if "savings_balance" not in st.session_state:
    st.session_state.savings_balance = 12500.0

if "savings_ledger" not in st.session_state:
    st.session_state.savings_ledger = [
        {"date": "2026-07-01", "type": "Deposit", "amount": 500.0}
    ]

if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "AAPL": {"shares": 25.0, "avg_cost": 150.0, "current_price": 175.0},
        "MSFT": {"shares": 15.0, "avg_cost": 380.0, "current_price": 420.0},
        "VTI": {"shares": 50.0, "avg_cost": 210.0, "current_price": 230.0}
    }

if "net_worth_history" not in st.session_state:
    st.session_state.net_worth_history = [
        {"date": "2026-03-31", "net_worth": 24000.0},
        {"date": "2026-04-30", "net_worth": 26200.0},
        {"date": "2026-05-31", "net_worth": 27800.0},
        {"date": "2026-06-30", "net_worth": 29400.0},
    ]

# --- Helper logic to compute current math ---
def get_total_portfolio_value():
    return sum(h["shares"] * h["current_price"] for h in st.session_state.holdings.values())

def get_current_net_worth():
    return st.session_state.savings_balance + get_total_portfolio_value()

def get_total_expenses():
    return sum(exp["amount"] for exp in st.session_state.expenses)


# --- 2. SIDEBAR: STATE EXPORT & IMPORT ---
with st.sidebar:
    st.title("🎯 Apex Ledger")
    st.subheader("Data Portability")
    st.caption("Since this app runs in-memory, you can export your data as JSON below to keep a backup.")
    
    # Pack up session state
    export_payload = {
        "expenses": st.session_state.expenses,
        "savings_balance": st.session_state.savings_balance,
        "savings_ledger": st.session_state.savings_ledger,
        "holdings": st.session_state.holdings,
        "net_worth_history": st.session_state.net_worth_history
    }
    json_string = json.dumps(export_payload, indent=2)
    
    st.download_button(
        label="📥 Export Ledger JSON",
        data=json_string,
        file_name="financial_ledger.json",
        mime="application/json",
        use_container_width=True
    )
    
    # Import panel
    uploaded_file = st.file_uploader("Restore Ledger JSON", type=["json"])
    if uploaded_file is not None:
        try:
            imported_data = json.load(uploaded_file)
            st.session_state.expenses = imported_data.get("expenses", st.session_state.expenses)
            st.session_state.savings_balance = imported_data.get("savings_balance", st.session_state.savings_balance)
            st.session_state.savings_ledger = imported_data.get("savings_ledger", st.session_state.savings_ledger)
            st.session_state.holdings = imported_data.get("holdings", st.session_state.holdings)
            st.session_state.net_worth_history = imported_data.get("net_worth_history", st.session_state.net_worth_history)
            st.success("Ledger restored successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error importing file: {e}")

st.sidebar.divider()
st.sidebar.info("💡 **Tip:** Add a manual transaction under the 'Data Entry' tab to watch your dashboard update instantly.")


# --- 3. MAIN NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Overview Dashboard", "📈 Investments", "✍️ Data Entry"])


# ==========================================
# MODULE 1: OVERVIEW DASHBOARD
# ==========================================
with tab1:
    st.title("Financial Overview")
    
    # Math Calculations
    total_exp = get_total_expenses()
    total_sav = st.session_state.savings_balance
    total_inv = get_total_portfolio_value()
    current_nw = get_current_net_worth()
    
    # Let's dynamically add today's snapshot to history to render accurately on the line chart
    today_str = datetime.today().strftime('%Y-%m-%d')
    temp_nw_history = st.session_state.net_worth_history.copy()
    if not any(item['date'] == today_str for item in temp_nw_history):
        temp_nw_history.append({"date": today_str, "net_worth": current_nw})
    
    # Metrics display
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Total MTD Expenses", value=f"${total_exp:,.2f}", delta="-4.8% vs last month", delta_color="inverse")
    col2.metric(label="Total Savings", value=f"${total_sav:,.2f}", delta="+3.1% vs target")
    col3.metric(label="Investment Portfolio", value=f"${total_inv:,.2f}", delta="+7.4% (All-time)")
    col4.metric(label="Total Net Worth", value=f"${current_nw:,.2f}", delta=f"+${(current_nw - temp_nw_history[0]['net_worth']):,.2f} overall")

    st.write("---")
    
    # Charts Row
    chart_col1, chart_col2 = st.columns([3, 2])
    
    with chart_col1:
        st.subheader("Net Worth Trend")
        df_nw = pd.DataFrame(temp_nw_history)
        fig_line = px.line(
            df_nw, x="date", y="net_worth", 
            labels={"net_worth": "Net Worth ($)", "date": "Date"},
            markers=True,
            template="plotly_dark"
        )
        fig_line.update_traces(line_color="#10b981", line_width=3)
        fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_line, use_container_width=True)
        
    with chart_col2:
        st.subheader("Expenses by Category")
        if st.session_state.expenses:
            df_exp = pd.DataFrame(st.session_state.expenses)
            df_grouped_exp = df_exp.groupby("category")["amount"].sum().reset_index()
            fig_pie = px.pie(
                df_grouped_exp, values="amount", names="category", 
                hole=0.4,
                template="plotly_dark",
                color_discrete_sequence=px.colors.sequential.Tealgrn
            )
            fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend_yanchor="bottom")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No expense data recorded yet.")


# ==========================================
# MODULE 2: INVESTMENTS
# ==========================================
with tab2:
    st.title("Portfolio & Holdings")
    
    st.warning("⚠️ **Last Updated Prices:** This module relies on manually entered current prices rather than live stock feeds.", icon="ℹ️")
    
    # Calculations & Formatting Holdings Table
    holdings_list = []
    for ticker, details in st.session_state.holdings.items():
        market_val = details["shares"] * details["current_price"]
        cost_basis = details["shares"] * details["avg_cost"]
        gain_loss_usd = market_val - cost_basis
        gain_loss_pct = (gain_loss_usd / cost_basis * 100) if cost_basis > 0 else 0
        
        holdings_list.append({
            "Ticker": ticker,
            "Shares": details["shares"],
            "Avg Cost": f"${details['avg_cost']:,.2f}",
            "Current Price": f"${details['current_price']:,.2f}",
            "Market Value": market_val,
            "Gain/Loss ($)": gain_loss_usd,
            "Gain/Loss (%)": f"{gain_loss_pct:+.2f}%"
        })
    
    df_holdings = pd.DataFrame(holdings_list)
    
    # Display table with stylings
    if not df_holdings.empty:
        # We format the values for presentation cleanly
        styled_df = df_holdings.copy()
        styled_df["Market Value"] = styled_df["Market Value"].map(lambda x: f"${x:,.2f}")
        styled_df["Gain/Loss ($)"] = styled_df["Gain/Loss ($)"].map(lambda x: f"${x:+,.2f}")
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("No investments entered in your portfolio yet.")
        
    st.divider()
    
    # Bottom Layout: Quick Pricing Updater & Portfolio Allocation Pie Chart
    inv_col1, inv_col2 = st.columns([1, 1])
    
    with inv_col1:
        st.subheader("Update Stock Prices Manually")
        with st.form("price_update_form", clear_on_submit=True):
            ticker_to_update = st.selectbox("Select Asset Ticker", list(st.session_state.holdings.keys()))
            new_px = st.number_input("New Market Price ($)", min_value=0.01, step=1.0, value=float(st.session_state.holdings[ticker_to_update]["current_price"]))
            submitted_px = st.form_submit_button("Apply Market Update")
            if submitted_px:
                st.session_state.holdings[ticker_to_update]["current_price"] = new_px
                st.success(f"Updated {ticker_to_update} market price to ${new_px:,.2f}!")
                st.rerun()
                
    with inv_col2:
        st.subheader("Asset Allocation")
        if holdings_list:
            df_alloc = pd.DataFrame(holdings_list)
            fig_alloc = px.pie(
                df_alloc, values="Market Value", names="Ticker",
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Pastel2
            )
            fig_alloc.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_alloc, use_container_width=True)


# ==========================================
# MODULE 3: MANUAL DATA ENTRY
# ==========================================
with tab3:
    st.title("Manual Ledger Transactions")
    st.write("Submit changes here to instantly calculate and update components on your main dashboard tabs.")
    
    entry_type = st.radio("Choose Transaction Category", ["Expense Tracker", "Savings Vault", "Investment Buy/Sell"], horizontal=True)
    st.divider()
    
    # Entry Choice A: Expenses Form
    if entry_type == "Expense Tracker":
        with st.form("expense_form", clear_on_submit=True):
            st.subheader("Record an Expense")
            exp_date = st.date_input("Transaction Date", value=datetime.today())
            exp_cat = st.selectbox("Category", ["Rent", "Groceries", "Utilities", "Dining Out", "Entertainment", "Travel", "Misc"])
            exp_amount = st.number_input("Amount ($)", min_value=0.01, step=1.0)
            exp_note = st.text_input("Memo/Notes", placeholder="e.g. Weekly supermarket visit")
            
            submit_exp = st.form_submit_button("Log Expense")
            if submit_exp:
                st.session_state.expenses.append({
                    "date": exp_date.strftime("%Y-%m-%d"),
                    "category": exp_cat,
                    "amount": exp_amount,
                    "note": exp_note
                })
                st.success(f"Successfully recorded ${exp_amount:,.2f} spent on {exp_cat}!")
                
    # Entry Choice B: Savings Form
    elif entry_type == "Savings Vault":
        with st.form("savings_form", clear_on_submit=True):
            st.subheader("Record Savings Deposit or Withdrawal")
            sav_date = st.date_input("Transaction Date", value=datetime.today())
            sav_action = st.selectbox("Action", ["Deposit", "Withdrawal"])
            sav_amount = st.number_input("Amount ($)", min_value=0.01, step=10.0)
            
            submit_sav = st.form_submit_button("Modify Savings Vault")
            if submit_sav:
                if sav_action == "Deposit":
                    st.session_state.savings_balance += sav_amount
                else:
                    st.session_state.savings_balance -= sav_amount
                
                st.session_state.savings_ledger.append({
                    "date": sav_date.strftime("%Y-%m-%d"),
                    "type": sav_action,
                    "amount": sav_amount
                })
                st.success(f"Successfully logged savings {sav_action.lower()} of ${sav_amount:,.2f}!")
                
    # Entry Choice C: Investments Buy/Sell Form
    elif entry_type == "Investment Buy/Sell":
        with st.form("investment_form", clear_on_submit=True):
            st.subheader("Log a Buy or Sell Order")
            trade_action = st.selectbox("Action", ["BUY", "SELL"])
            trade_ticker = st.text_input("Ticker Symbol", value="AAPL").upper().strip()
            trade_shares = st.number_input("Number of Shares", min_value=0.0001, step=1.0, value=1.0)
            trade_price = st.number_input("Execution Price ($)", min_value=0.01, step=1.0, value=150.0)
            
            submit_trade = st.form_submit_button("Confirm Execution")
            if submit_trade:
                # Initialize key if not existing
                if trade_ticker not in st.session_state.holdings:
                    st.session_state.holdings[trade_ticker] = {"shares": 0.0, "avg_cost": 0.0, "current_price": trade_price}
                
                curr_shares = st.session_state.holdings[trade_ticker]["shares"]
                curr_cost = st.session_state.holdings[trade_ticker]["avg_cost"]
                
                if trade_action == "BUY":
                    new_shares = curr_shares + trade_shares
                    # Weighted cost basis formula
                    new_cost = ((curr_shares * curr_cost) + (trade_shares * trade_price)) / new_shares
                    st.session_state.holdings[trade_ticker]["shares"] = new_shares
                    st.session_state.holdings[trade_ticker]["avg_cost"] = new_cost
                    # Keep current price match
                    st.session_state.holdings[trade_ticker]["current_price"] = trade_price
                    st.success(f"Bought {trade_shares} shares of {trade_ticker} at ${trade_price:,.2f} per share!")
                else:
                    if curr_shares >= trade_shares:
                        new_shares = curr_shares - trade_shares
                        st.session_state.holdings[trade_ticker]["shares"] = new_shares
                        st.success(f"Sold {trade_shares} shares of {trade_ticker} at ${trade_price:,.2f} per share!")
                    else:
                        st.error(f"Insufficient stock balance. You only own {curr_shares} shares of {trade_ticker}.")
