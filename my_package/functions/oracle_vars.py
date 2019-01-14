# Получиение конфигурации для импорта/экспорта базы данных Oracle
# Версия: 0.4

'''
    ; AUTH
    ; username - имя пользователя с правами sysdba
    ; password - пароль пользователя
    ; instance - инстанс Oracle
    ; pdb - указание на название контейнерной базы

    ; CONN
    ; localhost - програма запущена на сервере? (0 или 1)
    ; host - адрес сервера
    ; port - порт сервера

    ; TEMP
    ; name - имя директории для экспорта
    ; directory - путь к директории для экспорта
    ; username - имя пользователя от лица которого будет осуществлен экспорт
    ; password - пароль пользователя
    ; tablespace - табличное пространство пользователя

    ; PATH
    ; home - путь к домешнему каталогу Oracle
'''

import os
import yaml
import configparser

def read_config(filename):
    # Получение конфигурации из файла
    result = {}
    error_flag = False

    mime = filename.split('.')[-1]
    if mime == 'yaml':
        result, error_flag = read_yaml(filename)
    elif mime == 'ini':
        result, error_flag = read_ini(filename)
    else:
        error_flag = True

    return result, error_flag

def read_ini(filename):
    # Получение конфигурации из файла ini
    result = {}
    config = configparser.ConfigParser()
    error_flag = False

    if os.path.exists(filename):
        try:
            config.read(filename)
            for item in config.sections():
                result.setdefault(item, {})

            for item in result:
                result[item] = dict(config[item])
        except:
            error_flag = True
    else:
        error_flag = True
    return result, error_flag

def read_yaml(filename):
    # Получение конфигурации из файла yaml
    result = {}
    error_flag = False
    with open(filename, 'r') as file:
        try: result = yaml.load(file)
        except: error_flag = True

    return result, error_flag


def get(env,array):
    # Получение элемента из конфиграции
    empty = False
    for num in range(len(array)):
        if env: env = (env.get(array[num]) or env.get(array[num].lower()))

    if env is None:
        empty = True

    return env, empty

VAR_ACTION = 'action'
VAR_CONFIG = 'config'
VAR_LOCALC = 'local_check'
VAR_PDBCHK = 'pdb_check'
VAR_SERVER = 'server_name'
VAR_PORTNM = 'port_name'
VAR_INSTAN = 'instance_name'
VAR_PDBNAM = 'pdb_name'
VAR_SYSDBA = 'sysdba_check'
VAR_LOGINA = 'login_auth_name'
VAR_LOGINT = 'login_tmp_name'
VAR_PASSWA = 'password_auth_name'
VAR_PASSWT = 'password_tmp_name'
VAR_HOMENM = 'oracle_home'
VAR_CREATE = 'check_create_user'
VAR_TABLES = 'user_tablespace'
VAR_DIRNAM = 'directory_name'
VAR_DIRPAT = 'directory_path'
VAR_PARALL = 'parallelizm_count'
VAR_MODENM = 'action_mode'
VAR_OPTSNM = 'opts'
VAR_SCHEMA = 'schemas'
VAR_SPECFL = 'spec_file'
VAR_DEBUGM = 'debug_mode'
VAR_SPECUS = 'use_spec_file'

ENV_SERVER = ['CONN','host']
ENV_PORTNM = ['CONN','port']
ENV_HOMENM = ['PATH','home']
ENV_INSTAN = ['AUTH','instance']
ENV_LOCALC = ['CONN','localhost']
ENV_PDBNAM = ['AUTH','pdb']
ENV_PARALL = ['TEMP','parallel']
ENV_LOGINT = ['TEMP','username']
ENV_PASSWT = ['TEMP','password']
ENV_LOGINA = ['AUTH','username']
ENV_PASSWA = ['AUTH','password']
ENV_DIRNAM = ['TEMP','name']
ENV_DIRPAT = ['TEMP','directory']
ENV_TABLES = ['TEMP','tablespace']
ENV_SPECUS = ['OPT', 'speccheck']
ENV_SPECFL = ['OPT', 'specfile']
ENV_DEBUGM = ['OPT', 'debug']
ENV_SCHEMA = ['OPT', 'schemas']
ENV_OPTSNM = ['OPT', 'opts']
ENV_ACTION = ['MAIN','action']
ENV_MODENM = ['MAIN','mode']