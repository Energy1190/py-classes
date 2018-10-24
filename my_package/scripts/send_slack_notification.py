import json
import socket
import requests
from datetime import datetime

def main(url, title, color=None, date=None, host=None, msg=None, traceback=None):
    # color = good | warning | danger | hex #000000
    if not color: color = 'warning'
    if not date: date = datetime.now()
    if not host: host = socket.gethostname()
    if not msg: msg = 'No description.'
    if not traceback: traceback = 'No traceback.'

    headers = {'Content-type': 'application/json'}
    body = {"attachments": [{"title": str(title),
                            "color": color,
                            "mrkdwn_in": ["text"],
                            "fields":[{"title": "Date", "value": str(date), "short": True},
                                      {"title": "Host", "value": str(host), "short": True},
                                      {"title": "Description", "value": str(msg), "short": True},
                                      {"title": "Traceback", "value": str(traceback), "short": True}]
                            }]}

    try: responce = requests.post(url, data=json.dumps(body), headers=headers)
    except: return None

    return responce
