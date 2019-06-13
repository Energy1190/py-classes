import os
import sys
import pickle
import datetime
import subprocess
from jinja2 import Template
from traceback import format_exc
from argparse import ArgumentParser
from my_package.scripts.send_slack_notification import main as send
from io import StringIO

class RmanTasks():
    '''
        Класс для хранения заранее сгенерированных шаблонов
    '''
    backup = '8003587d0000004241434b555020415320434f4d50524553534544204241434b555053455420444154414241534520504c555320415243484956454c4f472044454c45544520414c4c20494e5055543b0a44454c455445204e4f50524f4d5054204f42534f4c455445205245434f564552592057494e444f57204f46203320444159533b71002e'
    backup_controlfile = '8003582700000072756e207b0a202020204241434b55502043555252454e5420434f4e54524f4c46494c453b0a7d71002e'

class RunRmanApiError(Exception):
    pass


class StdEmul():
    def __init__(self,old,filename=None, func=None, stream=None):
        self.value = StringIO
        sys.stdout = self.value

        self.old = old
        self.func = func
        self.stream = stream
        self.filename = filename

        self.source = None
        if self.filename:
            self.source = open(self.filename, 'w')

    def write(self, *args,**kwargs):
        if self.source: self.source.write(args[0])
        if self.func: self.func(args[0],stream=self.stream)

    def flush(self, *args,**kwargs):
        return self.value.getvalue()


class RmanApi():
    '''
        Класс для взаимодействия с командой rman с помощью заранее сгенерированных шаблонов
    '''
    def compilate_template(string:str):
        return pickle.dumps(string).hex()

    def unpack_template(bytecode):
        return pickle.loads(bytes.fromhex(bytecode))

    def __init__(self, path, username, password, instance, hostname="localhost", port="1521", debug=None):
        self.debug = debug
        self.outputIO = None
        self.home_path = path

        if hasattr(self, 'logpath') and self.logpath:
            self.outputIO = StdEmul(sys.stdout,func=self.msg,stream=self.logpath)
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
        if not self.workdir: self.workdir = os.path.dirname(os.path.abspath(__file__))
        self.msg('DEBUG: build RmanApi: Done',debug=self.debug)

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

    def msg(self,msg,debug=None,url=None,stream=None):
        if debug:
            print(msg)

        if stream:
            stream.write(msg + '\n')

        if url:
            send(url, title='RmanApi', msg=msg)

        if hasattr(self, 'logpath') and self.logpath:
            source = (bool(debug) and 'DEBUG') or (bool(url) and 'URL') or (bool(stream) and 'STREAM')
            self.logpath.write('{}: {}\n'.format(source,msg))

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
        return '{} TARGET {} cmdfile="{}" log="{}"'.format(self.exe_path,self.conn_string,self.script_path,self.log_path)

    def execute(self, proc):
        self.msg('DEBUG: execute RmanApi: proc: {}'.format(proc), debug=self.debug)

        CREATE_NO_WINDOW = 0x08000000
        x = subprocess.Popen(
            proc, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        return [i.decode(encoding='utf-8') for i in x.stdout], [i.decode(encoding='utf-8') for i in x.stderr]

    def run(self, task, log=None, **kwargs):
        self.msg('DEBUG: run RmanApi: task: {}'.format(task), debug=self.debug)
        raw = None
        if hasattr(RmanTasks, task):
            raw = RmanApi.unpack_template(getattr(RmanTasks, task))
        else:
            RunRmanApiError("Операция '{}' не определена.".format(task))

        source = Template(str(raw)).render(**kwargs)
        self.msg('DEBUG: run RmanApi: source: {}'.format(source), debug=self.debug)

        self.script_path = os.path.join(self.workdir, 'task.rman')
        self.msg('DEBUG: run RmanApi: script_path: {}'.format(self.script_path), debug=self.debug)

        self.log_path = (log or os.path.join(self.workdir, 'task.log'))
        self.msg('DEBUG: run RmanApi: log_path: {}'.format(self.log_path), debug=self.debug)

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
    def __init__(self, parse=sys.argv, logs=None, url=None, work_dir=None, debug=None):
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

        if work_dir:
            self.workdir = work_dir

        if logs and work_dir:
            self.logpath = open(os.path.join(work_dir,'output_log_{}'.format(self.date)), 'w')

        super(RmanApiExtended, self).__init__(self.parameters['path'],
                                              self.parameters['username'],
                                              self.parameters['password'],
                                              self.parameters['instance'],
                                              port=self.parameters['port'],
                                              hostname=self.parameters['hostname'],
                                              debug=self.debug)


    def close(self):
        output = self.outputIO.flush()
        self.outputIO.write(output)
        if self.url and self.workdir:
            for file in [os.path.join(self.workdir,'output_log_{}'.format(self.date)), self.log_path]:
                stream = open(file,'r')
                send(self.url,title='RmanApi - {}'.format(file),msg=stream.read())
                stream.close()
