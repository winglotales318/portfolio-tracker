import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# ====================== CONFIG ======================
st.set_page_config(
    page_title="Portfolio Tracker",
    page_icon="💰",
    layout="wide"
)

# ====================== DATABASE ======================
conn = sqlite3.connect('portfolio.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS transactions
                (id INTEGER PRIMARY KEY, 
                 asset TEXT, 
                 type TEXT, 
                 qty REAL, 
                 price REAL, 
                 date TEXT, 
                 notes TEXT)''')
conn.commit()

# ====================== HELPERS ======================
def get_current_price(symbol: str):
    try:
        symbol = symbol.upper()
        if symbol == "BTC":
            ticker = yf.Ticker("BTC-USD")
        elif symbol == "CASH":
            return 1.0
        else:
            ticker = yf.Ticker(symbol)
        price = ticker.history(period="1d")['Close'].iloc[-1]
        return round(price, 4)
    except Exception:
        st.warning(f"Could not fetch price for {symbol}")
        return None

def add_transaction(asset, ttype, qty, price, tdate, notes=""):
    conn.execute("INSERT INTO transactions (asset, type, qty, price, date, notes) VALUES (?,?,?,?,?,?)",
                 (asset.upper(), ttype, qty, price, str(tdate), notes))
    conn.commit()

def get_all_transactions():
    return pd.read_sql("SELECT * FROM transactions ORDER BY date DESC", conn)

def calculate_portfolio():
    df = pd.read_sql("SELECT * FROM transactions", conn)
    if df.empty:
        return pd.DataFrame()
    
    summary = []
    for asset in df['asset'].unique():
        sub = df[df['asset'] == asset]
        total_qty = sub['qty'].sum()
        if total_qty <= 0:
            continue
            
        total_cost = (sub['qty'] * sub['price']).sum()
        avg_price = total_cost / total_qty
        
        curr_price = get_current_price(asset) or avg_price
        value = total_qty * curr_price
        unrealized_pnl = value - total_cost
        pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0
        
        summary.append({
            'Asset': asset,
            'Quantity': round(total_qty, 6),
            'Avg Buy Price': round(avg_price, 4),
            'Current Price': round(curr_price, 4),
            'Value ($)': round(value, 2),
            'Unrealized P&L ($)': round(unrealized_pnl, 2),
            'P&L %': round(pnl_pct, 2)
        })
    
    return pd.DataFrame(summary)

# ====================== UI ======================
st.title("💰 Personal Portfolio Tracker")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Add Transaction", "📜 History"])

with tab1:
    st.header("Current Portfolio")
    portfolio = calculate_portfolio()
    
    if not portfolio.empty:
        total_value = portfolio['Value ($)'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Portfolio Value", f"${total_value:,.2f}")
        col2.metric("Number of Assets", len(portfolio))
        col3.metric("Total Unrealized P&L", 
                   f"${portfolio['Unrealized P&L ($)'].sum():,.2f}")
        
        # Pie Chart
        fig_pie = px.pie(portfolio, values='Value ($)', names='Asset', title="Asset Allocation")
        st.plotly_chart(fig_pie, use_container_width=True)
        
        st.dataframe(portfolio, use_container_width=True, hide_index=True)
        
    else:
        st.info("No holdings yet. Add transactions in the second tab.")

with tab2:
    st.header("Add Transaction")
    with st.form("add_tx_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        asset = col_a.text_input("Asset Symbol", value="AAPL").upper()
        ttype = col_b.selectbox("Transaction Type", ["Buy", "Sell"])
        
        col_c, col_d = st.columns(2)
        qty = col_c.number_input("Quantity", min_value=0.000001, value=10.0, step=0.1)
        price = col_d.number_input("Price per Unit", min_value=0.01, value=150.0, step=0.01)
        
        tdate = st.date_input("Date", value=date.today())
        notes = st.text_input("Notes (optional)")
        
        if st.form_submit_button("Add Transaction"):
            add_transaction(asset, ttype, qty, price, tdate, notes)
            st.success(f"✅ {ttype} {qty} {asset} @ ${price} added!")

with tab3:
    st.header("Transaction History")
    df = get_all_transactions()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions recorded yet.")

st.sidebar.success("Portfolio Tracker v1.0")
st.sidebar.info("Data fetched from Yahoo Finance")
