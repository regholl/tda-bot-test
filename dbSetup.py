# This file creates several tables in our Deta base with the below default values; run only once

# Import packages

from db import *
import streamlit_authenticator as stauth
import os

# Connect to database

deta = connect_db()
config_db = deta.Base("config_db")
users_db = deta.Base("users_db")
tickers_db = deta.Base("tickers_db")
checkpoints_db = deta.Base("checkpoints_db")

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

# Fetch existing entries in checkpoints_db and delete them

items = checkpoints_db.fetch().items
keys = [item['key'] for item in items]
for key in keys:
    checkpoints_db.delete(key)

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
config_keys = config_keys + ["TDA_ACCESS", "TDA_LAST_ACCESS", "TDA_LAST_REFRESH", "TDA_ACCESS_LIMIT", "BOT_ON"]
config_values = config_values + ["asfdasdf", "8/8/2022 20:54:30", "8/18/2022 19:08:26", "30", True]

for i in range(len(config_keys)):
    entry = {
        "key": config_keys[i],
        "value": config_values[i]
    }
    config_db.put(entry)

# Setup tickers database

tickers = ["F", "LCID"]
# Market data
use_closes = [False] * len(tickers)
extended_hours = [False] * len(tickers)
frequencies = [5] * len(tickers)
frequency_types = ["minute"] * len(tickers)
periods = [10] * len(tickers)
period_types = ["day"] * len(tickers)
# Candles
candle_types = ["Heikin Ashi"] * len(tickers)
wick_requirements = ["Any wick okay"] * len(tickers)
# Indicators
indicators_entry = [["HMA", "EMA"]] * len(tickers)
indicators_exit = [["HMA", "EMA"]] * len(tickers)
ema_lengths = [100] * len(tickers)
hma_lengths = [7] * len(tickers)
# Option contract
order_types = ["MARKET"] * len(tickers)
option_types = ["Both calls and puts"] * len(tickers)
contracts = [1] * len(tickers)
delta_mins = [50] * len(tickers)
dte_mins = [0] * len(tickers)
# Time
confirm_times = [5] * len(tickers)
confirm_units = ["second"] * len(tickers)
pause_times = [5] * len(tickers)
pause_units = ["minute"] * len(tickers)
# Stoploss
stoploss_types = ["Fixed $"] * len(tickers)
stoplosses = [1000] * len(tickers)
stoploss_pcts = [10] * len(tickers)
trail_pcts = [10] * len(tickers)
# Take profit
take_profit_types = ["Fixed $"] * len(tickers)
take_profits = [1000] * len(tickers)
take_profit_pcts = [100] * len(tickers)
# Trailing triggers
trigger_trail_types = ["Fixed $"] * len(tickers)
trigger_trails = [100000] * len(tickers)
trigger_trail_pcts = [100] * len(tickers)
trigger_trail_trail_pcts = [100] * len(tickers)
# Other
maxes = [0] * len(tickers)
mins = [0] * len(tickers)
times_in_candles = [0] * len(tickers)
triggereds = [False] * len(tickers)

for i in range(len(tickers)):
    entry = {
        "candle_type": candle_types[i],
        "confirm_time": confirm_times[i],
        "confirm_unit": confirm_units[i],
        "contracts": contracts[i],
        "delta_min": delta_mins[i],
        "dte_min": dte_mins[i],
        "ema_length": ema_lengths[i],
        "extended_hours": extended_hours[i],
        "frequency_type": frequency_types[i],
        "frequency": frequencies[i],
        "hma_length": hma_lengths[i],
        "indicator_entry": indicators_entry[i],
        "indicator_exit": indicators_exit[i],
        "key": tickers[i], 
        "max": maxes[i],
        "min": mins[i],
        "option_type": option_types[i],
        "order_type": order_types[i],
        "pause_time": pause_times[i],
        "pause_unit": pause_units[i],
        "period_type": period_types[i], 
        "period": periods[i],
        "stoploss": stoplosses[i],
        "stoploss_pct": stoploss_pcts[i],
        "stoploss_type": stoploss_types[i],
        "take_profit": take_profits[i],
        "take_profit_pct": take_profit_pcts[i],
        "take_profit_type": take_profit_types[i],
        "trail_pct": trail_pcts[i],
        "trigger_trail": trigger_trails[i],
        "trigger_trail_pct": trigger_trail_pcts[i],
        "trigger_trail_trail_pct": trigger_trail_trail_pcts[i],
        "trigger_trail_type": trigger_trail_types[i],
        "triggered": triggereds[i],
        "time_in_candle": times_in_candles[i],
        "use_close": use_closes[i],
        "wick_requirement": wick_requirements[i],
    }
    tickers_db.put(entry)

# Set up checkpoints database

cp = 10

checkpoint_on = False
activation_value = 100
exit_value = 80
activated = False

gain_type = "None"
gain_amount = 1000
gain_pct = 10
contract_nbr = 1

entry = {}
for i in range(len(tickers)):
    entry["key"] = tickers[i]
    for j in range(cp):
        entry[f"checkpoint_on{j}"] = checkpoint_on
        entry[f"activation_value{j}"] = activation_value
        entry[f"exit_value{j}"] = exit_value
        entry[f"activated{j}"] = activated
        entry[f"gain_type{j}"] = gain_type
        entry[f"gain_amount{j}"] = gain_amount
        entry[f"gain_pct{j}"] = gain_pct
        entry[f"contract_nbr{j}"] = contract_nbr
    checkpoints_db.put(entry)

# Finish

print("Deta updated")