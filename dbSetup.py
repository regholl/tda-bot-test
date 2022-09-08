# Run this file once to create database tables

# Import packages

from db import *
import streamlit_authenticator as stauth
import os

# Connect to database

deta = connect_db()
config_db = deta.Base("config_db")
users_db = deta.Base("users_db")
tickers_db = deta.Base("tickers_db")

# Fetch existing entries in config_db and delete them

# items = config_db.fetch().items
# keys = [item['key'] for item in items]
# for key in keys:
#     config_db.delete(key)

# Fetch existing entries in users_db and delete them

# items = users_db.fetch().items
# keys = [item['key'] for item in items]
# for key in keys:
#     users_db.delete(key)

# Fetch existing entries in tickers_db and delete them

items = tickers_db.fetch().items
keys = [item['key'] for item in items]
for key in keys:
    tickers_db.delete(key)

# Define user properties and insert into database

usernames = ["will", "tyler"]
names = ["Will", "Tyler"]
passwords = ["tradebot", "tdabot"]
hashed_passwords = stauth.Hasher(passwords).generate() # Encrypt passwords

for i in range(len(usernames)):
    entry = {
        "key": usernames[i], 
        "name": names[i], 
        "password": hashed_passwords[i]
    }
    users_db.put(entry)

# Setup config database

config_keys = ["DETA_NAME", "HEROKU_API", "TDA_API", "TDA_REFRESH", "TDA_ACCOUNT"]
config_values = [os.getenv(key) for key in config_keys]
config_keys = config_keys + ["TDA_ACCESS", "TDA_LAST_ACCESS", "TDA_LAST_REFRESH", "TDA_ACCESS_LIMIT", "BOT_ON", "PAUSE_TIME", "PAUSE_UNIT"]
config_values = config_values + ["asfdasdf", "8/8/2022 20:54:30", "8/18/2022 19:08:26", "30", True, "5", "minute"]

for i in range(len(config_keys)):
    entry = {
        "key": config_keys[i],
        "value": config_values[i]
    }
    config_db.put(entry)

# Setup tickers database

tickers = ["F", "NOK"]
period_types = ["day"] * len(tickers)
periods = [10] * len(tickers)
frequency_types = ["minute"] * len(tickers)
frequencies = [10] * len(tickers)
extended_hours = [False] * len(tickers)
ema_lengths = [100] * len(tickers)
hma_lengths = [7] * len(tickers)
contracts = [1] * len(tickers)
stoplosses = [1000] * len(tickers)
stoploss_pcts = [10] * len(tickers)
trail_pcts = [10] * len(tickers)
use_pct_stops = [False] * len(tickers)
use_trail_stops = [False] * len(tickers)
dte_mins = [0] * len(tickers)
delta_mins = [50] * len(tickers)
maxes = [0] * len(tickers)
mins = [0] * len(tickers)
trigger_trails = [100000] * len(tickers)
trigger_trail_pcts = [100] * len(tickers)
take_profits = [1000] * len(tickers)
take_profit_pcts = [100] * len(tickers)
use_pct_profits = [False] * len(tickers)

for i in range(len(tickers)):
    entry = {
        "key": tickers[i], 
        "period_type": period_types[i], 
        "period": periods[i],
        "frequency_type": frequency_types[i],
        "frequency": frequencies[i],
        "extended_hours": extended_hours[i],
        "ema_length": ema_lengths[i],
        "hma_length": hma_lengths[i],
        "contracts": contracts[i],
        "stoploss": stoplosses[i],
        "stoploss_pct": stoploss_pcts[i],
        "trail_pct": trail_pcts[i],
        "use_trail_stop": use_trail_stops[i],
        "use_pct_stop": use_pct_stops[i],
        "dte_min": dte_mins[i],
        "delta_min": delta_mins[i],
        "max": maxes[i],
        "min": mins[i],
        "trigger_trail": trigger_trails[i],
        "trigger_trail_pct": trigger_trail_pcts[i],
        "take_profit": take_profits[i],
        "take_profit_pct": take_profit_pcts[i],
        "use_pct_profit": use_pct_profits[i]
    }
    tickers_db.put(entry)

print("Deta updated")