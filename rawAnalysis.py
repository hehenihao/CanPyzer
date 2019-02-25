import tkinter as tk
from tkinter import ttk, Toplevel


class TablePopup(Toplevel):
    def __init__(self,
                 root=None,
                 title='数据分析',
                 value=None,
                 callback=None,
                 **kwarg):
        self.root = root
        self.value = value
        if root is not None:
            root.wm_attributes("-disabled", True)
        self.callback = callback
        Toplevel.__init__(self)
        w = 373
        h = 385
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

        tk.Label(
            self,
            text=' ',
            font=('微软雅黑', 5),
            width=12,
        ).pack(side=tk.TOP)

        self._data = tk.StringVar()
        self._data.set(value)
        _row1 = tk.Frame(self, width=self.minsize()[0], height=30, pady=5)
        _row1.pack(side=tk.TOP, fill=tk.X, padx=25)
        tk.Label(
            _row1, text='原始数据', font=('微软雅黑', 10), width=8, anchor='w').pack(
                side=tk.LEFT, padx=5)
        tk.Entry(
            _row1,
            textvariable=self._data,
            font=('微软雅黑', 10),
            width=30,
            state='readonly').pack(
                side=tk.RIGHT, fill=tk.X, padx=5)
        tmp = value.strip().replace(' ','')
        self._binData = '{0:0>64}'.format(bin(int(tmp, base=16))[2:])

        self._type = tk.StringVar()
        self._type.set('Intel')
        _row2 = tk.Frame(self, width=self.minsize()[0], height=30, pady=5)
        _row2.pack(side=tk.TOP, fill=tk.X, padx=25)
        tk.Label(
            _row2, text='数据格式', font=('微软雅黑', 10), width=8, anchor='w').pack(
                side=tk.LEFT, padx=5)
        ttk.Combobox(
            _row2,
            value=(
                'Intel',
                'Motorola',
            ),
            width=30,
            state='readonly',
            textvariable=self._type).pack(
                side=tk.RIGHT, fill=tk.X, padx=5)

        self._start = tk.IntVar()
        self._start.set(0)
        _row3 = tk.Frame(self, width=self.minsize()[0], height=30, pady=5)
        _row3.pack(side=tk.TOP, fill=tk.X, padx=25)
        tk.Label(
            _row3, text='起始位', font=('微软雅黑', 10), width=8, anchor='w').pack(
                side=tk.LEFT, padx=5)
        tk.Scale(
            _row3,
            from_=0,
            to=64,
            orient=tk.HORIZONTAL,
            variable=self._start,
            width=30,
            command=self._range1).pack(
                side=tk.RIGHT, fill=tk.X, padx=5, expand=True)

        self._end = tk.IntVar()
        self._end.set(0)
        _row4 = tk.Frame(self, width=self.minsize()[0], height=30, pady=5)
        _row4.pack(side=tk.TOP, fill=tk.X, padx=25)
        tk.Label(
            _row4, text='结束位', font=('微软雅黑', 10), width=8, anchor='w').pack(
                side=tk.LEFT, padx=5)
        tk.Scale(
            _row4,
            from_=0,
            to=64,
            orient=tk.HORIZONTAL,
            variable=self._end,
            width=30,
            command=self._range2).pack(
                side=tk.RIGHT, fill=tk.X, padx=5, expand=True)

        _row6 = tk.Frame(self, width=self.minsize()[0], height=30, pady=5)
        _row6.pack(side=tk.TOP, fill=tk.X, padx=25)
        # tk.Label(
        #     _row6, text='二进制数', font=('微软雅黑', 10), width=12, anchor='w').pack(
        #         side=tk.LEFT, padx=5)
        self._text = tk.Text(
            _row6,
            font=('微软雅黑', 10),
            background='#eee',
            height=2)
        self._text.pack(
                side=tk.LEFT, fill=tk.X, padx=5, expand=True)
        _head = self._binData[:32]
        _tmp1 = ' '.join([_head[4*i:4*i+4] for i in range(8)])
        _tail = self._binData[32:]
        _tmp2 = ' '.join([_tail[4*i:4*i+4] for i in range(8)])
        self._text.insert('1.0', '   ' + _tmp1+'\n')
        self._text.insert('2.0', '   ' + _tmp2)
        self._text.tag_config('selected', background='yellow',foreground='red')
        # self._text.tag_add('selected', '1.0', '1.1')

        self._selectedvalue = tk.StringVar()
        _row5 = tk.Frame(self, width=self.minsize()[0], height=30, pady=5)
        _row5.pack(side=tk.TOP, fill=tk.X, padx=25)
        tk.Label(
            _row5, text='截取数据', font=('微软雅黑', 10), width=8, anchor='w').pack(
                side=tk.LEFT, padx=5)
        tk.Entry(
            _row5,
            textvariable=self._selectedvalue,
            font=('微软雅黑', 10),
            width=30,
            state='readonly').pack(
                side=tk.RIGHT, fill=tk.X, padx=5)

        self._value = tk.StringVar()
        _row5 = tk.Frame(self, width=self.minsize()[0], height=30, pady=5)
        _row5.pack(side=tk.TOP, fill=tk.X, padx=25)
        tk.Label(
            _row5, text='最终值', font=('微软雅黑', 10), width=8, anchor='w').pack(
                side=tk.LEFT, padx=5)
        tk.Entry(
            _row5,
            textvariable=self._value,
            font=('微软雅黑', 10),
            width=30,
            state='readonly').pack(
                side=tk.RIGHT, fill=tk.X, padx=5)

        _row7 = tk.Frame(self)
        _row7.pack(pady=5, side=tk.BOTTOM)
        tk.Button(
            _row7, text='确定', font=('微软雅黑', 9), width=6,
            command=self._ok).pack(
                side=tk.LEFT, padx=30)
        self.protocol('WM_DELETE_WINDOW', self._cancel)
        # self.grab_set()

    def _ok(self):
        if self.root is not None:
            self.root.wm_attributes("-disabled", False)
        self.destroy()

    def _cancel(self):
        if self.root is not None:
            self.root.wm_attributes("-disabled", False)
        self.destroy()

    def _range1(self, value):
        if self._start.get() >= self._end.get():
            self._start.set(self._end.get())
        self._calculate()

    def _range2(self, value):
        if self._start.get() > self._end.get():
            self._end.set(self._start.get())
        self._calculate()

    def _calculate(self):
        self._text.tag_delete('selected')
        self._value.set(0)
        _bytesall = self._data.get().strip().split(' ')
        _startbit = self._start.get()
        _endbit = self._end.get()
        _bitsize = _endbit - _startbit
        _bytes = []
        _startByte = int(_startbit / 8)
        _endByte = int((_endbit-1)/ 8)
        _usedlen = 0
        if _startbit == _endbit:
            return
        # highlight the selected range
        if _endbit <= 32:
            self._text.tag_add(
                'selected', '1.' + str(_startbit + int(_startbit / 4) + 3),
                '1.' + str(_endbit + int(_endbit / 4) + 3))
        elif _startbit >= 32:
            self._text.tag_add(
                'selected', '2.' + str(_startbit-32 + int((_startbit-32) / 4  + 3)),
                '2.' + str(_endbit-32 + int((_endbit-32) / 4) + 3))
        elif _startbit < 32 and _endbit > 32:
            self._text.tag_add(
                'selected', '1.' + str(_startbit + int(_startbit / 4)  + 3),
                '1.42')
            self._text.tag_add(
                'selected', '2.3',
                '2.' + str(_endbit-32 + int((_endbit-32) / 4)  + 3))

        for i in range(_startByte, _endByte+1):
            if i == _startByte:
                _masklen = 8 - _startbit % 8 if (8 - _startbit % 8) < _bitsize else _bitsize
                print(i, _masklen)
            elif i == _endByte:
                if _endbit == _endByte*8:
                    _masklen = 0
                elif _endbit == _endByte*8+8:
                    _masklen = 8
                else:
                    _masklen = _endbit % 8
                print(i, _masklen)
            else:
                _bytes.append(self._data.get().split(' ')[i])
        self._text.tag_config('selected', background='yellow',foreground='red')