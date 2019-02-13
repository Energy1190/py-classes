import os
import re
import csv
import time
import json
import pickle
import threading
import zipfile
import datetime

from os.path import basename
from flask import Flask, render_template, url_for, Response, request, jsonify, send_from_directory
from .store import SftpConfig, OutputData

data_path = (os.environ.get('DB_PATH') or 'data')
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = data_path
sftp_config = SftpConfig((os.environ.get('DB_FILE') or '.sftp'))
thread_files = []

def thread_remove_zip(filepath, thread_files, *args):
    if filepath in thread_files: return False
    thread_files.append(filepath)
    time.sleep(3600)
    os.remove(filepath)
    thread_files.remove(filepath)

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file), basename(os.path.join(root, file)))

def validate_forms(data):
    error_flag = False
    required_keys = ["InputHost", "InputPort", "InputLogin", "InputPassword"]
    if len([item for item in data if item not in required_keys]): error_flag = True
    if len([item for item in data if not data[item]]): error_flag = True
    if not str(data.get("InputPort")).isnumeric(): error_flag = True
    return error_flag

@app.route('/api/v1/upload', methods=['POST'])
def upload_file():
    return Response('Hello', 200)

@app.route('/api/v1/files/<path:filename>', methods=['GET'])
def files_operation_get(filename):
    global thread_files
    current = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current, app.config['UPLOAD_FOLDER'])
    if '/' in filename:
        add_to_path = filename.split('/')[:1]
        filename = filename.split('/')[-1]
        file_path = os.path.join(file_path, *add_to_path)

    if os.path.isdir(os.path.join(file_path,filename)):
        filename_tmp = '{}.zip'.format(filename)
        file_path_tmp = file_path.replace(data_path, 'tmp')
        zipf = zipfile.ZipFile(os.path.join(file_path_tmp,filename_tmp), 'w', zipfile.ZIP_DEFLATED)
        zipdir(os.path.join(file_path,filename), zipf)
        zipf.close()

        file_path = file_path_tmp
        threading.Thread(target=thread_remove_zip,args=(os.path.join(file_path,filename_tmp), thread_files)).start()
        return send_from_directory(directory=file_path, filename=filename_tmp)

    return send_from_directory(directory=file_path, filename=filename, mimetype='application/octet-stream')

@app.route('/api/v1/files/<path:filename>', methods=['POST', 'DELETE'])
def files_operation_post(filename):
    global sftp_object, sftp_status
    current = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current, app.config['UPLOAD_FOLDER'])
    path_to_upload = file_path
    if '/' in filename:
        add_to_path = filename.split('/')[:-1]
        filename = filename.split('/')[-1]
        file_path = os.path.join(file_path, *add_to_path)

        for directory in add_to_path:
            path_to_upload = os.path.join(path_to_upload, directory)
            if not os.path.exists(path_to_upload):
                os.mkdir(path_to_upload)

    file_path = os.path.join(file_path, filename)
    if request.method == 'DELETE':
        if os.path.isdir(file_path): os.rmdir(file_path)
        else: os.remove(file_path)
        return Response('Ok', 200)

    if request.data:
        upload_file = open(file_path, 'wb')
        upload_file.write(request.data)
        upload_file.close()

    return Response('Ok', 200)

@app.route('/api/v1/local')
def get_local_catalog():
    data = []
    global sftp_object, sftp_status
    if sftp_status and sftp_object:
        sftp_object.build_local_map()
        object = OutputData(sftp_object.local_map, '/api/v1/files')
        data = object.generate()
    return jsonify(data)

@app.route('/api/v1/connect', methods=['POST'])
def connect_to_server():
    global sftp_object, sftp_status
    connection = 0
    if sftp_status and sftp_object:
        sftp_object._connect()
        if not sftp_object.error:
            connection = int(sftp_object.connect)
    return jsonify({'status': connection})

@app.route('/api/v1/disconnect', methods=['POST'])
def disconnect_from_server():
    global sftp_object, sftp_status
    connection = 1
    if sftp_status and sftp_object:
        sftp_object.close()
        if not sftp_object.error:
            connection = int(sftp_object.connect)
    return jsonify({'status': connection})

@app.route('/api/v1/sconnect', methods=['GET'])
def get_connection():
    global sftp_object, sftp_status
    connection = 0
    if sftp_status and sftp_object: connection = int(sftp_object.connect)
    return jsonify({'status': connection})

@app.route('/api/v1/conf', methods=['GET', 'POST'])
def get_config():
    global sftp_object, sftp_status
    data = dict(request.form)
    data = {item:data[item][0] for item in data if len(data[item]) == 1}
    check = validate_forms(data)
    if not check:
        parms = {}
        parms['host'] = data["InputHost"]
        parms['port'] = data["InputPort"]
        parms['login'] = data["InputLogin"]
        parms['password'] = data["InputPassword"]
        sftp_config.set(parms)
        sftp_object, sftp_status = sftp_config.reinit()
        if sftp_status : sftp_config.write()
    return jsonify({'validate': int(check),'status':int(sftp_status)})

@app.route('/api/v1/status', methods=['GET'])
def get_status():
    def gt(): return datetime.datetime.now()
    global sftp_object,sftp_config,sftp_status
    if sftp_object and sftp_object.sync_time:
        sync_time = datetime.datetime.fromtimestamp(int(sftp_object.sync_time))
        error_status = int(sftp_object.error)
    else:
        sync_time = 0
        error_status = 1

    if sftp_config.isinit:
        is_init = 1
        init_time = datetime.datetime.fromtimestamp(int(sftp_config.init_time))
    else:
        is_init = 0
        init_time = 0

    connection = 0
    connect_time = 0
    if sftp_status and sftp_object:
        connection = int(sftp_object.connect)
        if sftp_object.connect_time:
            connect_time = int((gt() - datetime.datetime.fromtimestamp(int(sftp_object.connect_time))).total_seconds())

    return jsonify({'config': {'status': is_init, 'time': init_time},
                    'sync': {'status': error_status, 'time': sync_time},
                    'connect': {'status': connection, 'time': connect_time}})

@app.route('/api/v1/init', methods=['POST'])
def reinit_config():
    global sftp_object, sftp_status
    sftp_object, sftp_status = sftp_config.reinit()
    return jsonify({'status': int(sftp_status)})

@app.route('/api/v1/repo/<operation>', methods=['POST'])
def repository_actions(operation):
    global sftp_object
    if sftp_object:
        actions = {'upload': sftp_object.smart_upload,
                   'modify': sftp_object.smart_modify,
                   'download': sftp_object.smart_sync,
                   'clean': sftp_object.sync}

        if actions.get(operation):
            logs, error_status = actions[operation]()
        else:
            error_status = 1
            logs = []
    else:
        error_status = 1
        logs = []
    return jsonify({'error_status':error_status,'logs':logs})

@app.route('/api/v1/sync', methods=['POST'])
def smart_sync():
    return repository_actions('download')

@app.route('/api/v1/clean', methods=['POST'])
def clean_sync():
    return repository_actions('clean')

@app.route('/', methods=['GET'])
def main_page():
    return render_template('main.html')

@app.route('/conf', methods=['GET'])
def config_page():
    return render_template('conf.html')

@app.route('/help', methods=['GET'])
def help_me():
    return render_template('help.html')

if __name__ == '__main__':
    sftp_object, sftp_status = sftp_config.init()
    app.run(host="0.0.0.0", port=5999, threaded=True)