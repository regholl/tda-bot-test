# This is the main file that executes the automated trades. Everything else is a supporting document.

# Import required packages

import datetime as dt
from db import *
import math
import numpy as np
import pandas as pd
import pytz
from stop import stop
import ta
from tda import *
import threading
import time

# Global variables

log_count = 0
error_streak = 0
bot_on_last = False
down_for_day = False
cp = 10
utc = pytz.timezone("UTC")
local_timezone = pytz.timezone("US/Pacific")
ticker_db_dict = {}
checkpoint_db_dict = {}

# Define the strategy function which will run a loop

def run():

    # Execution start

    time_start = time.time()

    # Check if bot is on

    deta = connect_db()
    config_db = deta.Base("config_db")
    bot_on = bool(config_db.get("BOT_ON")['value'])
    global bot_on_last
    if bot_on_last == True and bot_on == False:
        print("Bot turning off")
    elif bot_on_last == False and bot_on == True:
        print("Bot turning on")
    bot_on_last = bot_on
    if bot_on == False:
        return False

    # Check if it's after-hours and time to shut down

    start_local = pd.Timestamp(time_start, unit="s", tz=utc).astimezone(local_timezone)
    time_cutoff = dt.datetime(year=start_local.year, month=start_local.month, day=start_local.day, hour=13, minute=1) 
    time_cutoff = pd.Timestamp(time_cutoff, tz=local_timezone)
    global down_for_day
    heroku_token = config_db.get("HEROKU_API")['value']
    if start_local > time_cutoff and down_for_day == False:
        print(f"{start_local} > {time_cutoff}, shutting down...")
        down_for_day = True
        stop()

    # Error counter

    global error_streak
    error_streak += 1

    # Extract values from Deta and create master dictionary

    tickers_db = deta.Base("tickers_db")
    tickers_info = tickers_db.fetch().items
    tickers = [item["key"].upper() for item in tickers_info]
    checkpoints_db = deta.Base("checkpoints_db")
    checkpoints_info = checkpoints_db.fetch().items
    indicator_options = ["HMA", "EMA", "Candles"]
    ticker_dict = {}
    global ticker_db_dict
    global checkpoint_db_dict
    for i in range(len(tickers)):
        ticker_dict[tickers[i]] = tickers_info[i]
        ticker_db_dict[tickers[i]] = tickers_info[i].copy()
        checkpoint_db_dict[tickers[i]] = checkpoints_info[i]
        ticker_dict[tickers[i]]["option_symbol"] = tickers[i]
        ticker_dict[tickers[i]]["average_price"] = 0
        ticker_dict[tickers[i]]["market_value"] = 0
        ticker_dict[tickers[i]]["long_shares"] = 0
        ticker_dict[tickers[i]]["short_shares"] = 0
        ticker_dict[tickers[i]]["quantity"] = 0
        ticker_dict[tickers[i]]["option_last"] = 0

    for i in range(len(checkpoints_info)):
        key2 = checkpoints_info[i]['key']
        if key2 in tickers:
            idx = tickers.index(key2)
            for key, value in checkpoints_info[i].items():
                ticker_dict[tickers[idx]][key] = value

    # Get market status

    hours = get_hours_tda()
    market_open = hours[0]
    closing_time = hours[1]
    #current_time = hours[2]

    # Calculate time
    
    current_time = dt.datetime.now(tz=local_timezone)
    minutes_until_close = np.round((closing_time - current_time).total_seconds() / 60, 2)
    # condition1 = market_open
    condition1 = 0 < minutes_until_close < 450

    # Get positions from TDA API

    tda_positions = get_positions_tda()
    if tda_positions != []:
        tda_tickers_held = [position['instrument']['symbol'] for position in tda_positions]
        tda_average_prices = [np.round(float(position['averagePrice']),2) for position in tda_positions]
        tda_market_values = [np.round(float(position['marketValue']),2) for position in tda_positions]
        tda_long_shares = [int(position['longQuantity']) for position in tda_positions]
        tda_short_shares = [int(position['shortQuantity']) for position in tda_positions]
        tda_quantities = list(np.array(tda_long_shares) - np.array(tda_short_shares))
    else:
        print("No positions found")
        tda_tickers_held = []
        tda_average_prices = []
        tda_market_values = []
        tda_long_shares = []
        tda_short_shares = []
        tda_quantities = []
    tda_quantities = [int(abs(qty)) for qty in tda_quantities]

    # Adjust tickers for options holdings and get options quotes

    tda_symbols_held = []
    for i in range(len(tda_tickers_held)):
        symb = tda_tickers_held[i]
        if "_" in tda_tickers_held[i]:
            symb = tda_tickers_held[i].split("_")[0]
        tda_symbols_held.append(symb)
        quote = get_quote_tda(tda_tickers_held[i])
        last_option = np.round(float(quote[tda_tickers_held[i]]['lastPrice']), 2)
        if symb in tickers:
            ticker_dict[symb]["option_symbol"] = tda_tickers_held[i]
            ticker_dict[symb]["average_price"] = tda_average_prices[i]
            ticker_dict[symb]["market_value"] = tda_market_values[i]
            ticker_dict[symb]["long_shares"] = tda_long_shares[i]
            ticker_dict[symb]["short_shares"] = tda_short_shares[i]
            ticker_dict[symb]["quantity"] = tda_quantities[i]
            ticker_dict[symb]["option_last"] = last_option

    # Get orders from TDA API

    tda_orders = get_orders2_tda()
    time_now = dt.datetime.now(utc)
    recent_tickers = []

    # Define giant function, will later iterate over each ticker using multi-threading for extra speed

    def strategy(tickers, i):

        # Get database entry

        entry = ticker_db_dict[tickers[i]]
        values1 = checkpoint_db_dict[tickers[i]]
    
        # Get quotes for underlying

        quote = get_quote_tda(tickers[i])
        if tickers[i] not in list(quote.keys()):
            print(quote)
        last = np.round(float(quote[tickers[i]]['lastPrice']), 2)
        bid = np.round(float(quote[tickers[i]]['bidPrice']), 2)
        ask = np.round(float(quote[tickers[i]]['lastPrice']), 2)
        mid = np.round((bid + ask) / 2, 2)
        ticker_dict[tickers[i]]["last"] = last
        ticker_dict[tickers[i]]["bid"] = bid
        ticker_dict[tickers[i]]["ask"] = ask
        ticker_dict[tickers[i]]["mid"] = mid

        # Fetch ticker data settings from Deta

        periodType = ticker_dict[tickers[i]]['period_type']
        period = int(ticker_dict[tickers[i]]['period'])
        frequencyType = ticker_dict[tickers[i]]['frequency_type']
        frequency = int(ticker_dict[tickers[i]]['frequency'])
        extended_hours = ticker_dict[tickers[i]]['extended_hours']

        # Shorten data period if able to increase speed

        ema_window = int(ticker_dict[tickers[i]]['ema_length'])
        hma_window = int(ticker_dict[tickers[i]]['hma_length'])
        max_window = max(ema_window, hma_window)
        min_in_day = 60 * 6.5
        if frequencyType == "minute":
            min_req = frequency * max_window
            day_req = int(min_req / min_in_day) + 1
            day_req = max(day_req, 2)
            if day_req <= 10:
                valid_periods_day = [1, 2, 3, 4, 5, 10]
                if day_req in valid_periods_day:
                    period = day_req
                else:
                    period = 10
            else:
                periodType = "month"
                mon_req = int(day_req / 31) + 1
                if mon_req <= 6:
                    valid_periods_month = [1, 2, 3, 6]
                    if mon_req in valid_periods_month:
                        period = mon_req
                    else:
                        period = 6
                else:
                    periodType = "year"
                    yr_req = int(mon_req / 12) + 1
                    if yr_req <= 20:
                        valid_periods_year = [1, 2, 3, 5, 10, 15, 20]
                        if yr_req in valid_periods_year:
                            period = yr_req
                        elif 3 < yr_req < 5:
                            yr_req = 5
                        elif 5 < yr_req < 10:
                            yr_req = 10
                        elif 10 < yr_req < 15:
                            yr_req = 15
                        else:
                            yr_req = 20

        # Fetch data from TDA API

        data = get_data_tda(ticker=tickers[i], periodType=periodType, period=period, frequencyType=frequencyType, frequency=frequency, extended_hours=extended_hours)
        tda_opens = [item['open'] for item in data]
        tda_highs = [item['high'] for item in data]
        tda_lows = [item['low'] for item in data]
        tda_closes = [item['close'] for item in data]

        # Change to Heikin Ashi candles

        ha_opens = [None] * len(tda_opens)
        ha_highs = [None] * len(tda_highs)
        ha_lows = [None] * len(tda_lows)
        ha_closes = [None] * len(tda_closes)
        ha_closes[0] = 0.25 * (tda_opens[0] + tda_highs[0] + tda_lows[0] + tda_closes[0])
        ha_opens[0] = tda_opens[0]
        ha_highs[0] = max(tda_highs[0], ha_opens[0], ha_closes[0])
        ha_lows[0] = min(tda_lows[0], ha_opens[0], ha_closes[0])
        k = 1
        while k < len(ha_closes):
            ha_opens[k] = 0.5 * (ha_opens[k-1] + ha_closes[k-1])
            ha_highs[k] = max(tda_highs[k], ha_opens[k], tda_closes[k])
            ha_lows[k] = min(tda_lows[k], ha_opens[k], tda_closes[k])
            ha_closes[k] = 0.25 * (ha_opens[k] + tda_highs[k] + tda_lows[k] + tda_closes[k])
            k += 1
        if ticker_dict[tickers[i]]["candle_type"] == "Heikin Ashi":
            tda_opens = ha_opens
            tda_highs = ha_highs
            tda_lows = ha_lows
            tda_closes = ha_closes

        # Determine if candles and wicks are bullish or bearish

        last_open1 = tda_opens[len(tda_opens)-1]
        last_high1 = tda_highs[len(tda_highs)-1]
        last_low1 = tda_lows[len(tda_lows)-1]
        last_close1 = tda_closes[len(tda_closes)-1]
        ticker_dict[tickers[i]]["last_open1"] = last_open1
        ticker_dict[tickers[i]]["last_high1"] = last_high1
        ticker_dict[tickers[i]]["last_low1"] = last_low1
        ticker_dict[tickers[i]]["last_close1"] = last_close1

        if last_close1 > last_open1:
            bullish_candle1 = True
        elif last_close1 < last_open1:
            bullish_candle1 = False
        else:
            bullish_candle1 = None

        ticker_dict[tickers[i]]["bullish_candle1"] = bullish_candle1
        candle_body1 = abs(last_close1 - last_open1)
        candle_wick_top1 = last_high1 - max(last_close1, last_open1)
        candle_wick_bottom1 = min(last_close1, last_high1) - last_low1

        if candle_wick_top1 + candle_wick_bottom1 > candle_body1 * 2:
            doji_candle1 = True
        else:
            doji_candle1 = False

        ticker_dict[tickers[i]]["candle_body1"] = candle_body1
        ticker_dict[tickers[i]]["candle_wick_top1"] = candle_wick_top1
        ticker_dict[tickers[i]]["candle_wick_bottom1"] = candle_wick_bottom1
        ticker_dict[tickers[i]]["doji_candle1"] = doji_candle1

        last_open2 = tda_opens[len(tda_opens)-2]
        last_high2 = tda_highs[len(tda_highs)-2]
        last_low2 = tda_lows[len(tda_lows)-2]
        last_close2 = tda_closes[len(tda_closes)-2]
        ticker_dict[tickers[i]]["last_open2"] = last_open2
        ticker_dict[tickers[i]]["last_high2"] = last_high2
        ticker_dict[tickers[i]]["last_low2"] = last_low2
        ticker_dict[tickers[i]]["last_close2"] = last_close2

        if last_close2 > last_open2:
            bullish_candle2 = True
        elif last_close2 < last_open2:
            bullish_candle2 = False
        else:
            bullish_candle2 = None

        ticker_dict[tickers[i]]["bullish_candle2"] = bullish_candle2
        candle_body2 = abs(last_close2 - last_open2)
        candle_wick_top2 = last_high2 - max(last_close2, last_open2)
        candle_wick_bottom2 = min(last_close2, last_high2) - last_low2

        if candle_wick_top2 + candle_wick_bottom2 > candle_body2:
            doji_candle2 = True
        else:
            doji_candle2 = False

        ticker_dict[tickers[i]]["candle_body2"] = candle_body2
        ticker_dict[tickers[i]]["candle_wick_top2"] = candle_wick_top2
        ticker_dict[tickers[i]]["candle_wick_bottom2"] = candle_wick_bottom2
        ticker_dict[tickers[i]]["doji_candle2"] = doji_candle2

        # Create dataframe and fill with market data

        df = pd.DataFrame()
        df['open'] = tda_opens
        df['high'] = tda_highs
        df['low'] = tda_lows
        df['close'] = tda_closes

        # Calculate technical indicators

        emas_all = np.round(ta.trend.ema_indicator(pd.to_numeric(df['close']), window=ema_window), 4)
        ema = emas_all[len(emas_all)-1]
        ticker_dict[tickers[i]]["ema"] = ema

        hma1 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=int(hma_window/2))
        hma2 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=hma_window)
        hma_raw = (2 * hma1) - hma2
        hmas_all = np.round(ta.trend.wma_indicator(hma_raw, window=math.floor(math.sqrt(hma_window))), 4)
        hma = hmas_all[len(hmas_all)-1]
        ticker_dict[tickers[i]]["hma"] = hma

        # Determine if moving averages are bullish or bearish

        last_ema1 = emas_all[len(emas_all)-1]
        last_ema2 = emas_all[len(emas_all)-2]
        last_ema3 = emas_all[len(emas_all)-3]
        ticker_dict[tickers[i]]["last_ema1"] = last_ema1
        ticker_dict[tickers[i]]["last_ema2"] = last_ema2
        ticker_dict[tickers[i]]["last_ema3"] = last_ema3

        if last_ema1 > last_ema2:
            bullish_ema1 = True
        elif last_ema1 < last_ema2:
            bullish_ema1 = False
        else:
            bullish_ema1 = None
        ticker_dict[tickers[i]]["bullish_ema1"] = bullish_ema1

        if last_ema2 > last_ema3:
            bullish_ema2 = True
        elif last_ema2 < last_ema3:
            bullish_ema2 = False
        else:
            bullish_ema2 = None
        ticker_dict[tickers[i]]["bullish_ema2"] = bullish_ema2

        last_hma1 = hmas_all[len(hmas_all)-1]
        last_hma2 = hmas_all[len(hmas_all)-2]
        last_hma3 = hmas_all[len(hmas_all)-3]
        ticker_dict[tickers[i]]["last_hma1"] = last_hma1
        ticker_dict[tickers[i]]["last_hma2"] = last_hma2
        ticker_dict[tickers[i]]["last_hma3"] = last_hma3

        if last_hma1 > last_hma2:
            bullish_hma1 = True
        elif last_hma1 < last_hma2:
            bullish_hma1 = False
        else:
            bullish_hma1 = None
        ticker_dict[tickers[i]]["bullish_hma1"] = bullish_hma1

        if last_hma2 > last_hma3:
            bullish_hma2 = True
        elif last_hma2 < last_hma3:
            bullish_hma2 = False
        else:
            bullish_hma2 = None
        ticker_dict[tickers[i]]["bullish_hma2"] = bullish_hma2

        # Get the relevant option symbol bot will purchase if entry criteria are met

        chain = get_chain_tda(tickers[i])
        ticker_dict[tickers[i]]["chain"] = chain

        # Calculate costbasis and gainloss from quotes and average prices

        if tickers[i] in tda_symbols_held:
            idx = tda_symbols_held.index(tickers[i])
            if tda_long_shares[idx] > 0:
                if ticker_dict[tickers[i]]["option_symbol"] == tickers[i]:
                    tda_costbasis = np.round(tda_average_prices[idx] * tda_long_shares[idx], 2)
                else:
                    tda_costbasis = np.round(tda_average_prices[idx] * tda_long_shares[idx] * 100, 2)
                tda_gainloss = np.round(tda_market_values[idx] - tda_costbasis, 2)
                tda_gainloss_pct = np.round(tda_gainloss / tda_costbasis * 100, 2)
            elif tda_short_shares[idx] > 0:
                if ticker_dict[tickers[i]]["option_symbol"] == tickers[i]:
                    tda_costbasis = np.round(tda_average_prices[idx] * tda_short_shares[idx], 2)
                else:
                    tda_costbasis = np.round(tda_average_prices[idx] * tda_short_shares[idx] * 100, 2)
                tda_gainloss = np.round(abs(tda_costbasis) - abs(tda_market_values[idx]), 2)
                tda_gainloss_pct = np.round(tda_gainloss / tda_costbasis * 100, 2)
            else:
                tda_costbasis = 0
                tda_gainloss = 0
                tda_gainloss_pct = 0
        else:
            tda_costbasis = 0
            tda_gainloss = 0
            tda_gainloss_pct = 0

        ticker_dict[tickers[i]]["gainloss"] = tda_gainloss
        ticker_dict[tickers[i]]["costbasis"] = tda_costbasis
        ticker_dict[tickers[i]]["gainloss_pct"] = tda_gainloss_pct

        # Adjust costbasis based on trigger trails

        trigger_trail_type = ticker_dict[tickers[i]]["trigger_trail_type"]
        trigger_trail = ticker_dict[tickers[i]]["trigger_trail"]
        trigger_trail_pct = ticker_dict[tickers[i]]["trigger_trail_pct"]
        triggered = ticker_dict[tickers[i]]["triggered"]
        trigger_trail_trail_pct = ticker_dict[tickers[i]]["trigger_trail_trail_pct"]
        if trigger_trail_type == "Fixed $":
            if (tda_gainloss > trigger_trail or triggered == True) and tickers[i] in tda_symbols_held:
                tda_costbasis = np.round(ticker_dict[tickers[i]]["costbasis"] + trigger_trail, 2)
                if triggered != True:
                    print(f"Trailing stop loss of {trigger_trail_trail_pct}% triggered on ticker {tickers[i]} due to \
                            gainloss {tda_gainloss} > trigger_trail {trigger_trail}")
                    triggered = True
                    ticker_dict[tickers[i]]["triggered"] = True
                    entry["triggered"] = True
                    # entry["costbasis"] = tda_costbasis
                    # entry["stoploss_type"] = "Trailing %"
                    # entry["trail_pct"] = trigger_trail_trail_pct
                ticker_dict[tickers[i]]["costbasis"] = tda_costbasis
                ticker_dict[tickers[i]]["stoploss_type"] = "Trailing %"
                ticker_dict[tickers[i]]["trail_pct"] = trigger_trail_trail_pct
            elif tickers[i] not in tda_symbols_held:
                if triggered == True:
                    print(f"Ticker {tickers[i]} not found, triggered set to False")
                    triggered = False
                    ticker_dict[tickers[i]]["triggered"] = False
                    entry["triggered"] = False
        elif trigger_trail_type == "Fixed %":
            if (tda_gainloss_pct > trigger_trail_pct or triggered == True) and tickers[i] in tda_symbols_held:
                tda_costbasis = np.round(ticker_dict[tickers[i]]["costbasis"] * (1 + trigger_trail_pct / 100), 2)
                if triggered != True:
                    print(f"Trailing stop loss of {trigger_trail_trail_pct}% triggered on ticker {tickers[i]} due to \
                            gainloss of {tda_gainloss_pct}% > {trigger_trail_pct}%")
                    triggered = True
                    ticker_dict[tickers[i]]["triggered"] = True
                    entry["triggered"] = True
                    # entry["costbasis"] = tda_costbasis
                    # entry["stoploss_type"] = "Trailing %"
                    # entry["trail_pct"] = trigger_trail_trail_pct
                ticker_dict[tickers[i]]["costbasis"] = tda_costbasis
                ticker_dict[tickers[i]]["stoploss_type"] = "Trailing %"
                ticker_dict[tickers[i]]["trail_pct"] = trigger_trail_trail_pct
            elif tickers[i] not in tda_symbols_held:
                if triggered == True:
                    print(f"Ticker {tickers[i]} not found, triggered set to False")
                    triggered = False
                    ticker_dict[tickers[i]]["triggered"] = False
                    entry["triggered"] = False
        elif trigger_trail_type == "None":
            entry = entry
        else:
            print("Unrecognized trigger_trail_type")

        # Activate checkpoints based on gainloss

        for j in range(cp):
            if tickers[i] in tda_symbols_held and ticker_dict[tickers[i]][f"checkpoint_on{j}"]:
                if ticker_dict[tickers[i]]["gainloss"] > ticker_dict[tickers[i]][f"activation_value{j}"] \
                and ticker_dict[tickers[i]][f"activated{j}"] != True:
                    ticker_dict[tickers[i]][f"activated{j}"] = True
                    values1[f"activated{j}"] = True
            else:
                if ticker_dict[tickers[i]][f"activated{j}"] != False:
                    ticker_dict[tickers[i]][f"activated{j}"] = False
                    values1[f"activated{j}"] = False

        # Update max and min so drawdown can be tracked and trailing stops can execute

        if tickers[i] in tda_symbols_held:
            maxi = max(ticker_dict[tickers[i]]["max"], ticker_dict[tickers[i]]["market_value"], ticker_dict[tickers[i]]["costbasis"])
            mini = min(ticker_dict[tickers[i]]["market_value"], ticker_dict[tickers[i]]["costbasis"])
            if ticker_dict[tickers[i]]["min"] != 0:
                mini = min(ticker_dict[tickers[i]]["min"], mini)
        else:
            maxi = 0
            mini = 0
        if maxi != ticker_dict[tickers[i]]["max"]:
            entry["max"] = maxi
            ticker_dict[tickers[i]]["max"] = maxi
        if mini != ticker_dict[tickers[i]]["min"]:
            entry["min"] = mini
            ticker_dict[tickers[i]]["min"] = mini
        
        # Get recent orders from TDA API, so we can determine recent tickers and implement a pause period on them

        pause_unit = ticker_dict[tickers[i]]["pause_unit"]
        pause_time = ticker_dict[tickers[i]]["pause_time"]
        if "sec" in pause_unit.lower():
            pause_time = pause_time
        elif "min" in pause_unit.lower():
            pause_time = np.round(pause_time * 60, 1)
        elif "hour" in pause_unit.lower():
            pause_time = np.round(pause_time * 60 * 60, 1)
        else:
            pause_time = pause_time
        recent_orders = [order for order in tda_orders if (time_now - pd.to_datetime(order['enteredTime'])).seconds < pause_time]
        recent_opt_tickers = [order['orderLegCollection'][0]['instrument']['symbol'] for order in recent_orders]
        recent_tickers1 = [ticker.split("_")[0] for ticker in recent_opt_tickers]
        if tickers[i] in recent_tickers1:
            recent_tickers.append(tickers[i])

        # Exit order

        ticker_dict[tickers[i]]["condition1"] = bool(condition1)
        condition2x = tickers[i] in tda_symbols_held
        ticker_dict[tickers[i]]["condition2x"] = bool(condition2x)
        order_type = ticker_dict[tickers[i]]["order_type"]
        indicator_exit = ticker_dict[tickers[i]]["indicator_exit"]
        mid = ticker_dict[tickers[i]]["mid"]
        if condition2x:
            trail_pct = ticker_dict[tickers[i]]["trail_pct"]
            stoploss_pct = ticker_dict[tickers[i]]["stoploss_pct"]
            stoploss = ticker_dict[tickers[i]]["stoploss"]
            gainloss_pct = ticker_dict[tickers[i]]["gainloss_pct"]
            gainloss = ticker_dict[tickers[i]]["gainloss"]
            market_value = ticker_dict[tickers[i]]["market_value"]
            maxi = ticker_dict[tickers[i]]["max"]
            mini = ticker_dict[tickers[i]]["min"]
            drawdown_from_high = maxi - market_value
            drawdown_from_low = market_value - mini
            try:
                drawdown_pct_high = np.round((drawdown_from_high / maxi) * 100, 2)
                drawdown_pct_low = np.round((drawdown_from_low / mini) * 100, 2)
            except ZeroDivisionError:
                drawdown_pct_high = 0
                drawdown_pct_low = 0
            if ticker_dict[tickers[i]]["stoploss_type"] == "Trailing %":
                condition3x = abs(drawdown_pct_high) > trail_pct
            elif ticker_dict[tickers[i]]["stoploss_type"] == "Fixed %":
                condition3x = abs(gainloss_pct) > stoploss_pct and gainloss_pct < 0
            elif ticker_dict[tickers[i]]["stoploss_type"] == "Fixed $":
                condition3x = abs(gainloss) > stoploss and gainloss < 0
            elif ticker_dict[tickers[i]]["stoploss_type"] == "None":
                condition3x = False
            else:
                print("Unrecognized stoploss_type")
            ticker_dict[tickers[i]]["condition3x"] = bool(condition3x)
            take_profit = ticker_dict[tickers[i]]["take_profit"]
            take_profit_pct = ticker_dict[tickers[i]]["take_profit_pct"]
            if ticker_dict[tickers[i]]["take_profit_type"] == "Fixed %":
                condition4x = gainloss_pct > take_profit_pct
            elif ticker_dict[tickers[i]]["take_profit_type"] == "Fixed $":
                condition4x = gainloss > take_profit
            elif ticker_dict[tickers[i]]["take_profit_type"] == "None":
                condition4x = False
            else:
                print("Unrecognized take_profit_type")
            ticker_dict[tickers[i]]["condition4x"] = bool(condition4x)
            exit_symbol = ticker_dict[tickers[i]]["option_symbol"]
            exit_quantity = ticker_dict[tickers[i]]["quantity"]
            stoploss_exit = condition1 and condition2x and condition3x and not condition4x
            ticker_dict[tickers[i]]["stoploss_exit"] = bool(stoploss_exit)
            profit_exit = condition1 and condition2x and not condition3x and condition4x
            ticker_dict[tickers[i]]["profit_exit"] = bool(profit_exit)
            condition5x = "C" in exit_symbol.split("_")[1] if "_" in exit_symbol else False
            ticker_dict[tickers[i]]["condition5x"] = bool(condition5x)
            condition6x = "P" in exit_symbol.split("_")[1] if "_" in exit_symbol else False
            ticker_dict[tickers[i]]["condition6x"] = bool(condition6x)
            indicator_bools = []
            for indicator in indicator_options:
                if indicator in indicator_exit:
                    if indicator == "Candles":
                        indicator_bools.append(ticker_dict[tickers[i]]["bullish_candle1"])
                    elif indicator == "HMA":
                        indicator_bools.append(ticker_dict[tickers[i]]["bullish_hma1"])
                    elif indicator == "EMA":
                        indicator_bools.append(ticker_dict[tickers[i]]["bullish_ema1"])
            if indicator_bools == []:
                print("Error: No indicators")
                condition7x = None
            elif indicator_bools == [False] * len(indicator_bools): # Everything is bearish
                condition7x = False
            elif indicator_bools == [True] * len(indicator_bools): # Everything is bullish
                condition7x = True
            else: 
                condition7x = None
            ticker_dict[tickers[i]]["condition7x"] = bool(condition7x)
            confirm_time = ticker_dict[tickers[i]]["confirm_time"]
            confirm_unit = ticker_dict[tickers[i]]["confirm_unit"]
            if "sec" in confirm_unit.lower():
                confirm_time = confirm_time
            elif "min" in confirm_unit.lower():
                confirm_time = np.round(confirm_time * 60, 1)
            elif "hour" in confirm_unit.lower():
                confirm_time = np.round(confirm_time * 60 * 60, 1)
            else:
                confirm_time = confirm_time
            curr_time = dt.datetime.now(tz=utc)
            old_time = pd.Timestamp(ticker_db_dict[tickers[i]]['time_in_candle'], tz=utc)
            if confirm_time in [0, None]:
                condition8x = True
            elif old_time == 0:
                condition8x = False
                print(f"Starting timer on {tickers[i]}")
            else:
                condition8x = curr_time > old_time + dt.timedelta(seconds=confirm_time)
            ticker_dict[tickers[i]]["condition8x"] = bool(condition8x)
            if condition8x:
                ticker_dict[tickers[i]]["time_in_candle"] = 0
                entry["time_in_candle"] = 0
            else:
                ticker_dict[tickers[i]]["time_in_candle"] = curr_time
                entry["time_in_candle"] = curr_time
            # if not ticker_dict[tickers[i]]["doji_candle1"]:
            call_exit = condition1 and condition2x and condition5x and not condition6x and condition7x==False and condition8x
            put_exit = condition1 and condition2x and not condition5x and condition6x and condition7x==True and condition8x
            # else:
            #     call_exit = False
            #     put_exit = False
            ticker_dict[tickers[i]]["call_exit"] = bool(call_exit)
            ticker_dict[tickers[i]]["put_exit"] = bool(put_exit)
            any_exit = stoploss_exit or profit_exit or call_exit or put_exit
            ticker_dict[tickers[i]]["any_exit"] = bool(any_exit)
            if any_exit:
                exit_order = tda_submit_order("SELL_TO_CLOSE", exit_quantity, exit_symbol, orderType=order_type, limit_price=mid)
                print(json.dumps(ticker_dict, indent=4))
                entry["triggered"] = False
                exit_log = f"Closing out {exit_quantity} contracts of {exit_symbol} due to"
                if stoploss_exit:
                    if ticker_dict[tickers[i]]["stoploss_type"] == "Trailing %":
                        exit_log = exit_log + f" drawdown % {drawdown_pct_high} > trail % {trail_pct}, max = {maxi}, market_value = {market_value}"
                    elif ticker_dict[tickers[i]]["stoploss_type"] == "Fixed %":
                        exit_log = exit_log + f" gainloss % {gainloss_pct} > stoploss % {stoploss_pct}"
                    elif ticker_dict[tickers[i]]["stoploss_type"] == "Fixed $":
                        exit_log = exit_log + f" gainloss {gainloss} > stoploss {stoploss}"
                elif profit_exit:
                    if ticker_dict[tickers[i]]["take_profit_type"] == "Fixed %":
                        exit_log = exit_log + f" gainloss % {gainloss_pct} > take_profit % {take_profit_pct}"
                    elif ticker_dict[tickers[i]]["take_profit_type"] == "Fixed $":
                        exit_log = exit_log + f" gainloss {gainloss} > take_profit {take_profit}"
                elif call_exit:
                    tda_symbols_held.remove(tickers[i])
                    exit_log = exit_log + f" indicators {indicator_exit} being bearish while holding call"
                elif put_exit:
                    tda_symbols_held.remove(tickers[i])
                    exit_log = exit_log + f" indicators {indicator_exit} being bullish candle while holding put"
                print(exit_log)

        # Checkpoint exits

        gainloss = ticker_dict[tickers[i]]["gainloss"]
        gainloss_pct = ticker_dict[tickers[i]]["gainloss_pct"]
        exit_symbol = ticker_dict[tickers[i]]["option_symbol"]
        qty = ticker_dict[tickers[i]]["quantity"]
        if tickers[i] in tda_symbols_held:
            for j in range(cp):
                activated = ticker_dict[tickers[i]][f"activated{j}"]
                exit_value = ticker_dict[tickers[i]][f"exit_value{j}"]
                gain_type = ticker_dict[tickers[i]][f"gain_type{j}"]
                gain_amount = ticker_dict[tickers[i]][f"gain_amount{j}"]
                gain_pct = ticker_dict[tickers[i]][f"gain_pct{j}"]
                qty2 = int(ticker_dict[tickers[i]][f"contract_nbr{j}"])
                if activated and exit_value > gainloss:
                    exit_order = tda_submit_order("SELL_TO_CLOSE", qty, exit_symbol, orderType=order_type, limit_price=mid)
                    print(f"{qty} contracts of {tickers[i]} closed out due to checkpoint: \
                            exit_value {exit_value} > gainloss {gainloss}")
                    print(json.dumps(ticker_dict, indent=4))
                    break
                if gain_type == "Fixed $":
                    if gain_amount > gainloss:
                        exit_order = tda_submit_order("SELL_TO_CLOSE", qty2, exit_symbol, orderType=order_type, limit_price=mid)
                        print(f"{qty2} contracts of {tickers[i]} closed out due to checkpoint: \
                                gain_amount {gain_amount} > gainloss {gainloss}")
                        print(json.dumps(ticker_dict, indent=4))
                elif gain_type == "Fixed %":
                    if gain_pct > gainloss_pct:
                        exit_order = tda_submit_order("SELL_TO_CLOSE", qty2, exit_symbol, orderType=order_type, limit_price=mid)
                        print(f"{qty2} contracts of {tickers[i]} closed out due to checkpoint: \
                                gain_pct {gain_pct} > gainloss_pct {gainloss_pct}")
                        print(json.dumps(ticker_dict, indent=4))
                elif gain_type == "None":
                    exit_order = ""
                else:
                    print("Unrecognized gain_type")     

        # Entry order

        order_type = ticker_dict[tickers[i]]["order_type"]
        option_type = ticker_dict[tickers[i]]["option_type"]
        indicator_entry = ticker_dict[tickers[i]]["indicator_entry"]
        mid = ticker_dict[tickers[i]]["mid"]
        if ticker_dict[tickers[i]]["use_close"]:
            bullish_candle = ticker_dict[tickers[i]]["bullish_candle2"]
            bullish_hma = ticker_dict[tickers[i]]["bullish_hma2"]
            bullish_ema = ticker_dict[tickers[i]]["bullish_ema2"]
            candle_wick_bottom = ticker_dict[tickers[i]]["candle_wick_bottom2"]
            candle_wick_top = ticker_dict[tickers[i]]["candle_wick_top2"]
            candle_body = ticker_dict[tickers[i]]["candle_body2"]
        else:
            bullish_candle = ticker_dict[tickers[i]]["bullish_candle1"]
            bullish_hma = ticker_dict[tickers[i]]["bullish_hma1"]
            bullish_ema = ticker_dict[tickers[i]]["bullish_ema1"]
            candle_wick_bottom = ticker_dict[tickers[i]]["candle_wick_bottom1"]
            candle_wick_top = ticker_dict[tickers[i]]["candle_wick_top1"]
            candle_body = ticker_dict[tickers[i]]["candle_body1"]
        condition2e = tickers[i] not in tda_symbols_held
        ticker_dict[tickers[i]]["condition2e"] = bool(condition2e)
        condition3e = bullish_candle
        ticker_dict[tickers[i]]["condition3e"] = bool(condition3e)
        if ticker_dict[tickers[i]]["wick_requirement"] == "Any wick okay":
            condition4e = True
        elif ticker_dict[tickers[i]]["wick_requirement"] == "Can't have wick":
            if condition3e==True:
                if candle_wick_bottom > 0:
                    condition4e = False
                else:
                    condition4e = True
            elif condition3e==False:
                if candle_wick_top > 0:
                    condition4e = False
                else:
                    condition4e = True
        elif ticker_dict[tickers[i]]["wick_requirement"] == "Smaller wick":
            if condition3e==True:
                if candle_wick_bottom > candle_wick_top:
                    condition4e = False
                else:
                    condition4e = True
            elif condition3e==False:
                if candle_wick_top > candle_wick_bottom:
                    condition4e = False
                else:
                    condition4e = True
        elif ticker_dict[tickers[i]]["wick_requirement"] == "1/3 the size of candle body or smaller":
            if condition3e==True:
                if candle_wick_bottom > candle_body * (1/3):
                    condition4e = False
                else:
                    condition4e = True
            elif condition3e==False:
                if candle_wick_top > candle_body * (1/3):
                    condition4e = False
                else:
                    condition4e = True
        else:
            condition4e = True
            print("Unrecognized wick requirement")
        ticker_dict[tickers[i]]["condition4e"] = bool(condition4e)
        indicator_bools = []
        for indicator in indicator_options:
            if indicator in indicator_entry:
                if indicator == "Candles":
                    indicator_bools.append(bullish_candle)
                elif indicator == "HMA":
                    indicator_bools.append(bullish_hma)
                elif indicator == "EMA":
                    indicator_bools.append(bullish_ema)
        if indicator_bools == []:
            print("Error: No indicators")
            condition5e = None
        elif indicator_bools == [False] * len(indicator_bools): # Everything is bearish
            condition5e = False
        elif indicator_bools == [True] * len(indicator_bools): # Everything is bullish
            condition5e = True
        else: 
            condition5e = None
        ticker_dict[tickers[i]]["condition5e"] = bool(condition5e)
        condition6e = tickers[i] not in recent_tickers
        ticker_dict[tickers[i]]["condition6e"] = bool(condition6e)
        bullish_entry = condition1 and condition2e and condition3e==True and condition4e and condition5e==True and condition6e and "calls" in option_type.lower()
        bearish_entry = condition1 and condition2e and condition3e==False and condition4e and condition5e==False and condition6e and "puts" in option_type.lower()
        ticker_dict[tickers[i]]["bullish_entry"] = bool(bullish_entry)
        ticker_dict[tickers[i]]["bearish_entry"] = bool(bearish_entry)
        contracts = ticker_dict[tickers[i]]["contracts"]
        if bullish_entry:
            entry_symbol = ticker_dict[tickers[i]]["chain"]["call"]
            # entry_symbol = entry_symbol.split("_")[0]
            entry_order = tda_submit_order("BUY_TO_OPEN", contracts, entry_symbol, orderType=order_type, limit_price=mid)
            print(f"Bullish entry: Buying {contracts} contracts of {entry_symbol}")
            print(json.dumps(ticker_dict, indent=4))
        if bearish_entry:
            entry_symbol = ticker_dict[tickers[i]]["chain"]["put"]
            # entry_symbol = entry_symbol.split("_")[0]
            entry_order = tda_submit_order("BUY_TO_OPEN", contracts, entry_symbol, orderType=order_type, limit_price=mid)
            print(f"Bearish entry: Buying {contracts} contracts of {entry_symbol}")
            print(json.dumps(ticker_dict, indent=4))

        # Update dictionary

        ticker_db_dict[tickers[i]] = entry
        checkpoint_db_dict[tickers[i]] = values1

        # End strategy() function

    # Multi-thread and update database

    threads = []       
    for i in range(len(tickers)): 
        tickers_db.put(ticker_db_dict[tickers[i]])
        checkpoints_db.put(checkpoint_db_dict[tickers[i]])                                                   
        t = threading.Thread(target=strategy, args=(tickers,i)) 
        threads.append(t)
        threads[-1].start()
        threads[-1].join()                                
    # for t in threads:
    #     t.join()                                                                          

    # Print log

    now = dt.datetime.now(tz=local_timezone).strftime("%Y-%m-%d %X")
    time_end = time.time()
    time_total = np.round(time_end - time_start, 2)
    global log_count
    log_count += 1
    if log_count == 1 or log_count % 50 == 0:
        print_log = [
            ["Time", f" = {now}"],
            ["Market open", f" = {market_open}"],
            ["Recent tickers", f" = {recent_tickers}"],
            ["Execution Speed", f" = {time_total} seconds"],
            ["---------------", "---------------"]
        ]
        try:
            ticker_dict_json = json.dumps(ticker_dict, indent=4)
            print(ticker_dict_json)
        except Exception as e:
            print(e)
            print(ticker_dict)
    else:
        print_log = [
            ["Execution Speed", f" = {time_total} seconds"],
        ]

    for item_list in print_log:
        for i in item_list:
            print(i.ljust(20), end='')
        print()

    # Since the bot made it to the end of the script successfully, reset error streak to 0

    error_streak = 0

    # End run() function

# Run the entire script in a continuous loop

run()
while True:
    if error_streak < 5:
        try:
            run()
        except Exception as e:
            print(e)
            pass
    else:
        run()
    time.sleep(0.01)