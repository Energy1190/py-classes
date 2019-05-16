# Модуль для обработки запросов к программам datapump impdp.exe и expdp.exe
# Версия: 0.1

import os
from traceback import format_exc

class RunDataPumpError(Exception):
    pass

class DatapumpApi():
    def __init__(self, path, action=None, username=None, password=None, instance=None, sysdba=False, mode=None,
                 directory=None, **kwargs):
        self.action = action
        self.home_path = path

        self.exe_path, error = self._get_program_path()
        if error:
            raise RunDataPumpError("Указанная операция '{}' не определена.".format(action))

        self.conn_str = self._get_connect_data(username,password,instance,sysdba=sysdba)
        self.mode_str, error = self._get_mode_data(mode,schemas=kwargs.get('schemas'))
        if error:
            raise RunDataPumpError("Указанный режим '{}' не определен.".format(mode))

        if not directory:
            raise RunDataPumpError("Не задана директория.")

        self.body_str = 'DIRECTORY={} DUMPFILE=database%U.dmp LOGFILE={}.log PARALLEL={}'.format(directory,
                                                                                                 str(action).lower(),
                                                                                                 str((kwargs.get('parallel') or 1)))
        self.opts = (kwargs.get('opts') or '')
        self.exec_cmd = ' '.join([self.exe_path, self.conn_str, self.mode_str, self.body_str, self.opts])

    def _get_program_path(self):
        if str(self.action).upper() == 'IMPORT':
            tmp = ('bin', 'impdp.exe')
        elif str(self.action).upper() == 'EXPORT':
            tmp = ('bin', 'expdp.exe')
        else:
            return '', True

        if self.home_path[-1] == os.sep:
            self.home_path = self.home_path[:-1]

        self.exe_path = os.path.join(self.home_path,*tmp)
        if not os.path.exists(self.exe_path):
            raise RunDataPumpError("Исполняемый файл '{}' не существует".format(self.exe_path))

        return self.exe_path, False

    def _get_connect_data(self, username, password, instance, sysdba=False):
        for item in [username,password,instance]:
            if not item:
                raise RunDataPumpError("Параметр '{}' не определен.".format(item))

        if sysdba:
            template = '''\\"{}/{}@{} AS SYSDBA\\"'''
        else:
            template = '''{}/{}@{}'''

        return template.format(username,password,instance)

    def _get_mode_data(self,mode, schemas=None):
        if str(mode).upper() == 'FULL':
            return 'FULL=Y', False

        elif str(mode).upper() == 'SCHEMA':
            if not schemas:
                raise RunDataPumpError("Объявлен режим SCHEMA, но не объявлены схемы.")

            schemas = ','.join(schemas)
            return 'SCHEMAS={}'.format(schemas), False
        else:
            return '', True

    def run(self):
        try:
            os.system(self.exec_cmd)
        except:
            print(format_exc())
            raise RunDataPumpError("Не удалось выполнить команду: \n\n {}".format(self.exec_cmd))

    def debug(self):
        output = "Сформирована команда: \n\n {}".format(self.exec_cmd)
        print(output)
        return output

def backup_database(path, username=None, password=None, instance=None, directory='EXPORT'):
    '''
    Функция для создания бекапа базы данных
    '''
    pass