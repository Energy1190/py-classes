import os
import sys
import pickle
import datetime
import subprocess
from jinja2 import Template
from traceback import format_exc
from argparse import ArgumentParser


class RmanTasks():
    '''
        Класс для хранения заранее сгенерированных шаблонов
    '''
    backup = '8003587d0000004241434b555020415320434f4d50524553534544204241434b555053455420444154414241534520504c555320415243484956454c4f472044454c45544520414c4c20494e5055543b0a44454c455445204e4f50524f4d5054204f42534f4c455445205245434f564552592057494e444f57204f46203320444159533b71002e'
    backup_controlfile = '8003581b0000004241434b55502043555252454e5420434f4e54524f4c46494c453b71002e'

class RunRmanApiError(Exception):
    pass

class RmanApi():
    '''
        Класс для взаимодействия с командой rman с помощью заранее сгенерированных шаблонов
    '''
    def compilate_template(string:str):
        return pickle.dumps(string).hex()

    def unpack_template(bytecode):
        return pickle.loads(bytes.fromhex(bytecode))

    def __init__(self, path, username, password, instance, hostname="localhost", port="1521",debug=None):
        self.debug = debug
        self.home_path = path
        self.exe_path, error = self._get_program_path()
        if error:
            raise RunRmanApiError("Не опознанная ошибка.")

        self.port = port
        self.username = username
        self.password = password
        self.instance = instance
        self.hostname = hostname
        self.conn_string = self._get_connect_data(self.username,self.password,self.instance)

        self.log_path = None
        self.script_path = None
        self.workdir = os.path.dirname(os.path.abspath(__file__))
        if self.debug:
            print('DEBUG: build RmanApi: Done')
            print('DEBUG: build RmanApi: workdir:', self.workdir)

    def _get_program_path(self):
        tmp = ('bin', 'rman.exe')
        if self.home_path[-1] == os.sep:
            self.home_path = self.home_path[:-1]

        self.exe_path = os.path.join(self.home_path,*tmp)
        if not os.path.exists(self.exe_path):
            raise RunRmanApiError("Исполняемый файл '{}' не существует.".format(self.exe_path))

        return self.exe_path, False

    def _get_connect_data(self, username, password, instance):
        [ RunRmanApiError("Параметр '{}' не определен.".format(item)) for item in [username,password,instance] if not item]
        return '{}/{}@{}:{}/{}'.format(username,password,self.hostname,self.port,instance)

    def create_temp_file(self, path, source):
        try:
            if not os.path.exists(path):
                with open(path, 'w') as stream:
                    stream.write(source)
            else:
                RunRmanApiError("Ошибка при создании временного файла: файл уже существует.")
        except:
            RunRmanApiError("Ошибка при создании временного файла.")

    def remove_temp_file(self, path):
        if os.path.exists(path):
            os.remove(path)
        else:
            RunRmanApiError("Ошибка при удалении временного файла: файла не существует.")

    def _build_query(self):
        [RunRmanApiError("Параметр '{}' не определен.".format(item)) for item in [self.exe_path,self.conn_string,self.script_path,self.log_path] if
         not item]
        return '{} TARGET {} {} log={}'.format(self.exe_path,self.conn_string,self.script_path,self.log_path)

    def execute(self, proc):
        if self.debug: print('DEBUG: execute RmanApi: proc:', proc)
        
        CREATE_NO_WINDOW = 0x08000000
        x = subprocess.Popen(
            [proc], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        return [i.decode(encoding='utf-8') for i in x.stdout], [i.decode(encoding='utf-8') for i in x.stderr]

    def run(self, task, log=None, **kwargs):
        if self.debug: print('DEBUG: run RmanApi: task:', task)
        raw = None
        if hasattr(RmanTasks, task):
            raw = RmanApi.unpack_template(getattr(RmanTasks, task))
        else:
            RunRmanApiError("Операция '{}' не определена.".format(task))

        source = Template(str(raw)).render(**kwargs)
        if self.debug: print('DEBUG: run RmanApi: source:', source)

        self.script_path = os.path.join(self.workdir, 'task.rman')
        if self.debug: print('DEBUG: run RmanApi: script_path:', self.script_path)

        self.log_path = (log or os.path.join(self.workdir, 'task.log'))
        if self.debug: print('DEBUG: run RmanApi: log_path:', self.log_path)

        try:
            self.create_temp_file(self.script_path,source)
            stdout, stderr = self.execute(self._build_query())
            if os.path.exists(self.log_path):
                stream = open(self.log_path, "w+")
                stream.write('\n\n')
                stream.write('\n'.join(stdout))
                stream.write('\n\n')
                stream.write('\n'.join(stderr))
                stream.close()
            else:
                print('Файл для записи логов еще не создан. Вывод: \n\n {} \n\n Ошибки: {} END. \n\n'.format('\n'.join(stdout),
                                                                                                             '\n'.join(stderr)))
        except:
            print(format_exc())
            RunRmanApiError("Операция '{}' не была выполнена.".format(task))
        finally:
            self.remove_temp_file(self.script_path)

class RmanApiExtended(RmanApi):
    def __init__(self, parse=sys.argv, logs=None, url=None, debug=None):
        self.debug = debug
        if debug: print('DEBUG INCOMING: parse', parse)
        if debug: print('DEBUG INCOMING: logs', logs)
        if debug: print('DEBUG INCOMING: url', url)

        parser = ArgumentParser(add_help=False)

        parser.add_argument('instance')
        parser.add_argument('--path', required=True)
        parser.add_argument('--username', required=True)
        parser.add_argument('--password', required=True)

        parser.add_argument('--port', default='1521')
        parser.add_argument('--hostname', default='localhost')
        args, unknown = parser.parse_known_args(parse)

        self.url = url
        self.parameters = dict(vars(args))
        self.date = datetime.datetime.now().strftime("%d.%m.%Y-%H:%M")

        if debug: print('DEBUG PARAMS: parameters', self.parameters)
        if debug: print('DEBUG PARAMS: date', self.date)

        if logs:
            pass
            #sys.stdout = open('output_log_{}'.format(self.date), 'w')
            #sys.stderr = open('error_log_{}'.format(self.date), 'w')

        super(RmanApiExtended, self).__init__(self.parameters['path'],
                                              self.parameters['username'],
                                              self.parameters['password'],
                                              self.parameters['instance'],
                                              port=self.parameters['port'],
                                              hostname=self.parameters['hostname'],
                                              debug=self.debug)

    def close(self):
        if self.url:
            from my_package.scripts.send_slack_notification import main as send
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except:
                pass

            for file in ['output_log_{}'.format(self.date), 'error_log_{}'.format(self.date), self.log_path]:
                stream = open(file,'r')
                send(self.url,title='RmanApi - {}'.format(file),msg=stream.read())
                stream.close()
