# Import packages

import datetime as dt
from db import *
import json
import numpy as np
import pandas as pd
import pytz
import requests

# Database connection

deta = connect_db()
config_db = deta.Base("config_db")

# Global variables

utc = pytz.timezone('UTC')
local_timezone = pytz.timezone('US/Pacific')
tda_base = 'https://api.tdameritrade.com'
tda_access_limit = int(config_db.get("TDA_ACCESS_LIMIT")['value'])
tda_refresh = config_db.get("TDA_REFRESH")['value']
tda_api = config_db.get("TDA_API")['value']
tda_account = config_db.get("TDA_ACCOUNT")['value']

# TDA functions

def tda_authenticate():
    config_db = connect_db().Base("config_db")
    access_time_adj = int(tda_access_limit * 0.9)
    tda_access_last = pd.Timestamp(config_db.get("TDA_LAST_ACCESS")['value'], tz=utc).astimezone(local_timezone)
    tda_payload = {
        'grant_type': 'refresh_token',
        'refresh_token': tda_refresh,
        'client_id': tda_api,
    }
    tda_auth_url = '{}/v1/oauth2/token'.format(tda_base)
    now_time = dt.datetime.now(tz=local_timezone)
    minutes_since_refresh = round((now_time - tda_access_last).total_seconds() / 60, 2)
    if minutes_since_refresh > access_time_adj:
        tda_token_request = requests.post(tda_auth_url, data = tda_payload)
        tda_token_response = json.loads(tda_token_request.content)
        tda_access_token = tda_token_response['access_token']
        put_keys = ["TDA_ACCESS", "TDA_LAST_ACCESS"]
        put_values = [tda_access_token, dt.datetime.now(tz=utc).strftime("%Y-%m-%d %X")]
        for i in range(len(put_keys)):
            entry = {
                "key": put_keys[i],
                "value": put_values[i]
            }
            config_db.put(entry)
    else:
        tda_access_token = config_db.get("TDA_ACCESS")['value']
    tda_headers = {'Authorization': 'Bearer {}'.format(tda_access_token)}
    return tda_headers

def get_quote_tda(symbol="SPY"):
    quote_url = f"{tda_base}/v1/marketdata/quotes?apikey={tda_api}&symbol={symbol}"
    tda_headers = tda_authenticate()
    req = requests.get(quote_url, headers = tda_headers)
    resp = json.loads(req.content)
    return resp

def get_data_tda(ticker="SPY", periodType="day", period=10, frequencyType="minute", frequency=30, extended_hours=False):
    # periodType = day, month, year, ytd
    # period = day: 1, 2, 3, 4, 5, 10*, month: 1*, 2, 3, 6, year: 1*, 2, 3, 5, 10, 15, 20, ytd: 1*
    # frequencyType = day: minute*, month: daily, weekly*, year: daily, weekly, monthly*, ytd: daily, weekly*
    # frequency = "minute: 1*, 5, 10, 15, 30, daily: 1*, weekly: 1*, monthly: 1*"
    # ext = False
    useEpoch = False
    now = dt.datetime.now(tz=utc)
    epoch = dt.datetime.utcfromtimestamp(0)
    epoch_now_diff = now - epoch
    epoch_to_now = epoch_now_diff.days * 24 * 60 * 60 * 1000 + (epoch_now_diff.seconds * 1000) + (int(epoch_now_diff.microseconds / 1000))
    then = now - dt.timedelta(days=1)
    epoch_then_diff = then - epoch
    epoch_to_then = epoch_then_diff.days * 24 * 60 * 60 * 1000 + (epoch_then_diff.seconds * 1000) + (int(epoch_then_diff.microseconds / 1000))
    startDate = epoch_to_then
    endDate = epoch_to_now
    data_url = f"{tda_base}/v1/marketdata/{ticker}/pricehistory?apikey={tda_api}&frequencyType={frequencyType}&frequency={frequency}&needExtendedHoursData={extended_hours}&endDate={endDate}"
    if useEpoch:
        data_url = data_url + f"&startDate={startDate}"
    else:
        data_url = data_url + f"&periodType={periodType}&period={period}"
    tda_headers = tda_authenticate()
    req = requests.get(data_url, headers = tda_headers)
    resp = json.loads(req.content)
    bars = resp['candles']
    return bars

def get_positions_tda():
    tda_headers = tda_authenticate()
    tda_account_url = '{}/v1/accounts/{}'.format(tda_base, tda_account)
    tda_positions_url = '{}?fields=positions'.format(tda_account_url)
    tda_positions_request = requests.get(tda_positions_url, headers = tda_headers)
    tda_positions_content = json.loads(tda_positions_request.content)
    positions = []
    if 'positions' in tda_positions_content['securitiesAccount']:
        positions = tda_positions_content['securitiesAccount']['positions']
    # else:
    #     positions = [{
    #         "instrument": {
    #             "symbol": "None"
    #         },
    #         "longQuantity": 0,
    #         "shortQuantity": 0,
    #         "averagePrice": 0,
    #         "marketValue": 0,
    #         "currentDayProfitLossPercentage": 0
    #     }]
    return positions

def get_orders_tda():
    tda_headers = tda_authenticate()
    tda_history_url = '{}/v1/accounts/{}/transactions'.format(tda_base, tda_account)
    tda_history_request = requests.get(tda_history_url, headers = tda_headers)
    tda_history_content = json.loads(tda_history_request.content)
    orders = []
    if len(tda_history_content) < 1:
        orders = [{
            "orderDate": "1/1/2000 12:00:00",
            "transactionItem": {
                "instrument": {
                    "symbol": "none"
                },
                "instruction": "none",
                "amount": 0,
                "price": 0
            }
        }]
    else:
        orders = [item for item in tda_history_content if item['type'] == 'TRADE']
    return orders

def get_hours_tda():
    tda_headers = tda_authenticate()
    # market_date = dt.datetime.now().strftime('%Y-%m-%d')
    # tda_hours_url = '{}/v1/marketdata/EQUITY/hours?apikey={}&date={}'.format(tda_base, tda_api, market_date)
    # tda_hours_content = json.loads(requests.get(tda_hours_url, headers = tda_headers).content)
    # market_open = pd.to_datetime(tda_hours_content['equity']['EQ']['sessionHours']['regularMarket'][0]['start'])
    # market_close = pd.to_datetime(tda_hours_content['equity']['EQ']['sessionHours']['regularMarket'][0]['end'])
    # if market_close > dt.datetime.now(tz=local_timezone) > market_open:
    #     market_is_open = True
    # else:
    #     market_is_open = False
    # return market_is_open
    current_time = dt.datetime.now(tz=local_timezone)
    market = "EQUITY"
    tda_hours_url = '{}/v1/marketdata/{}/hours?apikey={}'.format(tda_base, market, tda_api)
    tda_hours_request = requests.get(tda_hours_url, headers = tda_headers)
    if tda_hours_request.status_code != 200:
        tda_hours_content = tda_hours_request.content
        print(tda_hours_content)
        closing_time = current_time
        market_is_open = False
    else:
        tda_hours_content = json.loads(tda_hours_request.content)
        if 'EQ' in list(tda_hours_content['equity'].keys()):
            closing_time = pd.to_datetime(tda_hours_content['equity']['EQ']['sessionHours']['regularMarket'][0]['end']).astimezone(local_timezone)
            market_is_open = tda_hours_content['equity']['EQ']['isOpen']
        else:
            closing_time = current_time
            market_is_open = False
    return (market_is_open, closing_time, current_time)

def get_chain_tda(ticker):
    result = {}
    contract_type = "ALL" # ALL (default), CALL, PUT
    tickers_db = connect_db().Base("tickers_db")
    delta_min = int(tickers_db.get(ticker)['delta_min'])
    delta_min = 90
    strike_count = 3
    from50 = np.round(abs(1 - delta_min / 50), 2)
    while from50 > 0:
        strike_count += 2
        from50 = np.round(from50 - 0.05, 2)
    moneyness = "ALL" # ITM, NTM, OTM, SAK, SBK, SNK, ALL
    now = dt.datetime.now()
    dte_min = int(tickers_db.get(ticker)['dte_min'])
    from_date = (now - dt.timedelta(days=dte_min)).strftime("%Y-%m-%d")
    to_date = (now + dt.timedelta(days=dte_min+32)).strftime("%Y-%m-%d")
    chain_url = f'{tda_base}/v1/marketdata/chains?apikey={tda_api}&symbol={ticker}&contractType={contract_type} \
                &includeQuotes=false&strikeCount={strike_count}&range={moneyness}&fromDate={from_date}&toDate={to_date} \
                &optionType=S'
    tda_headers = tda_authenticate()
    tda_chain_request = requests.get(chain_url, headers = tda_headers)
    if tda_chain_request.status_code != 200:
        print("Error: TDA status code")
        tda_chain_content = tda_chain_request.content
    else:
        tda_chain_content = json.loads(tda_chain_request.content)
        if tda_chain_content['status'] != 'FAILED':
            calls = tda_chain_content['callExpDateMap']
            call_exps = list(calls.keys())
            call_exp = call_exps[0]
            call_strikes = list(calls[call_exp].keys())
            call_strikes = list(reversed(call_strikes))
            call_strike = 0
            i = 0
            while i < len(call_strikes):
                call = calls[call_exp][call_strikes[i]][0]
                call_delta = np.round(abs(float(call['delta'])) * 100)
                if call_delta > delta_min:
                    call_strike = call_strikes[i]
                    break
                i += 1
            puts = tda_chain_content['putExpDateMap']
            put_exps = list(puts.keys())
            put_exp = put_exps[0]
            put_strikes = list(puts[put_exp].keys())
            put_strike = 0
            i = 0
            while i < len(put_strikes):
                put = puts[put_exp][put_strikes[i]][0]
                put_delta = np.round(abs(float(put['delta'])) * 100)
                if put_delta > delta_min:
                    put_strike = put_strikes[i]
                    break
                i += 1
            
    result = {
        "put": put['symbol'],
        "call": call['symbol']
    }
    return result

def tda_submit_order(instruction, quantity, symbol, assetType="OPTION"):
    tda_orders_url = '{}/v1/accounts/{}/orders'.format(tda_base, tda_account)
    data = {
        "orderType": "MARKET",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
            "instruction": instruction,
            "quantity": quantity,
            "instrument": {
                "symbol": symbol,
                "assetType": assetType # EQUITY or OPTION
            }
            }
        ]
    }
    tda_headers = tda_authenticate()
    r = requests.post(tda_orders_url, json=data, headers = tda_headers)
    if r.status_code in [200, 201]:
        print(f"{r.status_code}: {r.content}")
        return r.content
    else:
        print(f"{r.status_code}: {json.loads(r.content)}")
        return json.loads(r.content)