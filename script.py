# This is the main file that executes the automated trades. Everything else is a supporting document.

# Import required packages

import datetime as dt
from db import *
import math
import numpy as np
import pandas as pd
import ta
from tda import *
#import threading
import time

# Global variables

log_count = 0
error_streak = 0
bot_on_last = False

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

    # Error counter

    global error_streak
    error_streak += 1

    # Extract values from Deta and create master dictionary

    tickers_db = deta.Base("tickers_db")
    tickers_info = tickers_db.fetch().items
    tickers = [item["key"].upper() for item in tickers_info]
    ticker_dict = {}
    for i in range(len(tickers)):
        ticker_dict[tickers[i]] = tickers_info[i]
        ticker_dict[tickers[i]]["option_symbol"] = tickers[i]
        ticker_dict[tickers[i]]["average_price"] = 0
        ticker_dict[tickers[i]]["market_value"] = 0
        ticker_dict[tickers[i]]["long_shares"] = 0
        ticker_dict[tickers[i]]["short_shares"] = 0
        ticker_dict[tickers[i]]["quantity"] = 0
        ticker_dict[tickers[i]]["option_last"] = 0

    checkpoints_db = deta.Base("checkpoints_db")
    checkpoints_info = checkpoints_db.fetch().items
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

    # Examine watchlist

    for ticker in tickers:

        # Get quotes for underlying

        quote = get_quote_tda(ticker)
        last = np.round(float(quote[ticker]['lastPrice']), 2)
        bid = np.round(float(quote[ticker]['bidPrice']), 2)
        ask = np.round(float(quote[ticker]['lastPrice']), 2)
        mid = np.round((bid + ask) / 2, 2)
        ticker_dict[ticker]["last"] = last
        ticker_dict[ticker]["bid"] = bid
        ticker_dict[ticker]["ask"] = ask
        ticker_dict[ticker]["mid"] = mid

        # Fetch ticker data settings from Deta

        periodType = ticker_dict[ticker]['period_type']
        period = int(ticker_dict[ticker]['period'])
        frequencyType = ticker_dict[ticker]['frequency_type']
        frequency = int(ticker_dict[ticker]['frequency'])
        extended_hours = ticker_dict[ticker]['extended_hours']

        # Fetch data from TDA API

        data = get_data_tda(ticker=ticker, periodType=periodType, period=period, frequencyType=frequencyType, frequency=frequency, extended_hours=extended_hours)
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
        i = 1
        while i < len(ha_closes):
            ha_opens[i] = 0.5 * (ha_opens[i-1] + ha_closes[i-1])
            ha_highs[i] = max(tda_highs[i], ha_opens[i], tda_closes[i])
            ha_lows[i] = min(tda_lows[i], ha_opens[i], tda_closes[i])
            ha_closes[i] = 0.25 * (ha_opens[i] + tda_highs[i] + tda_lows[i] + tda_closes[i])
            i += 1
        if ticker_dict[ticker]["candle_type"] == "Heikin Ashi":
            tda_opens = ha_opens
            tda_highs = ha_highs
            tda_lows = ha_lows
            tda_closes = ha_closes

        # Determine if candles and wicks are bullish or bearish

        if ticker_dict[ticker]["use_close"]:
            last_open = tda_opens[len(tda_opens)-2]
            last_high = tda_highs[len(tda_highs)-2]
            last_low = tda_lows[len(tda_lows)-2]
            last_close = tda_closes[len(tda_closes)-2]
        else:
            last_open = tda_opens[len(tda_opens)-1]
            last_high = tda_highs[len(tda_highs)-1]
            last_low = tda_lows[len(tda_lows)-1]
            last_close = tda_closes[len(tda_closes)-1]
        ticker_dict[ticker]["last_open"] = last_open
        ticker_dict[ticker]["last_high"] = last_high
        ticker_dict[ticker]["last_low"] = last_low
        ticker_dict[ticker]["last_close"] = last_close
        if last_close > last_open:
            bullish_candle = True
        elif last_close < last_open:
            bullish_candle = False
        else:
            bullish_candle = None
        ticker_dict[ticker]["bullish_candle"] = bullish_candle
        candle_body = abs(last_close - last_open)
        candle_wick_top = last_high - max(last_close, last_open)
        candle_wick_bottom = min(last_close, last_high) - last_low
        if candle_wick_top + candle_wick_bottom > candle_body:
            doji_candle = True
        else:
            doji_candle = False
        ticker_dict[ticker]["candle_body"] = candle_body
        ticker_dict[ticker]["candle_wick_top"] = candle_wick_top
        ticker_dict[ticker]["candle_wick_bottom"] = candle_wick_bottom
        ticker_dict[ticker]["doji_candle"] = doji_candle

        # Create dataframe and fill with market data

        df = pd.DataFrame()
        df['open'] = tda_opens
        df['high'] = tda_highs
        df['low'] = tda_lows
        df['close'] = tda_closes

        # Calculate technical indicators

        ema_window = int(ticker_dict[ticker]['ema_length'])
        emas_all = np.round(ta.trend.ema_indicator(pd.to_numeric(df['close']), window=ema_window), 2)
        ema = emas_all[len(emas_all)-1]
        ticker_dict[ticker]["ema"] = ema

        hma_window = int(ticker_dict[ticker]['hma_length'])
        hma1 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=int(hma_window/2))
        hma2 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=hma_window)
        hma_raw = (2 * hma1) - hma2
        hmas_all = np.round(ta.trend.wma_indicator(hma_raw, window=math.floor(math.sqrt(hma_window))), 2)
        hma = hmas_all[len(hmas_all)-1]
        ticker_dict[ticker]["hma"] = hma

        # Determine if moving averages are bullish or bearish

        if ticker_dict[ticker]["use_close"]:
            last_ema = emas_all[len(emas_all)-2]
            last_ema1 = emas_all[len(emas_all)-3]
            last_hma = hmas_all[len(hmas_all)-2]
            last_hma1 = hmas_all[len(hmas_all)-3]
        else:
            last_ema = emas_all[len(emas_all)-1]
            last_ema1 = emas_all[len(emas_all)-2]
            last_hma = hmas_all[len(hmas_all)-1]
            last_hma1 = hmas_all[len(hmas_all)-2]
        ticker_dict[ticker]["last_ema"] = last_ema
        ticker_dict[ticker]["last_ema1"] = last_ema1
        ticker_dict[ticker]["last_hma"] = last_hma
        ticker_dict[ticker]["last_hma1"] = last_hma1
        if last_ema > last_ema1:
            bullish_ema = True
        elif last_ema < last_ema1:
            bullish_ema = False
        else:
            bullish_ema = None
        ticker_dict[ticker]["bullish_ema"] = bullish_ema
        if last_hma > last_hma1:
            bullish_hma = True
        elif last_hma < last_hma1:
            bullish_hma = False
        else:
            bullish_hma = None
        ticker_dict[ticker]["bullish_hma"] = bullish_hma

        # Get the relevant option symbol bot will purchase if entry criteria are met

        chain = get_chain_tda(ticker)
        ticker_dict[ticker]["chain"] = chain

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

    # Calculate costbasis and gainloss from quotes and average prices

    for i in range(len(tickers)):
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

    for i in range(len(tickers)):
        trigger_trail_type = ticker_dict[tickers[i]]["trigger_trail_type"]
        trigger_trail = ticker_dict[tickers[i]]["trigger_trail"]
        trigger_trail_pct = ticker_dict[tickers[i]]["trigger_trail_pct"]
        triggered = ticker_dict[tickers[i]]["triggered"]
        trigger_trail_trail_pct = ticker_dict[tickers[i]]["trigger_trail_trail_pct"]
        if trigger_trail_type == "Fixed $":
            if tda_gainloss > trigger_trail or triggered == True:
                entry = tickers_db.get(tickers[i])
                entry["triggered"] = True
                # entry["costbasis"] = np.round(ticker_dict[tickers[i]]["costbasis"] - trigger_trails[i], 2)
                # entry["stoploss_type"] = "Trailing %"
                # entry["trail_pct"] = trigger_trail_trail_pcts[i]
                tda_costbasis = np.round(ticker_dict[tickers[i]]["costbasis"] + trigger_trail, 2)
                ticker_dict[tickers[i]]["triggered"] = True
                ticker_dict[tickers[i]]["costbasis"] = np.round(ticker_dict[tickers[i]]["costbasis"] + trigger_trail, 2)
                ticker_dict[tickers[i]]["stoploss_type"] = "Trailing %"
                ticker_dict[tickers[i]]["trail_pct"] = trigger_trail_trail_pct
                tickers_db.put(entry)
                print(f"Trailing stop loss of {trigger_trail_trail_pct}% triggered due to \
                        gainloss {tda_gainloss} > trigger_trail {trigger_trail}")
        elif trigger_trail_type == "Fixed %":
            if tda_gainloss_pct > trigger_trail_pct or triggered == True:
                entry = tickers_db.get(tickers[i])
                entry["triggered"] = True
                # entry["costbasis"] = np.round(ticker_dict[tickers[i]]["costbasis"] * (1 + trigger_trail_pct / 100), 2)
                # entry["stoploss_type"] = "Trailing %"
                # entry["trail_pct"] = trigger_trail_trail_pct
                tda_costbasis = np.round(ticker_dict[tickers[i]]["costbasis"] * (1 + trigger_trail_pct / 100), 2)
                ticker_dict[tickers[i]]["triggered"] = True
                ticker_dict[tickers[i]]["costbasis"] = np.round(ticker_dict[tickers[i]]["costbasis"] * (1 + trigger_trail_pct / 100), 2)
                ticker_dict[tickers[i]]["stoploss_type"] = "Trailing %"
                ticker_dict[tickers[i]]["trail_pct"] = trigger_trail_trail_pct
                tickers_db.put(entry)
                print(f"Trailing stop loss of {trigger_trail_trail_pct}% triggered due to \
                        gainloss of {tda_gainloss_pct}% > {trigger_trail_pct}%")
        elif trigger_trail_type == "None":
            entry = ""

    # Activate checkpoints based on gainloss

    cp = 10
    for i in range(len(tickers)):
        values1 = checkpoints_db.get(tickers[i])
        for j in range(cp):
            if tickers[i] in tda_symbols_held and ticker_dict[tickers[i]]["checkpoint_on"]:
                if ticker_dict[tickers[i]]["gainloss"] > ticker_dict[tickers[i]][f"activation_value{j}"] \
                and ticker_dict[tickers[i]][f"activated{j}"] != True:
                    ticker_dict[tickers[i]][f"activated{j}"] = True
                    values1[f"activated{j}"] = True
            else:
                if ticker_dict[tickers[i]][f"activated{j}"] != False:
                    ticker_dict[tickers[i]][f"activated{j}"] = False
                    values1[f"activated{j}"] = False
        checkpoints_db.put(values1)

    # Update max and min so drawdown can be tracked and trailing stops can execute

    for i in range(len(tickers)):
        if tickers[i] in tda_symbols_held:
            maxi = max(ticker_dict[tickers[i]]["max"], ticker_dict[tickers[i]]["market_value"], ticker_dict[tickers[i]]["costbasis"])
            mini = min(ticker_dict[tickers[i]]["market_value"], ticker_dict[tickers[i]]["costbasis"])
            if ticker_dict[tickers[i]]["min"] != 0:
                mini = min(ticker_dict[tickers[i]]["min"], mini)
        else:
            maxi = 0
            mini = 0
        if maxi != ticker_dict[tickers[i]]["max"]:
            entry = tickers_db.get(tickers[i])
            entry["max"] = maxi
            ticker_dict[tickers[i]]["max"] = maxi
            tickers_db.put(entry)
        if mini != ticker_dict[tickers[i]]["min"]:
            entry = tickers_db.get(tickers[i])
            entry["min"] = mini
            ticker_dict[tickers[i]]["min"] = mini
            tickers_db.put(entry)
        
    # Get recent orders from TDA API, so we can determine recent tickers and implement a pause period on them

    tda_orders = get_orders2_tda()
    time_now = dt.datetime.now(utc)
    recent_tickers = []
    for i in range(len(tickers)):
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
    
    # Calculate time
    
    current_time = dt.datetime.now(tz=local_timezone)
    minutes_until_close = np.round((closing_time - current_time).total_seconds() / 60, 2)
    # condition1 = market_open
    condition1 = 0 < minutes_until_close < 450

    # Exit order

    for i in range(len(tickers)):
        condition2 = tickers[i] in tda_symbols_held
        order_type = ticker_dict[tickers[i]]["order_type"]
        mid = ticker_dict[tickers[i]]["mid"]
        if condition2:
            trail_pct = ticker_dict[tickers[i]]["trail_pct"]
            stoploss_pct = ticker_dict[tickers[i]]["stoploss_pct"]
            stoploss = ticker_dict[tickers[i]]["stoploss"]
            gainloss_pct = ticker_dict[tickers[i]]["gainloss_pct"]
            gainloss = ticker_dict[tickers[i]]["gainloss"]
            drawdown_from_high = ticker_dict[tickers[i]]["max"] - ticker_dict[tickers[i]]["market_value"]
            drawdown_from_low = ticker_dict[tickers[i]]["market_value"] - ticker_dict[tickers[i]]["min"]
            try:
                drawdown_pct_high = np.round((drawdown_from_high / ticker_dict[tickers[i]]["max"] - 1) * 100, 2)
                drawdown_pct_low = np.round((drawdown_from_low / ticker_dict[tickers[i]]["min"] - 1) * 100, 2)
            except ZeroDivisionError:
                drawdown_pct_high = 0
                drawdown_pct_low = 0
            if ticker_dict[tickers[i]]["stoploss_type"] == "Trailing %":
                condition3 = abs(drawdown_pct_high) > trail_pct
            elif ticker_dict[tickers[i]]["stoploss_type"] == "Fixed %":
                condition3 = abs(gainloss_pct) > stoploss_pct and gainloss_pct < 0
            elif ticker_dict[tickers[i]]["stoploss_type"] == "Fixed $":
                condition3 = abs(gainloss) > stoploss and gainloss < 0
            elif ticker_dict[tickers[i]]["stoploss_type"] == "None":
                condition3 = False
            take_profit = ticker_dict[tickers[i]]["take_profit"]
            take_profit_pct = ticker_dict[tickers[i]]["take_profit_pct"]
            if ticker_dict[tickers[i]]["take_profit_type"] == "Fixed %":
                condition4 = gainloss_pct > take_profit_pct
            elif ticker_dict[tickers[i]]["take_profit_type"] == "Fixed $":
                condition4 = gainloss > take_profit
            elif ticker_dict[tickers[i]]["take_profit_type"] == "None":
                condition4 = False
            exit_symbol = ticker_dict[tickers[i]]["option_symbol"]
            exit_quantity = ticker_dict[tickers[i]]["quantity"]
            stoploss_exit = condition1 and condition2 and condition3 and not condition4
            profit_exit = condition1 and condition2 and not condition3 and condition4
            condition5 = "C" in exit_symbol.split("_")[1] if "_" in exit_symbol else False
            condition6 = "P" in exit_symbol.split("_")[1] if "_" in exit_symbol else False
            condition7 = ticker_dict[tickers[i]]["bullish_candle"]
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
            old_time = pd.Timestamp(tickers_db.get(tickers[i])['time_in_candle'], tz=utc)
            if confirm_time in [0, None]:
                condition8 = True
            elif old_time == 0:
                condition8 = False
                print(f"Starting timer on {tickers[i]}")
            else:
                condition8 = curr_time > old_time + dt.timedelta(seconds=confirm_time)
            if condition8:
                ticker_dict[tickers[i]]["time_in_candle"] = 0
                entry = tickers_db.get(tickers[i])
                entry["time_in_candle"] = 0
                tickers_db.put(entry)
            else:
                ticker_dict[tickers[i]]["time_in_candle"] = curr_time
                entry = tickers_db.get(tickers[i])
                entry["time_in_candle"] = curr_time
                tickers_db.put(entry)
            if not ticker_dict[tickers[i]]["doji_candle"]:
                call_exit = condition1 and condition2 and condition5 and not condition6 and condition7==False and condition8
                put_exit = condition1 and condition2 and not condition5 and condition6 and condition7==True and condition8
            else:
                call_exit = False
                put_exit = False
            any_exit = stoploss_exit or profit_exit or call_exit or put_exit
            if any_exit:
                exit_order = tda_submit_order("SELL_TO_CLOSE", exit_quantity, exit_symbol, orderType=order_type, limit_price=mid)
                entry = tickers_db.get(tickers[i])
                entry["triggered"] = False
                tickers_db.put(entry)
                exit_log = f"Closing out {exit_quantity} contracts of {exit_symbol} due to"
                if stoploss_exit:
                    if ticker_dict[tickers[i]]["stoploss_type"] == "Trailing %":
                        exit_log = exit_log + f" drawdown % {drawdown_pct_high} > trail % {trail_pct}"
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
                    exit_log = exit_log + f" bearish candle while holding call"
                elif put_exit:
                    tda_symbols_held.remove(tickers[i])
                    exit_log = exit_log + f" bullish candle while holding put"
                print(exit_log)

    # Checkpoint exits

    for i in range(len(tickers)):
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
                    break
                if gain_type == "Fixed $":
                    if gain_amount > gainloss:
                        exit_order = tda_submit_order("SELL_TO_CLOSE", qty2, exit_symbol, orderType=order_type, limit_price=mid)
                        print(f"{qty2} contracts of {tickers[i]} closed out due to checkpoint: \
                                gain_amount {gain_amount} > gainloss {gainloss}")
                elif gain_type == "Fixed %":
                    if gain_pct > gainloss_pct:
                        exit_order = tda_submit_order("SELL_TO_CLOSE", qty2, exit_symbol, orderType=order_type, limit_price=mid)
                        print(f"{qty2} contracts of {tickers[i]} closed out due to checkpoint: \
                                gain_pct {gain_pct} > gainloss_pct {gainloss_pct}")
                elif gain_type == "None":
                    exit_order = ""        

    # Entry order

    for i in range(len(tickers)):
        order_type = ticker_dict[tickers[i]]["order_type"]
        option_type = ticker_dict[tickers[i]]["option_type"]
        mid = ticker_dict[tickers[i]]["mid"]
        condition2 = tickers[i] not in tda_symbols_held
        condition3 = ticker_dict[tickers[i]]["bullish_candle"] # bullish_candles[i]
        if ticker_dict[tickers[i]]["wick_requirement"] == "Any wick okay":
            condition4 = True
        elif ticker_dict[tickers[i]]["wick_requirement"] == "Can't have wick":
            if condition3==True:
                if ticker_dict[tickers[i]]["candle_wick_bottom"] > 0:
                    condition4 = False
                else:
                    condition4 = True
            elif condition3==False:
                if ticker_dict[tickers[i]]["candle_wick_top"] > 0:
                    condition4 = False
                else:
                    condition4 = True
        elif ticker_dict[tickers[i]]["wick_requirement"] == "Can have wick, but must be smaller":
            if condition3==True:
                if ticker_dict[tickers[i]]["candle_wick_bottom"] > ticker_dict[tickers[i]]["candle_wick_top"]:
                    condition4 = False
                else:
                    condition4 = True
            elif condition3==False:
                if ticker_dict[tickers[i]]["candle_wick_top"] > ticker_dict[tickers[i]]["candle_wick_bottom"]:
                    condition4 = False
                else:
                    condition4 = True
        if ticker_dict[tickers[i]]["indicator"] == "HMA":
            condition5 = ticker_dict[tickers[i]]["bullish_hma"]
        elif ticker_dict[tickers[i]]["indicator"] == "EMA":
            condition5 = ticker_dict[tickers[i]]["bullish_ema"]
        condition6 = tickers[i] not in recent_tickers
        bullish_entry = condition1 and condition2 and condition3==True and condition4 and condition5==True and condition6 and "calls" in option_type.lower()
        bearish_entry = condition1 and condition2 and condition3==False and condition4 and condition5==False and condition6 and "puts" in option_type.lower()
        contracts = ticker_dict[tickers[i]]["contracts"]
        if bullish_entry:
            entry_symbol = ticker_dict[tickers[i]]["chain"]["call"]
            entry_order = tda_submit_order("BUY_TO_OPEN", contracts, entry_symbol, orderType=order_type, limit_price=mid)
            print(f"Bullish entry: Buying {contracts} contracts of {entry_symbol}")
        if bearish_entry:
            entry_symbol = ticker_dict[tickers[i]]["chain"]["put"]
            entry_order = tda_submit_order("BUY_TO_OPEN", contracts, entry_symbol, orderType=order_type, limit_price=mid)
            print(f"Bearish entry: Buying {contracts} contracts of {entry_symbol}")

    # Print log

    now = dt.datetime.now(tz=local_timezone).strftime("%Y-%m-%d %X")
    time_end = time.time()
    time_total = np.round(time_end - time_start, 2)
    global log_count
    log_count += 1
    if log_count == 1 or log_count % 30 == 0:
        print_log = [
            ["Time", f" = {now}"],
            ["Market open", f" = {market_open}"],
            ["Recent tickers",f" = {recent_tickers}"],
            ["Execution Speed",f" = {time_total} seconds"],
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
            ["---------------", "---------------"]
        ]

    for item_list in print_log:
        for i in item_list:
            print(i.ljust(20), end='')
        print()

    # Since the bot made it to the end of the script successfully, reset error streak to 0

    error_streak = 0

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
    time.sleep(1)