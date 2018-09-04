# Модуль содержащий класс, призванный хранить данные для web-приложений Flask
# Версия: 1.0
# Дата: 30.08.2018

import inspect

PRIMARY_INDEX = 'id'

class FlaskCache():
    def __init__(self, id=0, db=None, table=None, db_type='SQL_LITE'):
        self.id = id

        self.db = db
        self.type = db_type.lower()
        self.table = table

        self.object = {}
        self.object[PRIMARY_INDEX] = self.id

        self.functions = {}
        for name, obj in inspect.getmembers(self):
            if '_get_' in name: self.functions[name] = obj
            if '_set_' in name: self.functions[name] = obj
            if '_update_' in name: self.functions[name] = obj
            if '_delete_' in name: self.functions[name] = obj

        try: self.object = self.get(table=self.table, **{PRIMARY_INDEX: self.id})
        except: pass

    def limit_one(func):
        def wraper(self, *args, **kwargs):
            data = func(self, *args, **kwargs)
            if data and len(data) == 1: return data[0]
        return wraper

    @limit_one
    def _get_sql_lite(self, *args, **kwargs):
        table = kwargs['table']
        kwargs.pop('table', None)
        self.object = self.db.select(table, *args, **kwargs)
        return self.object

    def _set_sql_lite(self, *args, **kwargs):
        table = kwargs['table']
        kwargs.pop('table', None)
        data = self.db.insert(table, **kwargs)
        self.id = self.db.lastrowid
        return data

    def _update_sql_lite(self, *args, **kwargs):
        table = kwargs['table']
        kwargs.pop('table', None)
        self.db.update(table, *args, **kwargs)

    def _delete_sql_lite(self, *args, **kwargs):
        table = kwargs['table']
        kwargs.pop('table', None)
        self.db.delete(table, *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.functions['_get_{}'.format(self.type)](*args, **kwargs)

    def set(self, *args, **kwargs):
        return self.functions['_set_{}'.format(self.type)](*args, **kwargs)

    def update(self, *args, **kwargs):
        self.functions['_update_{}'.format(self.type)](*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.functions['_delete_{}'.format(self.type)](*args, **kwargs)

class SmartFlaskCache(FlaskCache):
    def __full_check(self, raw: list):
        for item in raw:
            if type(item) == dict:
                if item.get(PRIMARY_INDEX) and self.object.get(PRIMARY_INDEX):
                    if item[PRIMARY_INDEX] == self.object[PRIMARY_INDEX]:
                        return True

        return False

    def add(self, *args, **kwargs):
        service_list = ['table']
        self.object = {}
        self.object[PRIMARY_INDEX] = self.id
        for item in kwargs:
            if item not in service_list:
                self.object[item] = kwargs[item]

    def set(self, *args, **kwargs):
        table = kwargs['table']
        kwargs.pop('table', None)

        if not self.object: self.add(*args, **kwargs)

        conditions = []
        for item in self.object:
            conditions.append((item, '=', self.object[item]))

        try: exist = self.get(conditions, table=table)
        except: exist = None

        if not exist:
            self.functions['_set_{}'.format(self.type)](*args, table=table, **kwargs)
        elif self.__full_check(exist):
            self.functions['_update_{}'.format(self.type)](*args, table=table, **kwargs)
        else:
            self.functions['_set_{}'.format(self.type)](*args, table=table, **kwargs)
            if self.id: self.object['id'] = self.id
            else: assert False, 'Can not get id.'

    def get(self, *args, **kwargs):
        table = kwargs['table']
        kwargs.pop('table', None)

        if self.object and len(self.object) > 1:
            return self.object
        else:
            conditions = []
            for item in kwargs:
                conditions.append((item, '=', self.object[item]))

            return self.functions['_get_{}'.format(self.type)](conditions, *args, table=table)

    def delete(self, *args, **kwargs):
        table = kwargs['table']
        kwargs.pop('table', None)

        conditions = []
        for item in kwargs:
            conditions.append((item, '=', self.object[item]))

        if self.object:
            self.object = {}

        self.functions['_delete_{}'.format(self.type)](conditions, *args, table=table)

class ArrayFlaskCache():
    def __init__(self, table=None, db=None, db_type='SQL_LITE'):
        self.db = db
        self.type = db_type.lower()
        self.table = table

        self.objects = {}
        self.functions = {}
        for name, obj in inspect.getmembers(self):
            if '_init_db_' in name: self.functions[name] = obj

        self.functions['_init_db_{}'.format(self.type)]()
        self.max_index = len(self.objects)

    def _init_db_sql_lite(self):
        init_data = self.db.select(self.table)
        for item in init_data:
            self.objects[item[PRIMARY_INDEX]] = SmartFlaskCache(id=item[PRIMARY_INDEX],db=self.db,table=self.table,db_type=self.type)

    def get(self, index, *args, **kwargs):
        kwargs['table'] = self.table
        return self.objects[index].get(*args, **kwargs)

    def set(self, index, *args, **kwargs):
        kwargs['table'] = self.table
        if not self.objects.get(index):
            self.objects[index] = SmartFlaskCache(db=self.db,db_type=self.type)

        self.objects[index] = SmartFlaskCache(id=index,db=self.db,table=self.table,db_type=self.type)
        self.objects[index].set(*args, **kwargs)
        if index != self.objects[index].id: assert False, 'Can not set id.'
        self.max_index += 1

    def delete(self, index, *args, **kwargs):
        kwargs['table'] = self.table
        self.objects[index].delete(*args, **kwargs)
        self.objects.pop(index, None)
        self.max_index -= 1
