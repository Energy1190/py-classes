import tkinter as tk
from my_package.gui.oracle_gui import OracleGUI

if __name__ == '__main__':
    root = tk.Tk()
    my_gui = OracleGUI(root)
    root.mainloop()