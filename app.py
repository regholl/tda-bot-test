# Import packages

import datetime as dt # pip install datetime
import math
import numpy as np # pip install numpy
import pandas as pd  # pip install pandas
import plotly.graph_objs as go  # pip install plotly
import streamlit as st  # pip install streamlit
import streamlit.components.v1 as components
import streamlit_authenticator as stauth  # pip install streamlit-authenticator
from streamlit_option_menu import option_menu # pip install streamlit-option-menu
import ta # pip install ta
from tda import *

# Set page config

st.set_page_config(page_title="Trade Bot", page_icon=":chart_with_upwards_trend:", layout="wide")
# emojis: https://www.webfx.com/tools/emoji-cheat-sheet/

# Database connection

deta = connect_db()
users_db = deta.Base("users_db")

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

    whitespace_style = \
        """
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
        """
    st.markdown(whitespace_style, unsafe_allow_html=True)

    # Title of page

    st.title(":chart_with_upwards_trend: Trade Bot")
    st.markdown("##")

    # Database connection (again)

    deta = connect_db()
    config_db = deta.Base("config_db")
    tickers_db = deta.Base("tickers_db")

    # Get data from database

    tickers_info = tickers_db.fetch().items
    tickers = [item["key"].upper() for item in tickers_info]

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

    # Display market status

    hours = get_hours_tda()
    market_open = hours[0]
    closing_time = hours[1]
    current_time = hours[2]
    minutes_until_close = np.round((closing_time - current_time).total_seconds() / 60, 2)
    if 0 < minutes_until_close < 450:
        market_str = "OPEN"
    else:
        market_str = "CLOSED"

    # Display cloud status

    heroku_token = config_db.get("HEROKU_API")['value']
    heroku_url = 'https://api.heroku.com'
    apps_url = '{}/apps'.format(heroku_url)
    app_name = 'the-process'
    headers = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Content-Type": "application/json", 
        "Authorization": "Bearer {}".format(heroku_token)
    }

    def get_cloud(id_=False):
        dyno_list_url_all = '{}/{}/dynos'.format(apps_url, app_name)
        get_dyno_list_all = requests.get(dyno_list_url_all, headers = headers)
        dyno_content = get_dyno_list_all.content
        if get_dyno_list_all.status_code in [200, 201]:
            dyno_content = json.loads(dyno_content)
        detached_dyno = [dyno for dyno in dyno_content if dyno['command'] == 'python script.py']
        if id_:
            return detached_dyno
        if len(detached_dyno) > 0:
            cloud_bool = True
        else:
            cloud_bool = False
        return cloud_bool

    def start_cloud():
        cloud = get_cloud()
        if not cloud:
            run_script = {"command": "python script.py",
                        "type": "run:detached"}
            dyno_create_url_all = '{}/{}/dynos'.format(apps_url, app_name)
            post_dyno_all = requests.post(dyno_create_url_all, data = json.dumps(run_script), headers = headers)
            post_dyno_all_content = json.loads(post_dyno_all.content)
            return post_dyno_all_content
        else:
            return cloud

    def stop_cloud():
        dyno = get_cloud(id_=True)
        try:
            detached_dyno_id = dyno[0]['id']
        except:
            return false
        dyno_stop_url_all = '{}/{}/dynos/{}/actions/stop'.format(apps_url, app_name, detached_dyno_id)
        post_dyno_stop_all = requests.post(dyno_stop_url_all, headers = headers)
        dyno_stop_all_content = json.loads(post_dyno_stop_all.content)
        return dyno_stop_all_content

    cloud_options = ["On", "Off"]
    if "cloud_str" not in st.session_state:
        cloud_bool = get_cloud()
        if cloud_bool:
            cloud_str = "On"
        else:
            cloud_str = "Off"
        st.session_state["cloud_str"] = cloud_str

    def toggle_cloud():
        if cloud_radio == "Off":
            start_cloud()
        else:
            stop_cloud()

    # Display bot status

    bot_options = ["On", "Off"]
    if "bot_str" not in st.session_state:
        bot_bool = bool(config_db.get("BOT_ON")['value'])
        if bot_bool:
            bot_str = "On"
        else:
            bot_str = "Off"
        st.session_state["bot_str"] = bot_str
    
    def toggle_bot():
        entry = {}
        entry["key"] = "BOT_ON"
        entry["value"] = ""
        if bot_radio == "Off":
            entry["value"] = True
        else:
            entry["value"] = False
        print(entry)
        config_db.put(entry)
        
    # ---- SIDEBAR ----

    authenticator.logout("Logout", "sidebar")
    with st.sidebar:
        st.title(f"Welcome {name}")
        st.write(f"Market is {market_str}")
        cloud_radio = st.radio(
            label = "Cloud",
            options = cloud_options,
            index = cloud_options.index(st.session_state["cloud_str"]),
            on_change = toggle_cloud,
            horizontal = True
        )
        bot_radio = st.radio(
            label = "Bot",
            options = bot_options,
            index = bot_options.index(st.session_state["bot_str"]),
            on_change = toggle_bot,
            horizontal = True
        )

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
    
    # Deta page

    deta_name = config_db.get("DETA_NAME")['value']
    deta_link = f"Click here to view these settings in [Deta](https://web.deta.sh/home/{deta_name}/default/bases/tickers_db)"
    if selected_side == "Deta":
        st.title("Deta")
        st.dataframe(data=tickers_info)
        with st.form(key="tickers"):
            edit_symbol = st.text_input(
                label = "Symbol",
                placeholder = "MSFT"
            )
            add_delete = st.radio(
                label = "Action",
                options = ["Add", "Delete"]
            )
            symbol_submit = st.form_submit_button()
            if symbol_submit:
                if len(edit_symbol) < 1:
                    st.warning("No symbol typed, replace placeholder", icon="⚠️")
                else:
                    edit_symbol = edit_symbol.upper()
                    items = tickers_db.fetch().items
                    symbol_keys = [item['key'] for item in items]
                    if add_delete == "Add":
                        if edit_symbol in symbol_keys:
                            st.warning("Symbol already in Deta base, cannot be added again", icon="⚠️")
                        else:
                            default_values = items[0]
                            default_values["key"] = edit_symbol
                            tickers_db.put(default_values)
                            st.success('Deta updated successfully!', icon="✅")
                    elif add_delete == "Delete":
                        if edit_symbol not in symbol_keys:
                            st.warning("Symbol not in Deta base, cannot be deleted", icon="⚠️")
                        else:
                            if len(items) == 1:
                                st.error("Cannot delete last symbol in Deta base", icon="🚨")
                            else:
                                tickers_db.delete(edit_symbol)
                                st.success('Deta updated successfully!', icon="✅")
        st.write(deta_link)

    # Chart page

    if selected_side == "Chart":
        for ticker in tickers:
            # if selected_side == ticker:
            if selected_ticker == ticker:

                # Plotly chart
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
                # print(data[-2:])
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
                blank = pd.Series(" ")
                fig.add_trace(go.Candlestick(
                    x = pd.Series(pd.concat([df['datetime'], blank], ignore_index=True)),
                    open = pd.Series(pd.concat([df['open'], blank], ignore_index=True)),
                    high = pd.Series(pd.concat([df['high'], blank], ignore_index=True)),
                    low = pd.Series(pd.concat([df['low'], blank], ignore_index=True)),
                    close = pd.Series(pd.concat([df['close'], blank], ignore_index=True)),
                    name = 'Candles',
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

                # TradingView Chart
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

                # Form
                values = tickers_db.get(ticker)
                confirm_unit_options = ["second", "minute", "hour"]
                frequency_type_options = ["minute", "daily", "weekly", "monthly"]
                period_type_options = ["day", "month", "year", "ytd"]
                stoploss_options = ["Dollars", "Percent", "Trailing %", "None"]
                take_profit_options = ["Dollars", "Percent", "None"]
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.title(f"Deta settings for {ticker}")
                    with st.form(key="deta_settings"):
                        confirm_time = st.number_input(
                            label = "Confirm time",
                            help = "The amount of time to sit in a HA candle before exiting",
                            value = values['confirm_time'],
                            step = 1,
                            min_value = 0
                        )
                        confirm_unit = st.selectbox(
                            label = "Confirm unit",
                            help = "The unit of measure associated with confirm time",
                            options = confirm_unit_options,
                            index = confirm_unit_options.index(values['confirm_unit'].lower()),
                        )
                        contracts = st.number_input(
                            label = "Contracts",
                            help = "The number of shares/option contracts to purchase on entry",
                            value = values['contracts'],
                            step = 1,
                            min_value = 1
                        )
                        delta_min = st.slider(
                            label = "Delta min",
                            help = "Determines which strike to buy (0=OTM, 50=ATM, 99=ITM)",
                            value = values['delta_min'],
                            step = 1,
                            min_value = 0,
                            max_value = 99
                        )
                        dte_min = st.number_input(
                            label = "DTE min",
                            help = "Determines which expiration date to buy (0=today)",
                            value = values['dte_min'],
                            step = 1,
                            min_value = 0,
                        )
                        ema_length = st.number_input(
                            label = "EMA length",
                            help = "The length of the exponential moving average",
                            value = values['ema_length'],
                            step = 1,
                            min_value = 1
                        )
                        extended_hours = st.checkbox(
                            label = "Extended hours",
                            help = "Determines whether data includes pre/post",
                            value = values['extended_hours'],
                        )
                        frequency = st.number_input(
                            label = "Frequency",
                            help = "The timeframe length of your market data",
                            value = values['frequency'],
                            step = 1,
                            min_value = 1
                        )
                        frequency_type = st.selectbox(
                            label = "Frequency type",
                            help = "The unit of measure associated with frequency",
                            options = frequency_type_options,
                            index = frequency_type_options.index(values['frequency_type'].lower())
                        )
                        hma_length = st.number_input(
                            label = "HMA length",
                            help = "The length of the Hull Suite moving average",
                            value = values['hma_length'],
                            step = 1,
                            min_value = 1
                        )
                        #max
                        #min
                        period = st.number_input(
                            label = "Period",
                            help = "The length back of your market data",
                            value = values['period'],
                            step = 1,
                            min_value = 1
                        )
                        period_type = st.selectbox(
                            label = "Period type",
                            help = "The unit of measure associated with period",
                            options = period_type_options,
                            index = period_type_options.index(values['period_type'].lower())
                        )
                        stoploss = st.number_input(
                            label = "Stoploss ($)",
                            help = "The max amount of loss before closing",
                            value = values['stoploss'],
                            step = 1,
                            min_value = 0
                        )
                        stoploss_pct = st.slider(
                            label = "Stoploss (%)",
                            help = "The max percentage of loss before closing",
                            value = values['stoploss_pct'],
                            step = 1,
                            min_value = 0,
                            max_value = 100
                        )
                        stoploss_type = st.selectbox(
                            label = "Stoploss type",
                            help = "The method of calculating stoploss",
                            options = stoploss_options,
                            index = stoploss_options.index(values['stoploss_type'])
                        )
                        take_profit = st.number_input(
                            label = "Take profit ($)",
                            help = "The max amount of gain before closing",
                            value = values['take_profit'],
                            step = 1,
                            min_value = 0
                        )
                        take_profit_pct = st.slider(
                            label = "Take profit (%)",
                            help = "The max percentage of gain before closing",
                            value = values['take_profit_pct'],
                            step = 1,
                            min_value = 0,
                            max_value = 100
                        )
                        take_profit_type = st.selectbox(
                            label = "Take profit type",
                            help = "The method of calculating take profit",
                            options = take_profit_options,
                            index = take_profit_options.index(values['take_profit_type'])
                        )
                        # time_in_candle
                        trail_pct = st.slider(
                            label = "Trail (%): The max trailing percentage of loss before closing",
                            value = values['trail_pct'],
                            step = 1,
                            min_value = 0,
                            max_value = 100
                        )
                        trigger_trail = st.number_input(
                            label = "Trigger trail ($)",
                            help = "The gain amount at which a trailing stop triggers",
                            value = values['trigger_trail'],
                            step = 1,
                            min_value = 0
                        )
                        trigger_trail_pct = st.slider(
                            label = "Trigger Trail (%)",
                            help = "The trailing stop set after reaching trigger",
                            value = values['trigger_trail_pct'],
                            step = 1,
                            min_value = 0,
                            max_value = 100
                        )
                        submit_settings = st.form_submit_button(label="Update Deta")
                        if submit_settings:
                            entry = {
                                "confirm_time": confirm_time,
                                "confirm_unit": confirm_unit,
                                "contracts": contracts,
                                "dte_min": dte_min,
                                "delta_min": delta_min,
                                "ema_length": ema_length,
                                "extended_hours": extended_hours,
                                "frequency_type": frequency_type,
                                "frequency": frequency,
                                "hma_length": hma_length,
                                "key": ticker,
                                "max": values['max'],
                                "min": values['min'],
                                "period": period,
                                "period_type": period_type, 
                                "stoploss": stoploss,
                                "stoploss_pct": stoploss_pct,
                                "stoploss_type": stoploss_type,
                                "take_profit": take_profit,
                                "take_profit_pct": take_profit_pct,
                                "take_profit_type": take_profit_type,
                                "time_in_candle": values['time_in_candle'],
                                "trail_pct": trail_pct,
                                "trigger_trail": trigger_trail,
                                "trigger_trail_pct": trigger_trail_pct,
                            }
                            tickers_db.put(entry)
                            st.success('Deta updated successfully!', icon="✅")

    # ---- HIDE STREAMLIT STYLE ----
    hide_st_style = \
        """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
        """
    st.markdown(hide_st_style, unsafe_allow_html=True)