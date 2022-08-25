# Run this file once to create database tables

# Import packages

from boto.s3.connection import S3Connection
from deta import Deta
from dotenv import load_dotenv
import streamlit_authenticator as stauth
import os

# Connect to database

def connect_db():
    env = load_dotenv(".env")
    if env:
        DETA_KEY = os.getenv("DETA_KEY")
    else:
        DETA_KEY = S3Connection(os.environ['DETA_KEY'])
    deta = Deta(DETA_KEY)
    return deta

deta = connect_db()
config_db = deta.Base("config_db")
users_db = deta.Base("users_db")
tickers_db = deta.Base("tickers_db")

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

# Fetch existing entries and delete them

# items = config_db.fetch().items
# keys = [item['key'] for item in items]
# for key in keys:
#     config_db.delete(key)

# Setup config database

config_keys = ["DETA_NAME", "HEROKU_API", "TDA_API", "TDA_REFRESH", "TDA_ACCOUNT"]
config_values = [os.getenv(key) for key in config_keys]
config_keys = config_keys + ["TDA_ACCESS", "TDA_LAST_ACCESS", "TDA_LAST_REFRESH", "TDA_ACCESS_LIMIT"]
config_values = config_values + ["asfdasdf", "8/8/2022 20:54:30", "8/18/2022 19:08:26", "30"]

for i in range(len(config_keys)):
    entry = {
        "key": config_keys[i],
        "value": config_values[i]
    }
    config_db.put(entry)

# Setup tickers database

tickers = ["SWN", "SNAP", "WBD"]
period_types = ["day"] * len(tickers)
periods = [10] * len(tickers)
frequency_types = ["minute"] * len(tickers)
frequencies = [30] * len(tickers)
extended_hours = [False] * len(tickers)
ema_lengths = [10] * len(tickers)
hma_lengths = [7] * len(tickers)
contracts = [1] * len(tickers)
stoplosses = [1000] * len(tickers)
stoploss_pcts = [10] * len(tickers)
trailing_pcts = [10] * len(tickers)
use_pcts = [False] * len(tickers)
use_trailings = [False] * len(tickers)
dte_mins = [0] * len(tickers)
delta_mins = [50] * len(tickers)

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
        "trailing_pct": trailing_pcts[i],
        "use_trailing": use_trailings[i],
        "use_pct": use_pcts[i],
        "dte_min": dte_mins[i],
        "delta_min": delta_mins[i],
    }
    tickers_db.put(entry)