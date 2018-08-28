import os
import re
import csv
import time
import threading
import datetime

from flask import Flask, render_template, url_for, Response, request

fileName = 'accountingDoc.csv'
pathToCsv = os.path.join('C:{}'.format(os.sep), 'syncs', 'Dropbox', 'WORK', 'WIKI', 'main_docs', fileName)

class MemoryObject():
    def __init__(self, pathToFile):
        self.path = pathToFile
        self.object = []

        self.lock = False

    def silentLock(func):
        def wrapper(self,*args, recursive=0, **kwargs):
            recursive += 1
            return self._callback(func, *args, recursive=recursive, **kwargs)
        return wrapper

    def _callback(self,func,*args, recursive=0, **kwargs):
        recursive += 1
        if not self.lock:
            self.lock = True
            f = func(*args, **kwargs)
            self.lock = False
            return f
        else:
            time.sleep(recursive)
            return self._callback(func, *args, recursive=recursive, **kwargs)

    def validateObject(self, writeObj):
        if type(writeObj) != list:
            return False

        for row in writeObj:
            if type(row) != list:
                return False

            for object in row:
                if type(object) != str:
                    return False

        return True

    def checkFile(self, pathToFile, recursive=False):
        if os.path.exists(pathToFile): return True
        elif not recursive:
            file = open(pathToFile, 'w')
            file.close()
            return self.checkFile(pathToFile, recursive=True)
        else:
            return False

    @silentLock
    def readFile(self, pathToFile, *args):
        result = []
        with open(pathToFile,'r', newline='') as file:
            fileData = csv.reader(file,delimiter=' ', quotechar='|')
            for row in fileData:
                result.append(row)

        self.object = result
        return result

    @silentLock
    def writeFile(self, pathToFile, writeObj, *args):
        if not self.validateObject(writeObj):
            return False

        with open(pathToFile, 'w', newline='') as file:
            fileData = csv.writer(file,delimiter=' ', quotechar='|')
            for row in writeObj:
                fileData.writerow(row)

        return True

    def silentRead(self):
        threading.Thread(target=self.readFile,args=(self,self.path,)).start()

    def silentWrite(self):
        threading.Thread(target=self.writeFile, args=(self,self.path,self.object,)).start()

    def get(self):
        if not len(self.object):
            return self.readFile(self.path)
        else:
            self.silentRead()
            return self.object

    def set(self, position):
        if type(position) != list:
            return False

        for row in position:
            if type(row) != str:
                return False

        index = [int(num[0]) for num in self.object]
        if int(position[0]) in index:
            return False

        self.object.append(position)
        self.silentWrite()
        return True

    def remove(self, object):
        if object in self.object:
            self.object.remove(object)
            self.silentWrite()
            return True

        return False

app = Flask(__name__)
mem = MemoryObject(pathToCsv)

def validateForm(object):
    if len(object) != 7:
        return False

    if len([i for i in object if not object[i]]):
        return False

    if not object.get('number').isnumeric():
        return False

    if not object.get('cost').isnumeric():
        return False

    try:
        datetime.datetime.strptime(object.get('date'), '%d.%m.%y').date()
    except:
        return False

    return True

def outputPage(requestObj, memory=mem):
    data = memory.readFile(memory, pathToCsv)
    return render_template('accountingList.html', positions=data)

def addPosition(requestObj, formDict, memory=mem):
    position = [formDict['number'],
                formDict['date'],
                formDict['name'],
                formDict['count'],
                formDict['cost'],
                formDict['desctiption'],
                formDict['solution']]
    memory.set(position)

@app.route('/', methods=['GET', 'POST'])
def mainFunc(memory=mem):
    if request.method == 'POST':
        formDict={i:request.form[i] for i in request.form}
        checkForm = validateForm(formDict)
        if checkForm: addPosition(request,formDict)

    return outputPage(request)

@app.route('/<name>', methods=['GET'])
def detailFunc(name, memory=mem):
    index = [i for i in memory.object if int(i[0]) == int(name)]
    if len(index): index = index[0]
    else: index = ['','','Объект не найден.', '','','','']
    return render_template('accountingDetail.html',data=index)

@app.route('/<name>/remove', methods=['GET'])
def removeFunc(name, memory=mem):
    object = []
    if name.isnumeric():
        index = [i for i in memory.object if int(name) == int(i[0])]
        if len(index) == 1:
            object = index[0]

    if object:
        memory.remove(object)

    return Response(response='Delete it!', status=200)

@app.route('/help')
def help_me():
    return Response(response='Help here!', status=200)

def runner():
    app.run(host='0.0.0.0', port=6001, threaded=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=6001, threaded=True)
    #writeFile(pathToCsv,[['1','08.02.2018','Барабан HP 32A CF232A черный для HP LJ Pro M203/M227(23000стр.)', '1', '5970', 'Расходник. Барабан для принтера, расположенного в бухгалтерии.', 'Замена аналогичного барабана, израсходовавшего свой ресурс.']])
