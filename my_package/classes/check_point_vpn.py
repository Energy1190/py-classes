# Модуль на основе библиотеки Селениум для работы с ситемой CheckPoint VPN
# Версия: 1.0
# Дата: 19.07.2018

import os
import sys
import time
import subprocess
from threading import Thread
from .button_clicker import ButtonAutoAnswer

try:
    from selenium import webdriver
    import selenium.webdriver.support.ui as ui
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException

    SELENIUM_IMPORT = True
except:
    SELENIUM_IMPORT = False

def regExpCheckAndAdd(keyReg, keyName, encoding='cp866', debug=False):
    # Функция для проверки ключей в реестре
    existed = False
    extended = False
    pathRoot = os.environ.get('SYSTEMROOT')
    if not pathRoot:
        return False

    pathReg = os.path.join(pathRoot, 'system32', 'reg.exe')
    if not os.path.exists(pathReg):
        return False

    try:
        r = subprocess.check_output([pathReg, 'query', keyReg])
        answer = bytes(r).decode(encoding='cp866')
        for i in answer.split(sep='\n'):
            if 'REG_SZ ' in i: existed = True
            if '{} '.format(keyName) in i: extended = True
    except subprocess.CalledProcessError as e:
        if debug: print(bytes(e.output).decode(encoding=encoding))

    if not existed:
        r = subprocess.check_output([pathReg, 'add', keyReg])
        answer = bytes(r).decode(encoding=encoding)
        if debug: print(answer)

    if not extended:
        r = subprocess.check_output(
            [pathReg, 'add', keyReg, '/v', keyName, '/t', 'REG_DWORD', '/d', '0'])
        answer = bytes(r).decode(encoding=encoding)
        if debug: print(answer)

    return (existed and extended)

def convert_time(raw_time):
    # Функция для получения секунд из строки времени
    # Ожидается строка вида "0 Дни 00:00:00"
    total_second = 0
    list_time = raw_time.split(sep=' ')
    days, name, hours = list_time
    if not str(days).isnumeric(): return 0
    total_second += int(days) * 86400

    h,m,s = hours.split(sep=':')
    if not str(h).isnumeric(): return 0
    if not str(m).isnumeric(): return 0
    if not str(s).isnumeric(): return 0

    total_second += int(h) * 3600
    total_second += int(m) * 60
    total_second += int(s)

    return total_second

class SeleniumBase():
    """
        Класс для работы Селениума.
        При инициализации принимает начальную ссылку, тип браузера, опции, которые надо передать браузеру.
        Для работы требуются драйвера, которые необходимо поместить в папку drivers в каталоге с модулем и
        установленного браузера, из под которого осуществляется работа.

        Принимает аргументы:
            url - cсылка на сайт, где развернут CheckPoint VPN
            browser - используемы селениумом браузер
            options - передаваемые браузеру настройки
            until - время ожидания для поиска эллементов, по умолчанию 15 секунд
            min_time - время, в секундах, до принудительного разрыва соединения,
                       при котором будет перезапущенно соединение, по умолчанию
                       10 минут.
            mode - режим, в котором будет работать программа, по умолчанию программа
                   запускается в режиме демона.
            debug - расширенный вывод данных в консоль.

        Методы in_browser_* определяют набор действия непосредственно с элементами сайта:
            in_browser_login - Нажатие кнопки "Регистрация"

            in_browser_re_login - Нажатие кнопки "Выполнить повторную регистрацию"

            in_browser_logout - Нажатие кнопки "Выход" в основном окне

            in_browser_exit - Нажатие кнопки "Выход" в окне подтверждения выхода

            in_browser_connect - Нажатие кнопки "Подключение" в основном окне

            in_browser_disconnect - Вызов функции "Disconnect" в окне подключения

            in_browser_main_disconnect - вызов функции для разрыва соединения в основном окне

            in_browser_switch_to_popup - Переход на всплывающее окно

            in_browser_switch_to_main - Переход на основное окно

            in_browser_wait_ssl - Ожидание определенного статуса соединения, принимает статус, которого
                                  необходимо дождаться

            in_browser_wait_connection - Ожидание разрыва соединения, принимает значение, которого
                                         необходимо дождаться

            in_browser_get_time - Получение времени до принудительного разрыва соединения
            
            in_browser_wait_time - Ожидание заданного времени
    """

    # Карта с параметрами для конкретного браузера.
    #   exe_name - файл для запуска браузера
    #   options - шаблон для передачи опций драйверу
    #   type - шаблон драйвера
    browser_map = {'IE':{'exe_name': 'iexplore.exe',
                         'options': DesiredCapabilities().INTERNETEXPLORER,
                         'type': webdriver.Ie}}
    def __init__(self, url, browser='IE', options=None, until=15, min_time=600, mode='daemon', debug=False):
        self.url = url
        self.browser = browser
        self.options = options

        self.debug = debug
        self.status = {'import': False, 'x86': False, 'x64': False, 'error': False}
        self.until = until
        self.min_time = min_time

        self.driver = None
        self.drivers = {}

        self.mode = mode
        self.modes = {'daemon': self.daemon_start}

        self.object = None
        self.main_window = None
        self.popup_windows = []

        self.exit_flag = False

    def _check_reg(self):
        # Метод для проверки существования браузера в системе
        # Совместим только c Internet Explorer
        name = self.browser_map[self.browser]['exe_name']

        x86Status = False
        x64Status = False

        x86 = os.environ.get('PROGRAMFILES(X86)')
        x64 = os.environ.get('PROGRAMFILES')

        x86Path = os.path.join(x86, 'Internet Explorer', 'iexplore.exe')
        x64Path = os.path.join(x64, 'Internet Explorer', 'iexplore.exe')

        if os.path.exists(x86Path):
            x86Status = True
            key = r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BFCACHE'
            if not (regExpCheckAndAdd(key,name,debug=self.debug)): x86Status = False

        if os.path.exists(x64Path):
            x64Status = True
            key = r'HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BFCACHE'
            if not (regExpCheckAndAdd(key,name,debug=self.debug)): x64Status = False

        self.status['x86'] =  x86Status
        self.status['x64'] =  x64Status

        return (x64Status, x86Status)

    def _check_driver(self):
        # Метод для проверки существования драйвера для селениума
        pathDir = os.path.dirname(os.path.abspath(__file__))
        pathDriverDir = os.path.join(pathDir, 'drivers')

        self.drivers['x86'] = os.path.join(pathDriverDir, 'IEDriverServer32x.exe')
        self.drivers['x64'] = os.path.join(pathDriverDir, 'IEDriverServer64x.exe')

        if not os.path.exists(self.drivers['x86']):
            pathDir = os.getcwd()
            pathDriverDir = os.path.join(pathDir, 'drivers')
            self.drivers['x86'] = os.path.join(pathDriverDir, 'IEDriverServer32x.exe')

            if not os.path.exists(self.drivers['x86']):
                self.status['x86'] = False

        if not os.path.exists(self.drivers['x64']):
            pathDir = os.getcwd()
            pathDriverDir = os.path.join(pathDir, 'drivers')
            self.drivers['x86'] = os.path.join(pathDriverDir, 'IEDriverServer64x.exe')

            if not os.path.exists(self.drivers['x64']):
                self.status['x64'] = False

    def _self_checks(self):
        # Список выполняемых проверок, результат передается в словарь self.status
        self._check_reg()
        self._check_driver()

        if self.status['x64']: self.driver = self.drivers['x64']
        elif self.status['x86']: self.driver = self.drivers['x86']
        else: assert False, "Can not perform the checks and determine the driver. Exit."

    def init(self):
        # Инициализация браузера, объект с браузером записывается в self.object
        self._self_checks()
        options = self.browser_map[self.browser]['options']
        for key, value in self.options.items():
            options[key] = value

        self.object = self.browser_map[self.browser]['type'](self.driver, capabilities=options)

    def start(self):
        # Опеределения главного окна, основное окно записывается в self.main_window
        self.object.get(self.url)

        counter = 0
        while not self.main_window:
            counter +=1
            self.main_window = self.object.current_window_handle
            if counter > 50: assert False, "Recursion error. Exit."

    def stop(self):
        # Выход из браузера
        self.object.close()
        self.object.quit()

    def refresh(self):
        # Обновление страницы
        self.object.refresh()

    def _until_click_by_xpath(self, value):
        # Шаблон для кликов по элементам
        button = ui.WebDriverWait(self.object, self.until).until(
            lambda browser: browser.find_element_by_xpath(value))

        button.click()

    def _run_script(self, name):
        # Шаблон для запуска скриптов
        self.object.execute_script(name)

    def in_browser_login(self):
        self._until_click_by_xpath('//*[@id="LoginButton"]')

    def in_browser_re_login(self):
        self._until_click_by_xpath('//*[@id="Login"]')

    def in_browser_logout(self):
        self._until_click_by_xpath('//*[@id="LogOutTD"]')

    def in_browser_connect(self):
        self._until_click_by_xpath('//*[@id="doc_btn"]')

    def in_browser_exit(self):
        self._until_click_by_xpath('//*[@id="doSignOut"]')

    def in_browser_disconnect(self):
        self._run_script('Disconnect')

    def in_browser_main_disconnect(self):
        self._run_script('ToggleSNX();')

    def in_browser_switch_to_popup(self):
        popup_window_handle = None

        counter = 0
        while not popup_window_handle:
            counter += 1
            time.sleep(0.1)
            for handle in self.object.window_handles:
                if handle != self.main_window:
                    popup_window_handle = handle
                    break
            if counter > 50: assert False, "Recursion error. Exit."

        self.object.switch_to_window(popup_window_handle)

    def in_browser_switch_to_main(self):
        self.object.switch_to_window(self.main_window)

    def in_browser_wait_ssl(self, wait):
        counter = 0
        while counter < 50:
            counter += 1
            time.sleep(1)
            status = self.object.find_element_by_xpath('//*[@id="displayStatus"]').text
            if status == wait: break

    def in_browser_wait_connection(self, wait):
        counter = 0
        while counter < 50:
            counter += 1
            time.sleep(1)
            value = self.object.find_element_by_xpath('//*[@id="doc_btn"]').get_attribute('value')
            if value == wait: break

    def in_browser_get_time(self):
        try: return convert_time(self.object.find_element_by_xpath('//*[@id="remaining_time"]').text)
        except: return 0

    def in_browser_wait_time(self):
        while True:
            time.sleep(1)
            now = self.in_browser_get_time()
            if now < self.min_time: break

    def connect(self):
        # Установка соединение с сревером, может потребоваться человеческое вмешательство - подтвердить сертификат
        self.in_browser_login()
        self.in_browser_connect()

    def wait(self):
        # Ожидание истечения времени соединения
        self.in_browser_switch_to_popup()
        self.in_browser_wait_ssl("Подключено")

        time.sleep(1)
        self.in_browser_wait_time()

    def disconnect(self):
        # Разрыв соединения с сервером, может потребоваться человеческое вмешательство - всплывающее окно
        self.in_browser_disconnect()
        self.object.close()

        time.sleep(1)
        self.in_browser_switch_to_main()

        time.sleep(1)
        self.in_browser_main_disconnect()
        self.in_browser_wait_connection("Подключение")

    def re_connect(self):
        # Возвращение на начальный экран
        self.in_browser_logout()
        self.in_browser_exit()
        self.in_browser_re_login()

    def daemon_mode(self):
        # Метод программы для режима демона
        self.init()
        self.start()
        while True:
            self.connect()
            self.wait()
            self.disconnect()
            self.re_connect()
            if self.exit_flag: break

    def daemon_start(self):
        # Инициализация режима демона, демон запускается в отдельном потоке
        print('-----------------------------------')
        print('VPN connection run in daemon mode.')
        print('    Start daemon.')
        Thread(target=self.daemon_mode).start()
        print('    Started.')
        print('-----------------------------------')
        print('Press Any button to exit')
        input()

        print('Exit.')
        self.exit_flag = True
        sys.exit(0)

    def run(self):
        # Метод запуска.
        self.modes[self.mode]()

class SeleniumExtended(SeleniumBase):
    def __init__(self, *args, auth_window_title=None, auth_button_title=None, **kwargs):
        self.auth_window_title = auth_window_title
        self.auth_button_title = auth_button_title

        super(SeleniumExtended, self).__init__(*args,**kwargs)

    def auth_click(self):
        while True:
            try:
                security_event = ButtonAutoAnswer(self.auth_window_title, self.auth_button_title)

                security_event.find()
                security_event.click()

                self.in_browser_connect()
                break
            except:
                pass

    def connect(self):
        self.in_browser_login()

        try:
            self.in_browser_connect()
        except:
            self.auth_click()

#if __name__ == '__main__':
#    options = {'ignoreProtectedModeSettings': True,
#               'acceptSslCerts': True}
#
#    x = SeleniumBase('https://example.com',options=options)
#    x.run()
