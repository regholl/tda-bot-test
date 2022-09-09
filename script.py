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

# Define the strategy

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

    # Extract values from Deta

    tda_account = config_db.get("TDA_ACCOUNT")['value']
    tickers_db = deta.Base("tickers_db")
    tickers_info = tickers_db.fetch().items
    tickers = [item["key"].upper() for item in tickers_info]
    period_types = [item["period_type"] for item in tickers_info]
    periods = [item["period"] for item in tickers_info]
    frequencies = [item["frequency"] for item in tickers_info]
    frequency_types = [item["frequency_type"] for item in tickers_info]
    extended_hours = [bool(item["extended_hours"]) for item in tickers_info]
    ema_lengths = [int(item["ema_length"]) for item in tickers_info]
    hma_lengths = [int(item["hma_length"]) for item in tickers_info]
    contracts = [int(item["contracts"]) for item in tickers_info]
    stoplosses = [float(item["stoploss"]) if item["stoploss"] != None else 1000000 for item in tickers_info]
    stoploss_pcts = [float(item["stoploss_pct"]) if item["stoploss_pct"] != None else 1000000 for item in tickers_info]
    trail_pcts = [float(item["trail_pct"]) if item["trail_pct"] != None else 1000000 for item in tickers_info]
    stoploss_types = [item["stoploss_type"] for item in tickers_info]
    maxes = [float(item["max"]) for item in tickers_info]
    mins = [float(item["min"]) for item in tickers_info]
    trigger_trails = [float(item["trigger_trail"]) for item in tickers_info]
    trigger_trail_pcts = [float(item["trigger_trail_pct"]) for item in tickers_info]
    take_profits = [float(item["take_profit"]) for item in tickers_info]
    take_profit_pcts = [float(item["take_profit_pct"]) for item in tickers_info]
    take_profit_types = [item["take_profit_type"] for item in tickers_info]
    confirm_times = [int(item["confirm_time"]) for item in tickers_info]
    confirm_units = [item["confirm_unit"] for item in tickers_info]
    times_in_candles = [item["time_in_candle"] for item in tickers_info]

    # Create master ticker_dict

    ticker_dict = {}
    for i in range(len(tickers)):
        ticker_dict[tickers[i]] = {}
        ticker_dict[tickers[i]]["period_type"] = period_types[i]
        ticker_dict[tickers[i]]["period"] = periods[i]
        ticker_dict[tickers[i]]["frequency"] = frequencies[i]
        ticker_dict[tickers[i]]["frequency_type"] = frequency_types[i]
        ticker_dict[tickers[i]]["extended_hours"] = extended_hours[i]
        ticker_dict[tickers[i]]["ema_length"] = ema_lengths[i]
        ticker_dict[tickers[i]]["hma_length"] = hma_lengths[i]
        ticker_dict[tickers[i]]["contracts"] = contracts[i]
        ticker_dict[tickers[i]]["stoploss"] = stoplosses[i]
        ticker_dict[tickers[i]]["stoploss_pct"] = stoploss_pcts[i]
        ticker_dict[tickers[i]]["trail_pct"] = trail_pcts[i]
        ticker_dict[tickers[i]]["stoploss_type"] = stoploss_types[i]
        ticker_dict[tickers[i]]["max"] = maxes[i]
        ticker_dict[tickers[i]]["min"] = mins[i]
        ticker_dict[tickers[i]]["trigger_trail"] = trigger_trails[i]
        ticker_dict[tickers[i]]["trigger_trail_pct"] = trigger_trail_pcts[i]
        ticker_dict[tickers[i]]["take_profit"] = take_profits[i]
        ticker_dict[tickers[i]]["take_profit_pct"] = take_profit_pcts[i]
        ticker_dict[tickers[i]]["take_profit_type"] = take_profit_types[i]
        ticker_dict[tickers[i]]["confirm_time"] = confirm_times[i]
        ticker_dict[tickers[i]]["confirm_unit"] = confirm_units[i]
        ticker_dict[tickers[i]]["times_in_candles"] = times_in_candles[i]

        ticker_dict[tickers[i]]["option_symbol"] = tickers[i]
        ticker_dict[tickers[i]]["average_price"] = 0
        ticker_dict[tickers[i]]["market_value"] = 0
        ticker_dict[tickers[i]]["long_shares"] = 0
        ticker_dict[tickers[i]]["short_shares"] = 0
        ticker_dict[tickers[i]]["quantity"] = 0
        ticker_dict[tickers[i]]["option_last"] = 0

    # Get market status

    hours = get_hours_tda()
    market_open = hours[0]
    closing_time = hours[1]
    #current_time = hours[2]

    # Examine watchlist

    lasts, bullish_candles, emas, hmas, bullish_hmas, chains = [], [], [], [], [], []
    for ticker in tickers:

        # Get quotes for underlying

        quote = get_quote_tda(ticker)
        last = np.round(float(quote[ticker]['lastPrice']), 2)
        lasts.append(last)
        ticker_dict[ticker]["last"] = last

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
        tda_opens = ha_opens
        tda_highs = ha_highs
        tda_lows = ha_lows
        tda_closes = ha_closes

        # Bullish or bearish candle

        # if market_open:
        #     last_close = tda_closes[len(tda_closes)-2]
        #     last_open = tda_opens[len(tda_opens)-2]
        # else:
        last_close = tda_closes[len(tda_closes)-1]
        last_open = tda_opens[len(tda_opens)-1]
        if last_close > last_open:
            bullish_candle = True
        else:
            bullish_candle = False
        bullish_candles.append(bullish_candle)
        ticker_dict[ticker]["bullish_candle"] = bullish_candle

        # Create dataframe

        df = pd.DataFrame()
        df['open'] = tda_opens
        df['high'] = tda_highs
        df['low'] = tda_lows
        df['close'] = tda_closes

        # Calculate indicators

        ema_window = int(ticker_dict[ticker]['ema_length'])
        emas_all = np.round(ta.trend.ema_indicator(pd.to_numeric(df['close']), window=ema_window), 2)
        ema = emas_all[len(emas_all)-1]
        emas.append(ema)
        ticker_dict[ticker]["ema"] = ema

        hma_window = int(ticker_dict[ticker]['hma_length'])
        hma1 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=int(hma_window/2))
        hma2 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=hma_window)
        hma_raw = (2 * hma1) - hma2
        hmas_all = np.round(ta.trend.wma_indicator(hma_raw, window=math.floor(math.sqrt(hma_window))), 2)
        hma = hmas_all[len(hmas_all)-1]
        hmas.append(hma)
        ticker_dict[ticker]["hma"] = hma

        # Bullish or bearish HMA

        # if market_open:
        #     last_hma = hmas_all[len(hmas_all)-2]
        #     last_hma1 = hmas_all[len(hmas_all)-3]
        # else:
        last_hma = hmas_all[len(hmas_all)-1]
        last_hma1 = hmas_all[len(hmas_all)-2]
        if last_hma > last_hma1:
            bullish_hma = True
        else:
            bullish_hma = False
        bullish_hmas.append(bullish_hma)
        ticker_dict[ticker]["bullish_hma"] = bullish_hma

        # Get option symbols

        chain = get_chain_tda(ticker)
        chains.append(chain)
        ticker_dict[ticker]["chain"] = chain

    # Get positions

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

    # Adjust tickers for optional holdings and get quotes

    tda_symbols_held, lasts_option = [], []
    for i in range(len(tda_tickers_held)):
        symb = tda_tickers_held[i]
        if "_" in tda_tickers_held[i]:
            symb = tda_tickers_held[i].split("_")[0]
        tda_symbols_held.append(symb)
        quote = get_quote_tda(tda_tickers_held[i])
        last_option = np.round(float(quote[tda_tickers_held[i]]['lastPrice']), 2)
        lasts_option.append(last_option)
        if symb in tickers:
            ticker_dict[symb]["option_symbol"] = tda_tickers_held[i]
            ticker_dict[symb]["average_price"] = tda_average_prices[i]
            ticker_dict[symb]["market_value"] = tda_market_values[i]
            ticker_dict[symb]["long_shares"] = tda_long_shares[i]
            ticker_dict[symb]["short_shares"] = tda_short_shares[i]
            ticker_dict[symb]["quantity"] = tda_quantities[i]
            ticker_dict[symb]["option_last"] = last_option

    # Calculate gainloss from quotes and average prices

    tda_gainlosses, tda_costbases, tda_gainloss_pcts = [], [], []
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
        if tda_gainloss > trigger_trails[i] or tda_gainloss_pct > trigger_trail_pcts[i]:
            if ticker_dict[tickers[i]]["stoploss_type"] != "Trailing %":
                entry = tickers_db.get(tickers[i])
                entry["stoploss_type"] = "Trailing %"
                stoploss_types[i] = "Trailing %"
                ticker_dict[tickers[i]]["stoploss_type"] = "Trailing %"
                tickers_db.put(entry)
                print(f"Trailing stop loss triggerd due to gainloss {tda_gainloss} > trigger_trail {trigger_trails[i]} \
                        or gainloss % {tda_gainloss_pct} > {trigger_trail_pcts[i]}")
        tda_gainlosses.append(tda_gainloss)
        tda_costbases.append(tda_costbasis)
        tda_gainloss_pcts.append(tda_gainloss_pct)
        ticker_dict[tickers[i]]["gainloss"] = tda_gainloss
        ticker_dict[tickers[i]]["costbasis"] = tda_costbasis
        ticker_dict[tickers[i]]["gainloss_pct"] = tda_gainloss_pct

    # Update max and min

    for i in range(len(tickers)):
        if tickers[i] in tda_symbols_held:
            maxi = max(ticker_dict[tickers[i]]["max"], ticker_dict[tickers[i]]["market_value"], ticker_dict[tickers[i]]["costbasis"])
            mini = min(ticker_dict[tickers[i]]["min"], ticker_dict[tickers[i]]["market_value"], ticker_dict[tickers[i]]["costbasis"])
        else:
            maxi = 0
            mini = 0
        if maxi != ticker_dict[tickers[i]]["max"]:
            entry = tickers_db.get(tickers[i])
            entry["max"] = maxi
            maxes[i] = maxi
            ticker_dict[tickers[i]]["max"] = maxi
            tickers_db.put(entry)
        if mini != ticker_dict[tickers[i]]["min"]:
            entry = tickers_db.get(tickers[i])
            entry["min"] = mini
            mins[i] = mini
            ticker_dict[tickers[i]]["min"] = mini
            tickers_db.put(entry)
        
    # Get recent orders

    tda_orders = get_orders2_tda()
    time_now = dt.datetime.now(utc)
    pause_time = float(config_db.get("PAUSE_TIME")['value'])
    pause_unit = config_db.get("PAUSE_UNIT")['value']
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
    recent_tickers = [ticker.split("_")[0] for ticker in recent_opt_tickers]
    
    # Calculate time
    
    current_time = dt.datetime.now(tz=local_timezone)
    minutes_until_close = np.round((closing_time - current_time).total_seconds() / 60, 2)

    # Exit order

    for i in range(len(tickers)):
        # condition1 = market_open
        condition1 = 0 < minutes_until_close < 450
        condition2 = tickers[i] in tda_symbols_held
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
            elif ticker_dict[tickers[i]]["stoploss_type"] == "Percent":
                condition3 = abs(gainloss_pct) > stoploss_pct and gainloss_pct < 0
            elif ticker_dict[tickers[i]]["stoploss_type"] == "Dollars":
                condition3 = abs(gainloss) > stoploss and gainloss < 0
            elif ticker_dict[tickers[i]]["stoploss_type"] == "None":
                condition3 = False
            take_profit = ticker_dict[tickers[i]]["take_profit"]
            take_profit_pct = ticker_dict[tickers[i]]["take_profit_pct"]
            if ticker_dict[tickers[i]]["take_profit_type"] == "Percent":
                condition4 = gainloss_pct > take_profit_pct
            elif ticker_dict[tickers[i]]["take_profit_type"] == "Dollars":
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
                times_in_candles[i] = 0
                ticker_dict[tickers[i]]["time_in_candle"] = 0
                entry = tickers_db.get(tickers[i])
                entry["time_in_candle"] = 0
                tickers_db.put(entry)
            else:
                times_in_candles[i] = curr_time
                ticker_dict[tickers[i]]["time_in_candle"] = curr_time
                entry = tickers_db.get(tickers[i])
                entry["time_in_candle"] = curr_time
                tickers_db.put(entry)
            call_exit = condition1 and condition2 and condition5 and not condition6 and not condition7 and condition8
            put_exit = condition1 and condition2 and not condition5 and condition6 and condition7 and condition8
            any_exit = stoploss_exit or profit_exit or call_exit or put_exit
            if any_exit:
                tickers_db.put(entry)
                exit_order = tda_submit_order("SELL_TO_CLOSE", exit_quantity, exit_symbol)
                exit_log = f"Closing out {exit_quantity} contracts of {exit_symbol} due to"
                if stoploss_exit:
                    if ticker_dict[tickers[i]]["stoploss_type"] == "Trailing %":
                        exit_log = exit_log + f" drawdown % {drawdown_pct_high} > trail % {trail_pct}"
                    elif ticker_dict[tickers[i]]["stoploss_type"] == "Percent":
                        exit_log = exit_log + f" gainloss % {gainloss_pct} > stoploss % {stoploss_pct}"
                    elif ticker_dict[tickers[i]]["stoploss_type"] == "Dollars":
                        exit_log = exit_log + f" gainloss {gainloss} > stoploss {stoploss}"
                elif profit_exit:
                    if ticker_dict[tickers[i]]["take_profit_type"] == "Percent":
                        exit_log = exit_log + f" gainloss % {gainloss_pct} > take_profit % {take_profit_pct}"
                    elif ticker_dict[tickers[i]]["take_profit_type"] == "Dollars":
                        exit_log = exit_log + f" gainloss {gainloss} > take_profit {take_profit}"
                elif call_exit:
                    tda_symbols_held.remove(tickers[i])
                    exit_log = exit_log + f" bearish candle while holding call"
                elif put_exit:
                    tda_symbols_held.remove(tickers[i])
                    exit_log = exit_log + f" bullish candle while holding put"
                print(exit_log)

    # Entry order

    for i in range(len(tickers)):
        # condition1 = market_open
        condition1 = 0 < minutes_until_close < 450
        condition2 = tickers[i] not in tda_symbols_held
        condition3 = ticker_dict[tickers[i]]["bullish_candle"] # bullish_candles[i]
        condition4 = ticker_dict[tickers[i]]["bullish_hma"] # bullish_hmas[i]
        condition5 = tickers[i] not in recent_tickers
        bullish_entry = condition1 and condition2 and condition3 and condition4 and condition5
        bearish_entry = condition1 and condition2 and not condition3 and not condition4 and condition5
        contracts = ticker_dict[tickers[i]]["contracts"]
        if bullish_entry:
            entry_symbol = ticker_dict[tickers[i]]["chain"]["call"]
            entry_order = tda_submit_order("BUY_TO_OPEN", contracts, entry_symbol)
            print(f"Bullish entry: Buying {contracts} contracts of {entry_symbol}")
        if bearish_entry:
            entry_symbol = ticker_dict[tickers[i]]["chain"]["put"]
            entry_order = tda_submit_order("BUY_TO_OPEN", contracts, entry_symbol)
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
            ["Held Tickers", f" = {tda_tickers_held}"],
            ["Long shares",f" = {tda_long_shares}"],
            ["Short shares",f" = {tda_short_shares}"],
            ["Quantities Held",f" = {tda_quantities}"],
            ["Average prices",f" = {tda_average_prices}"],
            ["Market values",f" = {tda_market_values}"],
            ["Number Tickers", f" = {len(tickers)}"],
            ["Tickers",f" = {tickers}"],
            ["Contracts",f" = {contracts}"],
            ["Stoplosses",f" = {stoplosses}"],
            ["Stoploss pcts",f" = {stoploss_pcts}"],
            ["Trailing pcts",f" = {trail_pcts}"],
            ["Stoploss types",f" = {stoploss_types}"],
            ["Gainloss",f" = {tda_gainlosses}"],
            ["Gainloss Pct",f" = {tda_gainloss_pcts}"],
            ["Maxes",f" = {maxes}"],
            ["Mins",f" = {mins}"],
            ["Cost Basis",f" = {tda_costbases}"],
            ["Period types",f" = {period_types}"],
            ["Periods",f" = {periods}"],
            ["Frequency types",f" = {frequency_types}"],
            ["Frequencies",f" = {frequencies}"],
            ["EMA lengths",f" = {ema_lengths}"],
            ["HMA lengths",f" = {hma_lengths}"],
            ["EMAs",f" = {emas}"],
            ["HMAs",f" = {hmas}"],
            ["Extended hours",f" = {extended_hours}"],
            ["Stock Lasts",f" = {lasts}"],
            ["Option Lasts",f" = {lasts_option}"],
            ["Bullish Candles",f" = {bullish_candles}"],
            ["Bullish HMAs",f" = {bullish_hmas}"],
            ["Recent tickers",f" = {recent_tickers}"],
            ["Execution Speed",f" = {time_total} seconds"],
            ["---------------", "---------------"]
        ]
    else:
        print_log = [
            ["No"," log"],
            ["---------------", "---------------"]
        ]

    for item_list in print_log:
        for i in item_list:
            print(i.ljust(20), end='')
        print()

    # Reset error streak to 0

    error_streak = 0

# Run

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