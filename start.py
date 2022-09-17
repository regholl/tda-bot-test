# This file will start our Heroku cloud server

# Required packages

import requests
import json
from db import *

# Grab Heroku token from Deta Base

deta = connect_db()
config_db = deta.Base("config_db")
heroku_token = config_db.get("HEROKU_API")['value']

# URL and headers info

heroku_url = 'https://api.heroku.com'
apps_url = '{}/apps'.format(heroku_url)
app_name = 'the-process'
headers = {
    "Accept": "application/vnd.heroku+json; version=3",
    "Content-Type": "application/json", 
    "Authorization": "Bearer {}".format(heroku_token)
}

# Start the dyno

run_script = {"command": "python script.py",
              "type": "run:detached"}
dyno_create_url_all = '{}/{}/dynos'.format(apps_url, app_name)
post_dyno_all = requests.post(dyno_create_url_all, data = json.dumps(run_script), headers = headers)
post_dyno_all_content = json.loads(post_dyno_all.content)
print(post_dyno_all_content)