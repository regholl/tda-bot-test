# Import packages

import datetime as dt # pip install datetime
from deta import Deta  # pip install deta
from dotenv import load_dotenv  # pip install python-dotenv
import json
import math
import numpy as np # pip install numpy
import os
import pandas as pd  # pip install pandas
import pytz
import plotly.graph_objs as go  # pip install plotly
import requests # pip install requests
import streamlit as st  # pip install streamlit
import streamlit.components.v1 as components
import streamlit_authenticator as stauth  # pip install streamlit-authenticator
from streamlit_option_menu import option_menu # pip install streamlit-option-menu
import ta # pip install ta
from tda import *

# Database connection

# @st.cache
def connect_db():
    load_dotenv(".env")
    DETA_KEY = os.getenv("DETA_KEY")
    deta = Deta(DETA_KEY)
    return deta

config_db = connect_db().Base("config_db")
users_db = connect_db().Base("users_db")
tickers_db = connect_db().Base("tickers_db")

# Set page config

st.set_page_config(page_title="Trade Bot", page_icon=":chart_with_upwards_trend:", layout="wide")
# emojis: https://www.webfx.com/tools/emoji-cheat-sheet/

# User login

users = users_db.fetch().items
usernames = [user["key"] for user in users]
names = [user["name"] for user in users]
hashed_passwords = [user["password"] for user in users]
authenticator = stauth.Authenticate(names, usernames, hashed_passwords, "sales_dashboard", "abcdef", cookie_expiry_days=30)
name, auth, username = authenticator.login("Login", "main")
if auth == False:
    st.error("Username/password is incorrect")
if auth == None:
    st.warning("Please enter your username and password")

# Main page after login

if auth:

    # Remove whitespace from the top of the page and sidebar
    st.markdown("""
            <style>
                .css-18e3th9 {
                        padding-top: 0rem;
                        padding-bottom: 10rem;
                        padding-left: 5rem;
                        padding-right: 5rem;
                    }
                .css-1d391kg {
                        padding-top: 3rem;
                        padding-right: 1rem;
                        padding-bottom: 3rem;
                        padding-left: 1rem;
                    }
                .css-hxt7ib {
                        padding-top: 3rem;
                        padding-left: 1rem;
                        padding-right: 1rem;
                    }
                .css-r4g17z {
                        height: 2rem;
                    }
            </style>
            """, unsafe_allow_html=True)

    # Title of page
    st.title(":chart_with_upwards_trend: Trade Bot")
    st.markdown("##")

    # Data from databse
    tickers_info = tickers_db.fetch().items
    tickers = [item["key"].upper() for item in tickers_info]
    # period_types = [item["period_type"] for item in tickers_info]
    # periods = [item["period"] for item in tickers_info]
    # frequencies = [item["frequency"] for item in tickers_info]
    # frequency_types = [item["frequency_type"] for item in tickers_info]
    # extended_hours = [item["extended_hours"] for item in tickers_info]
    # ema_lengths = [item["ema_length"] for item in tickers_info]
    # hma_lengths = [item["hma_length"] for item in tickers_info]
    # contracts = [item["contracts"] for item in tickers_info]
    # stoplosses = [item["stoploss"] for item in tickers_info]
    # stoploss_pcts = [item["stoploss_pct"] for item in tickers_info]
    # trailing_pcts = [item["trailing_pct"] for item in tickers_info]
    # use_trailings = [item["use_trailing"] for item in tickers_info]

    # Option menu
    # page_icons = ["table"] * 3 + ["currency-dollar"] * len(tickers)
    page_options = ["Chart", "Positions", "Orders", "Deta"]
    # selected_menu = option_menu(
    #         menu_title=None,  # required
    #         options=page_options,  # required
    #         icons=page_icons,  # optional https://icons.getbootstrap.com/
    #         menu_icon="cast",  # optional
    #         default_index=0,  # optional
    #         orientation="horizontal",
    #         styles = {
    #             "container": {
    #                 "padding": "0!important", 
    #                 "background-color": "black"
    #             },
    #             "icon": {
    #                 "color": "orange", 
    #                 "font-size": "25px"
    #             },
    #             "nav-link": {
    #                 "font-size": "25px",
    #                 "text-align": "left",
    #                 "margin": "0px",
    #                 "--hover-color": "gray",
    #             },
    #             "nav-link-selected": {
    #                 "background-color": "#0083B8"
    #             },
    #         },
    #     )
    deta_name = config_db.get("DETA_NAME")['value']
    deta_link = f"Click here to edit these settings: [Deta](https://web.deta.sh/home/{deta_name}/default/bases/tickers_db)"
    market_open = get_hours_tda()
    if market_open:
        market_str = "OPEN"
    else:
        market_str = "CLOSED"

    # ---- SIDEBAR ----
    authenticator.logout("Logout", "sidebar")
    st.sidebar.title(f"Welcome {name}")
    st.sidebar.write(f"Market is {market_str}")
    #if selected_menu in tickers:
    selected_side = st.sidebar.selectbox("Select Page:", options=page_options)
    if selected_side == "Chart":
        selected_ticker = st.sidebar.selectbox("Select Ticker:", options=tickers)
        candle_options = ["Heikin Ashi", "Normal"]
        selected_candle = st.sidebar.selectbox("Select Candle:", options=candle_options)
        indicator_options = ["HMA", "EMA"]
        selected_indicators = st.sidebar.multiselect(
            "Select Indicators:",
            options = indicator_options,
            default = indicator_options
        )

    # Positions page

    if selected_side == "Positions":
        st.title("Positions")
        positions = get_positions_tda()
        positions1 = []
        for position in positions:
            pos_dict = {}
            pos_dict["Symbol"] = position["instrument"]["symbol"]
            pos_dict["Quantity"] = max(int(position["longQuantity"]), int(position["shortQuantity"]))
            pos_dict["Average Price"] = np.round(float(position["averagePrice"]), 2)
            pos_dict["Market Value"] = np.round(float(position["marketValue"]), 2)
            positions1.append(pos_dict)
        positions = positions1
        st.table(data=positions)

    # Orders page

    if selected_side == "Orders":
        st.title("Orders")
        orders = get_orders_tda()
        orders1 = []
        for order in orders:
            order_dict = {}
            order_dict["Datetime"] = pd.Timestamp(order["orderDate"], tz=utc).astimezone(local_timezone).strftime("%m/%d/%Y %X")
            order_dict["Symbol"] = order["transactionItem"]["instrument"]["symbol"]
            order_dict["Side"] = order["transactionItem"]["instruction"]
            order_dict["Quantity"] = int(order["transactionItem"]["amount"])
            order_dict["Price"] = np.round(float(order["transactionItem"]["price"]), 2)
            orders1.append(order_dict)
        orders = orders1
        st.table(data=orders)
    
    # Deta Page

    if selected_side == "Deta":
        st.title("Deta")
        st.table(data=tickers_info)
        st.write(deta_link)

    # Display ticker info

    if selected_side == "Chart":
        for ticker in tickers:
            # if selected_side == ticker:
            if selected_ticker == ticker:
                idx = tickers.index(ticker)
                quote = get_quote_tda(ticker)
                last = str(np.round(float(quote[ticker]['lastPrice']), 2))
                if "." not in last:
                    last = last + ".00"
                if len(last.split(".")[1]) == 1:
                    last = last + "0"
                periodType = tickers_info[idx]['period_type']
                period = tickers_info[idx]['period']
                frequencyType = tickers_info[idx]['frequency_type']
                frequency = tickers_info[idx]['frequency']
                extended_hours = tickers_info[idx]['extended_hours']
                data = get_data_tda(ticker=ticker, periodType=periodType, period=period, frequencyType=frequencyType, frequency=frequency, extended_hours=extended_hours)
                df = pd.DataFrame()
                if frequencyType == "minute":
                    time_format = "%m/%d %H:%M"
                elif frequencyType == "daily":
                    time_format = "%m/%d"
                elif frequencyType == "weekly":
                    time_format = "%m/%d/%Y"
                elif frequencyType == "monthly":
                    time_format = "%b %Y"
                tda_times = [candle['datetime'] for candle in data]
                tda_dates = [dt.datetime.utcfromtimestamp(time_ / 1000) for time_ in tda_times]
                tda_locals = [utc.localize(date).astimezone(local_timezone) for date in tda_dates]
                tda_datetimes = [time_.strftime(time_format) for time_ in tda_locals]
                tda_opens = [item['open'] for item in data]
                tda_highs = [item['high'] for item in data]
                tda_lows = [item['low'] for item in data]
                tda_closes = [item['close'] for item in data]
                if selected_candle == "Heikin Ashi":
                    ha_opens = [None] * len(tda_opens)
                    ha_highs = [None] * len(tda_highs)
                    ha_lows = [None] * len(tda_lows)
                    ha_closes = [None] * len(tda_closes)
                    ha_closes[0] = 0.25 * (tda_opens[0] + tda_highs[0] + tda_lows[0] + tda_closes[0])
                    ha_opens[0] = tda_opens[0]
                    ha_highs[0] = max(tda_highs[0], ha_opens[0], ha_closes[0])
                    ha_lows[0] = min(tda_lows[0], ha_opens[0], ha_closes[0])
                    i = 1
                    while i < len(ha_closes):
                        ha_opens[i] = 0.5 * (ha_opens[i-1] + ha_closes[i-1])
                        ha_highs[i] = max(tda_highs[i], ha_opens[i], tda_closes[i])
                        ha_lows[i] = min(tda_lows[i], ha_opens[i], tda_closes[i])
                        ha_closes[i] = 0.25 * (ha_opens[i] + tda_highs[i] + tda_lows[i] + tda_closes[i])
                        i += 1
                    tda_opens = ha_opens
                    tda_highs = ha_highs
                    tda_lows = ha_lows
                    tda_closes = ha_closes
                tda_datetimes = [""] + tda_datetimes
                tda_opens = [""] + tda_opens
                tda_highs = [""] + tda_highs
                tda_lows = [""] + tda_lows
                tda_closes = [""] + tda_closes
                df['datetime'] = tda_datetimes
                df['open'] = tda_opens
                df['high'] = tda_highs
                df['low'] = tda_lows
                df['close'] = tda_closes
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x = df['datetime'].append(pd.Series(" ")),
                    open = df['open'].append(pd.Series(" ")),
                    high = df['high'].append(pd.Series(" ")),
                    low = df['low'].append(pd.Series(" ")),
                    close = df['close'].append(pd.Series(" ")), 
                    name = 'Candles'
                ))
                if "EMA" in selected_indicators:
                    ema_window = tickers_info[idx]['ema_length']
                    ema = np.round(ta.trend.ema_indicator(pd.to_numeric(df['close']), window=ema_window), 2)
                    fig.add_trace(go.Scatter(
                        x = df['datetime'], 
                        y = ema,
                        line = dict(color='blue', width=1.5), 
                        name = f'EMA {ema_window}'
                    ))
                if "HMA" in selected_indicators:
                    hma_window = tickers_info[idx]['hma_length']
                    hma1 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=int(hma_window/2))
                    hma2 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=hma_window)
                    hma_raw = (2 * hma1) - hma2
                    hma = np.round(ta.trend.wma_indicator(hma_raw, window=math.floor(math.sqrt(hma_window))), 2)
                    fig.add_trace(go.Scatter(
                        x = df['datetime'], 
                        y = hma,
                        line = dict(color='purple', width=1.5), 
                        name = f'HMA {hma_window}'
                    ))
                fig.update_layout(
                    title = f'Chart: {ticker} ({last}), {frequency} {frequencyType}',
                    height = 700,
                    yaxis_title = 'Price',
                    xaxis_title = 'Datetime',
                    plot_bgcolor = 'gainsboro'
                )
                fig.update_xaxes(
                    rangeslider_visible=False,
                    showgrid=False,
                    tickprefix=" "
                )
                fig.update_yaxes(
                    showgrid=False,
                    ticksuffix=" "
                )
                st.plotly_chart(fig, use_container_width = True)
                tv_chart = """
                    <div class="tradingview-widget-container">
                        <div id="tradingview_567ac"></div>
                        <div class="tradingview-widget-copyright">
                            <a href="https://www.tradingview.com/symbols/SPY/" rel="noopener" target="_blank">
                                <span class="blue-text">SPY Chart</span>
                            </a> by TradingView</div>
                        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                        <script type="text/javascript">
                            new TradingView.widget(
                            {
                                "width": 1000,
                                "height": 650,
                                "symbol": "SPY",
                                "interval": "D",
                                "timezone": "America/New_York",
                                "theme": "light",
                                "style": "8",
                                "locale": "en",
                                "toolbar_bg": "#f1f3f6",
                                "enable_publishing": false,
                                "withdateranges": true,
                                "hide_side_toolbar": false,
                                "allow_symbol_change": true,
                                "details": false,
                                "container_id": "tradingview_52a26"
                            });
                        </script>
                    </div>
                """
                # Style:8 is for Heikin Ashi
                if frequencyType == "minute":
                    interval = str(frequency)
                elif frequencyType == "daily":
                    interval = "D"
                elif frequencyType == "weekly":
                    interval = "W"
                elif frequencyType == "monthly":
                    interval = "M"
                tv_chart = tv_chart.replace("D", interval)
                tv_chart = tv_chart.replace("SPY", ticker)
                components.html(tv_chart, height = 650)
                st.table(data={"Value": tickers_db.get(ticker)})
                st.write(deta_link)

    # ---- HIDE STREAMLIT STYLE ----
    hide_st_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                header {visibility: hidden;}
                </style>
                """
    st.markdown(hide_st_style, unsafe_allow_html=True)