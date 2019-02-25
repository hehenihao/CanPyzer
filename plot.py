import csv
import json
import logging
import math
import os
import random
import time
import tkinter as tk
from threading import Thread
from tkinter import Canvas, Scrollbar, filedialog

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
# rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))
# log_path = os.path.dirname(os.getcwd()) + '/Logs/'
# log_name = log_path + rq + '.log'
# logfile = log_name
# fh = logging.FileHandler(logfile, mode='a')
# fh.setLevel(logging.DEBUG)
# fh.setFormatter(formatter)
# logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
ch.setFormatter(formatter)
logger.addHandler(ch)

''' signal plotter

a signal plotter using tkinter canvas

'''


lasty1, lasty2, lasty3, lasty4, lastx = 0, 0, 0, 0, 0
testLines = []

colorList = ('#FFA54F', '#FF83FA', '#FF4500', '#FDF5E6', '#F08080', '#EEE9E9',
             '#EEDC82', '#EED2EE', '#D02090', '#D1EEEE', '#DDA0DD', '#CAFF70',
             '#CAE1FF', '#CD6600', '#C1FFC1', '#CCCCCC', '#BBFFFF', '#BF3EFF',
             '#A2CD5A', '#76EEC6', '#4876FF', '#00CD00', '#228B22', '#20B2AA',
             '#228B22', '#8B7B8B', '#CDC673')


class Line:
    def __init__(self, canvas: tk.Canvas = None, id=None, name: str = '', decimal: int = 0, unit: str = '', valuetip: dict = {}, color='white', adaptation=True, history=10000):
        '''Line Class

        Keyword Arguments:
            canvas {tk.Canvas} -- canvas where the line will be drawed on (default: {None})
            id {str} -- unique id str (default: {None})
            name {str} -- name
            decimal {int} -- decimal point number of given value (default: {0})
            unit {str} -- unit of value, eg. A/V (default: {None})
            valuetip {dict} -- tip for given value (default: {None})
            color {str} -- line color (default: {'white'})
            adaptation {bool} -- auto adjust to whole canvas height (default: {True})
            history {int} -- number of points of the line (default: {10000})
        '''

        self.id = id  # 唯一
        self.name = name  # 不唯一
        self.decimal = decimal
        self.unit = unit
        self.valuetip = valuetip
        self.tags = (id, )
        self.selected = False
        self.hidden = False
        self.color = color
        self._offsety = 0
        self._offsetx = 0
        self._scaley = 1.0
        self._lastx = 0
        self._lasty = 0
        self._lastoffsety = 0
        self._lastscaley = 1.0
        self._canvas = canvas
        self._canvasy = canvas.winfo_height() / 2
        self._history = history if history < 20000 else 20000
        self._points = []
        self._valy = []
        self._x = 0
        self._starty = None
        self._maxy = 0
        self._miny = 0
        self._adaptation = adaptation

    def setSelected(self, selected=False):
        self._canvas.lift(self.id)
        self.selected = selected
        # _tags = list(self.tags)
        # if selected:
        # _tags.append('selected')
        # self.tags = tuple(set(_tags))
        # self._canvas.itemconfig(self.id, width=3, fill='white')
        # elif not selected:
        # if 'selected' in _tags:
        #     _tags.remove('selected')
        # self.tags = tuple(_tags)
        # self._canvas.itemconfig(self.id, width=1, fill=self.color)

    def setAdaptation(self, on=True):
        self._adaptation = on

    def setStatus(self, status):
        self._status = status

    def getStatus(self):
        return self._status

    def hide(self):
        self._canvas.itemconfig(self.id, state=tk.HIDDEN)
        self.hidden = True
        self.selected = False
        self.restore()

    def show(self):
        self._canvas.itemconfig(self.id, state=tk.NORMAL)
        self.hidden = False

    def addPoint(self, y):
        if self._starty is None:
            self._starty = y
            self._maxy = self._miny = y

        if y > self._maxy:
            self._maxy = y

        if y < self._miny:
            self._miny = y

        if self._history != 0:
            if len(self._points) >= self._history:
                self._offsetx = self._points[0][0]
                del self._points[0]
                del self._valy[0]
            self._points.append((self._x, -y))
            self._valy.append(y)

            self._x += 1

            # _lines = self._canvas.find_withtag(self.id)
            # _linecnt = _lines.__len__()
            # if _linecnt > self._history:
            #     self._canvas.delete(_lines[0])
            #     self._offsetx += 1
            #     for _line in _lines:
            #         self._canvas.move(_line, -1, 0)
        if len(self._points) < 2:
            return
        self._starty = (self._miny + self._maxy) / 2

        # if self._adaptation is True:
        #     if (self._maxy - self._miny)*self._scaley > self._canvas.winfo_height()*0.95:
        #         self._scaley = self._scaley * self._canvas.winfo_height()*0.95 / (self._maxy - self._miny)

        self._lastx = 0
        self._lasty = self._points[0]

    def addPoints(self, points=[]):
        '''add points to the signal points list

        Keyword Arguments:
            points {list} -- real y values (default: {[]})
        '''

        self._x += len(points)
        self._valy.extend(points)
        self._points.extend([(i, -y) for i, y in enumerate(points)])
        # points.append(self._miny)
        # points.append(self._maxy)
        self._miny = min(points)
        self._maxy = max(points)
        self._starty = (self._miny + self._maxy) / 2

        # for point in points:
            # self._valy.append(point)
            # self.addPoint(point)

    def plot(self):
        if self._canvas is not None and len(self._points) > 1 and self._starty is not None and self.hidden is False:
            offset_canvasy = self._canvasy + self._offsety
            self._canvas.delete(self.id)
            color = self.color
            if self.selected:
                color = 'white'
            _line = self._canvas.create_line(
                self._points,
                fill=color,
                width=1,
                tags=self.tags,
                activefill='white',
                activewidth=1)
            self._canvas.move(_line, -self._offsetx, offset_canvasy)
            self._canvas.scale(_line, 0, -self._starty +
                               offset_canvasy, 1.0, self._scaley)

    def configTag(self, tag):
        '''config line tag name
        if exsited, remove it
        else add it to tags tuple

        Arguments:
            tag {str} -- tag name
        '''
        _tags = list(self.tags)
        if tag not in _tags:
            self.tags = tuple(_tags.append(tag))
        else:
            self.tags = tuple(_tags.remove(tag))

    def moveY(self, y=0):
        '''move the lines in y direction by given distance

        Keyword Arguments:
            y {int} -- distance (default: {0})
        '''

        self._lastoffsety = self._offsety
        self._offsety += y
        # for _line in self._canvas.find_withtag(self.id):
        #     self._canvas.move(_line, 0, y)

    def scaleY(self, scaley=1.0):
        '''scale the lines in y direction by given factor

        Keyword Arguments:
            scaley {float} -- scale factor (default: {1.0})
        '''

        if self._starty == 65535:
            return
        self._lastscaley = self._scaley
        self._scaley = self._scaley * scaley
        # offset_canvasy = self._canvasy + self._offsety
        # for _line in self._canvas.find_withtag(self.id):
        #     self._canvas.scale(_line, 0, -self._starty+offset_canvasy, 1.0, scaley)

    def adaptation(self):
        if self._points.__len__() >= 2:
            _gap = max(self._maxy - self._miny, 1)
            tmp = (self._canvas.winfo_height()*0.9)/_gap
            if self._canvas.winfo_height()*0.9 > _gap*self._scaley:
                return
            self._scaley = tmp
            self._offsety = (self._maxy + self._miny)/2
            # self.scaleY(_scale/self._scaley)
            # print(self.id, _gap, self._scaley, self._offsety)

    def getY(self, canvasx):
        '''get (x,y) value by canvasx

        Arguments:
            canvasx {int} -- x value
        '''

        if canvasx < 0:
            canvasx = 0
        elif canvasx >= self._history:
            canvasx = self._history - 1

        # if canvasx out of points range, return the last one point
        if canvasx >= len(self._valy):
            return self._valy[-1]
        return self._valy[int(canvasx)]

    def getTipY(self, canvasx):
        '''get value Y tip by give canvasx

        Arguments:
            canvasx {int} -- canvas x 

        Returns:
            tip -- value Y tip
        '''

        _y = self.getY(canvasx)
        _scale = 10**self.decimal if self.decimal != 0 else 1
        _unit = self.unit
        _tipy = str(round(_y/_scale, self.decimal))
        if _scale == 1:
            _tipy = str(round(_y/_scale))
        if len(self.valuetip.keys()) == 0:
            return _tipy + _unit
        _tip = self.valuetip.get(_tipy, '')
        if _tip != '':
            _tipy = _tipy + _unit + ':' + _tip
        return _tipy

    def getScreenY(self, canvasx):
        '''calculate screen y by given canvas x

        Arguments:
            canvasx {int} -- canvas x

        Returns:
            screeny
        '''

        _y = -self.getY(canvasx)
        offset_canvasy = self._canvasy + self._offsety
        _y = (_y + self._starty)*self._scaley + offset_canvasy - self._starty
        # _y = offset_canvasy - self._starty
        return int(_y)

    def getMaxY(self):
        return self._maxy

    def getMinY(self):
        return self._miny

    def setOffsetY(self, offsety=0):
        self._offsety = offsety

    def getOffsetY(self):
        return self._offsety

    def setScaleY(self, scaley=1.0):
        self._scaley = scaley

    def getScaleY(self):
        return self._scaley

    def getStartY(self):
        return self._starty

    def getCenterScreenY(self):
        return (self._canvasy + self._offsety - self._starty)

    def setHistory(self, history):
        self._history = history

    def getHistory(self):
        return self._history

    def getColor(self):
        return self.color

    def getLineLen(self):
        return len(self._points)

    def restore(self):
        # for _line in self._canvas.find_withtag(self.id):
        #     self._canvas.move(_line, 0, -self._offsety)
        self._offsety = 0
        self._scaley = 1.0
        self.selected = False


class Signal(Line):
    def __init__(self, canvas=None, id=None, name='', **kwarg):
        Line.__init__(self, canvas=canvas, id=id, name=name, **kwarg)
        self.tags = (id, 'signal', )
        self.name = name


class Plotter(Canvas):
    def __init__(self, parent: tk.Frame = None, interval=20, linenum=10, save=True, drag=True, adaptation=True, lengthx=20000):
        Canvas.__init__(self, parent, bg='#345', closeenough=2)
        parent.update_idletasks()
        self.pack(fill=tk.BOTH, expand=True)
        self.update_idletasks()
        self.hScroll = Scrollbar(parent, orient='horizontal',
                                 command=self.hScrolled)
        self.hScroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.configure(yscrollcommand=None,
                       xscrollcommand=self._canvashScrolled)
        self.bind("<Button-1>", self.__mouseDown)
        self.bind("<MouseWheel>", self.__mouseScale)
        self.bind("<B1-Motion>", self.__mouseDownMove)
        self.bind("<B1-ButtonRelease>", self.__mouseUp)
        self.bind("<Enter>", self.__mouseEnter)
        self.bind("<Leave>", self.__mouseLeave)
        self.bind("<Motion>", self.__mouseHoverMove)
        self["xscrollincrement"] = 1
        self["yscrollincrement"] = 1
        self.__dataList = []
        self._rulerdata = [0]*linenum
        self.x = 0
        self.scrollx = 3.0
        self.offsety = 0
        self._interval = interval  # main loop interval to handle input data
        self._lengthx = lengthx  # scrollregion x
        self._rulerOn = False
        self._dragOn = drag  # enable mouse move items
        self._gridOn = True  # draw grid lines
        self._loopOn = True
        self._tipOn = False
        self._adaptation = adaptation
        self._ruler = None
        self._rulerX = -1
        self._save = save  # 保存数据
        self._dataWriter = None  # 数据保存writer
        self._datafile = ''  # 保存文件名称
        self._scrollOn = False
        self._lineNum = linenum
        self._firststart = True
        # this data is used to keep track of an item being dragged
        # in this app, only vertical position
        self._drag_data = {"sx": 0, "sy": 0, "x": 0, "y": 0, "item": None}
        self._lines = []
        self.after(200, self.__initCanvas)

    def __main(self):
        if self._drag_data['item'] is None:
            pass
        else:
            _item = self._drag_data['item']
            if _item._lastoffsety != _item._offsety:
                pass

        self.after(20, self.__main)

    def __loop(self):
        '''mainloop
        '''

        if self._loopOn:
            for _line in self._lines:
                # _line.adaptation()
                if _line.getLineLen() > 0:
                    _line.plot()
                pass

            self.setRulerValue()

            self.autoScrollToEnd()

            self.setSignalTip()

        self.after(self._interval, self.__loop)

    def __initCanvas(self):
        self.update_idletasks()
        self._width = self.winfo_width()
        self._height = self.winfo_height()
        self._originHeight = self.winfo_height()
        self._initHeight = self.winfo_height()
        self.drawGridLines(50)
        self.configure(scrollregion=(0, 0, self._lengthx, self.winfo_height()))
        self.xview_moveto(0)
        self.bind("<Configure>", self.__resize)
        self.__loop()

    # --------------- global API ---------------
    def setLoopStatus(self, on=False):
        '''set the mainloop status

        Keyword Arguments:
            on {bool} -- status (default: {False})
        '''

        self._loopOn = on

    def setDrag(self, on=False):
        '''enable or disable the mouse drag

        Keyword Arguments:
            on {bool} -- status (default: {False})
        '''

        self._dragOn = on

    def setRuler(self, on=False):
        '''show or hide coordinates when mouse move

        Keyword Arguments:
            on {bool} -- true for show ruler (default: {False})
        '''

        self._rulerOn = on

    def setInterval(self, interval=20):
        '''set mainloop interval

        Keyword Arguments:
            interval {int} -- loop interval (default: {20})
        '''

        self._interval = interval

    def setGrid(self, on=True):
        '''show or hide the grids

        Keyword Arguments:
            on {bool} -- true for show grid lines (default: {True})
        '''

        self._gridOn = on

    def setSignalTip(self):
        if self._tipOn and len(self._lines) > 0:
            self.delete('sigtip')
            maxlen = max([len(line.name) for line in self._lines])
            gap = (maxlen+1)*7
            gap = max(gap, 100)
            for i, line in enumerate(self._lines):
                color = line.color
                if line.hidden:
                    color = "#aaa"
                _row = int(i/5)
                _column = i % 5
                self.create_rectangle(
                    self.canvasx(10)+gap*_column, 10+20*_row, gap *
                    _column+self.canvasx(10) + 10, 20*_row+20,
                    fill=color, tags=('sigtip', 'tip'+line.id,))
                _text = line.id
                if line.name != '' and line.name is not None:
                    _text += '-' + line.name
                self.create_text(self.canvasx(10) + 15 + gap*_column, 15+20*_row, text=_text,
                                 fill=color, font=('微软雅黑', 8), tags=('sigtip', 'tip'+line.id,), anchor='w')
        else:
            self.delete('sigtip')

    def setRulerValue(self):
        '''draw ruler and valuey tip by given rulerx
        '''

        self.delete('valuey')
        self.delete('ruler')
        if not self._rulerOn or self._rulerX < 0:
            return
        x = self.canvasx(self._rulerX)
        self.create_line(
            (x, 0, x, self._height), fill="#FFFAFA", tags=('ruler', ))
        for _line in self._lines:
            if x > _line.getLineLen() or _line.hidden:
                continue
            tipy = _line.getTipY(x)
            valuey = _line.getScreenY(x)
            y = valuey
            # self.create_rectangle(x+5, y-15, x+15, y-5,  tags=('valuey', ), fill=_line.color, outline=_line.color)
            self.create_text(x+5, y-5, text=tipy, fill='#FFF',
                             font=('微软雅黑', 9), tags=('valuey', ), anchor='w')

    def setScroll(self, on=True):
        self._scrollOn = on

    def clear(self):  # Fill strip with background color
        self._loopOn = False
        self._lines = []
        self.drawGridLines()

    def stopLoop(self):
        self._loopOn = False

    def drawGridLines(self, width=50):
        '''draw grid lines

        Keyword Arguments:
            width {int} -- distance between grid lines (default: {50})
        '''

        _height = self.winfo_height()
        offsety = math.floor(_height / 2) + 1
        offsetx = self._lengthx if self._lengthx > self.winfo_width() else self.winfo_width()
        self.delete('grid')
        self.create_line(
            (0, offsety, offsetx, offsety),
            fill="#708090",
            dash=(2, 6),
            tags=('grid'))
        if self._gridOn is True:
            xnum = math.floor(offsetx / width)
            for i in range(xnum):
                self.create_line(
                    (i * 50 + 50, 0, i * 50 + 50, _height),
                    fill="#708090",
                    dash=(1, 6),
                    tags=('grid'))
            ynum = math.floor(_height / (2 * width))
            for j in range(ynum):
                self.create_line(
                    (0, j * 50 + 50 + offsety, offsetx,
                     j * 50 + 50 + offsety),
                    fill="#708090",
                    dash=(2, 6),
                    tags=('grid'))
                self.create_line(
                    (0, -j * 50 - 50 + offsety, offsetx,
                     -j * 50 - 50 + offsety),
                    fill="#708090",
                    dash=(2, 6),
                    tags=('grid'))

    def getSignalbyId(self, id):
        '''get signal by given id

        Arguments:
            id {str} -- signal id

        Returns:
            signal -- signal
        '''

        for _line in self._lines:
            if _line.id == id:
                return _line
        return None

    def getSignalbyTags(self, tags):
        '''get signal by given tag list

        Arguments:
            tags {list} -- signal's tag list

        Returns:
            [signal] -- signal
        '''

        for _line in self._lines:
            if _line.id in tags:  # 求交集
                return _line
        return None

    def sortSignals(self):
        '''sort signals by order in self._lines
        '''

        self.delete('auxiliary')
        _height = self._height - 40  # 上下各留20像素
        _lines = [line for line in self._lines if (
            len(line._points) > 0 and line.hidden is not True)]
        if len(_lines) == 0:
            return
        _blockHeight = _height / len(_lines)

        for i, _line in enumerate(_lines):
            desty = 20 + (i+1)*_blockHeight - _blockHeight / 2
            y = self._height / 2 - desty
            self.create_line(0, desty, self._lengthx, desty,
                             fill='red', dash=(6, 6), tags=('auxiliary', ))
            _offsety = (_line.getMaxY() + _line.getMinY()) / 2 - y
            _offsety = _offsety + (self._height - self._originHeight) / 2
            _line.setOffsetY(_offsety)

            _nowHeight = (_line.getMaxY() - _line.getMinY()) * \
                _line.getScaleY()
            _delta = 1
            if _nowHeight > 0:
                _delta = (_blockHeight-10) / _nowHeight
            _line.setScaleY(_delta * _line.getScaleY())

    def resortSignals(self):
        # if self.find_withtag('auxiliary'):
        self.delete('auxiliary')
        for _line in self._lines:
            _line.restore()

    def stopSave(self):
        self._save = False
        if self._dataWriter is not None:
            self._dataWriter.close()

    def loadData(self, filename):
        '''load csv file stored

        Arguments:
            filename {str} -- csv file name
        '''
        # if self._loopOn is True:
        # return

        self._width = self.winfo_width()
        self._height = self.winfo_height()
        self._originHeight = self.winfo_height()
        self._initHeight = self.winfo_height()

        with open(filename, mode='r', encoding='gbk') as f:
            reader = csv.reader(f)
            ids = next(reader)
            names = next(reader)
            historys = next(reader)
            colors = next(reader)
            decimals = next(reader)
            units = next(reader)
            valtips = next(reader)

            if set([len(ids), len(historys), len(colors), len(decimals), len(units), len(valtips)]) == 1:
                logger.warning('error param count in csv file')
                return

            self._lines = []
            num = len(ids)
            for i in range(num):
                _tips = {}
                if valtips[i] != '{}':
                    # print(valtips[i])
                    _tips = json.loads(valtips[i])
                _line = Signal(canvas=self, id=ids[i], name=names[i],
                               history=20000, color=colors[i],
                               unit=str(units[i]), decimal=int(decimals[i]),
                               valuetip=_tips)
                self._lines.append(_line)

        with open(filename, mode='r', encoding='gbk') as f:
            lines = f.readlines()
            datalen = len(lines)
            data = lines[7:]
            for i, _line in enumerate(self._lines):
                _line.setHistory(datalen)
                _line.addPoints([float(row.strip().split(',')[i])
                                 for row in data])

    def _selectOneSignal(self, id):
        for _line in self._lines:
            if _line.id == id:
                _line.setSelected(True)
            else:
                _line.setSelected(False)

    def deleteSignal(self, id):
        for _line in self._lines:
            if _line.id == id:
                _line.setSelected(False)
                _line.hide()

    def initLineList(self, lineNumber, names=[], decimals=[], valuetips=[], units=[]):
        '''init all lines by given number and other params

        Arguments:
            number {int} -- number of lines
        '''

        self._width = self.winfo_width()
        self._height = self.winfo_height()
        self._originHeight = self.winfo_height()
        self._initHeight = self.winfo_height()

        self._lines = []  #
        self._currentId = None  # 当前选择曲线id
        _list = list(colorList)
        _lineid = []
        _linenames = []
        _linedecimals = []
        _linevaluetips = []
        _lineunits = []
        self.x = 0
        _lineid = list(range(0, lineNumber))
        if len(names) == lineNumber:
            _linenames = names
        else:
            _linenames = ['']*lineNumber

        if len(decimals) == lineNumber:
            _linedecimals = decimals
        else:
            _linedecimals = [0]*lineNumber

        if len(valuetips) == lineNumber:
            _linevaluetips = valuetips
        else:
            _linevaluetips = [{}]*lineNumber

        if len(units) == lineNumber:
            _lineunits = units
        else:
            _lineunits = ['']*lineNumber

        while len(self._lines) < lineNumber:
            _len = len(self._lines)
            _index = random.randint(0, len(_list) - 1)
            _random = _list[_index]
            _list.remove(_random)
            _line = Signal(id=str(_lineid[_len]), 
                           name=str(_linenames[_len]),
                           canvas=self,
                           history=20000, color=_random,
                           decimal=_linedecimals[_len],
                           unit=_lineunits[_len],
                           valuetip=dict(_linevaluetips[_len]))
            self._lines.append(_line)

        if self._save:
            self._datafile = 'data/' + \
                time.strftime("%Y_%m_%d_%H_%M_%S",
                                time.localtime()) + '.csv'
            # logger.debug(self._datafile)
            with open(self._datafile, mode='a', encoding='gbk', newline='') as f:
                self._dataWriter = csv.writer(f)
                self._dataWriter.writerow(
                    [line.id for line in self._lines])
                self._dataWriter.writerow(
                    [line.name for line in self._lines])
                self._dataWriter.writerow(
                    [line.getHistory() for line in self._lines])
                self._dataWriter.writerow(
                    [line.color for line in self._lines])
                self._dataWriter.writerow(
                    [line.decimal for line in self._lines])
                self._dataWriter.writerow(
                    [line.unit for line in self._lines])
                self._dataWriter.writerow(
                    [json.dumps(line.valuetip) for line in self._lines])

    def addLinePoint(self, values=[]):
        if len(values) != len(self._lines):
            return
        for i, _line in enumerate(self._lines):
            _line.addPoint(values[i])

        if self._save:
            with open(self._datafile, mode='a', encoding='gbk', newline='') as f:
                self._dataWriter = csv.writer(f)
                self._dataWriter.writerow(values)

        self.x = self.x + 1

    # --------------- inner API ---------------
    def hScrolled(self, *args):
        self.xview(*args)
        # delta = self.canvasx(10) - self.scrollx
        # print(self.canvasx(10), delta)
        # for _tip in self.find_withtag('sigtip'):
        #     self.move(_tip, delta, 0)
        # self.scrollx = self.canvasx(10)

    def autoScrollToEnd(self):
        '''scrool canvas to signal end when needed
        '''

        if self._scrollOn is True:
            try:
                maxlen = max([_line.getLineLen() for _line in self._lines])
            except Exception:
                maxlen = 0
            if maxlen < self._width * 0.75:
                maxlen = 0
            elif maxlen > self._lengthx - self._width * 0.25:
                maxlen = int(self._lengthx - self._width * 0.25)
            else:
                maxlen = maxlen - int(self._width * 0.75)
            fraction = maxlen / self._lengthx
            self.xview_moveto(fraction)
        else:
            pass

    def _canvashScrolled(self, *args):
        self.hScroll.set(*args)
        # delta = self.canvasx(10) - self.scrollx
        # for _tip in self.find_withtag('sigtip'):
        #     self.move(_tip, delta, 0)
        # self.scrollx = self.canvasx(10)    
    
    def __resize(self, event):
        # self.update_idletasks()
        if len(self._lines) == 0:
            self._originHeight = self.winfo_height()
        _deltay = (self.winfo_height() - self._height) / 2
        self.drawGridLines(50)
        for _line in self._lines:
            _line.setSelected(False)
            _line.moveY(_deltay)
        for _item in self.find_withtag('auxiliary'):
            self.move(_item, 0, _deltay)
        self._height = self.winfo_height()
        self._width = self.winfo_width()

    def __mouseScale(self, event):
        if self._drag_data["item"] is None:
            return
        if (event.delta > 0):
            self._drag_data["item"].scaleY(1.2)
        else:
            self._drag_data["item"].scaleY(0.8)

    # def updateLines(self, lineList:list):
    def __mouseDown(self, event):
        for signal in self._lines:
            signal.setSelected(selected=False)
        self._drag_data['item'] = None
        # print('down', event.x, event.y)
        # _items = self.find_closest(event.x, event.y)
        # print('closest', self.gettags(_items[0]))
        _items1 = self.find_overlapping(
            event.x-3, event.y-3, event.x+3, event.y+3)
        _currentItem = None
        for _item in _items1:
            _tags = self.gettags(_item)
            if 'signal' in _tags:
                _currentItem = _item
                break
            elif 'sigtip' in _tags:
                # if selected item is sigtip, show or hide the signal
                selectedid = _tags[1][3:]
                _line = self.getSignalbyId(selectedid)
                if _line.hidden:
                    _line.show()
                else:
                    _line.hide()
                break
        if _currentItem is not None:
            _tags = self.gettags(_currentItem)
            self._drag_data['item'] = self.getSignalbyTags(_tags)
            self._drag_data['sy'] = event.y
            self._drag_data['sx'] = event.x
            self._drag_data['y'] = event.y
            self._drag_data['x'] = 0

            self._selectOneSignal(self._drag_data['item'].id)
            self.tag_raise(self._drag_data['item'].id)  # raise this signal

    def __mouseDownMove(self, event):
        '''Handle dragging of an object'''
        if self._drag_data["item"] is None or self._dragOn is not True:
            return
        # compute how much the mouse has moved
        # delta_x = 0 # event.x - self._drag_data["x"]
        delta_y = event.y - self._drag_data["y"]
        # offset_y = event.y - self._drag_data["sy"]
        self._drag_data["item"].moveY(delta_y)
        # record the new position
        self._drag_data["x"] = 0
        self._drag_data["y"] = event.y

    def __mouseHoverMove(self, event):
        if self._rulerOn:
            # delta_x = event.x - self._rulerX
            # self.after(80, self.__delayMove, delta_x)
            self._rulerX = event.x
            # print(self.gettags(self.find_withtag(tk.CURRENT)))

    def __delayMove(self, delta_x):
        if self._ruler:
            self.move(self._ruler, delta_x, 0)

    def __mouseUp(self, event):
        # print(event.x, event.y)
        pass

    def __mouseEnter(self, event):
        if self._rulerOn:
            #     self._ruler = self.create_line(
            #         (event.x, 0, event.x, self._height), fill="#FFFAFA")
            self._rulerX = event.x
        pass

    def __mouseLeave(self, event):
        self.delete('ruler')
        self._rulerX = -1
    
    # --------------- below code just for testing the function ---------------

    def _autoTest(self):
        if len(self._lines) != 5:
            self._lines = []
            valuetip = {
                "0": "disable",
                "1": "enable",
                "2": "rsvd"
            }
            self._lines.append(
                Signal(id='Y1', name='A', canvas=self, history=20000, color='#ff4'))
            self._lines.append(
                Signal(id='Y2', name='B', canvas=self, history=20000, color='#f40', decimal=2, unit='A'))
            self._lines.append(Signal(id='Y3', name='B999999', canvas=self,
                                      history=20000, color='#4af'))
            self._lines.append(Signal(id='Y4', name='A', canvas=self,
                                      history=20000, color='#080'))
            self._lines.append(
                Signal(id='Y5', name='C', canvas=self, history=20000, color='purple', valuetip=valuetip))
            if self._save:
                self._datafile = 'data/' + \
                    time.strftime("%Y_%m_%d_%H_%M_%S",
                                  time.localtime()) + '.csv'
                logger.debug(self._datafile)
                with open(self._datafile, mode='a', encoding='gbk', newline='') as f:
                    self._dataWriter = csv.writer(f)
                    self._dataWriter.writerow(
                        [line.id for line in self._lines])
                    self._dataWriter.writerow(
                        [line.name for line in self._lines])
                    self._dataWriter.writerow(
                        [line.getHistory() for line in self._lines])
                    self._dataWriter.writerow(
                        [line.color for line in self._lines])
                    self._dataWriter.writerow(
                        [line.decimal for line in self._lines])
                    self._dataWriter.writerow(
                        [line.unit for line in self._lines])
                    self._dataWriter.writerow(
                        [json.dumps(line.valuetip) for line in self._lines])

        y1 = 10 * math.sin(0.02 * math.pi * self.x)
        y2 = 20 + 5 * (random.random() - 0.5)
        y3 = 50
        y4 = -30 if (self.x % 20 == 0) else 20
        y5 = random.randint(-100, 2000)

        self._lines[0].addPoint(y1)
        self._lines[1].addPoint(y2)
        self._lines[2].addPoint(y3)
        self._lines[3].addPoint(y4)
        self._lines[4].addPoint(y5)
        if self._save:
            with open(self._datafile, mode='a', encoding='gbk', newline='') as f:
                self._dataWriter = csv.writer(f)
                self._dataWriter.writerow([y1, y2, y3, y4, y5])

        self.x = self.x + 1
        self.after(10, self._autoTest)

    def toggleRuler(self):
        self._rulerOn = True if self._rulerOn is False else False

    def toggleDrag(self):
        self._dragOn = True if self._dragOn is False else False

    def toggleGrid(self):
        self._gridOn = True if self._gridOn is False else False
        self.drawGridLines(50)

    def _selectTest(self):
        _line = self._lines[random.randint(0, 3)]
        if _line.selected is True:
            _line.setSelected(False)
        else:
            _line.setSelected(True)

    def toggleTip(self):
        self._tipOn = True if self._tipOn is False else False

    def _restoreTest(self):
        for _line in self._lines:
            _line.restore()

    def _scaleTest(self):
        _scale = random.randint(1, 3)
        if self._drag_data['item'] is not None:
            self._drag_data['item'].scaleY(_scale)

    def _sortTest(self):
        self.sortSignals()

    def _resortTest(self):
        self.resortSignals()

    def _scrollTest(self):
        self._scrollOn = True if self._scrollOn is False else False

    def _adapationTest(self):
        for _line in self._lines:
            if not _line.hidden:
                _line.adaptation()

    def _loadTest(self):
        filename = filedialog.askopenfilename(
            title='载入数据', filetypes=[('csv', '*.csv')])
        self.loadData(filename)

    def _clear(self):
        if len(self._lines) != 0:
            self._lines = []


if __name__ == '__main__':

    root = tk.Tk()
    root.geometry('900x400')
    frame = tk.Frame(root, width=900, height=300)
    frame.pack(fill=tk.BOTH, expand=True)

    plot = Plotter(frame)

    tk.Button(root, text='start', command=plot._autoTest).pack(side=tk.LEFT)
    tk.Button(root, text='clear', command=plot._clear).pack(side=tk.LEFT)
    tk.Button(root, text='ruler', command=plot.toggleRuler).pack(side=tk.LEFT)
    tk.Button(root, text='drag', command=plot.toggleDrag).pack(side=tk.LEFT)
    tk.Button(root, text='grid', command=plot.toggleGrid).pack(side=tk.LEFT)
    tk.Button(root, text='select', command=plot._selectTest).pack(side=tk.LEFT)
    tk.Button(root, text='restore',
              command=plot._restoreTest).pack(side=tk.LEFT)
    tk.Button(root, text='scale current',
              command=plot._scaleTest).pack(side=tk.LEFT)
    tk.Button(root, text='tip', command=plot.toggleTip).pack(side=tk.LEFT)
    tk.Button(root, text='sort', command=plot._sortTest).pack(side=tk.LEFT)
    tk.Button(root, text='resort', command=plot._resortTest).pack(side=tk.LEFT)
    tk.Button(root, text='scroll', command=plot._scrollTest).pack(side=tk.LEFT)
    tk.Button(root, text='adapation',
              command=plot._adapationTest).pack(side=tk.LEFT)
    tk.Button(root, text='load data',
              command=plot._loadTest).pack(side=tk.LEFT)

    root.mainloop()
