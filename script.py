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
    trigger_trail_types = [item["trigger_trail_type"] for item in tickers_info]
    trigger_trails = [float(item["trigger_trail"]) for item in tickers_info]
    trigger_trail_pcts = [float(item["trigger_trail_pct"]) for item in tickers_info]
    trigger_trail_trail_pcts = [float(item["trigger_trail_trail_pct"]) for item in tickers_info]
    triggereds = [bool(item["triggered"]) for item in tickers_info]
    take_profits = [float(item["take_profit"]) for item in tickers_info]
    take_profit_pcts = [float(item["take_profit_pct"]) for item in tickers_info]
    take_profit_types = [item["take_profit_type"] for item in tickers_info]
    confirm_times = [int(item["confirm_time"]) for item in tickers_info]
    confirm_units = [item["confirm_unit"] for item in tickers_info]
    pause_times = [int(item["pause_time"]) for item in tickers_info]
    pause_units = [item["pause_unit"] for item in tickers_info]
    times_in_candles = [item["time_in_candle"] for item in tickers_info]
    indicators = [item["indicator"] for item in tickers_info]
    use_closes = [item["use_close"] for item in tickers_info]
    wick_requirements = [item["wick_requirement"] for item in tickers_info]
    candle_types = [item["candle_type"] for item in tickers_info]
    order_types = [item["order_type"] for item in tickers_info]

    # Checkpoints db

    checkpoints_db = deta.Base("checkpoints_db")
    checkpoints_info = checkpoints_db.fetch().items
    # tickers = [item["key"].upper() for item in checkpoints_info]
    checkpoint_ons0 = [item["checkpoint_on0"] for item in checkpoints_info]
    activation_values0 = [item["activation_value0"] for item in checkpoints_info]
    activateds0 = [item["activated0"] for item in checkpoints_info]
    exit_values0 = [item["exit_value0"] for item in checkpoints_info]
    gain_types0 = [item["gain_type0"] for item in checkpoints_info]
    gain_amounts0 = [item["gain_amount0"] for item in checkpoints_info]
    gain_pcts0 = [item["gain_pct0"] for item in checkpoints_info]
    contract_nbrs0 = [item["contract_nbr0"] for item in checkpoints_info]
    checkpoint_ons1 = [item["checkpoint_on1"] for item in checkpoints_info]
    activation_values1 = [item["activation_value1"] for item in checkpoints_info]
    activateds1 = [item["activated1"] for item in checkpoints_info]
    exit_values1 = [item["exit_value1"] for item in checkpoints_info]
    gain_types1 = [item["gain_type1"] for item in checkpoints_info]
    gain_amounts1 = [item["gain_amount1"] for item in checkpoints_info]
    gain_pcts1 = [item["gain_pct1"] for item in checkpoints_info]
    contract_nbrs1 = [item["contract_nbr1"] for item in checkpoints_info]
    checkpoint_ons2 = [item["checkpoint_on2"] for item in checkpoints_info]
    activation_values2 = [item["activation_value2"] for item in checkpoints_info]
    activateds2 = [item["activated2"] for item in checkpoints_info]
    exit_values2 = [item["exit_value2"] for item in checkpoints_info]
    gain_types2 = [item["gain_type2"] for item in checkpoints_info]
    gain_amounts2 = [item["gain_amount2"] for item in checkpoints_info]
    gain_pcts2 = [item["gain_pct2"] for item in checkpoints_info]
    contract_nbrs2 = [item["contract_nbr2"] for item in checkpoints_info]
    checkpoint_ons3 = [item["checkpoint_on3"] for item in checkpoints_info]
    activation_values3 = [item["activation_value3"] for item in checkpoints_info]
    activateds3 = [item["activated3"] for item in checkpoints_info]
    exit_values3 = [item["exit_value3"] for item in checkpoints_info]
    gain_types3 = [item["gain_type3"] for item in checkpoints_info]
    gain_amounts3 = [item["gain_amount3"] for item in checkpoints_info]
    gain_pcts3 = [item["gain_pct3"] for item in checkpoints_info]
    contract_nbrs3 = [item["contract_nbr3"] for item in checkpoints_info]
    checkpoint_ons4 = [item["checkpoint_on4"] for item in checkpoints_info]
    activation_values4 = [item["activation_value4"] for item in checkpoints_info]
    activateds4 = [item["activated4"] for item in checkpoints_info]
    exit_values4 = [item["exit_value4"] for item in checkpoints_info]
    gain_types4 = [item["gain_type4"] for item in checkpoints_info]
    gain_amounts4 = [item["gain_amount4"] for item in checkpoints_info]
    gain_pcts4 = [item["gain_pct4"] for item in checkpoints_info]
    contract_nbrs4 = [item["contract_nbr4"] for item in checkpoints_info]
    checkpoint_ons5 = [item["checkpoint_on5"] for item in checkpoints_info]
    activation_values5 = [item["activation_value5"] for item in checkpoints_info]
    activateds5 = [item["activated5"] for item in checkpoints_info]
    exit_values5 = [item["exit_value5"] for item in checkpoints_info]
    gain_types5 = [item["gain_type5"] for item in checkpoints_info]
    gain_amounts5 = [item["gain_amount5"] for item in checkpoints_info]
    gain_pcts5 = [item["gain_pct5"] for item in checkpoints_info]
    contract_nbrs5 = [item["contract_nbr5"] for item in checkpoints_info]
    checkpoint_ons6 = [item["checkpoint_on6"] for item in checkpoints_info]
    activation_values6 = [item["activation_value6"] for item in checkpoints_info]
    activateds6 = [item["activated6"] for item in checkpoints_info]
    exit_values6 = [item["exit_value6"] for item in checkpoints_info]
    gain_types6 = [item["gain_type6"] for item in checkpoints_info]
    gain_amounts6 = [item["gain_amount6"] for item in checkpoints_info]
    gain_pcts6 = [item["gain_pct6"] for item in checkpoints_info]
    contract_nbrs6 = [item["contract_nbr6"] for item in checkpoints_info]
    checkpoint_ons7 = [item["checkpoint_on7"] for item in checkpoints_info]
    activation_values7 = [item["activation_value7"] for item in checkpoints_info]
    activateds7 = [item["activated7"] for item in checkpoints_info]
    exit_values7 = [item["exit_value7"] for item in checkpoints_info]
    gain_types7 = [item["gain_type7"] for item in checkpoints_info]
    gain_amounts7 = [item["gain_amount7"] for item in checkpoints_info]
    gain_pcts7 = [item["gain_pct7"] for item in checkpoints_info]
    contract_nbrs7 = [item["contract_nbr7"] for item in checkpoints_info]
    checkpoint_ons8 = [item["checkpoint_on8"] for item in checkpoints_info]
    activation_values8 = [item["activation_value8"] for item in checkpoints_info]
    activateds8 = [item["activated8"] for item in checkpoints_info]
    exit_values8 = [item["exit_value8"] for item in checkpoints_info]
    gain_types8 = [item["gain_type8"] for item in checkpoints_info]
    gain_amounts8 = [item["gain_amount8"] for item in checkpoints_info]
    gain_pcts8 = [item["gain_pct8"] for item in checkpoints_info]
    contract_nbrs8 = [item["contract_nbr8"] for item in checkpoints_info]
    checkpoint_ons9 = [item["checkpoint_on9"] for item in checkpoints_info]
    activation_values9 = [item["activation_value9"] for item in checkpoints_info]
    activateds9 = [item["activated9"] for item in checkpoints_info]
    exit_values9 = [item["exit_value9"] for item in checkpoints_info]
    gain_types9 = [item["gain_type9"] for item in checkpoints_info]
    gain_amounts9 = [item["gain_amount9"] for item in checkpoints_info]
    gain_pcts9 = [item["gain_pct9"] for item in checkpoints_info]
    contract_nbrs9 = [item["contract_nbr9"] for item in checkpoints_info]

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
        ticker_dict[tickers[i]]["trigger_trail_type"] = trigger_trail_types[i]
        ticker_dict[tickers[i]]["trigger_trail"] = trigger_trails[i]
        ticker_dict[tickers[i]]["trigger_trail_pct"] = trigger_trail_pcts[i]
        ticker_dict[tickers[i]]["trigger_trail_trail_pct"] = trigger_trail_trail_pcts[i]
        ticker_dict[tickers[i]]["triggered"] = triggereds[i]
        ticker_dict[tickers[i]]["take_profit"] = take_profits[i]
        ticker_dict[tickers[i]]["take_profit_pct"] = take_profit_pcts[i]
        ticker_dict[tickers[i]]["take_profit_type"] = take_profit_types[i]
        ticker_dict[tickers[i]]["confirm_time"] = confirm_times[i]
        ticker_dict[tickers[i]]["confirm_unit"] = confirm_units[i]
        ticker_dict[tickers[i]]["pause_time"] = pause_times[i]
        ticker_dict[tickers[i]]["pause_unit"] = pause_units[i]
        ticker_dict[tickers[i]]["times_in_candles"] = times_in_candles[i]
        ticker_dict[tickers[i]]["indicator"] = indicators[i]
        ticker_dict[tickers[i]]["use_close"] = use_closes[i]
        ticker_dict[tickers[i]]["wick_requirement"] = wick_requirements[i]
        ticker_dict[tickers[i]]["candle_type"] = candle_types[i]
        ticker_dict[tickers[i]]["order_type"] = order_types[i]

        ticker_dict[tickers[i]]["checkpoint_on0"] = checkpoint_ons0[i]
        ticker_dict[tickers[i]]["activation_value0"] = activation_values0[i]
        ticker_dict[tickers[i]]["activated0"] = activateds0[i]
        ticker_dict[tickers[i]]["exit_value0"] = exit_values0[i]
        ticker_dict[tickers[i]]["gain_type0"] = gain_types0[i]
        ticker_dict[tickers[i]]["gain_amount0"] = gain_amounts0[i]
        ticker_dict[tickers[i]]["gain_pct0"] = gain_pcts0[i]
        ticker_dict[tickers[i]]["contract_nbr0"] = contract_nbrs0[i]
        ticker_dict[tickers[i]]["checkpoint_on1"] = checkpoint_ons1[i]
        ticker_dict[tickers[i]]["activation_value1"] = activation_values1[i]
        ticker_dict[tickers[i]]["activated1"] = activateds1[i]
        ticker_dict[tickers[i]]["exit_value1"] = exit_values1[i]
        ticker_dict[tickers[i]]["gain_type1"] = gain_types1[i]
        ticker_dict[tickers[i]]["gain_amount1"] = gain_amounts1[i]
        ticker_dict[tickers[i]]["gain_pct1"] = gain_pcts1[i]
        ticker_dict[tickers[i]]["contract_nbr1"] = contract_nbrs1[i]
        ticker_dict[tickers[i]]["checkpoint_on2"] = checkpoint_ons2[i]
        ticker_dict[tickers[i]]["activation_value2"] = activation_values2[i]
        ticker_dict[tickers[i]]["activated2"] = activateds2[i]
        ticker_dict[tickers[i]]["exit_value2"] = exit_values2[i]
        ticker_dict[tickers[i]]["gain_type2"] = gain_types2[i]
        ticker_dict[tickers[i]]["gain_amount2"] = gain_amounts2[i]
        ticker_dict[tickers[i]]["gain_pct2"] = gain_pcts2[i]
        ticker_dict[tickers[i]]["contract_nbr2"] = contract_nbrs2[i]
        ticker_dict[tickers[i]]["checkpoint_on3"] = checkpoint_ons3[i]
        ticker_dict[tickers[i]]["activation_value3"] = activation_values3[i]
        ticker_dict[tickers[i]]["activated3"] = activateds3[i]
        ticker_dict[tickers[i]]["exit_value3"] = exit_values3[i]
        ticker_dict[tickers[i]]["gain_type3"] = gain_types3[i]
        ticker_dict[tickers[i]]["gain_amount3"] = gain_amounts3[i]
        ticker_dict[tickers[i]]["gain_pct3"] = gain_pcts3[i]
        ticker_dict[tickers[i]]["contract_nbr3"] = contract_nbrs3[i]
        ticker_dict[tickers[i]]["checkpoint_on4"] = checkpoint_ons4[i]
        ticker_dict[tickers[i]]["activation_value4"] = activation_values4[i]
        ticker_dict[tickers[i]]["activated4"] = activateds4[i]
        ticker_dict[tickers[i]]["exit_value4"] = exit_values4[i]
        ticker_dict[tickers[i]]["gain_type4"] = gain_types4[i]
        ticker_dict[tickers[i]]["gain_amount4"] = gain_amounts4[i]
        ticker_dict[tickers[i]]["gain_pct4"] = gain_pcts4[i]
        ticker_dict[tickers[i]]["contract_nbr4"] = contract_nbrs4[i]
        ticker_dict[tickers[i]]["checkpoint_on5"] = checkpoint_ons5[i]
        ticker_dict[tickers[i]]["activation_value5"] = activation_values5[i]
        ticker_dict[tickers[i]]["activated5"] = activateds5[i]
        ticker_dict[tickers[i]]["exit_value5"] = exit_values5[i]
        ticker_dict[tickers[i]]["gain_type5"] = gain_types5[i]
        ticker_dict[tickers[i]]["gain_amount5"] = gain_amounts5[i]
        ticker_dict[tickers[i]]["gain_pct5"] = gain_pcts5[i]
        ticker_dict[tickers[i]]["contract_nbr5"] = contract_nbrs5[i]
        ticker_dict[tickers[i]]["checkpoint_on6"] = checkpoint_ons6[i]
        ticker_dict[tickers[i]]["activation_value6"] = activation_values6[i]
        ticker_dict[tickers[i]]["activated6"] = activateds6[i]
        ticker_dict[tickers[i]]["exit_value6"] = exit_values6[i]
        ticker_dict[tickers[i]]["gain_type6"] = gain_types6[i]
        ticker_dict[tickers[i]]["gain_amount6"] = gain_amounts6[i]
        ticker_dict[tickers[i]]["gain_pct6"] = gain_pcts6[i]
        ticker_dict[tickers[i]]["contract_nbr6"] = contract_nbrs6[i]
        ticker_dict[tickers[i]]["checkpoint_on7"] = checkpoint_ons7[i]
        ticker_dict[tickers[i]]["activation_value7"] = activation_values7[i]
        ticker_dict[tickers[i]]["activated7"] = activateds7[i]
        ticker_dict[tickers[i]]["exit_value7"] = exit_values7[i]
        ticker_dict[tickers[i]]["gain_type7"] = gain_types7[i]
        ticker_dict[tickers[i]]["gain_amount7"] = gain_amounts7[i]
        ticker_dict[tickers[i]]["gain_pct7"] = gain_pcts7[i]
        ticker_dict[tickers[i]]["contract_nbr7"] = contract_nbrs7[i]
        ticker_dict[tickers[i]]["checkpoint_on8"] = checkpoint_ons8[i]
        ticker_dict[tickers[i]]["activation_value8"] = activation_values8[i]
        ticker_dict[tickers[i]]["activated8"] = activateds8[i]
        ticker_dict[tickers[i]]["exit_value8"] = exit_values8[i]
        ticker_dict[tickers[i]]["gain_type8"] = gain_types8[i]
        ticker_dict[tickers[i]]["gain_amount8"] = gain_amounts8[i]
        ticker_dict[tickers[i]]["gain_pct8"] = gain_pcts8[i]
        ticker_dict[tickers[i]]["contract_nbr8"] = contract_nbrs8[i]
        ticker_dict[tickers[i]]["checkpoint_on9"] = checkpoint_ons9[i]
        ticker_dict[tickers[i]]["activation_value9"] = activation_values9[i]
        ticker_dict[tickers[i]]["activated9"] = activateds9[i]
        ticker_dict[tickers[i]]["exit_value9"] = exit_values9[i]
        ticker_dict[tickers[i]]["gain_type9"] = gain_types9[i]
        ticker_dict[tickers[i]]["gain_amount9"] = gain_amounts9[i]
        ticker_dict[tickers[i]]["gain_pct9"] = gain_pcts9[i]
        ticker_dict[tickers[i]]["contract_nbr9"] = contract_nbrs9[i]

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

    lasts, bullish_candles, emas, hmas, bullish_emas, bullish_hmas, chains = [], [], [], [], [], [], []
    for ticker in tickers:

        # Get quotes for underlying

        quote = get_quote_tda(ticker)
        last = np.round(float(quote[ticker]['lastPrice']), 2)
        bid = np.round(float(quote[ticker]['bidPrice']), 2)
        ask = np.round(float(quote[ticker]['lastPrice']), 2)
        mid = np.round((bid + ask) / 2, 2)
        lasts.append(last)
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

        # Bullish or bearish candle + wicks

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
        if last_close > last_open:
            bullish_candle = True
        elif last_close < last_open:
            bullish_candle = False
        else:
            bullish_candle = None
        bullish_candles.append(bullish_candle)
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

        # Bullish or bearish moving averages

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
        if last_ema > last_ema1:
            bullish_ema = True
        else:
            bullish_ema = False
        bullish_emas.append(bullish_ema)
        ticker_dict[ticker]["bullish_ema"] = bullish_ema
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

        tda_gainlosses.append(tda_gainloss)
        tda_costbases.append(tda_costbasis)
        tda_gainloss_pcts.append(tda_gainloss_pct)
        ticker_dict[tickers[i]]["gainloss"] = tda_gainloss
        ticker_dict[tickers[i]]["costbasis"] = tda_costbasis
        ticker_dict[tickers[i]]["gainloss_pct"] = tda_gainloss_pct

    # Adjust costbasis based on trigger trails

    for i in range(len(tickers)):
        if trigger_trail_types[i] == "Fixed $":
            if tda_gainloss > trigger_trails[i] or triggereds[i] == True:
                entry = tickers_db.get(tickers[i])
                entry["triggered"] = True
                # entry["costbasis"] = np.round(ticker_dict[tickers[i]]["costbasis"] - trigger_trails[i], 2)
                # entry["stoploss_type"] = "Trailing %"
                # entry["trail_pct"] = trigger_trail_trail_pcts[i]
                tda_costbasis = np.round(ticker_dict[tickers[i]]["costbasis"] + trigger_trails[i], 2)
                triggereds[i] = True
                stoploss_types[i] = "Trailing %"
                trail_pcts[i] = trigger_trail_trail_pcts[i]
                ticker_dict[tickers[i]]["triggered"] = True
                ticker_dict[tickers[i]]["costbasis"] = np.round(ticker_dict[tickers[i]]["costbasis"] + trigger_trails[i], 2)
                ticker_dict[tickers[i]]["stoploss_type"] = "Trailing %"
                ticker_dict[tickers[i]]["trail_pct"] = trigger_trail_trail_pcts[i]
                tickers_db.put(entry)
                print(f"Trailing stop loss of {trigger_trail_trail_pcts[i]}% triggered due to \
                        gainloss {tda_gainloss} > trigger_trail {trigger_trails[i]}")
        elif trigger_trail_types[i] == "Fixed %":
            if tda_gainloss_pct > trigger_trail_pcts[i] or triggereds[i] == True:
                entry = tickers_db.get(tickers[i])
                entry["triggered"] = True
                # entry["costbasis"] = np.round(ticker_dict[tickers[i]]["costbasis"] * (1 + trigger_trail_pcts[i] / 100), 2)
                # entry["stoploss_type"] = "Trailing %"
                # entry["trail_pct"] = trigger_trail_trail_pcts[i]
                tda_costbasis = np.round(ticker_dict[tickers[i]]["costbasis"] * (1 + trigger_trail_pcts[i] / 100), 2)
                triggereds[i] = True
                stoploss_types[i] = "Trailing %"
                trail_pcts[i] = trigger_trail_trail_pcts[i]
                ticker_dict[tickers[i]]["triggered"] = True
                ticker_dict[tickers[i]]["costbasis"] = np.round(ticker_dict[tickers[i]]["costbasis"] * (1 + trigger_trail_pcts[i] / 100), 2)
                ticker_dict[tickers[i]]["stoploss_type"] = "Trailing %"
                ticker_dict[tickers[i]]["trail_pct"] = trigger_trail_trail_pcts[i]
                tickers_db.put(entry)
                print(f"Trailing stop loss of {trigger_trail_trail_pcts[i]}% triggered due to \
                        gainloss of {tda_gainloss_pct}% > {trigger_trail_pcts[i]}%")
        elif trigger_trail_types[i] == "None":
            entry = ""

    # Activate checkpoints based on gainloss

    cp = 10
    for i in range(len(tickers)):
        values1 = checkpoints_db.get(tickers[i])
        for j in range(cp):
            if tickers[i] in tda_symbols_held:
                if ticker_dict[tickers[i]]["gainloss"] > ticker_dict[tickers[i]][f"activation_value{j}"] \
                and ticker_dict[tickers[i]][f"activated{j}"] != True:
                    ticker_dict[tickers[i]][f"activated{j}"] = True
                    values1[f"activated{j}"] = True
            else:
                if ticker_dict[tickers[i]][f"activated{j}"] != False:
                    ticker_dict[tickers[i]][f"activated{j}"] = False
                    values1[f"activated{j}"] = False
        checkpoints_db.put(values1)

    # Update max and min

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

    checkpoint1_exit = False
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
        bullish_entry = condition1 and condition2 and condition3==True and condition4 and condition5 and condition6
        bearish_entry = condition1 and condition2 and condition3==False and condition4 and not condition5 and condition6
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