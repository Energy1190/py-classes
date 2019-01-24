import os
import tkinter as tk
import tkinter.ttk as ttk
from my_package.functions.oracle_vars import *
from my_package.functions.oracle_vars import get as get_env
from my_package.functions.oracle_main import main as init
from my_package.functions.oracle_main import read as read_cmd
from tkinter.messagebox import showerror, askokcancel
from tkinter.filedialog import askopenfilename, askdirectory

class OracleGUI:
    CONFIG = os.sep.join(os.path.abspath( __file__ ).split(os.sep)[:-1]) + os.sep + 'config.ini'
    ACTIONS = ['import', 'export']

    def __init__(self, master, envs=None):
        self.vars = {}
        self.objs = {}

        self.flags = {}
        self.parameters = {}

        self.envs = envs
        self.master = master

        self.define_all_vars()
        self.define_all_frames()
        self.checks()

    def create_named_frame(self, name):
        return tk.LabelFrame(self.master, text=name, borderwidth=2, relief=tk.GROOVE)

    def build(self,name,names,row=0, column=0,rowspan=1):
        frame = self.create_named_frame(name)
        frame.grid(row=row, column=column, rowspan=rowspan, sticky=tk.N + tk.S + tk.E + tk.W)
        names = self.config_build(frame, names)
        self.build_frame(frame,names)

    def build_frame(self, master, names):
        counter = 0
        for item in names:
            obj = tk.Label(master, text=item)
            obj.grid(row=counter, column=0, sticky=tk.W)
            names[item].grid(row=counter, column=1, sticky=tk.W + tk.E)

            counter += 1

    def create_button_frame(self,name,master,elem_class,callback,**kwargs):
        obj = tk.Frame(master)
        self.create_element(name,obj,elem_class,**kwargs).grid(row=0, column=0, sticky=tk.W + tk.E)
        self.create_element(name,obj, tk.Button, text='...', command=callback).grid(row=0, column=1, sticky=tk.W + tk.E)
        return obj

    def create_element(self,name,master, elem_class, **kwargs):
        element = elem_class(master, **kwargs)
        if not self.objs.get(name): self.objs[name] = []
        self.objs[name].append(element)
        return element

    def define_all_vars(self):
        self.create_var(VAR_CONFIG, tk.StringVar, self.CONFIG, self.checks)
        self.create_var(VAR_ACTION, tk.StringVar, self.ACTIONS[0], self.checks)
        self.create_var(VAR_LOCALC, tk.BooleanVar, True, self.checks)
        self.create_var(VAR_PDBCHK, tk.BooleanVar, False, self.checks)
        self.create_var(VAR_SERVER, tk.StringVar, 'localhost', self.checks)
        self.create_var(VAR_PORTNM, tk.IntVar, 1521, self.checks)
        self.create_var(VAR_INSTAN, tk.StringVar, 'ORACLE',self.checks)
        self.create_var(VAR_PDBNAM, tk.StringVar, 'ORACLE', self.checks)
        self.create_var(VAR_SYSDBA, tk.BooleanVar, True, self.checks)
        self.create_var(VAR_LOGINA, tk.StringVar, 'sys',self.checks)
        self.create_var(VAR_LOGINT, tk.StringVar, 'sys',self.checks)
        self.create_var(VAR_PASSWA, tk.StringVar, 'sys',self.checks)
        self.create_var(VAR_PASSWT, tk.StringVar, 'sys',self.checks)
        self.create_var(VAR_HOMENM, tk.StringVar, '', self.checks)
        self.create_var(VAR_CREATE, tk.BooleanVar, True, self.checks)
        self.create_var(VAR_TABLES, tk.StringVar, 'USERS',self.checks)
        self.create_var(VAR_DIRNAM, tk.StringVar, 'IMPORT',self.checks)
        self.create_var(VAR_DIRPAT, tk.StringVar, '', self.checks)
        self.create_var(VAR_PARALL, tk.IntVar, 50,self.checks)
        self.create_var(VAR_OPTSNM, tk.StringVar, '', self.checks)
        self.create_var(VAR_MODENM, tk.StringVar, 'FULL', self.checks)
        self.create_var(VAR_SCHEMA, tk.StringVar, '', self.checks)
        self.create_var(VAR_SPECFL, tk.StringVar, '', self.checks)
        self.create_var(VAR_DEBUGM, tk.BooleanVar, False, self.checks)
        self.create_var(VAR_SPECUS, tk.BooleanVar, False, self.checks)

    def create_var(self,name, var_type, default=None,func=None):
        self.vars[name] = var_type(self.master)
        if default: self.vars[name].set(default)
        if func: self.vars[name].trace('w', func)
        return self.vars[name]

    def checks(self, *args):
        if not self.vars[VAR_PDBCHK].get():
            [item.configure(state='disabled') for item in self.objs[VAR_PDBNAM]]
            self.vars[VAR_PDBNAM].set('')
        elif self.vars[VAR_PDBCHK].get():
            [item.configure(state='normal') for item in self.objs[VAR_PDBNAM]]

        if not self.vars[VAR_CREATE].get():
            [item.configure(state='disabled') for item in self.objs[VAR_TABLES]]
        elif self.vars[VAR_CREATE].get():
            [item.configure(state='normal') for item in self.objs[VAR_TABLES]]

        if not self.vars[VAR_LOCALC].get():
            [item.configure(state='normal') for item in self.objs[VAR_SERVER]]
            [item.configure(state='normal') for item in self.objs[VAR_PORTNM]]
        elif self.vars[VAR_LOCALC].get():
            [item.configure(state='disabled') for item in self.objs[VAR_SERVER]]
            [item.configure(state='disabled') for item in self.objs[VAR_PORTNM]]

        if self.vars[VAR_ACTION].get() == 'import':
            [item.configure(state='normal') for item in self.objs[VAR_SPECFL]]
        else:
            [item.configure(state='disabled') for item in self.objs[VAR_SPECFL]]

        if self.vars[VAR_MODENM].get() == 'SCHEMA':
            [item.configure(state='normal') for item in self.objs[VAR_SCHEMA]]
        else:
            [item.configure(state='disabled') for item in self.objs[VAR_SCHEMA]]

        if self.vars[VAR_SPECUS].get():
            [item.configure(state='normal') for item in self.objs[VAR_SPECFL]]
        else:
            [item.configure(state='disabled') for item in self.objs[VAR_SPECFL]]

    def _callback_set_config(self, var, filetypes=[("*.ini files", "*.ini"),("*.yaml files", "*.yaml")]):
        value = askopenfilename(initialdir=os.sep.join(os.path.abspath( __file__ ).split(os.sep)[:-1]),
                                filetypes=filetypes)
        if value: var.set(value)

    def _callback_set_home(self, var):
        value = askdirectory(initialdir=os.sep.join(os.path.abspath( __file__ ).split(os.sep)[:-1]))
        if value: var.set(value)

    def config_build(self,master, names):
        result = {}
        for item in names:
            if names[item].get('frame'):
                element = self.create_button_frame(names[item]['name'],master,names[item]['class'],names[item]['frame'],**names[item]['opts'])
            else:
                element = self.create_element(names[item]['name'],master,names[item]['class'],**names[item]['opts'])
            result[item] = element

        return result

    def build_name(self,name, _class, frame=None,**opts):
        result = {'name': name,
                  'class': _class,
                  'opts': {}}

        if _class == ttk.Combobox or _class == tk.Entry:
            result['opts']['textvariable'] = self.vars[name]
        else:
            result['opts']['variable'] = self.vars[name]

        if frame:
            result['frame'] = frame

        if opts:
            for item in opts:
                result['opts'][item] = opts[item]

        return result

    def define_all_frames(self):
        names = {'Действие:': self.build_name(VAR_ACTION,ttk.Combobox,state='readonly',values=self.ACTIONS),
                 'Конфигурация: ': self.build_name(VAR_CONFIG,tk.Entry,frame=lambda: self._callback_set_config(self.vars[VAR_CONFIG]))}
        self.build("Начальная конфигурация",names,row=0, column=0)

        names = {'Localhost:': self.build_name(VAR_LOCALC,tk.Checkbutton),
                 'PDB:': self.build_name(VAR_PDBCHK,tk.Checkbutton),
                 'Сервер:{}'.format(' '*47): self.build_name(VAR_SERVER,tk.Entry),
                 'Порт:': self.build_name(VAR_PORTNM,tk.Entry)}
        self.build("Cетевая конфигурация", names, row=0, column=1, rowspan=2)

        names = {'Инстанс:': self.build_name(VAR_INSTAN,tk.Entry),
                'PDB инстанс:  ': self.build_name(VAR_PDBNAM,tk.Entry)}
        self.build("Инстанс", names, row=0, column=3)

        names = {'SYSDBA:': self.build_name(VAR_SYSDBA,tk.Checkbutton),
                 'Логин:': self.build_name(VAR_LOGINA,tk.Entry),
                 'Пароль:': self.build_name(VAR_PASSWA,tk.Entry),
                 'ORACLE_HOME:': self.build_name(VAR_HOMENM,tk.Entry,frame=lambda: self._callback_set_home(self.vars[VAR_HOMENM]))}
        self.build("Аутентификация", names, row=2, column=0)

        names = {'Создать\Изменить пользователя:': self.build_name(VAR_CREATE,tk.Checkbutton),
                 'Логин:': self.build_name(VAR_LOGINT,tk.Entry),
                 'Пароль:': self.build_name(VAR_PASSWT,tk.Entry),
                 'Табличное пространство:': self.build_name(VAR_TABLES,tk.Entry)}
        self.build("Исполнитель", names, row=2, column=1)

        names = {'Название:           ': self.build_name(VAR_DIRNAM,tk.Entry),
                 'Путь:': self.build_name(VAR_DIRPAT,tk.Entry,frame=lambda: self._callback_set_home(self.vars[VAR_DIRPAT]))}
        self.build("Директория", names, row=1, column=0)

        names = {'Параллелизм:': self.build_name(VAR_PARALL,tk.Entry),
                 'Доп. опции:':  self.build_name(VAR_OPTSNM,tk.Entry)}
        self.build("Опции", names, row=1, column=3)

        names = {'Режим:': self.build_name(VAR_MODENM,ttk.Combobox,state='readonly',values=['FULL','SCHEMA']),
                 'Схема:': self.build_name(VAR_SCHEMA,tk.Entry),
                 'Cпецификация:': self.build_name(VAR_SPECFL,tk.Entry,frame=lambda: self._callback_set_config(self.vars[VAR_SPECFL], [("*.spec files", "*.spec"),]))}
        self.build("Режим", names, row=3, column=0)

        names = {'Отладка:': self.build_name(VAR_DEBUGM,tk.Checkbutton),
                 'Использовать / Создать спецификацию:   ': self.build_name(VAR_SPECUS,tk.Checkbutton)}
        self.build("Прочее", names, row=3, column=1)

        frame = self.create_named_frame('Команды')
        frame.grid(row=2, column=3, sticky=tk.N + tk.S + tk.E + tk.W)

        tk.Button(frame, text='Загрузить конфигурацию', command=self._callback_load_config).pack(anchor=tk.CENTER,fill=tk.X)
        tk.Button(frame, text='Запустить программу', command=self._callback_start_work).pack(anchor=tk.CENTER,fill=tk.X)
        tk.Button(frame, text='Отобразить команду', command=self._callback_get_cmd).pack(anchor=tk.CENTER,fill=tk.X)

    def _callback_load_config(self):
        filepath = self.vars[VAR_CONFIG].get()
        if os.path.exists(filepath) and os.path.isfile(filepath):
            envs, error = read_config(filepath)
            if error:
                showerror(title='Ошибка', message='Не удалось прочитать конфигурационный файл.')
            else:
                self.envs = envs
                self.set_vars_from_envs()
        else:
            showerror(title='Ошибка', message='Конфигурационный файл не найден.')

    def set_var(self,var_name,env_name):
        env, empty = get_env(self.envs,env_name)
        if not empty:
            self.vars[var_name].set(env)

    def set_vars_from_envs(self):
        self.set_var(VAR_LOCALC, ENV_LOCALC)
        self.set_var(VAR_SERVER, ENV_SERVER)
        self.set_var(VAR_PORTNM, ENV_PORTNM)
        self.set_var(VAR_INSTAN, ENV_INSTAN)
        self.set_var(VAR_PDBNAM, ENV_PDBNAM)
        self.set_var(VAR_PDBCHK, ENV_PDBCHK)
        self.set_var(VAR_LOGINA, ENV_LOGINA)
        self.set_var(VAR_LOGINT, ENV_LOGINT)
        self.set_var(VAR_PASSWA, ENV_PASSWA)
        self.set_var(VAR_PASSWT, ENV_PASSWT)
        self.set_var(VAR_HOMENM, ENV_HOMENM)
        self.set_var(VAR_TABLES, ENV_TABLES)
        self.set_var(VAR_DIRNAM, ENV_DIRNAM)
        self.set_var(VAR_DIRPAT, ENV_DIRPAT)
        self.set_var(VAR_PARALL, ENV_PARALL)
        self.set_var(VAR_SPECUS, ENV_SPECUS)
        self.set_var(VAR_SPECFL, ENV_SPECFL)
        self.set_var(VAR_DEBUGM, ENV_DEBUGM)
        self.set_var(VAR_SCHEMA, ENV_SCHEMA)
        self.set_var(VAR_OPTSNM, ENV_OPTSNM)
        self.set_var(VAR_ACTION, ENV_ACTION)
        self.set_var(VAR_MODENM, ENV_MODENM)

    def  _callback_start_work(self):
        for item in self.vars:
            self.parameters[item] = self.vars[item].get()

        if self.vars[VAR_DEBUGM].get():
            check = askokcancel('DEBUG. Проверка переменных.', message='\n'.join(['{}: {}'.format(item,self.parameters[item]) for item in self.parameters]))
            if not check:
                return

        body = init(run=False,**self.parameters)
        if not body:
            showerror('Ошибка',message='Не опознанная ошибка при формировании запроса.')
            return

        if body.get('error'):
            showerror('Ошибка',message='Ошибка при формировании запроса: \n\n {}'.format(body.get('description')))
            return

        if self.vars[VAR_DEBUGM].get():
            check = askokcancel('DEBUG. Окончательный запрос к программе', message=body['object'].debug())
            if not check:
                return

        body['object'].run()
    
    def _callback_get_cmd(self):
        for item in self.vars:
            self.parameters[item] = self.vars[item].get()

        body = read_cmd(**self.parameters)
        if not body:
            showerror('Ошибка',message='Не опознанная ошибка при формировании запроса.')
            return
			
        if body.get('error'):
            showerror('Ошибка',message='Ошибка при формировании запроса: \n\n {}'.format(body.get('description')))
            return

        check = askokcancel('DEBUG. Окончательный запрос к программе', message=body['object'].debug())
        if not check:
            return

if __name__ == '__main__':
    root = tk.Tk()
    my_gui = OracleGUI(root)
    root.mainloop()