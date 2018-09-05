import ctypes

class ButtonAutoAnswer():
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc =  ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    EnumChildWindows = ctypes.windll.user32.EnumChildWindows

    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW

    SendMessage = ctypes.windll.user32.SendMessageW

    def __init__(self, wnd_title, btn_title):
        self.wnd_title = wnd_title
        self.btn_title = btn_title

        self.map = {}
        self.windows = []
        self.current_title = None
        self.current_descriptor = None

        self.target_descriptor = None

    def callback_window(self, *args, **kwargs):
        wnd_descriptor, *over = args
        if self.IsWindowVisible(wnd_descriptor):
            text = self.get_winapi_text(wnd_descriptor)
            self.windows.append((wnd_descriptor, text))

        return True

    def callback_child(self, descriptor, *args, **kwargs):
        length = self.GetWindowTextLength(descriptor)
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.GetWindowText(descriptor, buffer, length + 1)

        if self.current_title:
            if self.current_title not in self.map: self.map[self.current_title] = {}
            self.map[self.current_title]['descriptor'] = self.current_descriptor

            if 'buttons' not in self.map[self.current_title]: self.map[self.current_title]['buttons'] = {}
            if buffer.value: self.map[self.current_title]['buttons'][buffer.value] = descriptor

        return True

    def get_winapi_text(self, descriptor, *args, **kwargs):
        length = self.GetWindowTextLength(descriptor)
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.GetWindowText(descriptor, buffer, length + 1)
        return buffer.value

    def find_window(self):
        self.EnumWindows(self.EnumWindowsProc(self.callback_window), 0)

    def find_child_window(self):
        for descriptor, title in self.windows:
            self.current_title = title
            self.current_descriptor = descriptor
            self.EnumChildWindows(descriptor, self.EnumWindowsProc(self.callback_child), 0)

    def output(self):
        for title in self.map:
            print(title)
            for item in self.map[title]:
                if item != 'buttons': print(' - ', item, ':', self.map[title][item])

            print(' - ', 'buttons:')
            for button in self.map[title]['buttons']:
                print('     - ', button, ':', self.map[title]['buttons'][button])
            print(' ')

    def find_target(self):
        if self.wnd_title in self.map:
            if self.btn_title in self.map[self.wnd_title]['buttons']:
                self.target_descriptor = self.map[self.wnd_title]['buttons'][self.btn_title]

    def click(self):
        if self.target_descriptor:
            self.SendMessage(self.target_descriptor, 0x00F5, 0, 0)

    def find(self):
        self.find_window()
        self.find_child_window()
        self.find_target()
