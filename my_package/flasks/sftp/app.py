# Веб-приложение, для работы SFTP
# Версия: 2.0
import os
import pickle
from flask_restful import Api, Resource, reqparse
from flask import Flask, request, jsonify, send_from_directory, render_template
from .store import WorkingCopy, Sync
from traceback import format_exc

# Получение переменных
data_path = (os.environ.get('DB_PATH') or 'data')
config_path = (os.environ.get('DB_FILE') or '.sftp')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = data_path
api = Api(app)

class BaseAPI():
    # Класс для хранения рабочей копии
    working_copy = WorkingCopy(data_path)

class HashAPI(Resource, BaseAPI):
    # Класс для получения хеша директории
    def _validate(self,path):
        if not path:
            return 'Path not specified.'

    def get(self):
        # Возвращает хеш запрошенного пути
        d = None,None
        path = request.args.get('path')
        e = self._validate(path)
        if not e:
            d, e = self.working_copy.hash(path)
        return jsonify({'data': d, 'error': e})

class ListAPI(Resource,BaseAPI):
    # Класс для просмотра рабочей директории
    def _validate(self, path):
        if not path:
            return 'Path not specified.'

    def patch(self):
        # Возвращает файл для скачивания или json с ошибкой
        d = None,None
        path = request.args.get('path')
        e = self._validate(path)
        if not e:
            d, e = self.working_copy.get(path)
            if not e:
                return send_from_directory(d['directory'],d['filename'],as_attachment=True)
        return jsonify({'data': d, 'error': e})

    def get(self):
        # Возвращает информацию о запрошеном пути
        d = None,None
        path = request.args.get('path')
        e = self._validate(path)
        if not e:
            d, e = self.working_copy.get(path)
        return jsonify({'data': d,'error':e})

class DirectoryAPI(Resource,BaseAPI):
    # Класс для работы с файлами - загрузка, удаление, добавление
    def _validate(self, path):
        if not path:
            return 'Path not specified.'

    def get(self):
        # Возвращает файл для скачивания или json с ошибкой
        d = None,None
        path = request.args.get('path')
        e = self._validate(path)
        if not e:
            d, e = self.working_copy.get(path)
            if not e:
                return send_from_directory(d['directory'],d['filename'],as_attachment=True)
        return jsonify({'data': d, 'error': e})

    def delete(self):
        description = ''
        class_description = 'alert alert-primary'
        path = request.args.get('path')
        e = self._validate(path)
        if e: return jsonify({'description': e})
        description, error = self.working_copy.delete(path)
        return jsonify({'error':error,'description': description,'class_description':class_description})

    def post(self):
        description = ''
        class_description = 'alert alert-primary'
        path = request.args.get('path')
        create_directory = request.args.get('directory')
        e = self._validate(path)
        if e: return jsonify({'description': e})
        try:
            if request.data:
                filename, directory = self.working_copy.prepare(path)
                try:
                    with open(os.path.join(directory,filename),'wb') as stream:
                        stream.write(request.data)
                    description = 'Файл "{}" успешно записан.'.format(filename)
                except:
                    print(format_exc())
                    description = 'Произошла ошибка при записи файла.'
            elif bool(create_directory):
                filename, directory = self.working_copy.prepare(path,mkdir=True)
                description = 'Была создана новая директория "{}".'.format(filename)
            else:
                description = 'Данные не были получены от клиента.'
        except:
            print(format_exc())
            description = 'Произошла ошибка при создании директории.'
        return jsonify({'description': description,'class_description':class_description})

class SyncAPI(Resource,BaseAPI):
    # Класс для синхронизации с сервером
    def _parser_answer(self,data:dict):
        # Метод для преобразования результатов синхронизации в строку
        msg = ''
        possible_keys = {'add_folder': 'Добавлено директорий',
                         'add_file': 'Добавлено файлов',
                         'remove_folder': 'Удалено директорий',
                         'remove_file': 'Удалено файлов',
                         'change_file': 'Изменено файлов'}

        for item in possible_keys:
            if item in data:
                msg += '{}: "{}". '.format(possible_keys[item],str(data[item]))

        return msg

    def post(self):
        # Метод, для вызова синхронизации
        description = ''
        parser = reqparse.RequestParser()
        parser.add_argument('action', type=str, help='Defines the type of synchronization.')
        parser.add_argument('remove', type=str, help='Whether to delete data.')
        args = parser.parse_args()
        if args['remove'].lower() == 'false': args['remove'] = False
        else: args['remove'] = True

        obj = Sync(self.working_copy,config_path)
        if args['action'] not in ['to','from']:
            return jsonify({'description':'Указанная операция не поддерживается.',
                            'class_description':"alert alert-danger"})

        data, s_error, m_errors = obj.sync(action=args['action'],remove=args['remove'])
        if s_error:
            description += s_error + ' '
        if m_errors:
            description += m_errors + ' '
        if not data and (s_error or m_errors):
            return jsonify({'description': 'Ошибка синхронизации. {}'.format(description),
                            'class_description':"alert alert-danger"})
        elif not data:
            return jsonify({'description': 'Нет объектов подлежащих синхронизации. {}'.format(description),
                            'class_description':"alert alert-warning"})

        return jsonify({'description':self._parser_answer(data) + description,'class_description':'alert alert-primary'})


class ConfigAPI(Resource):
    # Класс для работы с конфигурацией SFTP
    def post(self):
        # Метод, для получения конфигурации
        description = ''
        parser = reqparse.RequestParser()
        parser.add_argument('host', type=str, help='Defines the type of synchronization.')
        parser.add_argument('port', type=int, help='Whether to delete data.')
        parser.add_argument('login', type=str, help='Defines the type of synchronization.')
        parser.add_argument('password', type=int, help='Whether to delete data.')
        args = parser.parse_args()

        check_list = ['host','port','login','password']
        for item in check_list:
            if item not in args or not args[item]:
                return jsonify({'description': 'Получены недопустимые значения.',
                                'class_description':"alert alert-danger"})

        try:
            data = {'host':args['host'],'port':args['port'],'login':args['login'],'password':args['password']}
            pickle.dump(data, open(config_path, 'wb'))
        except:
            return jsonify({'description': 'Не удалось записать конфигурацию.',
                            'class_description': "alert alert-danger"})

        return ({'description':'Конфигурация успешно записана.','class_description':'alert alert-primary'})

api.add_resource(DirectoryAPI, '/api/v2/directory')
api.add_resource(SyncAPI, '/api/v2/directory/sync')
api.add_resource(HashAPI, '/api/v2/directory/hash')
api.add_resource(ListAPI, '/api/v2/directory/list')
api.add_resource(ConfigAPI, '/api/v2/config')

@app.route('/')
def main_page():
    return render_template('sftp.html')

@app.route('/config')
def conf_page():
    return render_template('config.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5888, threaded=True)