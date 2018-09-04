#!/usr/bin/env python3
#  -*- coding: utf-8 -*-
import re
import os
import sys
import ssl
from traceback import format_exc
from jinja2 import Environment, FileSystemLoader
from ldap3 import Server, Tls, Connection, SUBTREE

class AccessFileGenerator():
    env_dict = {'USER': 'LDAP_USER',
                'PASS': 'LDAP_PASS',
                'URL': 'LDAP_URL',
                'GROUPS': 'LDAP_GROUPS',
                'USERS': 'LDAP_USERS',
                'TEMPLATE': 'LDAP_ACC_TPL',
                'CERT': 'LDAP_TRUSTED_CERT',
                'SSL': 'LDAP_TLS_ENABLE'}
    args_dict = {}

    search_pattern = 'SVNDIR'
    search_delimiter = '|||'

    def __init__(self, log_driver=sys.stdout, debug=True):
        self.hosts = []
        self.connection = None
        self.template_data = {}

        self.log_driver = log_driver
        self.debug = debug

    def error_msg(self, func, msg=None, critical=False):
        if self.debug:
            if critical:
                status = "Error"
            else:
                status = "Info"

            print('{} in function {}. Msg: {}'.format(status, str(func),
                                                      (msg or 'no message')),
                  file=self.log_driver)

        if critical:
            assert False, (msg or 'no message')

    def _get_env(self):
        for key, value in self.env_dict.items():
            if value in os.environ:
                self.args_dict[key] = os.environ[value]
            else:
                msg = 'System variable {} not found'.format(value)
                self.error_msg(self._get_env, msg=msg, critical=True)

    def _re_parser(self, raw):
        regexp = re.compile(r"(?P<scheme>ldaps?)://(?P<hosts>[\w\s\d\.\-]+):?(?P<port>[\d]{0,5})/")
        data = regexp.search(raw)
        self.hosts = [(host, (data.group('port') or 389)) for host in data.group('hosts').split(' ')]
        return self.hosts

    def _parser(self, raw):
        scheme = raw.split('://')[0].replace('"', '').replace("'", "")
        special_port = lambda: raw.split(':')[-1] if str(raw.split(':')[-1]).isnumeric() else 0
        port_map = {'ldap': 389, 'ldaps': 636, 'special': special_port()}

        if port_map['special']:
            port = port_map['special']
        else:
            port = port_map[scheme]

        host = raw.split('/')[2]
        self.hosts = [(host, port)]
        return self.hosts

    def _get_hosts(self):
        try:
            if ' ' in self.args_dict['URL']:
                self.hosts = self._re_parser(self.args_dict['URL'])
            else:
                self.hosts = self._parser(self.args_dict['URL'])
        except:
            msg = 'Can not get information about servers. Data: {}'.format(self.args_dict['URL'])
            self.error_msg(self._get_hosts, msg=msg, critical=True)

    def _connect_to_server(self, server):
        try:
            kwargs = {'port': server[1], 'use_ssl': self.args_dict['SSL']}
            if self.args_dict['SSL']:
                kwargs['tls'] = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=self.args_dict['CERT'])

            server_object = Server(server[0], **kwargs)
            connection = Connection(server_object, user=self.args_dict['USER'],
                                    password=self.args_dict['PASS'],
                                    auto_bind=True)
            check_server = connection.bind()
            if self.args_dict['SSL']: connection.start_tls()

            return connection, check_server
        except:
            msg = 'Could not connect to server {} \n\n{}'.format(server[0], str(format_exc()))
            self.error_msg(self._connect_to_server, msg=msg, critical=False)
            return None, False

    def _get_connection(self):
        for server in self.hosts:
            connection, flag = self._connect_to_server(server)
            if flag: return connection

    def init(self):
        self._get_env()
        self._get_hosts()
        self.connection = self._get_connection()
        if not self.connection:
            msg = 'Could not connect to servers'
            self.error_msg(self._connect_to_server, msg=msg, critical=True)

    def _get_data(self):
        groups = []
        self.connection.search(search_base=self.args_dict['GROUPS'],
                               search_filter='(objectClass=group)',
                               search_scope=SUBTREE,
                               attributes=['name', 'member', 'info'])
        groups = self.connection.response[:]

        users = []
        self.connection.search(search_base=self.args_dict['USERS'],
                               search_filter='(objectClass=user)',
                               search_scope=SUBTREE,
                               attributes=['sAMAccountName'])
        users = self.connection.response[:]

        return (groups, users)

    def _parse_data(self, raw):
        def search_user(cns, users):
            result = []
            for cn in cns:
                data = [(user['attributes']['sAMAccountName'], cn) for user in users if user['dn'] == cn]
                result.append((len(data) and data[0]))
            return result

        groups, users = raw
        groups = list(groups)

        groups = filter(lambda x: (True if self.search_pattern in x['attributes']['name'] and x['attributes'].get(
            'info') and self.search_delimiter in x['attributes']['info'] else False),
                        groups)

        groups = list(groups)
        if not len(groups):
            msg = "It seems there are no groups with the necessary data"
            self.error_msg(self._connect_to_server, msg=msg, critical=False)

        groups = map(lambda x: (x['attributes']['info'].split(self.search_delimiter),
                                search_user(x['attributes']['member'], users)), groups)

        groups = list(groups)
        if len([user for item in list(groups) for user in item[1] if not user]):
            msg = "Can not get user information."
            self.error_msg(self._connect_to_server, msg=msg, critical=True)

        return groups

    def _format_data(self, raw):
        aliases = {user[0]: user[1] for item in raw for user in item[1]}
        for user in aliases:
            print(user)
        groups = {'SVN_{}'.format(user.lower()): [user.upper(), user.lower(), user.capitalize()] for user in aliases}

        directorys = []
        for item in raw:
            dirs = {}

            directory = item[0]
            directory[0] += ":"

            permission = directory.pop(-1)
            if permission == 'fb': permission = ''
            if len(directory) == 1: directory[0] += '/'

            directory = '/'.join(directory)
            dirs[directory] = [(group, permission) for group in groups if len(item[1])
                               and group.replace('SVN_', '').lower() in
                               [user[0].lower() for user in item[1]]]

            exists = [item for item in directorys if directory in [key for key in item]]
            if exists:
                exists[0][directory] += dirs[directory]
            else:
                directorys.append(dirs)

        return {'aliases': aliases, 'groups': groups, 'directorys': directorys}

    def _close_connection(self):
        self.connection.unbind()

    def collect_data(self):
        data = ""
        try:
            data = self._get_data()
            msg = "Data was successfully received from the server: \n\n{}".format(str(data))
            self.error_msg(self._connect_to_server, msg=msg, critical=False)
            data = self._parse_data(data)
            msg = "Data was successfully grouped: \n\n{}".format(str(data))
            self.error_msg(self._connect_to_server, msg=msg, critical=False)
            data = self._format_data(data)
            msg = "Data was successfully formatted: \n\n{}".format(str(data))
            self.error_msg(self._connect_to_server, msg=msg, critical=False)
        except:
            msg = "Can not convert data. \n\nDATA: \n\n{} \n\nTrace: \n\n{}".format(data,
                                                                                    str(format_exc()))
            self.error_msg(self._connect_to_server, msg=msg, critical=True)
        finally:
            self._close_connection()

        self.template_data = data
        return self.template_data

    def generate_template(self):
        try:
            file_path = os.path.dirname(os.path.abspath(self.args_dict['TEMPLATE']))
            temp_env = Environment(loader=FileSystemLoader(file_path), trim_blocks=True)
            temp = temp_env.get_template(os.path.basename(self.args_dict['TEMPLATE']))
            data = temp.render(**self.template_data)
            msg = "The template was successfully generated with the following data: \n\n{}".format(
                str(self.template_data))
            self.error_msg(self._connect_to_server, msg=msg, critical=False)
            return data
        except:
            msg = "Can not generate template. \n\nTrace: \n\n{}".format(str(format_exc()))
            self.error_msg(self._connect_to_server, msg=msg, critical=True)

    def run(self):
        self.init()
        self.collect_data()
        return self.generate_template()


if __name__ == '__main__':
    file_name = 'access_file'
    if len(sys.argv) > 1: file_name = sys.argv[1]
    data = AccessFileGenerator().run()

    if data:
        with open(file_name, 'w') as fw:
            fw.write(data)
