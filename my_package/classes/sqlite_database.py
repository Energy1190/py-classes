# Модуль на основе библиотеки sqlite3 для облегчения работы с базой данный SQL Lite.
# Основное назначение - максимально упростить работу с SQL Lite для простых проектов.
# Версия: 1.0
# Дата: 30.08.2018

import os
import sqlite3

TEXT = 'TEXT'
INTEGER = 'INTEGER'

class DbBase():
    """
        Родительский класс для все остальных классов.
        Содержит в себе методы:
            _format_result - метод для обработки сырых данных из базы, принимает в качестве аргументов список в
            данными и функцию, для их обработки, которой будет передан каждый элемент списка. Возвращает список
            обработанных значений.
    """
    def _format_result(self, raw: list, func):
        return list(map(func, raw))

class Database(DbBase):
    """
        Класс отвечает за файл - базу данных. Так же обрабатывает все запросы, распределяя их между таблицами.
        Принимает аргументы:
            path - путь к директории, где будет расположен файл базы данных
            filename - имя файла базы данных

        Включает в себя методы:
            _check_exist - проверяет существование каталога с базой, генерирует полный путь до файла базы
            _connect - соединяется с базой
            _check_connect - проверяет доступность соединения
            _check_tables - проверяет существующие таблицы в базе, записывает результат в self.tables

            execute - выполняет запрос к базе

        Пользовательские операции:
            create_table - создает таблицу в базе, принимает в качестве аргументов:
                __name - имя таблицы.
                **kwargs - словарь или набор именованных аргументов, где ключ - имя столбца базы данных, а
                значение - тип столбца базы данных.

            insert - вставляет значения в таблицу, принимает в качестве аргументов:
                __name - имя таблицы.
                **kwargs - словарь или набор именованных аргументов, где ключ - имя столбца базы данных, а
                значение - значение столбца базы данных.

            update - обновляет строки в таблице, принимает в качестве аргументов:
                __name - имя таблицы
                conditions - список кортежей, определяющих, для каких строк в базе будет производиться
                обновление. Первым значением в каждом кортеже должно быть название столбца базы, вторым
                логические оператор, третьим значение столбца в базе данных. Пример: [('number', '=', '1')].
                **kwargs - словарь или набор именованных аргументов, где ключ - имя столбца базы данных, а
                значение - новое значение для столбца базы данных.

            delete - удаляет строки в таблице, принимает в качестве аргументов:
                __name - имя таблицы.
                conditions - список кортежей, определяющих, какие строки будут удалены. Первым значением в
                каждом кортеже должно быть название столбца базы, вторым логические оператор, третьим
                значение столбца в базе данных. Пример: [('number', '=', '1')].

            select - предоставляет строки из таблицы, принимает в качестве аргументов:
                __name - имя таблицы.
                __conditions - список кортежей, определяющих, какие строки будут возвращены. Первым значением в
                каждом кортеже должно быть название столбца базы, вторым логические оператор, третьим
                значение столбца в базе данных. Пример: [('number', '=', '1')].
                __columns - список, определяющий, какие строки будут возвращены (секция SELECT).
                __limit - число, определяет лимит возвращаемых строк.
                __order_by - строка, определяет порядок сортировки строк.


    """
    def __init__(self, path='.', filename='data.db'):
        self.path = path
        self.name = filename

        self.tables = {}

        self._check_exist()
        self._check_connect()
        self._check_tables()

        self.lastrowid = 0

    def _check_exist(self):
        if not os.path.exists(self.path): os.mkdir(self.path)
        self.path = os.path.join(self.path, self.name)

    def _connect(self):
        return sqlite3.connect(self.path)

    def _check_connect(self):
        try: self.execute("SELECT SQLITE_VERSION()")
        except: raise

    def _get_tables(self):
        query = self.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return self._format_result(query, self._get_first_element)

    def _get_first_element(self, data):
        if data and len(data) >= 1: return data[0]
        else: return None

    def _check_tables(self):
        tables = self._get_tables()
        [self.tables.setdefault(table,Table(table, self)) for table in tables]

    def execute(self, execute_string, insert=None):
        connection = self._connect()
        cursor = connection.cursor()

        if insert: cursor.execute(execute_string, insert)
        else: cursor.execute(execute_string)

        self.lastrowid = cursor.lastrowid
        result = cursor.fetchall()

        connection.commit()
        connection.close()

        return result

    def insert(self, __name, **kwargs):
        return self.tables[__name].insert(**kwargs)

    def update(self, __name, *args, **kwargs):
        return self.tables[__name].update(*args, **kwargs)

    def select(self, __name, *args, **kwargs):
        return self.tables[__name].select(*args, **kwargs)

    def delete(self, __name, *args, **kwargs):
        return self.tables[__name].delete(*args, **kwargs)

    def create_table(self, __name: str, __if_exist=True, **kwargs):
        if not __if_exist: __if_exist = ''

        kwargs_string = ''
        for item in kwargs:
            kwargs_string += '{} {}, '.format(item, kwargs[item])

        query = 'CREATE TABLE {} {} ({})'.format((__if_exist and 'IF NOT EXISTS'), __name, kwargs_string[:-2])
        self.execute(query)

        self.tables[__name] = Table(__name, self)

class Table(DbBase):
    '''
        Класс отвечающий за работу с конкретной таблицей, содержит основную логику работы для всех операций с базой.
        Содержит информацию о столбцах в таблице, в списке  self.columns. При создании принимает аргументы:
            name - имя таблицы.
            database - класс отвечающий за работу с базой
    '''
    def __init__(self, name: str, database: Database):
        self.db = database
        self.name = name

        self.columns = {}

        self._set_columns()

    def execute(self, *args, **kwargs):
        # Все обращения к базе переадресуются классу отвечающему за базу
        return self.db.execute(*args,**kwargs)

    def _get_dict_columns(self, data):
        # Метод для _format_result, для получения информации о столбцах таблицы
        if data and len(data) >= 3:
            return {data[1]: {'index': data[0],'type': data[2].upper()}}
        else:
            return {'EMPTY': {}}

    def _check_column_exist(self, name):
        # Проверка существования столбца таблицы
        if name not in [obj for obj in self.columns]: return False
        else: return True

    def _get_full_dict(self, data):
        # Метод для _format_result, преобразует сырые данные, где каждая строка представлена кортежем в словарь, ключами у
        # которого становятся названия столбцов в базе, работает только с SELECT * FROM, если в выборке представлены все столбцы
        if data and len(data) and len(data) == len(self.columns):
            return {column:data[num] for num in range(len(data)) for column in self.columns if self.columns[column]['index'] == num }
        else:
            return data

    def full_output(func):
        # Декоратор для _get_full_dict
        def wraper(self,*args, **kwargs):
            return self._format_result(func(self,*args,**kwargs), self._get_full_dict)
        return wraper

    def insert(self, **kwargs):
        values_list = []
        template_list = []
        kwargs_list = []
        for item in kwargs:
            if not self._check_column_exist(item): assert False, 'Column {} not found'.format(item)
            kwargs_list.append(item)
            template_list.append('?')
            values_list.append(kwargs[item])

        kwargs_string = ','.join(kwargs_list)
        values_string = ','.join(template_list)
        query = 'INSERT INTO {} ({}) VALUES ({})'.format(self.name,kwargs_string,values_string)
        self.execute(query,values_list)

    def update(self, conditions: list, **kwargs):
        conditions_list = []
        for condition in conditions:
            conditions_list.append('{} {} "{}"'.format(*condition))

        kwargs_list = []
        for item in kwargs:
            kwargs_list.append('{} = "{}"'.format(item,kwargs[item]))

        conditions_string = ','.join(conditions_list)
        kwargs_string = ','.join(kwargs_list)
        query = 'UPDATE {} SET {} WHERE {}'.format(self.name, kwargs_string, conditions_string)
        self.execute(query)

    def delete(self, conditions=None, **kwargs):
        if conditions:
            conditions_list = []
            for condition in conditions:
                conditions_list.append('{} {} "{}"'.format(*condition))

            conditions_string = ' AND '.join(conditions_list)
            query = 'DELETE FROM {} WHERE {}'.format(self.name, conditions_string)

        else:
            query = 'DELETE FROM {}'.format(self.name)

        self.execute(query)

    @full_output
    def select(self, __conditions=None, __columns=None, __limit=None, __order_by=None):
        if not __columns: __columns = '*'
        else: __columns = ','.join(__columns)

        query = 'SELECT {} FROM {} '.format(__columns,self.name)
        if __conditions and len(__conditions):
            conditions_list = []
            for condition in __conditions:
                conditions_list.append('{} {} "{}"'.format(*condition))

            conditions_string = ','.join(conditions_list)
            query += 'WHERE {}'.format(conditions_string)

        if __order_by:
            query += 'ORDER BY "{}"'.format(__order_by)

        if __limit:
            query += 'LIMIT {}'.format(str(__limit))

        return self.execute(query)

    def _set_columns(self):
        # Получение информации о столбцах таблицы
        result = self.execute('PRAGMA table_info({});'.format(self.name))
        self.columns = { key:item[key] for item in self._format_result(result, self._get_dict_columns) for key in item}

# Примеры для работы с базой:
#   x = Database()
#
#   array = {'id': 'INTEGER PRIMARY KEY', 'name': 'TEXT', 'age': 'INTEGER'}
#
#   x.create_table('test', **array)                                            - Создание таблицы
#   x.insert('test', name='Bob', age=12)                                       - Добавление данных
#   x.update('test', [('name', '=', 'Bob')], name='Tom')                       - Обновление данных
#   x.select('test', [('name', '=', 'Tom')], __orger_by='name', __limit=1)     - Получение данных
#   x.delete('test', [('name', '=', 'Tom')])                                   - Удаление данных



