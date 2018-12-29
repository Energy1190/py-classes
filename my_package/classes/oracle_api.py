# Модуль для обработки запросов к базе данных oracle
# Версия: 0.1

import os
import cx_Oracle

class OracleApi():
    def __init__(self, conn_string, pdb=False):
        self._cs = conn_string
        self.pdb = pdb

    def _run_query(self,query):
        # Упрощение запросов к базе данных oracle
        result = []
        c = cx_Oracle.connect(self._cs, mode=cx_Oracle.SYSDBA)
        if self.pdb:
            cursor = c.cursor()
            cursor.execute('ALTER SESSION SET container = {}'.format(self.pdb))
            cursor.close()

        cursor = c.cursor()
        cursor.execute(query)
        try: [result.append(i) for i in cursor]
        except: pass
        cursor.close()
        c.close()
        return result

    def get_dirs(self):
        # Получает список всех директорий
        return self._run_query('SELECT DIRECTORY_NAME, DIRECTORY_PATH FROM all_directories')

    def check_dir(self, name):
        # Проверяет существует ли директория
        raw = self.get_dirs()
        names = [item[0] for item in raw]
        if name in names:
            return True

    def create_dir(self,name,path,force=False):
        # Создает директорию, если она еще не создана
        exist = self.check_dir(name)
        if not exist:
            return self._run_query("CREATE DIRECTORY {} AS '{}'".format(name,path))
        elif force:
            return self._run_query("CREATE OR REPLACE DIRECTORY {} AS '{}'".format(name, path))

    def grant_dir(self, user, directory, role):
        # Предоставляет пользователю полномочия на директорию
        return self._run_query('GRANT {} ON DIRECTORY {} TO {}'.format(role,directory,user))

    def get_users(self):
        # Получает список всех пользоватлей
        return self._run_query('SELECT USERNAME, USER_ID, ACCOUNT_STATUS, DEFAULT_TABLESPACE FROM dba_users')

    def check_user(self,name):
        # Проверяет существование пользователя
        raw = self.get_users()
        names = [item[0] for item in raw]
        if name.upper() in names:
            return True

    def create_user(self,name, password, force=False):
        # Создание нового пользователя
        exist = self.check_user(name)
        if not exist:
            return self._run_query('CREATE USER {} IDENTIFIED BY {}'.format(name,password))
        elif force:
            return self._run_query('ALTER USER {} IDENTIFIED BY {}'.format(name,password))

    def drop_user(self,name):
        # Удаляет пользователя
        self._run_query('DROP USER {}'.format(name))

    def get_tablespaces(self):
        # Получение данных о всех табличных пространствах
        return self._run_query('SELECT  FILE_NAME, BLOCKS, TABLESPACE_NAME FROM DBA_DATA_FILES')

    def check_tablespace(self,name):
        # Проверяет наличае табличного пространства
        raw = self.get_tablespaces()
        names = [item[2] for item in raw]
        if name.upper() in names:
            return True

    def create_tablespace(self,name,path,size='100M'):
        # Создает табличное пространство
        exist = self.check_tablespace(name)
        if not exist:
            return self._run_query("CREATE TABLESPACE {} DATAFILE '{}' SIZE {} REUSE AUTOEXTEND ON".format(name,path,size))

    def add_tablespace_df(self, name, datafile, maxsize=20000):
        # Добавляет в табличное пространство новый файл с данными
        exist = self.check_tablespace(name)
        if exist:
            exist_df = self.check_datafile(name, datafile)
            if not exist_df:
                path = os.sep.join(self.get_dba_path()[0])
                return self._run_query("""ALTER TABLESPACE "{}" ADD DATAFILE '{}{}{}' SIZE 300000000 AUTOEXTEND ON MAXSIZE {}M""".format(name,path,os.sep,datafile,str(maxsize)))

    def drop_tablespace(self,name):
        # Удаляет табличное простанство
        return self._run_query("DROP TABLESPACE {} INCLUDING CONTENTS AND DATAFILES".format(name))

    def change_user_tablespace(self,user,tablespace):
        # Устанавливает табличное пространство пользователя
        return self._run_query("ALTER USER {} DEFAULT TABLESPACE {}".format(user,tablespace))

    def grant_user(self, user, role, password):
        # Предоставляет пользователю полномочия
        return self._run_query("GRANT {} TO {} IDENTIFIED BY {}".format(role,user,password))

    def get_dba_path(self):
        # Возвращает пути к файлам базы данных
        raw = self.get_tablespaces()
        paths = []
        for item in raw:
            path = item[0].split(os.sep)[:-1]
            if path not in paths:
                paths.append(path)
        return paths

    def get_dba_files(self):
        # Возвращает все файлы базы данных
        return self._run_query('SELECT TABLESPACE_NAME, FILE_NAME, BYTES FROM DBA_DATA_FILES')

    def get_tablespace_files(self, name):
        # Возвращает все файлы указанного табличного пространства
        all_files = self.get_dba_files()
        return [(item[1], item[2]) for item in all_files if item[0] == name]

    def check_datafile(self,name,datafile):
        # Проверяет существование файла табличного пространства
        all_files = self.get_tablespace_files(name)
        if datafile in [item[0].split(os.sep)[-1] for item in all_files]:
            return True

def create_user(conn_string, username, password, grants=['CONNECT'], tablespace=False, pdb=False, force=True):
    '''
        Создает пользователя.
        Принимет:
            conn_string -    строка соединения
            username    -    имя пользователя
            password    -    пароль пользователя
            grants      -    роли нового пользователя
            tablespace  -    табличное пространство пользователя
            pdb         -    указание на контейнерную базу данных (название)
            force       -    перезаписать, если пользователь уже существует
    '''
    oracle = OracleApi(conn_string, pdb=pdb)
    oracle.create_user(username, password, force=force)
    for grant in grants:
        oracle.grant_user(username,grant,password)

    if tablespace:
        oracle.change_user_tablespace(username, tablespace)

def create_directory(conn_string,name,path, grants=['READ','WRITE'], users=[], pdb=False, force=True):
    '''
        Создает директорию.
        Принимет:
            conn_string -    строка соединения
            name        -    имя директории
            path        -    путь к директории
            grants      -    списко ролей, которые нужно предоставить на директорию
            users       -    список пользоватлей, которым нужно предоставить права на директорию
            pdb         -    указание на контейнерную базу данных (название)
            force       -    перезаписать, если пользователь уже существует
    '''
    oracle = OracleApi(conn_string, pdb=pdb)
    oracle.create_dir(name,path, force=force)

    if users and grants:
        for grant in grants:
            for user in users:
                oracle.grant_dir(user,name,grant)

def create_tablespace(conn_string,name,datafiles=[], pdb=False):
    '''
        Создает табличное пространство, если его не существует.
        Добавляет в тебличноепространство файлы.
        Принимет:
            conn_string -    строка соединения
            name        -    имя табличного пространства
            datafiles   -    список с именами файлов данных
            pdb         -    указание на контейнерную базу данных (название)
    '''
    oracle = OracleApi(conn_string, pdb=pdb)
    if len(datafiles):
        first = datafiles.pop(0)
        path = os.sep.join(oracle.get_dba_path()[0])

        oracle.create_tablespace(name,'{}{}{}'.format(path,os.sep,first))
        for file in datafiles:
            oracle.add_tablespace_df(name,file)



