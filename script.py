# This is the main file that executes the automated trades. Everything else is a supporting document.

# Import required packages

import datetime as dt
from db import *
import math
import numpy as np
import pandas as pd
import ta
from tda import *
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
    extended_hours = [item["extended_hours"] for item in tickers_info]
    ema_lengths = [item["ema_length"] for item in tickers_info]
    hma_lengths = [item["hma_length"] for item in tickers_info]
    contracts = [item["contracts"] for item in tickers_info]
    stoplosses = [item["stoploss"] for item in tickers_info]
    stoploss_pcts = [item["stoploss_pct"] for item in tickers_info]
    trailing_pcts = [item["trailing_pct"] for item in tickers_info]
    use_pcts = [item["use_pct"] for item in tickers_info]
    use_trailings = [item["use_trailing"] for item in tickers_info]

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

        # Fetch ticker data settings from Deta

        idx = tickers.index(ticker)
        periodType = tickers_info[idx]['period_type']
        period = int(tickers_info[idx]['period'])
        frequencyType = tickers_info[idx]['frequency_type']
        frequency = int(tickers_info[idx]['frequency'])
        extended_hours = tickers_info[idx]['extended_hours']

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

        if market_open:
            last_close = tda_closes[len(tda_closes)-2]
            last_open = tda_opens[len(tda_opens)-2]
        else:
            last_close = tda_closes[len(tda_closes)-1]
            last_open = tda_opens[len(tda_opens)-1]
        if last_close > last_open:
            bullish_candle = True
        else:
            bullish_candle = False
        bullish_candles.append(bullish_candle)

        # Create dataframe

        df = pd.DataFrame()
        df['open'] = tda_opens
        df['high'] = tda_highs
        df['low'] = tda_lows
        df['close'] = tda_closes

        # Calculate indicators

        ema_window = tickers_info[idx]['ema_length']
        emas_all = np.round(ta.trend.ema_indicator(pd.to_numeric(df['close']), window=ema_window), 2)
        ema = emas_all[len(emas_all)-1]
        emas.append(ema)

        hma_window = tickers_info[idx]['hma_length']
        hma1 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=int(hma_window/2))
        hma2 = ta.trend.wma_indicator(pd.to_numeric(df['close']), window=hma_window)
        hma_raw = (2 * hma1) - hma2
        hmas_all = np.round(ta.trend.wma_indicator(hma_raw, window=math.floor(math.sqrt(hma_window))), 2)
        hma = hmas_all[len(hmas_all)-1]
        hmas.append(hma)

        # Bullish or bearish HMA

        if market_open:
            last_hma = hmas_all[len(hmas_all)-2]
            last_hma1 = hmas_all[len(hmas_all)-3]
        else:
            last_hma = hmas_all[len(hmas_all)-1]
            last_hma1 = hmas_all[len(hmas_all)-1]
        if last_hma > last_hma1:
            bullish_hma = True
        else:
            bullish_hma = False
        bullish_hmas.append(bullish_hma)

        # Get option symbols

        chain = get_chain_tda(ticker)
        chains.append(chain)

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
        tda_tickers_held = []
        tda_average_prices = []
        tda_market_values = []
        tda_long_shares = []
        tda_short_shares = []
        tda_quantities = []
    tda_quantities = [int(abs(qty)) for qty in tda_quantities]

    # Get quotes for option tickers

    lasts_option = []
    for ticker in tda_tickers_held:
        quote = get_quote_tda(ticker)
        last_option = np.round(float(quote[ticker]['lastPrice']), 2)
        lasts_option.append(last_option)

    # Adjust tickers for optional holdings

    tda_symbols_held = []
    for ticker in tda_tickers_held:
        symb = ticker
        if "_" in ticker:
            symb = ticker.split("_")[0]
        tda_symbols_held.append(symb)
    held_symbol_dict = dict(zip(tda_symbols_held, tda_tickers_held))

    # Calculate gainloss from quotes and average prices

    tda_gainlosses, tda_costbases, tda_gainloss_pcts = [], [], []
    for ticker in tickers:
        if ticker in tda_symbols_held:
            idx = tda_symbols_held.index(ticker)
            if tda_long_shares[idx] > 0:
                if held_symbol_dict[ticker] == ticker:
                    tda_costbasis = np.round(tda_average_prices[idx] * tda_long_shares[idx], 2)
                else:
                    tda_costbasis = np.round(tda_average_prices[idx] * tda_long_shares[idx] * 100, 2)
                tda_gainloss = np.round(tda_market_values[idx] - tda_costbasis, 2)
                tda_gainloss_pct = np.round(tda_gainloss / tda_costbasis * 100, 2)
            elif tda_short_shares[idx] > 0:
                if held_symbol_dict[ticker] == ticker:
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
        
    # Map watchlist data to positions data

    ticker_quantity_dict = dict(zip(tda_tickers_held, tda_quantities))
    ticker_gainloss_dict = dict(zip(tickers, tda_gainlosses))
    ticker_gainloss_pct_dict = dict(zip(tickers, tda_gainloss_pcts))
    stoploss_dict, stoploss_pct_dict, trailing_pct_dict, use_pct_dict, use_trailing_dict = {}, {}, {}, {}, {}
    for i in range(len(tickers)):
        if tickers[i] in tda_symbols_held:
            idx = tda_symbols_held.index(tickers[i])
            # costbasis = tda_costbases[idx]
            stoploss = tickers_info[idx]['stoploss']
            stoploss_pct = tickers_info[idx]['stoploss_pct']
            trailing_pct = tickers_info[idx]['trailing_pct']
            use_pct = tickers_info[idx]['use_pct']
            use_trailing = tickers_info[idx]['use_trailing']
            # max_loss_adj = np.round(costbasis * max_loss / 100, 2)
            stoploss_dict[tickers[i]] = stoploss
            stoploss_pct_dict[tickers[i]] = stoploss_pct
            trailing_pct_dict[tickers[i]] = trailing_pct
            use_pct_dict[tickers[i]] = use_pct
            use_trailing_dict[tickers[i]] = use_trailing
        
    # Get recent orders

    tda_orders = get_orders2_tda()
    time_now = dt.datetime.now(utc)
    recent_orders = [order for order in tda_orders if (time_now - pd.to_datetime(order['enteredTime'])).seconds < 60 * 5]
    recent_opt_tickers = [order['orderLegCollection'][0]['instrument']['symbol'] for order in recent_orders]
    recent_tickers = [ticker.split("_")[0] for ticker in recent_opt_tickers]
    
    # Calculate time and make dictionaries
    
    current_time = dt.datetime.now(tz=local_timezone)
    minutes_until_close = np.round((closing_time - current_time).total_seconds() / 60, 2)
    wl_tickers_held = list(set(tickers).intersection(tda_symbols_held))
    ticker_long_dict = dict(zip(tda_tickers_held, tda_long_shares))
    ticker_short_dict = dict(zip(tda_tickers_held, tda_short_shares))
    ticker_gainloss_dict = dict(zip(tickers, tda_gainlosses))

    # Exit order

    for i in range(len(tickers)):
        # condition1 = market_open
        condition1 = 0 < minutes_until_close < 450
        condition2 = tickers[i] in tda_symbols_held
        if condition2:
            if use_pcts[i]:
                pct_limit = np.negative(stoploss_pct_dict[tickers[i]])
                pct_real = ticker_gainloss_pct_dict[tickers[i]]
                condition3 = pct_limit > pct_real
            else:
                stop_limit = np.negative(stoploss_dict[tickers[i]])
                stop_real = ticker_gainloss_dict[tickers[i]]
                condition3 = stop_limit > stop_real
            exit_symbol = held_symbol_dict[tickers[i]]
            exit_quantity = ticker_quantity_dict[exit_symbol]
            stoploss_exit = condition1 and condition2 and condition3
            condition4 = "C" in exit_symbol.split("_")[1]
            condition5 = bullish_candles[i]
            call_exit = condition1 and condition2 and condition4 and not condition5
            put_exit = condition1 and condition2 and not condition4 and condition5
            if stoploss_exit or call_exit or put_exit:
                # time.sleep(5)
                exit_order = tda_submit_order("SELL_TO_CLOSE", exit_quantity, exit_symbol)
                tda_symbols_held.remove(tickers[i])
                exit_log = f"Closing out {exit_quantity} contracts of {exit_symbol} due to"
                if stoploss_exit:
                    exit_log = exit_log + f" stop loss {stop_limit} > {stop_real}"
                elif call_exit:
                    exit_log = exit_log + f" bearish candle while holding call"
                elif put_exit:
                    exit_log = exit_log + f" bullish candle while holding put"
                print(exit_log)

    # Entry order

    for i in range(len(tickers)):
        # condition1 = market_open
        condition1 = 0 < minutes_until_close < 450
        condition2 = tickers[i] not in tda_symbols_held
        condition3 = bullish_candles[i]
        condition4 = bullish_hmas[i]
        condition5 = tickers[i] not in recent_tickers
        bullish_entry = condition1 and condition2 and condition3 and condition4 and condition5
        bearish_entry = condition1 and condition2 and not condition3 and not condition4 and condition5
        if bullish_entry:
            entry_symbol = chains[i]['call']
            entry_order = tda_submit_order("BUY_TO_OPEN", contracts[i], entry_symbol)
            print(f"Bullish entry: Buying {contracts[i]} contracts of {entry_symbol}")
        if bearish_entry:
            entry_symbol = chains[i]['put']
            entry_order = tda_submit_order("BUY_TO_OPEN", contracts[i], entry_symbol)
            print(f"Bearish entry: Buying {contracts[i]} contracts of {entry_symbol}")

    # Print log

    now = dt.datetime.now(tz=local_timezone).strftime("%Y-%m-%d %X")
    time_end = time.time()
    time_total = np.round(time_end - time_start, 2)
    global log_count
    log_count += 1
    if log_count % 30 == 0:
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
            ["Trailing pcts",f" = {trailing_pcts}"],
            ["Use pct?",f" = {use_pcts}"],
            ["Use trailing?",f" = {use_trailings}"],
            ["Gainloss",f" = {tda_gainlosses}"],
            ["Gainloss Pct",f" = {tda_gainloss_pcts}"],
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