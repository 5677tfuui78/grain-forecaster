{\rtf1\ansi\ansicpg1252\cocoartf2865
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import yfinance as yf\
import pandas as pd\
import numpy as np\
import plotly.graph_objects as go\
from datetime import datetime, timedelta\
import warnings\
\
# --- PAGE SETUP ---\
st.set_page_config(page_title="Grain Forecaster", layout="wide", page_icon="\uc0\u55356 \u57150 ")\
st.title("\uc0\u55356 \u57150  Grain Price Forecaster")\
st.markdown("### CBOT Seasonality & Futures Curve (USD/MT)")\
\
# --- SIDEBAR CONTROLS ---\
st.sidebar.header("Configuration")\
YEARS_HISTORY = st.sidebar.slider("Seasonality Lookback (Years)", min_value=5, max_value=30, value=15)\
LBS_PER_MT = 2204.62\
\
# --- DATA CONSTANTS ---\
COMMODITIES = \{\
    'Corn': \{\
        'Symbol': 'ZC=F', 'Root': 'ZC', 'Bushel_lbs': 56, \
        'Months': ['H', 'K', 'N', 'U', 'Z'] \
    \},\
    'Soybeans': \{\
        'Symbol': 'ZS=F', 'Root': 'ZS', 'Bushel_lbs': 60, \
        'Months': ['F', 'H', 'K', 'N', 'Q', 'U', 'X'] \
    \},\
    'Wheat': \{\
        'Symbol': 'ZW=F', 'Root': 'ZW', 'Bushel_lbs': 60, \
        'Months': ['H', 'K', 'N', 'U', 'Z'] \
    \}\
\}\
MONTH_CODES = \{'F':1, 'H':3, 'K':5, 'N':7, 'Q':8, 'U':9, 'X':11, 'Z':12\}\
\
# --- HELPER FUNCTIONS ---\
def to_usd_mt(price_cents, lbs_per_bu):\
    if price_cents is None: return 0\
    bushels_per_tonne = LBS_PER_MT / lbs_per_bu\
    return (price_cents / 100) * bushels_per_tonne\
\
@st.cache_data(ttl=3600) # Cache data for 1 hour to speed up phone loading\
def get_data(ticker, years):\
    start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y-%m-%d')\
    df = yf.download(ticker, start=start_date, progress=False)\
    if df.empty: return None\
    return df.dropna()\
\
def calculate_seasonality(df):\
    try:\
        # Handle different dataframe structures from yfinance\
        if isinstance(df.columns, pd.MultiIndex):\
            series = df.xs('Close', axis=1, level=0)\
        else:\
            series = df['Close']\
        \
        if isinstance(series, pd.DataFrame):\
            series = series.iloc[:, 0]\
\
        returns = series.pct_change()\
        monthly_avg = returns.groupby(series.index.month).mean()\
        \
        current_month = datetime.now().month\
        seasonality_order = []\
        for i in range(1, 13):\
            m = (current_month + i - 1) % 12 \
            if m == 0: m = 12\
            seasonality_order.append(m)\
            \
        return monthly_avg.loc[seasonality_order]\
    except Exception as e:\
        st.error(f"Error calculating seasonality: \{e\}")\
        return pd.Series()\
\
def generate_forecast(current_price_mt, ordered_returns):\
    prices = [current_price_mt]\
    dates = [datetime.now()]\
    for ret in ordered_returns:\
        prices.append(prices[-1] * (1 + ret))\
        dates.append(dates[-1] + timedelta(days=30))\
    return pd.DataFrame(\{'Date': dates, 'Forecast_MT': prices\})\
\
def get_futures_curve_mt(root_ticker, active_months, lbs_per_bu):\
    curve_data = []\
    today = datetime.now()\
    year = today.year\
    attempts = 0\
    \
    # Simple logic to find active contracts\
    while len(curve_data) < 8 and attempts < 18:\
        for code, month_num in MONTH_CODES.items():\
            if code not in active_months: continue\
            \
            contract_year = year\
            if month_num < today.month and year == today.year:\
                contract_year += 1\
            elif year > today.year:\
                contract_year = year\
                \
            contract_date = datetime(contract_year, month_num, 1)\
            if contract_date < today: continue\
\
            yy = str(contract_year)[-2:]\
            ticker = f"\{root_ticker\}\{code\}\{yy\}.CBT"\
            \
            try:\
                # We don't cache this as we want live market data\
                data = yf.Ticker(ticker).history(period="1d")\
                if not data.empty:\
                    price_mt = to_usd_mt(data['Close'].iloc[-1], lbs_per_bu)\
                    curve_data.append(\{'Contract': f"\{code\}\{yy\}", 'Date': contract_date, 'Price_MT': price_mt\})\
            except:\
                pass\
        year += 1\
        attempts += 1\
    \
    if not curve_data: return pd.DataFrame()\
    return pd.DataFrame(curve_data).sort_values('Date')\
\
# --- MAIN APP LOGIC ---\
if st.button('\uc0\u55357 \u56580  Refresh Data'):\
    st.cache_data.clear()\
\
tabs = st.tabs(["Corn", "Soybeans", "Wheat"])\
\
for i, (name, info) in enumerate(COMMODITIES.items()):\
    with tabs[i]:\
        # Fetch Data\
        df = get_data(info['Symbol'], YEARS_HISTORY)\
        \
        if df is not None:\
            # Current Price Processing\
            try:\
                last_price = df['Close'].iloc[-1]\
                if isinstance(last_price, pd.Series): last_price = last_price.item()\
                current_mt = to_usd_mt(last_price, info['Bushel_lbs'])\
            except:\
                current_mt = 0\
\
            # Forecasting\
            seasonality = calculate_seasonality(df)\
            forecast_df = generate_forecast(current_mt, seasonality)\
            curve_df = get_futures_curve_mt(info['Root'], info['Months'], info['Bushel_lbs'])\
            \
            # Key Metrics at top of screen\
            col1, col2, col3 = st.columns(3)\
            col1.metric("Current Spot", f"$\{current_mt:.2f\}")\
            \
            forecast_6mo = forecast_df['Forecast_MT'].iloc[6]\
            delta = forecast_6mo - current_mt\
            col2.metric("6-Month Target", f"$\{forecast_6mo:.2f\}", f"\{delta:.2f\}")\
            \
            trend = "\uc0\u55357 \u56322  Bullish" if forecast_6mo > current_mt else "\u55357 \u56379  Bearish"\
            col3.markdown(f"**Trend:** \{trend\}")\
\
            # INTERACTIVE CHART (Plotly)\
            fig = go.Figure()\
            \
            # 1. Seasonal Forecast Line\
            fig.add_trace(go.Scatter(\
                x=forecast_df['Date'], y=forecast_df['Forecast_MT'],\
                mode='lines+markers', name='Seasonal Model',\
                line=dict(color='blue', width=2, dash='dash')\
            ))\
            \
            # 2. Futures Curve Line\
            if not curve_df.empty:\
                fig.add_trace(go.Scatter(\
                    x=curve_df['Date'], y=curve_df['Price_MT'],\
                    mode='lines+markers', name='Futures Market',\
                    line=dict(color='green', width=3)\
                ))\
            \
            fig.update_layout(\
                title=f"\{name\} Price Forecast (USD/MT)",\
                yaxis_title="USD / Metric Tonne",\
                hovermode="x unified",\
                height=500,\
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)\
            )\
            st.plotly_chart(fig, use_container_width=True)\
            \
            # Data Table\
            if st.checkbox(f"Show Raw Data for \{name\}"):\
                st.dataframe(forecast_df)\
        else:\
            st.warning(f"Could not load data for \{name\}. Check internet connection.")\
\
st.markdown("---")\
st.caption("Data source: Yahoo Finance (Delayed). Not financial advice.")}