import os
import pickle
from traceback import format_exc
from collections import defaultdict
from my_package.classes.sqlite_database import Database as Db
from my_package.classes.flask_cache import ArrayFlaskCache as Cache

def init_config(db, cache):
    info = {}
    datafilepath = os.environ.get('DB_FILE') or '.db'
    with open(datafilepath, 'rb') as file:
        info = pickle.load(file)

    required = ['filename', 'filepath', 'table']
    for item in required:
        if item not in list(info) or not info[item]: return False

    db = Db(path=info['filepath'], filename=info['filename'])
    db.create_table(info['table'],
                    id='INTEGER PRIMARY KEY',
                    date='text',
                    name='text',
                    count='integer',
                    price='integer',
                    description='text',
                    causes='text')

    cache = Cache(table=info['table'], db=db)

    return True, db, cache

def accept_config(form):
    filepath = ''
    tablename = ''

    if form.get('FilePath'): filepaths = form.get('FilePath')
    else: return False

    if form.get('TableName'): tablename = form.get('TableName')
    else: return False

    try:
        path_list = filepaths.split(sep='/')
        filename = path_list[-1]
        filepath = os.path.join(*path_list[:-1])
        if not filename or not filepath: return False
    except:
        return False

    data = {'filename': filename, 'filepath': filepath, 'table': tablename}

    datafilepath = os.environ.get('DB_FILE') or '.db'
    with open('.db', 'wb') as file:
        pickle.dump(data, file)

    return True

def add_element(form, db):
    required = ['number', 'date', 'name', 'count', 'cost', 'desctiption', 'solution']
    for item in required:
        if not form.get(item): return False

    obj = None
    try:
        obj = db.get(int(form['number']))
        if obj and len(obj): return False
    except: pass

    try:
        db.set(db.max_index + 1,
                        date=form['date'],
                        name=form['name'],
                        count=int(form['count']),
                        price=int(form['cost']),
                        description=form['desctiption'],
                        causes=form['solution'])
        return True
    except:
        print(format_exc())
        return False

def remove_element(index, db):
    if not str(index).isnumeric(): return False

    obj = None
    try:
        obj = db.get(int(index))
        if not obj or not len(obj): return False
    except: return False

    db.delete(int(index), **obj)
    return True

def paginator(data, per_page=5):
    tmp_data = [(item, data[item]) for item in data]

    tmp_data = sorted(tmp_data, key= lambda x: x[0])
    tmp_data = reversed(tmp_data)

    pages = defaultdict(list)

    count = 1
    per_page_count = 0
    for obj in tmp_data:
        per_page_count += 1
        if per_page_count == per_page + 1:
            per_page_count = 0
            count += 1
        pages[count].append(obj)

    return pages
