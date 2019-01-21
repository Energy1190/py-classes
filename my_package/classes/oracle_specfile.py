# Класс для чтения, создания и исполнения операций до импорта\экспорта баз данных oracle
# Версия 0.1

import os
import pickle
from my_package.classes.oracle_api import create_tablespace, OracleApi

class RunSpecFileError(Exception):
    pass

class SpecFile():
    ACTIONS = ['create', 'execute', 'read']
    def __init__(self, path=None, action=None, data=None):
        self.raw = {}
        self.path = path
        self.data = data
        self.action = action

    def read(self):
        result = {}
        error = False
        with open(self.path, 'rb') as dump:
            try: result = pickle.load(dump)
            except: error = True

        return result, error

    def write(self, data):
        error = False

        with open(self.path, 'wb') as load:
            try: pickle.dump(data,load)
            except: error = True

        return error

    def init(self, **kwargs):
        if self.action not in SpecFile.ACTIONS:
            raise RunSpecFileError("Указанная операция '{}' не определена.".format(self.action))

        if self.action == 'read' or self.action == 'execute':
            if not self.path or not os.path.exists(self.path):
                raise RunSpecFileError("Файл спецификации '{}' не существует".format(self.path))

            self.raw, error = self.read()
            if error:
                raise RunSpecFileError("Не удалось открыть файл спецификации '{}'".format(self.path))

            if self.action == 'execute':
                return self.run(action=self.action,**kwargs)
            elif self.action == 'read':
                return self.raw

        elif self.action == 'create':
            self.data = self.run(action=self.action, **kwargs)
            error = self.write(self.data)
            if error:
                raise RunSpecFileError("Не удалось записать данные в файл")

    def _add_data(self,raw,result):
        exeptions = ['UNDOTBS1', 'SYSTEM', 'SYSAUX', 'USERS']
        for item in raw:
            if item and len(item):
                name = item[0]
                if name in exeptions:
                    continue

                if name not in result:
                    result[name] = []

                file = item[1].split(os.sep)[-1].split('.')[0]
                if file not in result[name]:
                    result[name].append(file)

    def run(self, action=None, **kwargs):
        pdb = kwargs.get('pdb')
        conn_string = kwargs.get('conn_string')
        if not conn_string:
            raise RunSpecFileError("Не определена строка подключения к инстансу")

        if action == 'execute':
            for tablespace in self.raw:
                create_tablespace(conn_string, tablespace, datafiles=[ '{}.DBF'.format(file) for file in self.raw[tablespace]], pdb=pdb)

            return True

        elif action == 'create':
            result = {}
            mode = kwargs.get('mode')
            if not mode or mode not in ['FULL', 'SCHEMA']:
                raise RunSpecFileError("Не определен режим работы")

            obj = OracleApi(conn_string,pdb=pdb)
            query = "SELECT DISTINCT sgm.TABLESPACE_NAME , dtf.FILE_NAME FROM DBA_SEGMENTS sgm JOIN DBA_DATA_FILES dtf ON (sgm.TABLESPACE_NAME = dtf.TABLESPACE_NAME)"
            if mode == 'FULL':
                raw = obj._run_query(query)
                self._add_data(raw,result)
				
                return result

            elif mode == 'SCHEMA':
                schemas = kwargs.get('schemas')
                if not schemas:
                    raise RunSpecFileError("Задан режим схема, но сами схемы не определены.")

                for schema in schemas:
                    tmp_query = query + "WHERE sgm.OWNER = '{}'".format(schema)
                    raw = obj._run_query(tmp_query)
                    self._add_data(raw, result)

                return result
