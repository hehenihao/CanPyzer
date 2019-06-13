import configparser
import logging
import os
import random as rd
import re
import sys
import time
import tkinter as tk
from ctypes import *
from multiprocessing import Array, Pool, Process, Queue, Value
from threading import Thread
from tkinter import Message, Toplevel, filedialog, messagebox, ttk

import checkTree as ct
import plot
import rawAnalysis as ra
import tableItemEntry as tie
import tablePopup as tp
from dbc import DBC, Frame, Signal

os.chdir(os.path.abspath(os.path.dirname(__file__)))
enbaleOfflineTest = True  # 启用自动生成测试报文数据
platformInfo = sys.version

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# 终端Handler
consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)
# 文件Handler
fileHandler = logging.FileHandler(
    './log/pycan.log', mode='a', encoding='UTF-8')
fileHandler.setLevel(logging.NOTSET)
# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
consoleHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
# 添加到Logger中
logger.addHandler(consoleHandler)
logger.addHandler(fileHandler)
if '64 bit' in platformInfo:
    _CanDLLName = os.getcwd() + r'/config/ControlCANx64/ControlCAN.dll'
else:
    _CanDLLName = os.getcwd() + r'config/ControlCANx86/ControlCAN.dll'
print('loading ' + _CanDLLName)
ZLGCAN = windll.LoadLibrary(_CanDLLName)
ubyte_array = c_ubyte*8
ubyte_3array = c_ubyte*3

# can type
CANTYPE = {
    'USBCAN-I': 3,
    'USBCAN-II': 4,
}

# can mode
NORMAL_MODE = 0
LISTEN_MODE = 1

# filter type
SINGLE_FILTER = 0
DOUBLE_FILTER = 1

# channel number
CAN_CHANNEL_0 = 0
CAN_CHANNEL_1 = 1
CAN_CHANNEL_2 = 2
CAN_CHANNEL_3 = 3
CAN_CHANNEL_4 = 4
CAN_CHANNEL_5 = 5
CAN_CHANNEL_6 = 6
CAN_CHANNEL_7 = 7
CAN_CHANNEL_8 = 8
CAN_CHANNEL_9 = 9
CAN_CHANNEL_10 = 10
CAN_CHANNEL_11 = 11
CAN_CHANNEL_12 = 12

# status
STATUS_OK = 1

# sendtype
SEND_NORMAL = 0
SEND_SINGLE = 1
SELF_SEND_RECV = 2
SELF_SEND_RECV_SINGLE = 3


class VCI_INIT_CONFIG(Structure):
    _fields_ = [("AccCode", c_ulong),
                ("AccMask", c_ulong),
                ("Reserved", c_ulong),
                ("Filter", c_ubyte),
                ("Timing0", c_ubyte),
                ("Timing1", c_ubyte),
                ("Mode", c_ubyte)
                ]


class VCI_CAN_OBJ(Structure):
    _fields_ = [("ID", c_uint),
                ("TimeStamp", c_uint),
                ("TimeFlag", c_ubyte),
                ("SendType", c_ubyte),
                ("RemoteFlag", c_ubyte),
                ("ExternFlag", c_ubyte),
                ("DataLen", c_ubyte),
                ("Data", c_ubyte*8),
                ("Reserved", c_ubyte*3)
                ]


class PVCI_ERR_INFO(Structure):
    _fields_ = [("ErrorCode", c_uint),
                ("PassiveErrData", c_ubyte*3),
                ("ArLostErrData", c_ubyte)
                ]


baudRateConfig = {
    '5Kbps': {'time0': 0xBF, 'time1': 0xFF},
    '10Kbps': {'time0': 0x31, 'time1': 0x1C},
    '20Kbps': {'time0': 0x18, 'time1': 0x1C},
    '40Kbps': {'time0': 0x87, 'time1': 0xFF},
    '50Kbps': {'time0': 0x09, 'time1': 0x1C},
    '80Kbps': {'time0': 0x83, 'time1': 0xFF},
    '100Kbps': {'time0': 0x04, 'time1': 0x1C},
    '125Kbps': {'time0': 0x03, 'time1': 0x1C},
    '200Kbps': {'time0': 0x81, 'time1': 0xFA},
    '250Kbps': {'time0': 0x01, 'time1': 0x1C},
    '400Kbps': {'time0': 0x80, 'time1': 0xFA},
    '500Kbps': {'time0': 0x00, 'time1': 0x1C},
    '666Kbps': {'time0': 0x80, 'time1': 0xB6},
    '800Kbps': {'time0': 0x00, 'time1': 0x16},
    '1000Kbps': {'time0': 0x00, 'time1': 0x14},
}


class MessageDeal:
    def __init__(self, canType, canIndex, canChannel, canBaudrate):
        self.canType = canType
        self.canIndex = canIndex
        self.canChannel = canChannel
        self.canBaudrate = canBaudrate

    def initCan(self):
        ret = ZLGCAN.VCI_OpenDevice(self.canType, self.canChannel, self.canChannel)
        if ret != STATUS_OK:
            logger.error('调用 VCI_OpenDevice 出错: {}'.format(str(self.canChannel)))
            # messagebox.showerror('错误', '打开CAN卡失败！')
            return False
        # 初始化通道
        _vci_initconfig = VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0, DOUBLE_FILTER,
                                        baudRateConfig[self.canBaudrate]['time0'],
                                        baudRateConfig[self.canBaudrate]['time1'],
                                        NORMAL_MODE)
        ret = ZLGCAN.VCI_InitCAN(self.canType, self.canIndex, self.canChannel, byref(_vci_initconfig))
        if ret != STATUS_OK:
            logger.error('调用 VCI_InitCAN 出错: {}'.format(str(self.canChannel)))
            # messagebox.showerror('错误', '初始化CAN失败！')
            return False

        ret = ZLGCAN.VCI_StartCAN(self.canType, self.canIndex, self.canChannel)
        if ret != STATUS_OK:
            # messagebox.showerror('错误', '启动CAN失败！')
            logger.error('调用 VCI_StartCAN 出错: {}'.format(str(self.canChannel)))
            return False
        return True

    def getUndealNumber(self):
        return ZLGCAN.VCI_GetReceiveNum(self.canType, self.canIndex, self.canChannel)

    def receive(self, number=1):
        # b = ubyte_3array(0, 0, 0)
        # a = ubyte_array(0, 0, 0, 0, 0, 0, 0, 0)
        # vci_can_obj = VCI_CAN_OBJ(0x0, 0, 0, 1, 0, 0, 8, a, b)
        objs = (VCI_CAN_OBJ*number)()
        # for i in range(number):
        #     objs[i] = vci_can_obj
        ret = ZLGCAN.VCI_Receive(self.canType, self.canIndex, self.canChannel, byref(objs), number, 10)
        if ret == 0xFFFFFFFF:
            return None
        else:
            return objs[:ret]

    def send(self, frames: list, number: int):
        ret = ZLGCAN.VCI_Transmit(
            self.canType, self.canIndex, self.canChannel, byref(frames), number)
        if ret != STATUS_OK:
            ret = ZLGCAN.VCI_Transmit(
                self.canType, self.canIndex, self.canChannel, byref(frames), number)
            if ret != STATUS_OK:
                logger.error('调用 VCI_Transmit 出错')
                self.readErrInfo()
        else:
            # print('send ok')
            pass

    def readErrInfo(self):
        errInfo = PVCI_ERR_INFO(0, ubyte_3array(0, 0, 0), 0)
        ZLGCAN.VCI_ReadErrInfo(self.canType, self.canIndex,
                               self.canChannel, byref(errInfo))
        logger.error(errInfo.ErrorCode, errInfo.PassiveErrData[0],
                     errInfo.PassiveErrData[1], errInfo.PassiveErrData[2],
                     errInfo.ArLostErrData)

    def clearBuffer(self):
        return ZLGCAN.VCI_ClearBuffer(self.canType, self.canIndex, self.canChannel)

    def closeCan(self):
        return ZLGCAN.VCI_CloseDevice(self.canType, self.canIndex)


def _listenMsg(msgDeal: MessageDeal, connectRet, needClose, start, msgQueue: Queue, sendQueue: Queue):
    '''call by single process to deal can messages. 
    
    Arguments:
        msgDeal {MessageDeal} -- can info
        connectRet {Value} -- return value of connection
        needClose {Value} -- disconnect when needed
        msgQueue {Queue} -- received data
    '''

    ret = msgDeal.initCan()
    connectRet.value = int(ret)
    loopCnt = 0
    while connectRet.value == 1:
        # print(connectRet.value, needClose.value, start.value)
        if needClose.value == 1:
            ret = msgDeal.closeCan()
            if ret == 1:
                needClose.value = 0
                connectRet.value = 0
            return
        msgToSendCnt = sendQueue.qsize()
        if msgToSendCnt > 0:
            objs = (VCI_CAN_OBJ*msgToSendCnt)()
            for i in range(msgToSendCnt):
                objs[i] = sendQueue.get()
            msgDeal.send(objs, msgToSendCnt)
        time.sleep(0.001)
        if start.value == 0:
            msgDeal.clearBuffer()
            msgQueue.empty()
            continue
        loopCnt += 1
        if loopCnt >= 15:
            loopCnt = 0
            restNum = msgDeal.getUndealNumber() if msgDeal.getUndealNumber() <= 10 else 10
            revRet = msgDeal.receive(restNum)
            if revRet is None:
                pass
            else:
                for i in revRet:
                    if i.ID > 0:
                        msgQueue.put(i)


class Canalyzer:
    def __init__(self):
        self.appConfig = configparser.ConfigParser()
        self.connected = False  # 当前连接状态
        self._start = False  # 开始/暂停
        self.msg = None
        self.dbc = None
        self.popLock = 0  # 防止多个toplevel
        self.dbcReceiveList = []
        self.dbcSendList = []
        self.msgQueue = Queue()
        self.sendQueue = Queue()
        self.connectedRet = Value('i', 0)  # 进程之间交换can连接状态
        self.needDisConnect = Value('i', 0)  # 当前连接需要断开
        self.startStatus = Value('i', 0)
        self.receiveNum = 0
        self.currentItem = None
        self._setupWidget()
        self._loadSendTable()
        # self._setupConnectWidget()

    def _setupWidget(self):
        self.root = tk.Tk()
        self.root.protocol('WM_DELETE_WINDOW', self.__closeWindow)
        self._cantypeVar = tk.StringVar()
        self._canIndexVar = tk.StringVar()
        self._canChanelVar = tk.StringVar()
        self._canBaudrateVar = tk.StringVar()
        self._cantypeVar.set('USBCAN-I')
        self._canBaudrateVar.set('250Kbps')
        self._canChanelVar.set('0')
        self._canIndexVar.set('0')
        pad = 20
        w, h, x, y = self.root.winfo_screenwidth(
        )-pad, self.root.winfo_screenheight()-pad, 0, 0
        # 获取屏幕 宽、高
        # ws = self.root.winfo_screenwidth()
        # hs = self.root.winfo_screenheight()
        # 计算 x, y 位置
        # x = (ws / 2) - (w / 2)
        # y = (hs / 2) - (h / 2) - 20
        # self.root.geometry('{}x{}+{}+{}'.format(w, h, int(x), int(y)))
        self.root.iconbitmap(bitmap='icon.ico', default='icon.ico')
        # self.root.attributes("-fullscreen", True)
        self.root.state('zoomed')
        self.root.title('CanPyzer')
        if enbaleOfflineTest:
            self.root.title('CanPyzer -- Testing')
        # menu
        _menu = tk.Menu(self.root)
        self._options = tk.Menu(_menu, tearoff=0)
        self._options.insert_command(0, label="连接设备", font=(
            '微软雅黑', 8), command=self._setupConnectWidget)
        # self._options.insert_command(
        #     2, label="保存数据", font=('微软雅黑', 8), command=None)
        self._options.insert_separator(3)
        self._options.insert_command(
            4, label="设置", font=('微软雅黑', 8), command=None)
        self._options.insert_command(4, label="退出", font=(
            '微软雅黑', 8), command=self.__closeWindow)
        _menu.add_cascade(label="菜单", menu=self._options)

        helpmenu = tk.Menu(_menu, tearoff=0)
        helpmenu.add_command(label="关于", font=('微软雅黑', 8), command=None)
        helpmenu.add_separator()
        helpmenu.add_command(label="使用方法", font=('微软雅黑', 8),command=None)
        _menu.add_cascade(label="帮助", menu=helpmenu)

        # full background
        # _back = tk.Frame(self.root, background='gray')
        # left frame
        # _leftFrame = tk.Frame(self.root, width=340, borderwidth = 1)
        # _leftFrame.pack_propagate(0)  # fixed size
        # _leftFrame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        # tk.Label(_leftFrame, text='').pack(pady=5)
        # tk.Button(_leftFrame, text='滤波设置', font=('微软雅黑', 8),command=None).pack()
        # tk.Button(_leftFrame, text='载入DBC', font=('微软雅黑', 8),command=self._loadDBC).pack()
        # # DBC数据
        # self._dbcFrame = tk.Frame(_leftFrame, width=200)
        # self._dbcFrame.pack(fill=tk.X, side=tk.TOP)
        # self._dbcFrame.config(height=100)
        # self._dbcName = tk.Label(self._dbcFrame)
        # self._dbcName.config(text='文件名')
        # self._dbcName.pack()
        # self._dbcbook = ttk.Notebook(_leftFrame)
        # self._dbcData = ttk.Treeview(self._dbcFrame, columns=('check', 'data'), show="tree")
        # self._dbcData.column('check', width=4, anchor='c')
        # self._dbcData.column('data', anchor='w')
        # self._dbcData.heading('#0', text='Name')
        # self._dbcData.pack(fill=tk.X, expand=True)

        # tk.Button(_leftFrame, text='保存数据', font=('微软雅黑', 8),command=None).pack()

        _paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashrelief=tk.SUNKEN)
        _paned.pack(fill=tk.BOTH, expand=1)

        # top frame
        _topFrame = tk.Frame(_paned)
        # _topFrame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, expand=True)
        _paned.add(_topFrame)

        _colnum = (self.root.winfo_screenheight()-350)/20
        tk.Label(_topFrame, text='数据显示', font=('微软雅黑', 12, 'bold')).pack()
        # notebook
        self._book = ttk.Notebook(_topFrame)
        self._book.pack(fill=tk.BOTH, expand=1)
        # tab 1
        self._rawDataTab = ttk.Frame(self._book)
        self._book.add(self._rawDataTab, text='  原始数据  ')
        _tableColumns = ('序号', '传输方向', '时间标志(0.1ms)', '帧ID', '帧格式', '帧类型',
                         '数据长度', '数据（HEX）')
        _tableColumnsWidth = (50, 100, 100, 100, 80, 80, 80, 200)
        _anchors = ('w', 'center', 'center', 'center', 'center', 'center',
                    'center', 'w')
        self.dataTable = ttk.Treeview(
            self._rawDataTab, show="headings", height=int(_colnum), columns=_tableColumns)
        for i in range(len(_tableColumns)):
            self.dataTable.column(
                i, width=_tableColumnsWidth[i], anchor=_anchors[i])  # 表示列,不显示
            self.dataTable.heading(
                i, text=_tableColumns[i], anchor=_anchors[i])  # 显示表头
        self.dataTable.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        _vbar = ttk.Scrollbar(
            self._rawDataTab, orient='vertical', command=self.dataTable.yview)
        self.dataTable.configure(
            yscrollcommand=_vbar.set)  # yscrollcommand与Scrollbar的set绑定
        _vbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        # self.dataTable.bind('<Double-Button-1>', self._anlysisRawData)
        self.dataTable.tag_configure("odd", background='#FCFCFC')
        self.dataTable.tag_configure("send", background='#F0FFFF')
        self._even = False
        # self.dataTable.insert("", "end", values=('', '', '', '', '','','', '00 01 02 03 04 05 06 07'))

        # tab 2
        self._dbcDataTab = ttk.Frame(self._book)
        self._book.add(self._dbcDataTab, text=' DBC数据 ')
        _tableColumns = ('传输方向', '时间标志', '消息名', 'ID(H)', 'PGN(H)',
                         '源地址', '目标地址', '帧类型', '帧格式', '数据长度', '帧数据')
        _tableColumnsWidth = (100, 100, 100, 80, 80, 80, 80, 80, 80, 80, 200)
        _anchors = ('w', 'w', 'w', 'w', 'w',
                    'w', 'w', 'center', 'center', 'center', 'w')
        self.dbcTable = ttk.Treeview(
            self._dbcDataTab, show="headings tree", height=int(_colnum), 
            columns=_tableColumns)
        for i in range(len(_tableColumns)):
            self.dbcTable.column(
                i, width=_tableColumnsWidth[i], anchor=_anchors[i])  #表示列,不显示
            self.dbcTable.heading(
                i, text=_tableColumns[i], anchor=_anchors[i])  #显示表头
        self.dbcTable.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # the minimum width default that Tk assigns
        minwidth = self.dbcTable.column('#0', option='minwidth')
        self.dbcTable.column('#0', width=minwidth+60, stretch=False, anchor='e')
        self.meassageImg = tk.PhotoImage(file='./config/message.png')
        self.dbcTable.tag_configure("frameRoot", image=self.meassageImg, background='#EBEBEB')
        self.signalImg = tk.PhotoImage(file='./config/signal.png')
        self.dbcTable.tag_configure("odd", background='#FCFCFC')
        self.dbcTable.tag_configure("signal", image=self.signalImg, background='#FEFEFE')
        self.dbcTable.tag_configure("signalHeader", background='#F6F6F6')
        self.dbcTable.bind("<Button-1>", self._dbc_signal_click, True)
        self.signal_check_Img = tk.PhotoImage(file='./config/signal_check.png')
        self.dbcTable.tag_configure("checked", image=self.signal_check_Img)
        self.dbcTable.tag_configure("unchecked", image=self.signalImg)

        _vbarDbc = ttk.Scrollbar(
            self._dbcDataTab, orient='vertical', command=self.dbcTable.yview)
        self.dbcTable.configure(
            yscrollcommand=_vbarDbc.set)  # yscrollcommand与Scrollbar的set绑定
        _vbarDbc.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # tab 3
        self._plotTab = ttk.Frame(self._book)
        self._book.add(self._plotTab, text=' 数据绘制 ')
        _framePlot = tk.Frame(self._plotTab)
        _framePlot.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        self.signalPlotter = plot.Plotter(_framePlot)
        self.signalPlotter.setScroll()
        self.signalPlotter.setDrag()
        self._plotInited = False

        _btnFrame = tk.Frame(self._plotTab)
        _btnFrame.pack(side=tk.RIGHT)

        tk.Button(_btnFrame, text='显示名称',
                  command=self.signalPlotter.toggleTip).pack(side=tk.TOP)
        tk.Button(_btnFrame, text='显示数值',
                  command=self.signalPlotter.toggleRuler).pack(padx=5, pady=5)
        tk.Button(_btnFrame, text='信号排序', command=self.signalPlotter.sortSignals).pack(
            side=tk.BOTTOM)
        tk.Button(_btnFrame, text='暂停当前', command=self.signalPlotter.stopLoop).pack(
            side=tk.BOTTOM)
        tk.Button(_btnFrame, text='清空数据', command=self.signalPlotter.clear).pack(
            side=tk.BOTTOM)

        # bottom frame
        self.appConfig.read(r'config\config.ini')
        self._bottomFrame = tk.Frame(_paned)
        # _bottomFrame.pack(fill=tk.BOTH, padx=5, expand=True)
        _paned.add(self._bottomFrame)
        _paned.paneconfig(self._bottomFrame, height=0, minsize=165)

        _sendFrame = tk.Frame(self._bottomFrame)
        _sendFrame.pack(side=tk.LEFT, fill=tk.Y)
        _tableColumns = ('id', '帧类型', '帧格式', '帧数据')
        _tableColumnsWidth = (100, 80, 80, 250)
        _anchors = ('w', 'c', 'c', 'w')
        self.sendTable = ct.CheckboxTreeview(_sendFrame
            , show="headings tree", height=10, columns=_tableColumns)
        for i in range(len(_tableColumns)):
            self.sendTable.column(
                i, width=_tableColumnsWidth[i], anchor=_anchors[i])  # 表示列,不显示
            self.sendTable.heading(
                i, text=_tableColumns[i], anchor=_anchors[i])  # 显示表头
        self.sendTable.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        self.sendTable.bind('<Double-Button-1>', self._editSendTableItem)
        # the minimum width default that Tk assigns
        minwidth = self.sendTable.column('#0', option='minwidth')
        self.sendTable.column('#0', width=minwidth+40, stretch=False, anchor='e')

        self._onlineImg = tk.PhotoImage(file='./config/online16.png')
        self._offlineImg = tk.PhotoImage(file='./config/offline16.png')
        _statusFrame1 = tk.Frame(self._bottomFrame)
        _statusFrame1.pack(side=tk.TOP, fill=tk.X, expand=True, pady=5, padx=5)
        tk.Label(_statusFrame1, text='状态').pack(side=tk.LEFT)
        self._statusLbl = tk.Label(_statusFrame1, image=self._offlineImg)
        self._statusLbl.pack(side=tk.LEFT)
        tk.Label(_statusFrame1, text='自动滚动').pack(side=tk.LEFT)
        self._autoScrollVar = tk.BooleanVar()
        self._autoScrollVar.set(self.appConfig.getboolean('ui', 'scroll'))
        tk.Checkbutton(_statusFrame1, variable=self._autoScrollVar, command=self._scrollTableToBottom).pack(side=tk.LEFT)

        _btnFrame1 = tk.Frame(self._bottomFrame)
        _btnFrame1.pack(side=tk.TOP, fill=tk.X, expand=True, pady=5, padx=5)
        self._rawStartBtn = tk.Button(_btnFrame1, text='开始', width=8, font=('微软雅黑', 8), command=self._rawDataStart)
        self._rawStartBtn.pack(side=tk.LEFT)
        tk.Button(_btnFrame1, text='清空列表', width=8, font=('微软雅黑', 8),command=self._clearRootList).pack(side=tk.LEFT, padx=5)
        tk.Button(_btnFrame1, text='载入DBC', width=8, font=('微软雅黑', 8),command=self._loadDBC).pack(side=tk.LEFT)
        tk.Button(_btnFrame1, text='绘制选择', width=8, font=('微软雅黑', 8),command=self._plotSignal).pack(side=tk.LEFT, padx=5)
        tk.Button(_btnFrame1, text='导入数据', width=8, font=('微软雅黑', 8),command=self._plotData).pack(side=tk.LEFT)

        _sendOptionFrame = tk.Frame(self._bottomFrame, pady=5, padx=5)
        _sendOptionFrame.pack(side=tk.TOP, fill=tk.X, expand=True)
        _tmpFrame = tk.Frame(_sendOptionFrame)
        _tmpFrame.pack(fill=tk.X, expand=True)
        tk.Label(_tmpFrame, text='发送次数').pack(side=tk.LEFT)
        self._sendtimeVar = tk.IntVar()
        self._sendtimeVar.set(self.appConfig.getint('ui', 'sendtimes'))
        tk.Entry(_tmpFrame, textvariable=self._sendtimeVar, width=5).pack(side=tk.LEFT, padx=5)
        tk.Label(_tmpFrame, text='发送间隔').pack(side=tk.LEFT)
        self._sendintervalVar = tk.IntVar()
        self._sendintervalVar.set(self.appConfig.getint('ui', 'interval'))
        tk.Entry(_tmpFrame, textvariable=self._sendintervalVar, width=5).pack(side=tk.LEFT, padx=5)
        self._sendintervalVar.set(100)
        tk.Label(_tmpFrame, text='每帧间隔').pack(side=tk.LEFT)
        self._frameintervalVar = tk.IntVar()
        self._frameintervalVar.set(self.appConfig.getint('ui', 'frameinterval'))
        tk.Entry(_tmpFrame, textvariable=self._frameintervalVar, width=5).pack(side=tk.LEFT, padx=5)
        self._frameintervalVar.set(1)
        tk.Button(_tmpFrame, text='发送选择', width=8, font=('微软雅黑', 8),command=self._sendFrameList).pack(side=tk.LEFT)
        tk.Button(_tmpFrame, text='停止发送', width=8, font=('微软雅黑', 8),command=self._stopSendFrameList).pack(side=tk.LEFT, padx=5)
        self._alreadySendTime = 0  # 发送次数
        self._sendOneInterval = 0  # 一个间隔里面发送帧数

        self.dataPlotter = None

        self.root.config(menu=_menu)
        self.root.after(1500, self._afterSetup)

    def _afterSetup(self):
        self.root.bind("<Configure>", self.__resizeWindow)
        if enbaleOfflineTest:
            self.root.after(1000, self.__OfflineTest, 0)

    def _setupConnectWidget(self):
        if self.connected is True:
            ret = messagebox.askyesno('提示', '存在已有连接，是否断开重连？')
            if ret is False:
                return
            self._disconnect()
        pw, ph, px, py = re.split('[\+x]', str(self.root.geometry()))
        w, h = 480, 160
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        # 计算 x, y 位置
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2) - 20
        self._top = Toplevel()
        self._top.attributes('-alpha', 1.0)
        self._top.attributes('-topmost', True)
        # self._top.attributes('-toolwindow', True)
        self._top.positionfrom(who='user')
        self._top.resizable(width=False, height=False)
        self._top.title('连接设备')
        self._top.geometry('{}x{}+{}+{}'.format(w, h, int(x), int(y)))
        _row1 = tk.Frame(self._top, width=self._top.minsize()[0], height=50, pady=5)
        _row1.pack(side=tk.TOP)
        tk.Label(_row1, text='CAN卡类型', font=('微软雅黑', 10), pady=10, width=12).pack(side=tk.LEFT, padx=25)
        tk.Label(_row1, text='设备索引号', font=('微软雅黑', 10), pady=10, width=10).pack(side=tk.LEFT, padx=5)
        tk.Label(_row1, text='通道号', font=('微软雅黑', 10), pady=10, width=10).pack(side=tk.LEFT, padx=0)
        tk.Label(_row1, text='波特率', font=('微软雅黑', 10), pady=10, width=11).pack(side=tk.LEFT, padx=28)

        _row2 = tk.Frame(self._top)
        _row2.pack()
        _cantypeCombox = ttk.Combobox(_row2, width=12, textvariable=self._cantypeVar, state='readonly')
        _cantypeCombox['values'] = list(CANTYPE.keys())
        _cantypeCombox.pack(side=tk.LEFT, padx=20)
        self._cantypeVar.set(self.appConfig.get('connect', 'cantype'))

        _canIndexCombox = ttk.Combobox(_row2, width=4, textvariable=self._canIndexVar, state='readonly')
        _canIndexCombox['values'] = list(range(7))
        _canIndexCombox.pack(side=tk.LEFT, padx=20)
        self._canIndexVar.set(self.appConfig.get('connect', 'canindex'))

        _canChanelCombox = ttk.Combobox(_row2, width=4, textvariable=self._canChanelVar, state='readonly')
        _canChanelCombox['values'] = list(range(3))
        _canChanelCombox.pack(side=tk.LEFT, padx=20)
        self._canChanelVar.set(self.appConfig.get('connect', 'chanel'))

        _canBaudrateCombox = ttk.Combobox(_row2, width=10, textvariable=self._canBaudrateVar, state='readonly')
        _canBaudrateCombox['values'] = list(baudRateConfig.keys())
        _canBaudrateCombox.pack(side=tk.LEFT, padx=20)
        self._canBaudrateVar.set(self.appConfig.get('connect', 'baudrate'))

        _row3 = tk.Frame(self._top)
        _row3.pack(pady=24)
        tk.Button(_row3, text='确定', font=('微软雅黑', 9), width=6, command=self._connectDev).pack(side=tk.LEFT, padx=30)
        tk.Button(_row3, text='取消', font=('微软雅黑', 9), width=6, command=self._top.destroy).pack(side=tk.LEFT, padx=30)
        self._top.grab_set()

    def __closeWindow(self):
        if messagebox.askokcancel("关闭", "确认退出？"):
            self._disconnect()
            time.sleep(0.1)
            self.root.destroy()

    def __resizeWindow(self, event):
        pass
        # if self._bottomFrame.winfo_height() > 220:
        #     self._bottomFrame.config(height=220)

    def _disconnect(self):
        '''disconnect and terminate process
        '''

        if self.connected is True:
            self.connected = False
            self.needDisConnect.value = 1
            self.root.after(1000, self._checkDisconnectStatus)
            self.updateListThread = None
            self._start = False
            self.startStatus.value = 0
            self._rawStartBtn['text'] = '开始'
            self._statusLbl['image']=self._offlineImg

    def _connectDev(self):
        self.saveConnectConfig()
        self._top.grab_release()
        self._top.destroy()
        canType = CANTYPE[self._cantypeVar.get()]
        canIndex = int(self._canIndexVar.get())
        canChannel = int(self._canChanelVar.get())
        canBaudrate = self._canBaudrateVar.get()
        logger.info('connect: {} {} {} {}'.format(canType, canIndex, canChannel, canBaudrate))
        self.msg = MessageDeal(canType, canIndex, canChannel, canBaudrate)
        self.startMsg = Thread(target=self._StartlistenMsgProcess)
        self.startMsg.run()

    def _StartlistenMsgProcess(self):
        self.msgProcess = Process(
            name='pyCanListener',
            target=_listenMsg,
            args=(self.msg, self.connectedRet, self.needDisConnect,
                  self.startStatus, self.msgQueue, self.sendQueue))
        self.msgProcess.daemon = True
        self.msgProcess.start()
        # 1.5s后检测连接状态，该值可能需要标定
        self.root.after(1500, func=self._checkConnectStatus)
        # process.join() join会导致阻塞

    def _scrollTableToBottom(self):
        if self.connected is True and self._autoScrollVar.get():
            if len(self.dataTable.get_children()) > 0:
                self.dataTable.see(self.dataTable.get_children()[-1])
            self.root.after(500, func=self._scrollTableToBottom)

    def _checkConnectStatus(self):
        logger.info('process connect status:{}'.format(self.connectedRet.value))
        if self.connectedRet.value == 1:
            self.connected = True
            self._options.insert_command(1, label="断开", font=('微软雅黑', 9), command=self._disconnect)
            self._statusLbl.configure(image=self._onlineImg)
            self._scrollTableToBottom()
        else:
            messagebox.showinfo('信息', '离线状态！')
            self.connected = False
            self.msgProcess.terminate()
            self.msgProcess = None

    def _checkDisconnectStatus(self):
        print('断开已有连接...')
        self.msg = None
        self.msgProcess.terminate()
        self.msgProcess = None
        self._options.delete(1)  # 删除菜单断开按钮

    def _updateRootList(self):
        if self.connected is True and self._start is True:
            # if self.receiveNum > 1000000:
            #     messagebox.showinfo('OK')
            #     self.needDisConnect.value = 1
            _dataSize = self.msgQueue.qsize()
            if _dataSize > 10:
                for i in range(10):
                    self.receiveNum += 1
                    item = self.msgQueue.get()
                    # print(hex(item.ID),list(item.Data), len(self.dataTable.get_children()))
                    data = self._formatMsgData(self.receiveNum, item, True)
                    self.root.after(5, self._insertDataSmooth, data)
            else:
                for i in range(_dataSize):
                    self.receiveNum += 1
                    item = self.msgQueue.get()
                    data = self._formatMsgData(self.receiveNum, item, True)
                    self.root.after(5, self._insertDataSmooth, data)
            self.root.after(100, self._updateRootList)

    def _rawDataStart(self):
        if self.connected is False:
            messagebox.showwarning('警告', '当前处于离线状态，请连接设备后重试！')
            return
        _text = self._rawStartBtn['text']
        if _text == '开始':
            self._start = True
            self.startStatus.value = 1
            self._rawStartBtn['text'] = '暂停'
            self.updateListThread = Thread(target=self._updateRootList)
            self.updateListThread.daemon = True
            self.updateListThread.run()
        else:
            self._start = False
            self.startStatus.value = 0
            self._rawStartBtn['text'] = '开始'

    def _insertDataSmooth(self, data):
        tag = ('odd', )
        if self._even:
            tag = ('even', )
            self._even = False
        else:
            self._even = True
        self.dataTable.insert("", "end", values=data, tags=tag)
        self._updateDbcTable(data)

    def _anlysisRawData(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        item = self.dataTable.identify_row(y)
        ra.TablePopup(root=self.root, value=self.dataTable.item(item, 'values')[-1])

    def _formatMsgData(self, index, item, received):
        '''msg data to list
        
        Arguments:
            index {int} -- msg index
            item {} -- recevive
            received {-bool} -- always true
        
        Returns:
            [list] -- data list:
                [index, received, TimeStamp, id, RemoteFlag, ExternFlag, DataLen, data]
        '''

        data = []
        if received:
            data.append('{0:0>7}'.format(index))
            data.append('接收')
        else:
            data.append('')
            data.append('发送')
        data.append(item.TimeStamp)
        # print(time.time(), time.localtime(item.TimeStamp), item.TimeStamp)
        data.append(str.upper(str(hex(item.ID))).replace('X', 'x'))

        data.append('远程帧' if int(item.RemoteFlag) == 1 else '数据帧')

        if int(item.ExternFlag) == 1:
            data.append('扩展帧')
        else:
            data.append('标准帧')
        data.append(item.DataLen)
        data.append(' '.join(['{:0<2x}'.format(a) for a in list(item.Data)]))

        return data

    def _updateDbcTable(self, data):
        frames = self.dbcTable.get_children()
        if self.dbc is not None and len(frames) > 0:
            for frame in frames:
                vals = self.dbcTable.item(frame, 'values')
                if int(vals[3][2:], 16) == int(data[3][2:], 16):
                    self.dbcTable.set(frame, column=1, value=data[2])
                    self.dbcTable.set(frame, column=8, value=data[4])
                    self.dbcTable.set(frame, column=10, value=data[-1])
                    handledData = self.dbc.analyzer(int(vals[3][2:], 16), data=data[-1])
                    signals = self.dbcTable.get_children(frame)
                    index = 0
                    points = []
                    for signal in signals:
                        _tags = self.dbcTable.item(signal, 'tags')
                        if 'value' in _tags:
                            if self.dbcTable.item(
                                    signal,
                                    'values')[0] == handledData[index]['name']:
                                self.dbcTable.set(
                                    signal,
                                    column=1,
                                    value=str(handledData[index]['value']['phy']) +
                                    handledData[index]['unit'])
                                self.dbcTable.set(
                                    signal,
                                    column=4,
                                    value=str(handledData[index]['value']['raw']))
                                values = self.dbc.frameById(int(vals[3][2:], 16)).signals[index].values
                                if str(handledData[index]['value']['raw']) in values.keys():
                                    description = values[str(handledData[index]['value']['raw'])]
                                    self.dbcTable.set(
                                        signal,
                                        column=2,
                                        value=description)
                            if 'checked' in _tags:
                                _y = float(handledData[index]['value']['phy'])
                                print(_y, '---------------')
                                points.append(_y)
                            index += 1

                    self._updateSignalPlot(points)
        else:
            pass

    def _dbcframesTopLevel(self, frames):
        '''根据读取的frames创建窗口
        
        Arguments:
            frames {list} -- dbcframes
        '''
        if len(frames) < 1:
            return

        self._dbcTop = Toplevel()
        w = 500
        h = len(frames)*30 + 100
        h = h if h < 480 else 480
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        # 计算 x, y 位置
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2) - 20
        self._dbcTop.attributes('-alpha', 1.0)
        self._dbcTop.attributes('-topmost', True)
        self._dbcTop.positionfrom(who='user')
        self._dbcTop.resizable(width=False, height=False)
        self._dbcTop.title('DBC报文选择')
        self._dbcTop.geometry('{}x{}+{}+{}'.format(w, h, int(x), int(y)))

        _tableColumns = ('报文名称', '数据长度', '收发类型')
        _tableColumnsWidth = (200, 50, 80)
        _anchors = ('w', 'c', 'c')
        # self.dbcChooseTable = ttk.Treeview(self._dbcTop
        #     , show="headings tree", height=2, columns=_tableColumns)
        self.dbcChooseTable = ct.CheckboxTreeview(self._dbcTop
            , show="tree", height=2, columns=_tableColumns) # headings
        for i in range(len(_tableColumns)):
            self.dbcChooseTable.column(
                i, width=_tableColumnsWidth[i], anchor=_anchors[i])  #表示列,不显示
            self.dbcChooseTable.heading(
                i, text=_tableColumns[i], anchor=_anchors[i])  #显示表头
        self.dbcChooseTable.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.dbcChooseTable.bind('<Double-Button-1>', self._editDbcFramesTableItem)
        #the minimum width default that Tk assigns
        minwidth = self.dbcChooseTable.column('#0', option='minwidth')
        self.dbcChooseTable.column('#0', width=minwidth+80, stretch=False, anchor='w')

        self.dbcChooseTable.insert(
                '',
                'end',
                'header',
                values=_tableColumns,
                text='',
            )

        _row3 = tk.Frame(self._dbcTop)
        _row3.pack(pady=10, side=tk.TOP)
        tk.Button(
            _row3,
            text='确定',
            font=('微软雅黑', 9),
            width=6,
            command=self._dbcframesCategory).pack(
                side=tk.LEFT, padx=30)
        tk.Button(
            _row3,
            text='取消',
            font=('微软雅黑', 9),
            width=6,
            command=self._dbcTop.destroy).pack(
                side=tk.LEFT, padx=30)

        # load data
        for frame in frames:
            _type = '本机发送'
            _name = frame.name
            if 'RCV' in str.upper(_name) or 'RECEIVE' in str.upper(_name):
                _type = '本机接收'
            self.dbcChooseTable.insert(
                'header',
                'end',
                values=(_name, frame.size, _type),
                text=str.upper(str(hex(frame.id))[2:]),
            )
        self.dbcChooseTable.item("header", open=True)

    def _dbcframesCategory(self):
        self.dbcReceiveList = []
        self.dbcSendList = []
        for pNode in self.dbcChooseTable.get_children():
            for i, item in enumerate(self.dbcChooseTable.get_children(pNode)):
                tags = self.dbcChooseTable.item(item, 'tags')
                if 'checked' in tags:
                    id = self.dbcChooseTable.item(item, 'text')
                    values = self.dbcChooseTable.item(item, 'values')
                    if values[-1].find('发送') > -1:
                        self.dbcSendList.append(self.dbc.frames[i])
                    else:
                        self.dbcReceiveList.append(self.dbc.frames[i])
                else:
                    pass
        self._dbcTop.destroy()
        self.signalPlotter.clear()
        self._initDbcTable(self.dbcReceiveList)
        self._addDbcSendFramesToSendTable(self.dbcSendList)
        self._book.select(1)

    def _editDbcFramesTableItem(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        if "image" not in elem:
            item = self.dbcChooseTable.identify_row(y)
            text = self.dbcChooseTable.item(item, 'values')
            values = {
                'id': {
                    'type': tp.LABEL,
                    'value': self.dbcChooseTable.item(item, 'text'),
                },
                '收发类型': {
                    'type': tp.COMBOBOX,
                    'value': [text[-1], '本机发送'] if text[-1] == '本机接收' else [text[-1], '本机接收']
                },
            }
            tp.TablePopup(
                root=self.root,
                title='编辑数据',
                values=values,
                callback=self._editDbcFramesTableItemCallback,
                tableItem=item)

    def _editDbcFramesTableItemCallback(self, item=None, values=None, result=None):
        if item and values and result:
            self.dbcChooseTable.set(item, column=2, value=result['收发类型'].get().strip())

    def _dbc_signal_click(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        if "image" in elem:
            # a box was clicked
            item = self.dbcTable.identify_row(y)
            tags = self.dbcTable.item(item, "tags")
            newtags = list(tags)
            val = self.dbcTable.item(item, "values")[0].strip()
            if val == '传输方向' or val == '接收' or val == '发送' or val == '信号名':
                return
            if ("unchecked" in tags):
                newtags.remove('unchecked')
                newtags.append('checked')
            elif 'checked' in tags:
                newtags.remove('checked')
                newtags.append('unchecked')
            self.dbcTable.item(item, tags=newtags)

    def _updateSignalPlot(self, points):
        if self.signalPlotter is None or self._plotInited == False:
            return
        self.signalPlotter.addLinePoint(points)

    def _plotInitSignal(self, signals):
        '''
        
        Arguments:
            frames {list} -- dbcframes
        '''

        self._plotInited = False
        num = len(signals)
        names = [s['name'] for s in signals]
        decimals = [1]*num
        units = [s['unit'] for s in signals]
        self.signalPlotter.initLineList(
            num, names=names, decimals=decimals, valuetips=[], units=units)
        self.signalPlotter.setLoopStatus(on=True)
        self._plotInited = True
    
    def _plotDataTopLevel(self, filename):
        '''绘制窗口
        
        Arguments:
            filename {str} -- csv file
        '''

        self._plotDataTop = Toplevel()
        w = 960
        h = 480
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        # 计算 x, y 位置
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2) - 20
        self._plotDataTop.attributes('-alpha', 1.0)
        # self._plotDataTop.attributes('-topmost', True)
        self._plotDataTop.positionfrom(who='user')
        self._plotDataTop.resizable(width=False, height=False)
        self._plotDataTop.title('信号解析')
        self._plotDataTop.geometry('{}x{}+{}+{}'.format(w, h, int(x), int(y)))

        _container = tk.Frame(self._plotDataTop)
        _container.pack(expand=True, fill=tk.BOTH, side=tk.TOP)
        _dataPlotter = plot.Plotter(_container)
        _btnFrame = tk.Frame(self._plotDataTop)
        _btnFrame.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Button(_btnFrame, text='显示名称',
                  command=_dataPlotter.toggleTip).pack(side=tk.LEFT)
        tk.Button(_btnFrame, text='显示数值',
                  command=_dataPlotter.toggleRuler).pack(side=tk.LEFT, padx=5)
        tk.Button(_btnFrame, text='信号排序', command=_dataPlotter.sortSignals).pack(
            side=tk.LEFT)
        tk.Button(_btnFrame, text='关闭',
                  command=self._plotDataTop.destroy).pack(side=tk.LEFT, padx=5)

        self.root.after(50, _dataPlotter.loadData, filename)


    def _clearRootList(self):
        # 删除原节点
        items = self.dataTable.get_children()
        [self.dataTable.delete(item) for item in items]
        self._even = False
        self.receiveNum = 0

    def _loadDBC(self):
        filedir = filedialog.askopenfilename(filetypes=[("DBC", "*.dbc")])
        if filedir:
            self.dbc = DBC(filedir)
            self._dbcframesTopLevel(self.dbc.frames)

    def _plotSignal(self):
        signals = []
        for pNode in self.dbcTable.get_children():
            for item in self.dbcTable.get_children(pNode):
                if 'checked' in self.dbcTable.item(item, 'tags'):
                    vals = self.dbcTable.item(item, 'values')
                    value = '0.0'
                    unit = ''
                    if '--' not in vals[1]:
                        value = str(re.match(r'-?[0-9.]+', vals[1]))  # 当前值
                        unit = vals[1].replace(value, '').strip()  # 单位
                    else:
                        unit = vals[1][2:]
                    info = {'name': vals[0], 
                            'value': value,
                            'unit': unit
                            }
                    signals.append(info)
        if len(signals) > 10:
            messagebox.showwarning('警告', '选择的信号数量太多（数量应该小于10）')
            return
        if len(signals) < 1:
            messagebox.showwarning('警告', '请选择信号后重试！')
            return
        self._plotInitSignal(signals)
        self._book.select(2)

    def _plotData(self):
        filedir = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if filedir:
            self._plotDataTopLevel(filedir)

    def _initDbcTable(self, frames):
        items = self.dbcTable.get_children()
        [self.dbcTable.delete(item) for item in items]
        signalHeader = [
            '信号名', '实际值', '描述', '注释', '原始值(H)', '起始位', '位宽', '比例', '偏移',
            ' ', ' '
        ]
        index = 1
        for frame in frames:
            # self._dbcFrame.forget()
            # self._dbcName.config(text=filedir.split('/')[-1])
            direction = '接收'
            time = '--'
            frameName = frame.name
            frameId = frame.id
            framePNG = frame.j1939_pgn if frame.j1939_pgn is not None else '--'
            frameSource = frame.j1939_source
            frameDest = '--'
            frameType = '扩展帧' if frame.extended else '标准帧'
            frameFormat = '--' # 数据帧' if frame.is_fd else '远程帧'
            dataSize = frame.size
            data = '00 01 02 03 04 05 06 07'
            self.dbcTable.insert(
                '',
                'end',
                id=str(frame.id),
                tags=('frameRoot', ),
                values=(direction, time, frameName, str.upper(str(hex(frameId))).replace('X', 'x'), framePNG,
                        frameSource, frameDest, frameType, frameFormat,
                        dataSize, data, ),
                text = '{0: >4}'.format(index))
            index += 1
            self.dbcTable.insert(str(frame.id), 'end', tags=('signalHeader', ), values=signalHeader)
            self.dbcTable.item(str(frame.id), open=True)
            for i, signal in enumerate(frame.signals):
                signalName = signal.name
                phyVal = '--' + signal.unit
                description = '--'
                comment = signal.comment if signal.comment is not None else '--'
                rawVal = '--'
                startbit = signal.startBit
                bitsize = signal.size
                factor = signal.factor
                offset = signal.offset
                self.dbcTable.insert(
                    str(frame.id),
                    'end',
                    tags=('unchecked', 'value') if i%2 == 1 else ('odd', 'unchecked', 'value'),
                    values=(signalName, phyVal, description, comment, rawVal,
                            startbit, bitsize, factor, offset))

    def _addDbcSendFramesToSendTable(self, frames):
        '''将dbc中发送报文加入到发送列表前面，同时相同id的报文会被删除
        
        Arguments:
            frames {list} -- 发送报文列表
        '''

        ids = []
        index = 0
        cnt = len(frames)
        for frame in frames:
            ids.append(int(frame.id))
            values = (frame.id, '扩展帧' if frame.extended else '标准帧',
                      '数据帧', '00 01 02 03 04 05 06 07')
            self.sendTable.insert('', str(index), values=values,
                                  text=str(index), tags=('unchecked',))
            index += 1

        datas = []
        items = self.sendTable.get_children()[index:]
        for item in items:
            vals = self.sendTable.item(item, 'values')
            self.sendTable.delete(item)
            if int(vals[0].strip()) not in ids:
                datas.append(vals)

        for data in datas:
            values = data
            if index < 100:
                self.sendTable.insert('', 'end', values=values, text=str(index), tags=('unchecked',))
                index += 1

        while index < 100:
            values = ('00000000', '标准帧', '数据帧', '00 01 02 03 04 05 06 07')
            self.sendTable.insert('', 'end', values=values, text=str(index), tags=('unchecked',))
            index += 1

    def _loadSendTable(self):
        index = 0
        if os.path.exists(r'config/sendlist.txt'):
            with open(r'config/sendlist.txt', mode='r', encoding='gbk') as file:
                for line in file.readlines():
                    if line.strip() == '':
                        continue
                    values = line.strip().split(',')
                    values[1] = '{0:0>8}'.format(values[1])
                    self.sendTable.insert(
                        '',
                        'end',
                        values=values[1:],
                        text=' ' + str(index),
                        tags=('checked',) if values[0] == '1' else ('unchecked',))
                    index += 1
        while index < 100:
            values = ('00000000', '标准帧', '数据帧', '00 01 02 03 04 05 06 07')
            self.sendTable.insert('', 'end', values=values, text=str(index), tags=('unchecked',))
            index += 1

    def _saveSendTable(self):
        if os.path.exists(r'config/sendlist.txt'):
            with open(r'config/sendlist.txt', mode='w', encoding='gbk') as file:
                for item in self.sendTable.get_children():
                    line = []
                    # index = self.sendTable.item(item, 'text')
                    tags = self.sendTable.item(item, 'tags')
                    vals = self.sendTable.item(item, 'values')
                    if 'unchecked' in tags:
                        line.append('0')
                    else:
                        line.append('1')
                    # line.append(index)
                    line.extend(vals)
                    file.write(','.join(line)+'\n')

    def _editSendTableItem(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        if "image" in elem:
            return
        # a box was clicked
        item = self.sendTable.identify_row(y)
        column = self.sendTable.identify_column(x)

        # print(column, self.sendTable.column(column, 'width'), )
        text = self.sendTable.item(item, 'values')
        # _index = int(column[1:])
        # if _index > 0:
        #     print(text[_index-1])
        # print(text)

        values = {
            'id': {
                'type': tp.ENTRY,
                'value':text[0],
            },
            '帧类型': {
                'type': tp.COMBOBOX,
                'value': [text[1], '标准帧'] if text[1] == '扩展帧' else [text[1], '扩展帧']
            },
            '帧格式': {
                'type': tp.COMBOBOX,
                'value': [text[2], '远程帧'] if text[2] == '数据帧' else [text[2], '数据帧']
            },
            '帧数据': {
                'type': tp.ENTRY,
                'value': text[3]
            }
        }
        tp.TablePopup(
            root=self.root,
            title='编辑数据',
            values=values,
            callback=self._editSendTableItemCallback,
            tableItem=item)
        # if str(column) == '#4':
        #     tie.ItemEntery(table=self.sendTable, item=item, column=column, root=self.root, value=text[-1],callback=self._editSendTableValueCallback)

    def _editSendTableValueCallback(self, item, text):
        # 校验数据格式是否正确
        vals = text.strip().split(' ')
        length = [len(val) for val in vals]
        maxcnt = max(length)
        if len(vals) > 8 or maxcnt > 2:
            messagebox.showerror('错误', '数据格式错误！')
            return
        self.sendTable.set(item, column=3, value=text.strip())
        self._saveSendTable()

    def _editSendTableItemCallback(self, item=None, values=None, result=None):
        if item and values and result:
            self.sendTable.set(item, column=0, value='{0:0>8}'.format(result['id'].get().strip()))
            self.sendTable.set(item, column=1, value=result['帧类型'].get().strip())
            self.sendTable.set(item, column=2, value=result['帧格式'].get().strip())
            # 校验数据格式是否正确
            vals = result['帧数据'].get().strip().split(' ')
            length = [len(val) for val in vals]
            maxcnt = max(length)
            if len(vals) > 8 or maxcnt > 2:
                messagebox.showerror('错误', '数据格式错误！')
                return
            self.sendTable.set(item, column=3, value=result['帧数据'].get().strip())
            self._saveSendTable()

    def _sendFrameList(self):
        self._saveSendTable()
        self.saveUIConfig()
        if self.connected is False:
            messagebox.showwarning('警告', '当前处于离线状态，请连接设备后重试！')
            return
        self._sendStop = False
        self._alreadySendTime = 0
        framesToSend = []
        for i, item in enumerate(self.sendTable.get_children()):
            if 'checked' in self.sendTable.item(item, 'tags'):
                vals = self.sendTable.item(item, 'value')
                framesToSend.append(vals)
        if len(framesToSend) * self._frameintervalVar.get() >= self._sendintervalVar.get():
            messagebox.showwarning('警告', '时间设置不合理，请重试。')
            return
        self._intervalSend(framesToSend)

    def _intervalSend(self, frames):
        if self.connected is False:
            messagebox.showwarning('警告', '连接已断开！')
            return
        if len(frames) == 0 or self._sendStop == True:
            return
        self._alreadySendTime += 1
        if self._alreadySendTime > self._sendtimeVar.get():
            return
        self._sendOneInterval = 0
        self._sendOneFrame(frames)
        self.root.after(self._sendintervalVar.get(), self._intervalSend, frames)

    def _sendOneFrame(self, frames):
        if self.connected is False:
            messagebox.showwarning('警告', '连接已断开！')
            return
        if self._sendOneInterval >= len(frames) or self._sendStop == True:
            return
        id = int(frames[self._sendOneInterval][0], base=16)
        remoteflag = 1 if frames[self._sendOneInterval][1] == '远程帧' else 0
        externFlag = 1 if frames[self._sendOneInterval][2] == '数据帧' else 0
        data = [int(item, base=16) for item in frames[self._sendOneInterval][3].split(' ')]
        sendtype = SEND_NORMAL
        ubyte_array = c_ubyte * 8
        a = ubyte_array(0, 0, 0, 0, 0, 0, 0, 0)
        for i, val in enumerate(data):
            a[i] = val
        ubyte_3array = c_ubyte * 3
        b = ubyte_3array(0, 0, 0)
        vci_can_obj = VCI_CAN_OBJ(id, 0, 0, sendtype, remoteflag, externFlag, 8, a, b)
        # print(self._alreadySendTime, self._sendOneInterval, time.time())
        # put the frame to the send queue
        self.sendQueue.put(vci_can_obj)
        vals = [
            '{}-{}'.format(self._alreadySendTime, self._sendOneInterval+1), '发送', '无', frames[self._sendOneInterval][0],
            frames[self._sendOneInterval][1], frames[self._sendOneInterval][2],
            len(data), frames[self._sendOneInterval][3]
        ]
        self.dataTable.insert("", "end", values=vals, tags=('send', ))
        self._sendOneInterval += 1
        self.root.after(self._frameintervalVar.get(), self._sendOneFrame, frames)

    def _stopSendFrameList(self):
        self._sendStop = True
        self._alreadySendTime = 0

    def run(self):
        self.root.mainloop()

    def saveUIConfig(self):
        self.appConfig.set('ui', 'scroll', self._autoScrollVar.get())
        self.appConfig.set('ui', 'sendtimes', self._sendtimeVar.get())
        self.appConfig.set('ui', 'interval', self._sendintervalVar.get())
        self.appConfig.set('ui', 'frameinterval', self._frameintervalVar.get())
        with open(r'config\config.ini', mode='w', encoding='gbk') as configFile:
            self.appConfig.write(configFile)

    def saveConnectConfig(self):
        self.appConfig.set('connect', 'cantype', self._cantypeVar.get())
        self.appConfig.set('connect', 'canindex', self._canIndexVar.get())
        self.appConfig.set('connect', 'chanel', self._canChanelVar.get())
        self.appConfig.set('connect', 'baudrate', self._canBaudrateVar.get())
        with open(r'config\config.ini', mode='w', encoding='gbk') as configFile:
            self.appConfig.write(configFile)

    def __OfflineTest(self, index):
        if self.connected is False:
            self.connected = True
            self._statusLbl.configure(image=self._onlineImg)

        index += 1
        interval = rd.randint(50, 1000)
        msgid = rd.randint(1, 6)
        content = [rd.randint(0, 16) for i in range(8)]
        # [index, received, TimeStamp, id, RemoteFlag, ExternFlag, DataLen, data]
        data = []
        data.append('{0:0>7}'.format(index))
        data.append('接收')
        data.append('00')
        # print(time.time(), time.localtime(item.TimeStamp), item.TimeStamp)
        data.append(str.upper(str(hex(msgid))).replace('X', 'x'))

        data.append('数据帧')
        data.append('标准帧')
        data.append('8')
        data.append(' '.join(['{:0<2x}'.format(a) for a in list(content)]))
        self.root.after(5, self._insertDataSmooth, data)
        self.root.after(interval, self.__OfflineTest, index)


if __name__ == '__main__':
    canalyzer = Canalyzer()
    canalyzer.run()
