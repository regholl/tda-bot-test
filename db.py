# Import required packages

from boto.s3.connection import S3Connection 
from deta import Deta
from dotenv import load_dotenv
import os

# Connect to Deta Base

def connect_db():
    if ".env" in os.listdir():
        env = load_dotenv(".env")
        DETA_KEY = os.getenv("DETA_KEY")
    else:
        DETA_KEY = os.environ["DETA_KEY"]
        # conn = S3Connection(DETA_KEY)
    deta = Deta(DETA_KEY)
    return deta