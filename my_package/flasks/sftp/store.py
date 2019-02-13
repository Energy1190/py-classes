import os
import stat
import time
import shutil
import pickle
import paramiko
from traceback import format_exc

data_path = (os.environ.get('DB_PATH') or 'data')

class Empty():
    def close(self):
        return True

class SftpConnection():
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password

        self.error = False
        self.connect = False
        self.connection = Empty()
        self.sftp = Empty()

        self.map = {}
        self.connect_time = 0

    def get_time(self):
        return time.time()

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

    def listdir(self, path):
        result = None
        if not self._check_connect(): return None
        try:
            result = self.sftp.listdir(path)
        except:
            self.error = True
            print(format_exc())

        return result

    def listdir_attr(self, path):
        result = None
        if not self._check_connect(): return None
        try:
            result = self.sftp.listdir_attr(path)
        except:
            self.error = True
            print(format_exc())

        return result

    def build_map(self, path=None, level=0, object=None):
        if not path: path = '.'
        if type(object) != dict: object = self.map

        try:
            names = self.listdir(path)
            attr = self.listdir_attr(path)
            for num in range(len(names)):
                new_path = path + '/' + names[num]
                object[new_path] = {}
                object[new_path]['att'] = attr[num]
                object[new_path]['size'] = attr[num].st_size
                object[new_path]['dir'] = stat.S_ISDIR(attr[num].st_mode)
                object[new_path]['path'] = new_path
                object[new_path]['level'] = level
                object[new_path]['childs'] = {}
                if object[new_path]['dir']:
                    new_level = level + 1
                    self.build_map(object[new_path]['path'], level=new_level, object=object[new_path]['childs'])

            if not level:
                return self.map
        except:
            self.error = True
            print(format_exc())
            return []


class LocalStore():
    def __init__(self, path=None):
        self.path = path
        self._check_dir()

        self.local_map = {}

    def _check_dir(self):
        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def build_local_map(self, path=None, lpath=None, level=0, object=None):
        def ld(path_to):
            return os.listdir(path_to)

        if not path: path = '.'
        if not lpath:
            lpath = self.path
        else:
            lpath = lpath.replace('./', '{}/'.format(self.path), 1)

        if type(object) != dict: object = self.local_map

        for item in ld(lpath):
            new_path = path + '/' + item
            full_path = new_path.replace('./', '{}/'.format(self.path), 1)
            object[new_path] = {}
            object[new_path]['att'] = os.stat(full_path)
            object[new_path]['size'] = os.stat(full_path).st_size
            object[new_path]['dir'] = os.path.isdir(full_path)
            object[new_path]['path'] = new_path
            object[new_path]['level'] = level
            object[new_path]['childs'] = {}
            if object[new_path]['dir']:
                new_level = level + 1
                self.build_local_map(object[new_path]['path'], object[new_path]['path'],
                                     level=new_level,
                                     object=object[new_path]['childs'])
        if not level:
            return self.local_map



class SftpSync(SftpConnection, LocalStore):
    def __init__(self, *args, **kwargs):
        SftpConnection.__init__(self, *args)
        LocalStore.__init__(self, **kwargs)
        self.sync_time = 0

    def _convert_path_to_local(self, name):
        remote_path = name
        local_path = str(name).replace('./', '{}/'.format(self.path), 1)
        return remote_path, local_path

    def _convert_path_to_remote(self, name):
        local_path = name
        remote_path = str(name).replace(self.path, './', 1)
        if '//' in remote_path: remote_path = remote_path.replace('//', '/', 1)
        return remote_path, local_path

    def get(self, name):
        remote, local = self._convert_path_to_local(name)
        if not self._check_connect(): return None
        try:
            self.sftp.get(remote, local)
        except:
            self.error = True
            print(format_exc())

        return True

    def put(self, name):
        remote, local = self._convert_path_to_remote(name)
        if not self._check_connect(): return None
        try:
            self.sftp.put(local, remote)
        except:
            self.error = True
            print(format_exc())

        return True

    def remove(self, name):
        remote, local = self._convert_path_to_remote(name)
        if not self._check_connect(): return None
        try:
            self.sftp.remove(remote)
        except:
            self.error = True
            print(format_exc())

        return True

    def mkdir(self, path):
        remote, local = self._convert_path_to_remote(path)
        if not self._check_connect(): return None
        try:
            self.sftp.mkdir(remote)
        except:
            self.error = True
            print(format_exc())

        return True

    def rmdir(self, path):
        remote, local = self._convert_path_to_remote(path)
        if not self._check_connect(): return None
        try:
            self.sftp.rmdir(remote)
        except:
            self.error = True
            print(format_exc())

        return True

    def sync(self):
        def cycle(items):
            [os.mkdir(item.replace('./', '{}/'.format(self.path), 1)) for item in items if items[item]['dir']]
            result = [self.get(item) for item in items if not items[item]['dir']]
            results = [cycle(items[item]['childs']) for item in items if items[item]['childs']]
            for obj in results: result += obj
            return result

        if self.error: return [], self.error

        shutil.rmtree(self.path)
        self._check_dir()
        self.build_map()
        self.build_local_map()
        if self.error: return [], self.error

        self.sync_time = self.get_time()
        result = cycle(self.map)
        if not all(result):
            self.error = True
            return [], self.error

        return [], self.error

    def smart_sync(self):
        def cycle(items, over_items):
            flag = False
            sync_result = []
            for item in items:
                local_path = item.replace('./', '{}/'.format(self.path), 1)
                if item not in over_items:
                    if items[item]['dir']:
                        os.mkdir(local_path)
                        sync_result.append({item: 'Add directory.'})
                    else:
                        self.get(item)
                        sync_result.append({item: 'Add file.'})
                elif int(over_items[item]['size']) != int(items[item]['size']) and not items[item]['dir']:
                    os.remove(local_path)
                    self.get(item)
                    sync_result.append({item: 'File changed.'})
                else:
                    sync_result.append({item: 'Not modified.'})

                if items[item]['childs']:
                    if not over_items.get(item): return sync_result, True
                    result, tmp_flag = cycle(items[item]['childs'], over_items[item]['childs'])
                    sync_result += result
                    if not flag: flag = tmp_flag

            return sync_result, flag

        if self.error: return [], self.error

        self._check_dir()
        flag = True
        counter = 0
        self.build_map()
        while flag:
            self.build_local_map()
            if self.error: return [], self.error
            sync_result, flag = cycle(self.map, self.local_map)
            counter += 1
            if counter > 10: break
        self.sync_time = self.get_time()

        print(sync_result)
        return sync_result, self.error

    def smart_upload(self):
        def cycle(items, over_items):
            flag = False
            sync_result = []
            for item in items:
                local_path = item.replace('./', '{}/'.format(self.path), 1)
                if item not in over_items:
                    if items[item]['dir']:
                        self.mkdir(item)
                        sync_result.append({item: 'Add directory.'})
                    else:
                        self.put(local_path)
                        sync_result.append({item: 'Add file.'})
                elif int(items[item]['size']) != int(over_items[item]['size']) and not items[item]['dir']:
                    self.put(local_path)
                    sync_result.append({item: 'File changed.'})
                else:
                    sync_result.append({item: 'Not modified.'})
                if items[item]['childs']:
                    if not over_items.get(item): return sync_result, True
                    result, tmp_flag = cycle(items[item]['childs'], over_items[item]['childs'])
                    sync_result += result
                    if not flag: flag = tmp_flag
            return sync_result, flag

        if self.error: return [], self.error

        self._check_dir()
        flag = True
        counter = 0
        while flag:
            self.build_map()
            self.build_local_map()
            if self.error: return [], self.error
            sync_result, flag = cycle(self.local_map, self.map)
            counter += 1
            if counter > 10: break

        return sync_result, self.error

    def smart_modify(self):
        def remove_cycle(items):
            sync_result = []
            for item in items:
                local_path = item.replace('./', '{}/'.format(self.path), 1)
                if items[item]['dir']: sync_result += remove_cycle(items[item]['childs'])
                else:
                    self.remove(local_path)
                    sync_result.append({item: 'Remove file.'})

            return sync_result

        def cycle(items, over_items):
            sync_result = []
            for item in items:
                local_path = item.replace('./', '{}/'.format(self.path), 1)
                if item not in over_items:
                    if items[item]['dir']:
                        self.mkdir(item)
                        sync_result.append({item: 'Add directory.'})
                    else:
                        self.put(local_path)
                        sync_result.append({item: 'Add file.'})
                elif int(items[item]['size']) != int(over_items[item]['size']) and not items[item]['dir']:
                    self.put(local_path)
                    sync_result.append({item: 'File changed.'})
                else:
                    sync_result.append({item: 'Not modified.'})

                try:
                    if items[item]['childs'] or over_items[item]['childs']:
                        sync_result += cycle(items[item]['childs'], over_items[item]['childs'])
                except KeyError:
                    print('Key Error. IN:')
                    print('----- ITEM:', item)

            for item in over_items:
                local_path = item.replace('./', '{}/'.format(self.path), 1)
                if item not in items:
                    try:
                        try:
                            if over_items[item]['childs']:
                                sync_result += remove_cycle(over_items[item]['childs'])
                        except:
                            sync_result.append({item: 'Remove error.'})
                            print(format_exc())

                        if over_items[item]['dir']:
                            self.rmdir(local_path)
                            sync_result.append({item: 'Remove folder.'})
                        else:
                            self.remove(local_path)
                            sync_result.append({item: 'Remove file.'})

                    except:
                        sync_result.append({item: 'Remove error.'})
                        print(format_exc())

            return sync_result

        if self.error: return [], self.error

        self._check_dir()
        self.build_map()

        if self.error: return [], self.error

        sync_result = cycle(self.local_map, self.map)
        print(sync_result)
        return sync_result, self.error

class SftpConfig():
    def __init__(self, path):
        self.path = path
        self.sftp = None

        self.host = None
        self.port = None
        self.login = None
        self.password = None

        self.init_time = 0

    def set(self, data):
        self.host = data['host']
        self.port = data['port']
        self.login = data['login']
        self.password = data['password']

    def get(self):
        return {'host': self.host, 'port': self.port,
                'login': self.login, 'password': self.password}

    def read(self):
        if os.path.exists(self.path): return pickle.load(open(self.path,'rb'))
        else: return None

    def write(self):
        if os.path.exists(self.path): os.remove(self.path)
        pickle.dump(self.get(),open(self.path, 'wb'))

    def get_time(self):
        return time.time()

    def init(self):
        confing = self.read()
        if confing:
            self.set(confing)
            self.init_time = self.get_time()
            self.sftp = SftpSync(confing['host'],confing['port'],confing['login'],confing['password'],path=data_path)
            self.isinit = True
        else:
            self.isinit = False

        return self.sftp, self.isinit

    def reinit(self):
        if self.sftp: self.sftp.close()
        self.init_time = self.get_time()
        self.sftp = SftpSync(self.host,self.port,self.login,self.password,path=data_path)
        self.isinit = True

        return self.sftp, self.isinit

class OutputData():
    def __init__(self, map, store, color="#000000", backColor="#FFFFFF",
                 icon="fas fa-folder",
                 selectedIcon="glyphicon glyphicon-stop"):
        self.map = map
        self.store = store
        self.result = []

        self.color = color
        self.back_color = backColor
        self.icon = icon
        self.selected_icon = selectedIcon

    def generate(self, list_dict=None, write_to=None, level=0):
        if not list_dict: list_dict = self.map
        if type(write_to) != list: write_to = self.result

        for item in list_dict:
            href = '{}{}'.format(self.store, item[1:])
            childs = []
            if list_dict[item]['dir'] and list_dict[item]['childs']:
                self.generate(list_dict=list_dict[item]['childs'],write_to=childs,level=level + 1)

            if list_dict[item]['dir']: icon = "fas fa-folder"
            else: icon = "fas fa-file"

            write_to.append({'text': ' {}'.format(item), 'href': href, 'nodes': childs,
                             'icon': icon, 'selectedIcon': icon,
                             'color': self.color, 'backColor': self.back_color})

        if not level: return self.result
        else: return childs
