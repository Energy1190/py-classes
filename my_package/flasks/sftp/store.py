import os
import re
import stat
import time
import pickle
import shutil
import hashlib
import paramiko
import collections
from shutil import copyfile
from traceback import format_exc

def connector(func):
    # Декоратор для соединения с sftp
    def wrapper(*args,**kwargs):
        # args[0] == self
        if not hasattr(args[0],'_check_connect'): return None
        if not hasattr(args[0], 'close'): return None
        if not args[0]._check_connect(): return None
        try: return func(*args,**kwargs)
        except:
            print(format_exc())
            return None
    return wrapper

def shutter(func):
    # Декоратор для разъединения с sftp
    def wrapper(*args,**kwargs):
        # args[0] == self
        if not hasattr(args[0], 'remote_copy'): return None
        if not hasattr(args[0].remote_copy, 'close'): return None
        try: return func(*args,**kwargs)
        except:
            print(format_exc())
            return None
        finally:
            args[0].remote_copy.close()
    return wrapper

class Store():
    # Класс для сравнения директорий
    def __init__(self,body:dict):
        self.obj = self._format_input(body)

    def _format_input(self, obj, objects_list=None):
        # Привидение данных к нужному типу
        # Возвращает список словарей
        if type(obj) == tuple:
            obj = obj[0]

        if obj.get('path') == '':
            obj['path'] = '.'

        obj['path'] = obj['path'].replace('\\','/')
        if not re.match('^\./',obj['path']) and obj['path'] != '.':
            obj['path'] = './{}'.format(obj['path'])

        result = {}
        objects_list = objects_list or []
        result['path'] = obj.get('path').replace('\\','/')
        result['type'] = (obj.get('stat') and not stat.S_ISDIR(obj.get('stat').st_mode) and 'file') or 'directory'
        result['size'] = (obj.get('stat') and obj['stat'].st_size) or 0
        objects_list.append(result)
        obj.get('include') and [self._format_input(elem,objects_list) for elem in obj.get('include')]
        return objects_list

    def sync(self, obj):
        # Метод синхронизации, возвращает список необходимых операций
        cmd_list = []
        description = ''
        try:
            obj = self._format_input(obj)
        except:
            description = 'Не удалось обработать входящие данные.'
            return cmd_list,description

        print('Start sync.')
        for item in obj:
            if item['path'] not in [litem['path'] for litem in self.obj]:
                print(' - Item: "{}" need to by add.'.format(item['path']))
                cmd_list.append(((item['path']), 'add', item['type']))

            elif item['type'] == 'file':
                size = [litem['size'] for litem in self.obj if item['path'] == litem['path']][0]
                if int(item['size']) != int(size):
                    print(' - Item: "{}" need to by change.'.format(item['path']))
                    cmd_list.append(((item['path']), 'modify', item['type']))

        for item in self.obj:
            if item['path'] not in [litem['path'] for litem in obj]:
                print(' - Item: "{}" need to by remove.'.format(item['path']))
                cmd_list.append(((item['path']), 'remove', item['type']))

        print('End sync.')
        return cmd_list, description

class WorkingCopy():
    # Класс описывающий рабочую директорию
    def __init__(self, path):
        self.path = path

    def _sort_func(self, *args):
        # Сортировка данных, для того, что бы папки всегда были вверху списка
        if not len(args):
            return False
        if not len(args[0]):
            return False
        if not hasattr(args[0][0],'get'):
            return False
        return (args[0][0].get('directoryname') or '')

    def get(self, path):
        # Метод для получения данных о рабочей копии
        e = None
        if path == '.': path = ''
        fullpath = os.path.join(self.path,path)

        try:
            if os.path.isfile(fullpath):
                data = {'path':path,
                        'stat':os.stat(fullpath),
                        'fullpath':fullpath,
                        'filename':fullpath.split(os.sep)[-1],
                        'directoryname':None,
                        'directory_path':'\\'.join(path.split('\\')[:-1]),
                        'file_path':path,
                        'directory': os.sep.join(fullpath.split(os.sep)[:-1])}
            elif os.path.isdir(fullpath):
                data = {'path':path,
                        'include':sorted([self.get(os.path.join(path,item)) for item in os.listdir(fullpath)],key=self._sort_func,reverse=True),
                        'fullpath':fullpath,
                        'filename': None,
                        'directoryname':fullpath.split(os.sep)[-1],
                        'directory_path': path,
                        'file_path': None,
                        'directory': fullpath}
            else:
                data = {}
        except:
            print(format_exc())
            data = None,None
            e = format_exc()

        return data,e

    def hash(self, path):
        # Метод для получения хеша рабочей директории
        e = None
        result = hashlib.md5()
        if path == '.': path = ''
        fullpath = os.path.join(self.path,path)
        try:
            for root, dirs, files in os.walk(fullpath):
                for file in files:
                    filepath = os.path.join(root,file)
                    result.update(filepath.encode('utf-8'))

        except:
            print(format_exc())
            result = None
            e = format_exc()

        if hasattr(result,'hexdigest'):
            result = result.hexdigest()

        return result,e

    def prepare(self, path,mkdir=False):
        # Подготавливает путь для записи
        filename = None
        directory = os.sep.join(path.replace('\\', os.sep).split(os.sep))
        if not os.path.isdir(os.path.join(self.path,directory)):
            filename = path.replace('\\', os.sep).split(os.sep)[-1]
            directory = os.sep.join(path.replace('/',os.sep).replace('\\', os.sep).split(os.sep)[:-1])
            if directory.split(os.sep)[-1] == '.':
                directory = os.sep.join(directory.split(os.sep)[:-1])
        check, e = self.get(directory)
        if not check:
            os.mkdir(os.path.join(self.path,directory))

        if mkdir:
            os.mkdir(os.path.join(self.path, directory,filename))

        return filename, os.path.join(self.path,directory)

    def delete(self, path):
        # Удаляет файл или директорию, возвращает два флага - успех и ошибку
        path = path.replace('/',os.sep).replace('\\', os.sep)
        fullpath = os.path.join(self.path,path)
        try:
            if os.path.exists(fullpath) and os.path.isfile(fullpath):
                os.remove(fullpath)
                return True, False
            elif os.path.exists(fullpath) and os.path.isdir(fullpath):
                shutil.rmtree(fullpath)
                return True, False
            else:
                return False, False
        except:
            return False,True

class RemoteCopy():
    # Класс описывающий директорию на сервере
    DB_FILE = '.sftp' # Путь к файлу хранения данных о сервере
    def __init__(self):
        self.host = None
        self.port = None
        self.username = None
        self.password = None

        self.path = None
        self.error = False
        self.connect = False

    def create_from_vars(host,port,username,password):
        obj = RemoteCopy()
        obj.host = host
        obj.port = int(port)
        obj.username = username
        obj.password = password
        return obj

    def create_from_file():
        if os.path.exists(RemoteCopy.DB_FILE):
            raw = pickle.load(open(RemoteCopy.DB_FILE,'rb'))

            data_list = ['host', 'port', 'login', 'password']
            for item in data_list:
                if item not in list(raw) or not raw.get(item):
                    return None

            return RemoteCopy.create_from_vars(raw['host'],raw['port'],raw['login'],raw['password'])

    def get_time(self):
        return time.time()

    def _save_to_file(self):
        if os.path.exists(self.DB_FILE): os.remove(self.DB_FILE)
        data = {'host':self.host,'port':self.port,'login':self.username,'password':self.password}
        pickle.dump(data,open(RemoteCopy.DB_FILE, 'wb'))

    def _preparation(self):
        try:
            sock = (self.host, self.port)
            self.connection = paramiko.Transport(sock)
            self.connection.connect(username=self.username, password=self.password)
        except:
            self.error = True
            print(format_exc())

    def _connect(self):
        self._preparation()
        if self.error: return False
        try:
            self.sftp = paramiko.SFTPClient.from_transport(self.connection)
            self.connect_time = self.get_time()
            self.connect = True
        except:
            self.error = True
            print(format_exc())

    def _check_connect(self):
        if not self.connect: self._connect()
        if self.error: return False
        return True

    def close(self):
        self.sftp.close()
        self.connection.close()
        self.connect_time = 0
        self.connect = False

    @connector
    def listdir(self, path=None):
        # Метод получения данных о директории
        if not path: path = '.'
        e = None
        try:
            obj = self.sftp.stat(path)
            data = {'path':path,
                    'stat': obj}
            if stat.S_ISDIR(obj.st_mode):
                data['directoryname'] = path
                data['directory_path'] = path
                data['filename']  = None
                data['file_path'] = None
                data['include'] = [self.listdir('/'.join([path,item])) for item in self.sftp.listdir(path)]
            else:
                data['directoryname'] = None
                data['directory_path'] = None
                data['filename']  = path
                data['file_path'] = path

            if self.path:
                data['fullpath'] = os.path.join(self.path,path.replace('/', os.sep))

        except:
            data = None, None
            print(format_exc())
            e = format_exc()

        return data,e

    @connector
    def get(self,remotepath,localpath):
        # Метод-обертка для sftp.get
        return self.sftp.get(remotepath,localpath)

    @connector
    def put(self,remotepath,localpath):
        # Метод-обертка для sftp.put
        return self.sftp.put(localpath,remotepath)

    @connector
    def delete(self,path):
        # Метод-обертка для sftp.remove
        return self.sftp.remove(path)

    @connector
    def mkdir(self,path,mode=511):
        # Метод-обертка для sftp.mkdir
        return self.sftp.mkdir(path,mode=mode)

    @connector
    def rmdir(self,path):
        # Метод-обертка для sftp.rmdir
        return self.sftp.rmdir(path)

class Sync():
    # Класс описывающий процесс синхронизации
    def __init__(self, working_copy:WorkingCopy,remote_copy_cfg):
        self.errors = ''
        self.local_copy = working_copy

        RemoteCopy.DB_FILE = remote_copy_cfg
        self.remote_copy = RemoteCopy.create_from_file()

        self.sync_array_to = {'add':{
                                    'file': self.remote_copy.put,
                                    'folder': self.remote_copy.mkdir
                                },
                              'remove':{
                                    'file': self.remote_copy.delete,
                                    'folder': self.remote_copy.rmdir
                                }}

        self.sync_array_from = {'add':{
                                    'file': self.remote_copy.get,
                                    'folder': os.mkdir
                                },
                              'remove':{
                                    'file': os.remove,
                                    'folder': os.rmdir
                                }}

    @shutter
    def sync(self,action=None,remove=False):
        # Универсальный метод синхронизации
        fullpath = None
        counters = collections.defaultdict(int)
        if action == 'to':
            dataset = self.local_copy.get('.')
            functions = self.sync_array_to
            container = Store(self.remote_copy.listdir('.'))
        elif action == 'from':
            dataset = self.remote_copy.listdir('.')
            functions = self.sync_array_from
            fullpath = os.path.join
            container = Store(self.local_copy.get('.'))
        else:
            return counters,'Тип операции не поддерживается.'

        cmd_list, error = container.sync(dataset)
        if error:
            return counters, error, self.errors

        print('Start apply sync result.')
        for item in cmd_list:
            self._sync_step_1(item,functions,counters,fullpath,remove=remove)
        for item in cmd_list:
            self._sync_step_2(item,functions,counters,fullpath,remove=remove)

        print('Apply sync result. Done.')
        return counters,None,self.errors

    def _sync_step_1(self,item,functions,counters,fullpath,remove=False):
        # Метод обрабатывающий шаг синхронизации
        # Первым шагом идет добавление директорий и удаление файлов,
        # что бы не возникло конфликтов при удалении не пустых папок и
        # создании файлов в еще не созданных папках
        # TODO: через fullpath передается проверка пути, которая обеспечивает совместимость с локальной ОС. Костыль-с
        # TODO: сортировать команды по длинне пути (ошибка при рекурсивном удалении папок)
        path, action, o_type = item
        try:
            if action == 'add' and o_type == 'directory':
                tmp = path
                if callable(fullpath):
                    tmp = fullpath(self.local_copy.path,os.path.normpath(path))
                functions['add']['folder'](tmp)
                counters['add_folder'] += 1
                print('- Item: "{}" added'.format(path))

            elif action == 'remove' and o_type == 'file' and remove:
                tmp = path
                if callable(fullpath):
                    tmp = fullpath(self.local_copy.path,os.path.normpath(path))
                functions['remove']['file'](tmp)
                counters['remove_file'] += 1
                print('- Item: "{}" removed'.format(path))
        except:
            print(format_exc())
            self.errors += 'Error in item: "{}"\n'.format(path)

    def _sync_step_2(self,item,functions,counters,f_fullpath,remove=False):
        # Метод обрабатывающий шаг синхронизации
        # Второй шаг, все остальные операции, которые не были сделаны в первом шаге
        # Операция модификации эквивалентна операции добавления.
        path, action, o_type = item
        fullpath = os.path.join(self.local_copy.path, os.path.normpath(path))
        try:
            if action == 'add' and o_type == 'file':
                functions['add']['file'](path, fullpath)
                counters['add_file'] += 1
                print('- Item: "{}" added'.format(path))
            elif action == 'modify' and o_type == 'file':
                functions['add']['file'](path, fullpath)
                counters['change_file'] += 1
                print('- Item: "{}" changed'.format(path))
            elif action == 'remove' and o_type == 'directory' and remove:
                tmp = path
                if callable(f_fullpath):
                    tmp = f_fullpath(self.local_copy.path,os.path.normpath(path))
                functions['remove']['folder'](tmp)
                counters['remove_directory'] += 1
                print('- Item: "{}" removed'.format(path))
        except:
            print(format_exc())
            self.errors += 'Error in item: "{}"\n'.format(path)
