import os
import re
import csv
import time
import pickle
import threading
import datetime

from my_package.classes.sqlite_database import Database as Db
from my_package.classes.flask_cache import ArrayFlaskCache as Cache

from .support_functions import *

from flask import Flask, render_template, url_for, Response, request, jsonify

app = Flask(__name__)
app.local_vars = {}

CACHE = None
DATABASE = None

def check_init(force=False):
    global DATABASE, CACHE

    status = False
    try:
        if not CACHE or force:
            db_file = app.local_vars.get('DB_FILE')
            status, *over = init_config(DATABASE, CACHE, db_file=db_file)
            if len(over): DATABASE, CACHE = over
    except:
        pass
    
    if DATABASE and CACHE:
        status = True

    return status

@app.route('/', methods=['GET'])
def main_page():
    status = check_init()
    if not status: return conf_page()
    
    data_list = CACHE.objects

    pages = paginator(data_list)
    if request.args.get('page') and str(request.args.get('page')).isnumeric():
        data_list = pages[int(request.args.get('page'))]
        data_list = {item[0]: item[1] for item in data_list}
        pages_list = list(pages)
    elif pages.get(1):
        data_list = pages[1]
        data_list = {item[0]: item[1] for item in data_list}
        pages_list = list(pages)
    else:
        data_list = CACHE.objects
        pages_list = []

    current_page = (request.args.get('page') or 1)
    return render_template('accountingList.html', data=data_list, pages=pages_list, current_page=current_page)

@app.route('/conf', methods=['GET'])
def conf_page():
    return render_template('conf.html')

@app.route('/conf/send', methods=['POST'])
def conf_send_page():
    db_file = app.local_vars.get('DB_FILE')
    status = accept_config(request.form, db_file=db_file)
    return jsonify({'status': status})

@app.route('/conf/init', methods=['POST'])
def conf_init_page():
    status = check_init(force=True)
    return jsonify({'status': status})

@app.route('/conf/status', methods=['GET'])
def conf_status_page():
    return jsonify({'db_status': bool(DATABASE),
                    'cache_status': bool(CACHE),
                    'cache_len': (int(bool(CACHE)) and CACHE.max_index)})

@app.route('/<name>', methods=['GET'])
def detail_page(name):
    return Response(response='Тут теперь ничего нет :(', status=200)

@app.route('/<name>/remove', methods=['POST'])
def remove_page(name):
    status = remove_element(name, CACHE)
    return jsonify({'status': status})

@app.route('/<name>/add', methods=['POST'])
def add_page(name):
    check_init()
    status = add_element(request.form, CACHE)
    return jsonify({'status': status})

@app.route('/<name>/edit', methods=['GET','POST'])
def edit_page(name):
    check_init()
    return render_template('edit.html')

@app.route('/<name>/get', methods=['GET'])
def get_page(name):
    check_init()

    try: data = CACHE.get(name)
    except: data = {}

    return jsonify(data)

@app.route('/help')
def help_me():
    return Response(response='Help here!', status=200)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=6001, threaded=True)