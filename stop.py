# This file will stop our Heroku cloud server

# Required packages

import requests
import json
from db import *

# Grab Heroku token from Deta Base

deta = connect_db()
config_db = deta.Base("config_db")
heroku_token = config_db.get("HEROKU_API")['value']

# Get a list of all dynos

heroku_url = 'https://api.heroku.com'
apps_url = '{}/apps'.format(heroku_url)
app_name = 'the-process'
headers = {
    "Accept": "application/vnd.heroku+json; version=3",
    "Content-Type": "application/json", 
    "Authorization": "Bearer {}".format(heroku_token)
}
dyno_list_url_all = '{}/{}/dynos'.format(apps_url, app_name)
get_dyno_list_all = requests.get(dyno_list_url_all, headers = headers)
dyno_content = get_dyno_list_all.content
if get_dyno_list_all.status_code in [200, 201]:
    dyno_content = json.loads(dyno_content)
print(dyno_content)

# Get dyno ID from list
detached_dyno_id = [dyno for dyno in dyno_content if dyno['command'] == 'python script.py'][0]['id']
print(detached_dyno_id)

# Stop the dyno using that ID
dyno_stop_url_all = '{}/{}/dynos/{}/actions/stop'.format(apps_url, app_name, detached_dyno_id)
post_dyno_stop_all = requests.post(dyno_stop_url_all, headers = headers)
dyno_stop_all_content = json.loads(post_dyno_stop_all.content)
print(dyno_stop_all_content)