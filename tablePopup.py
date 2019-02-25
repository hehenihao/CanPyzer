import tkinter as tk
from tkinter import ttk, Toplevel

ENTRY = 0
COMBOBOX = 1
CHECKBOX = 2
LABEL = 3

## values
values = {
    'label1': {
        'type': ENTRY,
        'value': '1'
    },
    'label4': {
        'type': ENTRY,
        'value': '1'
    },
    'label2': {
        'type': COMBOBOX,
        'value': ['1', '2']
    },
    'label3': {
        'type': CHECKBOX,
        'value': True
    }
}

class TablePopup(Toplevel):
    def __init__(self, root=None, title='Popup', values=values, callback=None, tableItem=None, **kwarg):
        self.root = root
        self.item = tableItem
        self.values = values
        if root is not None:
            root.wm_attributes("-disabled", True)
        self.callback = callback
        Toplevel.__init__(self)
        w = 400
        h = len(values.keys())*30 + 100
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        # 计算 x, y 位置
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2) - 20
        self.attributes('-alpha', 1.0)
        self.attributes('-topmost', True)
        # self._top.attributes('-toolwindow', True)
        self.positionfrom(who='user')
        self.resizable(width=False, height=False)
        self.title(title)
        self.geometry('{}x{}+{}+{}'.format(w, h, int(x), int(y)))

        tk.Label(self, text=' ', font=('微软雅黑', 5), width=12,).pack(side=tk.TOP)

        self.result = {}
        for label in values.keys():
            _row1 = tk.Frame(self, width=self.minsize()[0], height=30, pady=5)
            _row1.pack(side=tk.TOP, fill=tk.X, padx=25)
            tk.Label(_row1, text=label, font=('微软雅黑', 10), width=12, anchor='w').pack(side=tk.LEFT, padx=5)
            if values[label]['type'] == CHECKBOX:
                tmp = tk.BooleanVar()
                self.result[label] = tmp
                tk.Checkbutton(_row1, text='', font=('微软雅黑', 10), width=12, variable=tmp).pack(side=tk.RIGHT, fill=tk.X, padx=5)
            elif values[label]['type'] == COMBOBOX and 'value' in values[label].keys():
                tmp = tk.StringVar()
                self.result[label] = tmp
                # self.result.append(tmp)
                ttk.Combobox(
                    _row1,
                    font=('微软雅黑', 10),
                    width=30,
                    values = values[label]['value'],
                    textvariable=tmp).pack(side=tk.LEFT, padx=5)
                tmp.set(values[label]['value'][0])
            elif values[label]['type'] == ENTRY:
                tmp = tk.StringVar()
                # self.result.append(tmp)
                self.result[label] = tmp
                tk.Entry(
                    _row1,
                    font=('微软雅黑', 10),
                    width=30,
                    textvariable=tmp).pack(
                        side=tk.LEFT, padx=5)
                if 'value' in values[label].keys():
                    tmp.set(values[label]['value'])
            elif values[label]['type'] == LABEL:
                self.result[label] = values[label]['value']
                tk.Label(
                    _row1,
                    text=values[label]['value'],
                    font=('微软雅黑', 10),
                    width=30,
                    anchor='w').pack(
                        side=tk.LEFT, padx=5)

        _row3 = tk.Frame(self)
        _row3.pack(pady=20)
        tk.Button(_row3, text='确定', font=('微软雅黑', 9), width=6, command=self._ok).pack(side=tk.LEFT, padx=30)
        tk.Button(_row3, text='取消', font=('微软雅黑', 9), width=6, command=self._cancel).pack(side=tk.LEFT, padx=30)
        self.protocol('WM_DELETE_WINDOW', self._cancel)
        # self.grab_set()

    def _ok(self):
        self.root.wm_attributes("-disabled", False)
        self.destroy()
        self.callback(values=self.values, item=self.item, result=self.result)

    def _cancel(self):
        print('cancel')
        self.root.wm_attributes("-disabled", False)
        self.result.clear()
        self.destroy()