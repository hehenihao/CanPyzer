import tkinter as tk
from tkinter import ttk, Toplevel, Widget
import re


class ItemEntery(Toplevel):
    def __init__(self, root=None, x=0, y=0, table:ttk.Treeview=None, item=None, column=0, value=None, callback=None, **kwarg):
        self.value = value
        self._table = table
        self._item = item
        self._column = column
        self._callback = callback
        self.root = root
        self._position()
        Toplevel.__init__(self)
        # Hide the root window drag bar and close button
        self.overrideredirect(True)
        # Turn off the window shadow
        # self.wm_attributes("-transparentcolor", 'white')
        # self.attributes('-alpha', 0.0)
        self.attributes('-topmost', True)
        # Set the root window background color to a transparent color
        # self.attributes('-transparent', 'systemTransparent')
        # self.config(bg='systemTransparent')
        self.positionfrom(who='user')
        self.resizable(width=False, height=False)
        x, y, width, height = self._position()
        self.geometry('{}x{}+{}+{}'.format(int(width), int(height), int(x), int(y+42)))

        self._data = tk.StringVar()
        self._data.set(value)
        _frame = tk.Frame(self, width=width, height=height)
        _frame.pack(fill=tk.BOTH, expand=True)
        self._editor = tk.Entry(_frame, textvariable=self._data, font=('微软雅黑', 9), bg='#aaa')
        self._editor.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=0)    
        self._editor.focus_set()
        self._editor.bind('<FocusOut>', self._ok)
        self._editor.bind('<Key>', self._keyDown)
        self._editor.icursor(len(self._data.get()))
        self.protocol('WM_DELETE_WINDOW', self._cancel)
        # self.grab_set()

    def _position(self):
        x, y, width, height = self._table.bbox(self._item, column=self._column)
        _width = self._table.column(self._column, 'width')
        _geo = self._table.winfo_geometry()
        _x = self._table.winfo_x()
        _y = self._table.winfo_y()
        _nowWidget = self._table
        while str(_nowWidget) != '.':
            _nowWidget = _nowWidget.master
            if str(_nowWidget) != '.':
                tmp = self._table.nametowidget(_nowWidget)
                _x = _x + tmp.winfo_x()
                _y = _y + tmp.winfo_y()
            else:
                pass
        x = x + _x
        y = y + _y
        return (x, y, width, height)
            
    def _ok(self, event):
        self.destroy()
        if self._table and self._item:
            self._callback(self._item, self._editor.get())
            # self._table.set(self._item, column=)

    def _keyDown(self, event):
        self.destroy()
        if event.keycode == 13:
            if self._table and self._item:
                self._callback(self._item, self._editor.get())
                # self._table.set(self._item, column=)

    def _cancel(self):
        self.destroy()
