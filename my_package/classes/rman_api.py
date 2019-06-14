# Модуль - оболочка для вызова RMAN
# Версия: 0.2

import os
import sys
import json
import pickle
import datetime
import subprocess
from jinja2 import Template
from traceback import format_exc
from argparse import ArgumentParser
from collections.abc import Iterable
from my_package.scripts.send_slack_notification import main as send

class RmanTasks():
    '''
        Класс для хранения заранее сгенерированных шаблонов
    '''
    backup = '8003587d0000004241434b555020415320434f4d50524553534544204241434b555053455420444154414241534520504c555320415243484956454c4f472044454c45544520414c4c20494e5055543b0a44454c455445204e4f50524f4d5054204f42534f4c455445205245434f564552592057494e444f57204f46203320444159533b71002e'
    backup_controlfile = '8003582700000072756e207b0a202020204241434b55502043555252454e5420434f4e54524f4c46494c453b0a7d71002e'


class RunRmanApiError(Exception):
    '''
        Класс для обозначения ошибок
    '''
    pass

class RmanApi():
    '''
        Класс для взаимодействия с командой rman с помощью заранее сгенерированных шаблонов
    '''
    path_log = None
    path_exe = None
    path_script = None
    def compilate_template(string:str):
        # Метод для получения hex значения из команды
        return pickle.dumps(string).hex()

    def unpack_template(bytecode):
        # Метод для получения команды из hex значения
        return pickle.loads(bytes.fromhex(bytecode))

    def __init__(self, path, username, password, instance, hostname="localhost", port="1521"):
        self.port = port
        self.username = username
        self.password = password
        self.instance = instance
        self.hostname = hostname

        self.home_path = path
        self.path_exe, error = self._get_program_path()
        self.conn_string = self._get_connect_data(self.username, self.password, self.instance)

        if not hasattr(self, 'workdir') or not self.workdir:
            self.workdir = os.path.dirname(os.path.abspath(__file__))

    def _get_program_path(self):
        # Проверка существования исполняемого файла
        tmp = ('bin', 'rman.exe')
        if self.home_path[-1] == os.sep:
            self.home_path = self.home_path[:-1]

        self.path_exe = os.path.join(self.home_path,*tmp)
        if not os.path.exists(self.path_exe):
            raise RunRmanApiError("Исполняемый файл '{}' не существует.".format(self.path_exe))

        return self.path_exe, False

    def _get_connect_data(self, username, password, instance):
        # Построение строки для соединения с инстансом
        [ RunRmanApiError("Параметр '{}' не определен.".format(item)) for item in [username,password,instance] if not item]
        return '{}/{}@{}:{}/{}'.format(username,password,self.hostname,self.port,instance)

    def create_temp_file(self, path, source):
        # Создание временного файла с заданием
        with open(path, 'w') as stream:
            stream.write(source)

    def remove_temp_file(self, path):
        # Удаление временного файла с заданием
        if os.path.exists(path):
            os.remove(path)
        else:
            RunRmanApiError("Ошибка при удалении временного файла: файла не существует.")

    def _build_query(self):
        # Построение запроса для выполнения
        [RunRmanApiError("Параметр '{}' не определен.".format(item)) for item in [self.path_exe,self.conn_string,self.path_script,self.path_log] if
         not item]
        return '{} TARGET {} cmdfile="{}" log="{}"'.format(self.path_exe,self.conn_string,self.path_script,self.path_log)

    def execute(self, proc):
        # Выполнение запроса
        x = subprocess.Popen(
            proc, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        return [i.decode(encoding='utf-8') for i in x.stdout], [i.decode(encoding='utf-8') for i in x.stderr]

    def run(self, task, **kwargs):
        # Основная логика
        # Проверка и получение задания
        raw = None
        if hasattr(RmanTasks, task):
            raw = RmanApi.unpack_template(getattr(RmanTasks, task))
        else:
            RunRmanApiError("Операция '{}' не определена.".format(task))

        # Подстановка значений, если такие допустимы
        source = None
        try:
            source = Template(str(raw)).render(**kwargs)
        except:
            RunRmanApiError("Ошибка при получении задания из шаблона, возможно не хватает переменных.")

        # Построение путей к файлам с заданием и логом
        self.path_log = os.path.join(self.workdir, 'task.log')
        self.path_script = os.path.join(self.workdir, 'task.rman')

        # Создание временного файла с заданием
        try:
            self.create_temp_file(self.path_script, source)
        except:
            RunRmanApiError("Ошибка при создании временного файла с заданием.")

        # Выполнение занадия
        stdout, stderr = None, None
        try:
            stdout, stderr = self.execute(self._build_query())
        except:
            RunRmanApiError("Ошибка при выполнении задания.")
        finally:
            self.remove_temp_file(self.path_script)


class RmanApiExtended(RmanApi):
    '''
        Расширенный класс взаимодействия, включает в себя обработку логов
    '''
    def __init__(self, *args, url=None,workdir=None,logger=None,**kwargs):
        self.url = url
        self.logger = logger
        self.workdir = workdir

        self.logger.debuger('RmanApiExtended: __init__: Init')
        super(RmanApiExtended, self).__init__(*args,**kwargs)
        self.logger.debuger('RmanApiExtended: __init__: Done')

    def execute(self, proc):
        self.logger.debuger('RmanApiExtended: execute: Init: proc: "{}"'.format(proc))
        stdout, stderr = super(RmanApiExtended, self).execute(proc)
        self.logger.debuger('RmanApiExtended: execute: stdout: "{}"'.format('\n'.join(stdout)))
        self.logger.debuger('RmanApiExtended: execute: stderr: "{}"'.format('\n'.join(stderr)))
        self.logger.debuger('RmanApiExtended: execute: Done')

        print('\n'.join(stdout))
        print('\n'.join(stderr))

        return stdout, stderr

    def run(self, task, **kwargs):
        self.logger.debuger('RmanApiExtended: run: Init: task: "{}", kwargs: "{}"'.format(task,json.dumps(kwargs)))
        super(RmanApiExtended, self).run(task, **kwargs)
        self.logger.debuger('RmanApiExtended: run: Done')

    def close(self):
        self.logger.debuger('RmanApiExtended: close: Init')
        self.logger.write()
        if self.url:
            self.logger.send(self.url,files=[self.path_log])


class QueryParser():
    '''
        Класс для обработки входящих данных
    '''
    def __init__(self, incoming:list, debug=False, workdir=None):
        self.date = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M")

        self.debug = debug
        self.workdir = workdir
        self.incoming = incoming

        self.logger = Logger(self.debug,debug_file=os.path.join(self.workdir,'debug_log_{}'.format(self.date)),
                                        output_file=os.path.join(self.workdir,'output_log_{}'.format(self.date)),
                                        error_file=os.path.join(self.workdir,'error_log_{}'.format(self.date)))

        self.logger.debuger('QueryParser: __init__ : Init')
        self.logger.debuger('QueryParser: __init__ : Incoming: "{}"'.format(' '.join(incoming)))

        error = False
        self.parameters = None
        try:
            self.logger.debuger('QueryParser: __init__ : Parse')
            self.parameters = self._parser()
        except:
            error = True
            raise RunRmanApiError('Ошибка при обработке входящих данных. \n Incoming: "{}"'.format(' '.join(incoming)))
        finally:
            if error: self.logger.write()
        self.parameters = dict(vars(self.parameters))
        self.logger.debuger('QueryParser: __init__ : Parameters: "{}"'.format(json.dumps(self.parameters)))

    def _parser(self):
        # Обработка входящих данных
        parser = ArgumentParser(add_help=False)
        parser.add_argument('action')
        parser.add_argument('instance')
        parser.add_argument('--path', required=True)
        parser.add_argument('--port', default='1521')
        parser.add_argument('--username', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--hostname', default='localhost')
        parser.add_argument('--slack-url', required=False)
        args, unknown = parser.parse_known_args(self.incoming)
        return args

    def create(self):
        cls = RmanApiExtended(self.parameters['path'],
                              self.parameters['username'],
                              self.parameters['password'],
                              self.parameters['instance'],
                              url=self.parameters.get('slack_url'),
                              port=self.parameters['port'],
                              hostname=self.parameters['hostname'],
                              workdir=self.workdir,
                              logger=self.logger)
        return cls,self.parameters['action']


class StdPipe():
    '''
        Класс эмулятор дескриптора
    '''
    def __init__(self):
        self.array = []

    def write(self,*args,**kwargs):
        self.array.append(args[0])

    def flush(self):
        pass


class Logger():
    '''
        Класс для вывода информации
    '''
    def __init__(self, debug, debug_file=None, output_file=None, error_file=None):
        self.debug = debug

        self.debug_file = debug_file
        self.error_file = error_file
        self.output_file = output_file

        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

        sys.stdout = StdPipe()
        sys.stderr = StdPipe()
        self.debugIO = StdPipe()

        self.send_array = {self.error_file:sys.stderr,self.output_file:sys.stdout}
        if self.debug:
            self.send_array[self.debug_file] = self.debugIO

    def debuger(self,msg):
        # Метод для записи отладочных сообщений
        if self.debug:
            self.debugIO.write(msg)
            self.debugIO.write('\n')

    def write(self):
        # Запись данных из памяти в файлы
        for file in self.send_array:
            with open(file,'w') as stream:
                [stream.write(line) for line in self.send_array[file].array]

            self.send_array[file].array = []

    def send(self,url,files=None):
        # Отправка данных в чат
        array = list(self.send_array)
        if files and isinstance(files,Iterable):
            array += files

        for filename in array:
            with open(filename,'r') as stream:
                send(url, title='RmanApi - {}'.format(filename), msg=stream.read())
