# This file contains a function to connects to our Deta base

# Import required packages

from boto.s3.connection import S3Connection 
from deta import Deta
from dotenv import load_dotenv
import os
import streamlit as st

# Connect to Deta Base (using key for secondary email)

def connect_db():
    if ".env" in os.listdir():
        env = load_dotenv(".env")
        DETA_KEY = os.getenv("DETA_KEY")
    else:
        try:
            DETA_KEY = os.environ["DETA_KEY"]
            # conn = S3Connection(DETA_KEY)
        except KeyError:
            DETA_KEY = st.secrets["DETA_KEY"]
    deta = Deta(DETA_KEY)
    return deta