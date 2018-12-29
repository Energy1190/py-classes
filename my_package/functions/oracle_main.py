# Основная логика работы программы импорта\экспорта
# Версия: 0.1

import os
from my_package.classes.oracle_api import *
from my_package.classes.datapump_api import *
from my_package.functions.oracle_vars import *
from traceback import format_exc

def main(run=False,**kwargs):
    result = {'status': 0, 'desctiption': '', 'error': 0, 'object': None}

    username = kwargs.get(VAR_LOGINA)
    password = kwargs.get(VAR_PASSWA)
    instance = kwargs.get(VAR_INSTAN)
    oracle_home = kwargs.get(VAR_HOMENM)
    pdb = kwargs.get(VAR_PDBNAM)

    for item in [username,password,instance]:
        if not item:
            result['error'] = 1
            result['desctiption'] = 'No variables declared for authentication.'
            return result

    mode = kwargs.get(VAR_MODENM)
    action = kwargs.get(VAR_ACTION)
    for item in [mode,action]:
        if not item:
            result['error'] = 1
            result['desctiption'] = 'Not declared mode of operation.'
            return result

    localhost = kwargs.get(VAR_LOCALC)
    if not localhost:
        server = kwargs.get(VAR_SERVER)
        port = kwargs.get(VAR_PORTNM)
        for item in [server, port]:
            if not item:
                result['error'] = 1
                result['desctiption'] = 'No variables are declared to connect to the server.'
                return result

        conn_string = '{}/{}@{}:{}/{}'.format(username, password, server, port, instance)
    else:
        if not oracle_home:
            result['error'] = 1
            result['desctiption'] = 'not declared the path to ORACLE.'
            return result

        os.environ["ORACLE_HOME"] = oracle_home
        conn_string = '{}/{}@{}'.format(username, password, instance)

    manager = kwargs.get(VAR_LOGINT)
    manager_password = kwargs.get(VAR_PASSWT)
    for item in [manager, manager_password]:
        if not item:
            result['error'] = 1
            result['desctiption'] = 'The performer or his password has not been announced.'
            return result

    if kwargs.get(VAR_CREATE):
        tables = kwargs.get(VAR_TABLES)
        if tables:
            try:
                create_tablespace(conn_string,tables,datafiles=['{}.DBF'.format(tables)],pdb=pdb)
            except:
                result['error'] = 1
                result['desctiption'] = 'Error creating tablespace {}.'.format(tables)
                return result


        create_user_kwargs = {'grants': ['SYSDBA',
                                         'ALL PRIVILEGES',
                                         'DATAPUMP_IMP_FULL_DATABASE',
                                         'DATAPUMP_EXP_FULL_DATABASE',
                                         'IMP_FULL_DATABASE',
                                         'EXP_FULL_DATABASE']}
        if tables:
            create_user_kwargs['tablespace'] = tables

        try:
            create_user(conn_string,manager,manager_password,pdb=pdb,force=True, **kwargs)
        except:
            result['error'] = 1
            result['desctiption'] = 'Could not create or change user'
            return result

    directory = kwargs.get(VAR_DIRPAT)
    directory_name = kwargs.get(VAR_DIRNAM)
    for item in [directory, directory_name]:
        if not item:
            result['error'] = 1
            result['desctiption'] = 'The name or path to the directory is not declared.'
            return result

    try:
        create_directory(conn_string, directory_name, directory, users=[manager], pdb=pdb, force=True)
    except:
        result['error'] = 1
        result['desctiption'] = 'Could not create directory "{}", path: "{}"'.format(directory_name,directory)
        return result

    target = instance
    if pdb: target = pdb

    sysdba = kwargs.get(VAR_SYSDBA)
    datapump_kwargs = {}
    if kwargs.get(VAR_PARALL):
        datapump_kwargs['parallel'] = kwargs.get(VAR_PARALL)

    if kwargs.get(VAR_SCHEMA):
        datapump_kwargs['schemas'] = kwargs.get(VAR_SCHEMA).split(',')

    if kwargs.get(VAR_OPTSNM):
        datapump_kwargs['schemas'] = kwargs.get(VAR_OPTSNM)

    try:
        obj = DatapumpApi(oracle_home,action=action,
                          username=manager,
                          password=manager_password,
                          instance=target,
                          sysdba=sysdba,
                          mode=mode,
                          directory=directory_name, **datapump_kwargs)
    except:
        result['error'] = 1
        result['desctiption'] = 'Error creating executable command. \n\n {}'.format(format_exc())
        return result

    result['desctiption'] = 'Success.'
    result['status'] = 1
    if run:
        try:
            obj.run()
            result['desctiption'] = 'Done.'
            result['status'] = 2
        except:
            result['error'] = 1
            result['desctiption'] = 'Error at command execution.'
            return result

    print('END!')
    result['object'] = obj
    return result