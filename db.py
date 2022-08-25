# Import required packages

from boto.s3.connection import S3Connection 
from deta import Deta
from dotenv import load_dotenv
import os

# Connect to Deta Base

def connect_db():
    if ".env" in os.listdir():
        env = load_dotenv(".env1")
    else:
        conn = S3Connection(os.environ['DETA_KEY'])
    DETA_KEY = os.getenv("DETA_KEY")
    deta = Deta(DETA_KEY)
    return deta