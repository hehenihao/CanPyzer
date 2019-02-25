# reference: https://github.com/ebroecker/canmatrix

# this script translates dbc-files to list data
import sys
import os
import logging
import re
import attr
import math
import decimal

defaultFloatFactory = decimal.Decimal
dbcImportEncoding = 'iso-8859-1'

logging.basicConfig(
    level=logging.DEBUG,
    format=
    '%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

MOTOROLA = 0
INTERL = 1
UNSIGNED = 0
SIGNED = 1

def normalizeValueTable(table):
    return {int(k): v for k, v in table.items()}

@attr.s(cmp=False)
class Frame:
    """
    Contains one CAN Frame.
    The Frame has  following mandatory attributes
    * id,
    * name,
    * transmitters (list of boardunits/ECU-names),
    * size (= DLC),
    * signals (list of signal-objects),
    * attributes (list of attributes),
    * receiver (list of boardunits/ECU-names),
    * extended (Extended Frame = 1),
    * comment
    and any *custom* attributes in `attributes` dict.
    Frame signals can be accessed using the iterator.
    """

    name = attr.ib(default="")
    id = attr.ib(type=int, default=0)
    size = attr.ib(default=0)
    transmitters = attr.ib(default=attr.Factory(list))
    extended = attr.ib(type=bool, default=False)
    is_complex_multiplexed = attr.ib(type=bool, default=False)
    is_fd = attr.ib(type=bool, default=False)
    comment = attr.ib(default="")
    signals = attr.ib(default=attr.Factory(list))
    mux_names = attr.ib(type=dict, default=attr.Factory(dict))
    attributes = attr.ib(type=dict, default=attr.Factory(dict))
    receiver = attr.ib(default=attr.Factory(list))
    signalGroups = attr.ib(default=attr.Factory(list))
    cycle = attr.ib(type=int, default=0)

    j1939_pgn = attr.ib(default=None)
    j1939_source = attr.ib(default=0)
    j1939_prio = attr.ib(default=0)
    is_j1939 = attr.ib(type=bool, default=False)

    def calcDLC(self):
        """
        Compute minimal Frame DLC (length) based on its Signals
        :return: Message DLC
        """
        maxBit = 0
        for sig in self.signals:
            if sig.getStartbit() + int(sig.size) > maxBit:
                maxBit = sig.getStartbit() + int(sig.size)
        self.size = max(self.size, int(math.ceil(maxBit / 8)))
    
    def setFdType(self):
        """Try to guess and set the CAN type for every frame.
        If a Frame is longer than 8 bytes, it must be Flexible Data Rate frame (CAN-FD).
        If not, the Frame type stays unchanged.
        """
        for frame in self.frames:
            if frame.size > 8:
                frame.is_fd = True

    def findNotUsedBits(self):
        """
        Find unused bits in frame
        :return: dict with position and length-tuples
        """
        bitfield = []
        bitfieldLe = []
        bitfieldBe = []

        for i in range(0,64):
            bitfieldBe.append(0)
            bitfieldLe.append(0)
            bitfield.append(0)
        i = 0

        for sig in self.signals:
            i += 1
            for bit in range(sig.getStartbit(),  sig.getStartbit() + int(sig.size)):
                if sig.is_little_endian:
                    bitfieldLe[bit] = i
                else:
                    bitfieldBe[bit] = i

        for i in range(0,8):
            for j in range(0,8):
                bitfield[i*8+j] = bitfieldLe[i*8+(7-j)]

        for i in range(0,8):
            for j in range(0,8):
                if bitfield[i*8+j] == 0:
                    bitfield[i*8+j] = bitfieldBe[i*8+j]


        return bitfield

    def addSignal(self, signal):
        """
        Add Signal to Frame.
        :param Signal signal: Signal to be added.
        :return: the signal added.
        """
        self.signals.append(signal)
        return self.signals[len(self.signals) - 1]


@attr.s(cmp=False)
class Signal(object):
    """
    Represents a Signal in CAN Matrix.
    Signal has following attributes:
    * name
    * startBit, size (in Bits)
    * is_little_endian (1: Intel, 0: Motorola)
    * is_signed (bool)
    * factor, offset, min, max
    * receiver  (Boarunit/ECU-Name)
    * attributes, _values, unit, comment
    * _multiplex ('Multiplexor' or Number of Multiplex)
    """

    name = attr.ib(default = "")
    #    float_factory = attr.ib(default=defaultFloatFactory)
    float_factory = defaultFloatFactory
    startBit = attr.ib(type=int, default=0)
    size = attr.ib(type=int, default = 0)
    is_little_endian = attr.ib(type=bool, default = True)
    is_signed = attr.ib(type=bool, default = True)
    offset = attr.ib(converter = float_factory, default = float_factory(0.0))
    factor = attr.ib(converter = float_factory, default = float_factory(1.0))

    #    offset = attr.ib(converter = float_factory, default = 0.0)

    min  = attr.ib(converter=float_factory)
    @min.default
    def setDefaultMin(self):
        return  self.calcMin()

    max =  attr.ib(converter = float_factory)
    @max.default
    def setDefaultMax(self):
        return  self.calcMax()

    unit = attr.ib(type=str, default ="")
    receiver = attr.ib(default = attr.Factory(list))
    comment = attr.ib(default = None)
    multiplex  = attr.ib(default = None)

    mux_value = attr.ib(default = None)
    is_float = attr.ib(type=bool, default=False)
    enumeration = attr.ib(type=str, default = None)
    comments = attr.ib(type=dict, default = attr.Factory(dict))
    attributes = attr.ib(type=dict, default = attr.Factory(dict))
    values = attr.ib(type=dict, convert=normalizeValueTable, default = attr.Factory(dict))
    calc_min_for_none = attr.ib(type=bool, default = True)
    calc_max_for_none = attr.ib(type=bool, default = True)
    muxValMax = attr.ib(default = 0)
    muxValMin = attr.ib(default = 0)
    muxerForSignal= attr.ib(type=str, default = None)

    def __attrs_post_init__(self):
        self.multiplex = self.multiplexSetter(self.multiplex)


    @property
    def spn(self):
        """Get signal J1939 SPN or None if not defined."""
        return self.attributes.get("SPN", None)

    def multiplexSetter(self, value):
        self.mux_val = None
        self.is_multiplexer = False
        if value is not None and value != 'Multiplexor':
            ret_multiplex = int(value)
            self.mux_val = int(value)
        else:  # is it valid for None too?
            self.is_multiplexer = True
            ret_multiplex = value
        return ret_multiplex

    def attribute(self, attributeName, db=None, default=None):
        """Get any Signal attribute by its name.
        :param str attributeName: attribute name, can be mandatory (ex: startBit, size) or optional (customer) attribute.
        :param CanMatrix db: Optional database parameter to get global default attribute value.
        :param default: Default value if attribute doesn't exist.
        :return: Return the attribute value if found, else `default` or None
        """
        if attributeName in attr.fields_dict(type(self)):
            return getattr(self, attributeName)
        if attributeName in self.attributes:
            return self.attributes[attributeName]
        if db is not None:
            if attributeName in db.signalDefines:
                define = db.signalDefines[attributeName]
                return define.defaultValue
        return default

    def setStartbit(self, startBit, bitNumbering=None, startLittle=None):
        """
        Set startBit.
        bitNumbering is 1 for LSB0/LSBFirst, 0 for MSB0/MSBFirst.
        If bit numbering is consistent with byte order (little=LSB0, big=MSB0)
        (KCD, SYM), start bit unmodified.
        Otherwise reverse bit numbering. For DBC, ArXML (OSEK),
        both little endian and big endian use LSB0.
        If bitNumbering is None, assume consistent with byte order.
        If startLittle is set, given startBit is assumed start from lsb bit
        rather than the start of the signal data in the message data.
        """
        # bit numbering not consistent with byte order. reverse
        if bitNumbering is not None and bitNumbering != self.is_little_endian:
            startBit = startBit - (startBit % 8) + 7 - (startBit % 8)
        # if given startBit is for the end of signal data (lsbit),
        # convert to start of signal data (msbit)
        if startLittle is True and self.is_little_endian is False:
            startBit = startBit + 1 - self.size
        if startBit < 0:
            print("wrong startBit found Signal: %s Startbit: %d" %
                  (self.name, startBit))
            raise Exception("startBit lower zero")
        self.startBit = startBit

    def getStartbit(self, bitNumbering=None, startLittle=None):
        """Get signal start bit. Handle byte and bit order."""
        startBitInternal = self.startBit
        # convert from big endian start bit at
        # start bit(msbit) to end bit(lsbit)
        if startLittle is True and self.is_little_endian is False:
            startBitInternal = startBitInternal + self.size - 1
        # bit numbering not consistent with byte order. reverse
        if bitNumbering is not None and bitNumbering != self.is_little_endian:
            startBitInternal = startBitInternal - (startBitInternal % 8) + 7 - (startBitInternal % 8)
        return int(startBitInternal)

    def calculateRawRange(self):
        """Compute raw signal range based on Signal bit width and whether the Signal is signed or not.
        :return: Signal range, i.e. (0, 15) for unsigned 4 bit Signal or (-8, 7) for signed one.
        :rtype: tuple
        """
        rawRange = 2 ** (self.size - (1 if self.is_signed else 0))
        return (self.float_factory(-rawRange if self.is_signed else 0),
                self.float_factory(rawRange - 1))

    def calcMin(self):
        """Compute minimal physical Signal value based on offset and factor and `calculateRawRange`."""
        rawMin = self.calculateRawRange()[0]

        return self.offset + (rawMin * self.factor)

    def calcMax(self):
        """Compute maximal physical Signal value based on offset, factor and `calculateRawRange`."""
        rawMax = self.calculateRawRange()[1]

        return self.offset + (rawMax * self.factor)

    def bitstruct_format(self):
        """Get the bit struct format for this signal.
        :return: bitstruct representation of the Signal
        :rtype: str
        """
        endian = '<' if self.is_little_endian else '>'
        if self.is_float:
            bit_type = 'f'
        else:
            bit_type = 's' if self.is_signed else 'u'

        return endian + bit_type + str(self.size)

    def phys2raw(self, value=None):
        """Return the raw value (= as is on CAN).
        :param value: (scaled) value or value choice to encode
        :return: raw unscaled value as it appears on the bus
        """
        if value is None:
            return int(self.attributes.get('GenSigStartValue', 0))

        if isinstance(value, str):
            for value_key, value_string in self.values.items():
                if value_string == value:
                    value = value_key
                    break
            else:
                raise ValueError(
                        "{} is invalid value choice for {}".format(value, self)
                )

        if not (self.min <= value <= self.max):
            print(
                "Value {} is not valid for {}. Min={} and Max={}".format(
                    value, self, self.min, self.max)
                )
        raw_value = (value - self.offset) / self.factor

        if not self.is_float:
            raw_value = int(raw_value)
        return raw_value

    def raw2phys(self, value, decodeToStr=False):
        """Decode the given raw value (= as is on CAN)
        :param value: raw value
        :param bool decodeToStr: If True, try to get value representation as *string* ('Init' etc.)
        :return: physical value (scaled)
        """

        value = value * self.factor + self.offset
        if decodeToStr:
            for value_key, value_string in self.values.items():
                if value_key == value:
                    value = value_string
                    break

        return value

    def __str__(self):
        return self.name

class DBC:
    def __init__(self, dbcfile=None):
        self.filePath = dbcfile
        self.frames = self.__load()
        self.__setFdType()
        self.__setExtended()

    def __load(self):
        frameList = []
        i = 0
        frame = None
        with open(self.filePath, mode='r', encoding='gb2312') as f:
            for line in f.readlines():
                i = i + 1
                l = line.strip()
                if len(l) == 0:
                    continue
                # logging.info(l)
                if l.startswith('BO_ '):
                    # frames
                    regexp = re.compile("^BO\_ ([^\ ]+) ([^\ ]+) *: ([^\ ]+) ([^\ ]+)")
                    temp = regexp.match(l)
                    # name, id, dlc, transmitters
                    frame = Frame(
                        temp.group(2),
                        id=int(temp.group(1)),
                        size=int(temp.group(3)),
                        transmitters=temp.group(4).split())
                    frameList.append(frame)
                    pass
                elif l.startswith('SG_ '):
                    # signals
                    pattern = "^SG\_ +(\w+) *: *(\d+)\|(\d+)@(\d+)([\+|\-]) +\(([0-9.+\-eE]+),([0-9.+\-eE]+)\) +\[([0-9.+\-eE]+)\|([0-9.+\-eE]+)\] +\"(.*)\" +(.*)"
                    regexp = re.compile(pattern)
                    temp = regexp.match(l)
                    if temp:
                        extras = {}
                        receiver = list(map(str.strip, temp.group(11).split(',')))
                        tempSig = Signal(
                            temp.group(1),
                            startBit=int(temp.group(2)),
                            size=int(temp.group(3)),
                            is_little_endian=(int(temp.group(4)) == 1),
                            is_signed=(temp.group(5) == '-'),
                            factor=temp.group(6),
                            offset=temp.group(7),
                            min=temp.group(8),
                            max=temp.group(9),
                            unit=temp.group(10),
                            receiver=receiver,
                            **extras
                        )
                        if not tempSig.is_little_endian:
                            # startbit of motorola coded signals are MSB in dbc
                            tempSig.setStartbit(int(temp.group(2)), bitNumbering=1)
                        frame.signals.append(tempSig)
                    else:
                        pattern = "^SG\_ +(\w+) +(\w+) *: *(\d+)\|(\d+)@(\d+)([\+|\-]) +\(([0-9.+\-eE]+),([0-9.+\-eE]+)\) +\[([0-9.+\-eE]+)\|([0-9.+\-eE]+)\] +\"(.*)\" +(.*)"
                        regexp = re.compile(pattern)
                        temp = regexp.match(l)
                        receiver = list(map(str.strip, temp.group(12).split(',')))
                        multiplex = temp.group(2)

                        is_complex_multiplexed = False

                        if multiplex == 'M':
                            multiplex = 'Multiplexor'
                        elif multiplex.endswith('M'):
                            is_complex_multiplexed = True
                            multiplex = multiplex[:-1]

                        if multiplex != 'Multiplexor':
                            try:
                                multiplex = int(multiplex[1:])
                            except:
                                raise Exception('error decoding line',line)

                        extras = {}

                        tempSig = Signal(
                            temp.group(1),
                            startBit=int(temp.group(3)),
                            size=int(temp.group(4)),
                            is_little_endian=(int(temp.group(5)) == 1),
                            is_signed=(temp.group(6) == '-'),
                            factor=temp.group(7),
                            offset=temp.group(8),
                            min=temp.group(9),
                            max=temp.group(10),
                            unit=temp(11),
                            receiver=receiver,
                            multiplex=multiplex,
                            **extras
                        )

                        if is_complex_multiplexed:
                            tempSig.is_multiplexer = True
                            tempSig.multiplex = 'Multiplexor'

                        if not tempSig.is_little_endian:
                            # startbit of motorola coded signals are MSB in dbc
                            tempSig.setStartbit(int(temp.group(3)), bitNumbering=1)
                        frame.addSignal(tempSig)

                        if is_complex_multiplexed:
                            frame.is_complex_multiplexed = True
                elif l.startswith("BO_TX_BU_ "):
                    regexp = re.compile("^BO_TX_BU_ ([0-9]+) *: *(.+);")
                    temp = regexp.match(l)
                elif l.startswith("CM_ SG_ "):
                    pass
                elif l.startswith("CM_ BO_ "):
                    pattern = "^CM\_ +BO\_ +(\w+) +\"(.*)\";"
                    regexp = re.compile(pattern)
                elif l.startswith("CM_ BU_ "):
                    pattern = "^CM\_ +BU\_ +(\w+) +\"(.*)\";"
                    regexp = re.compile(pattern)
                elif l.startswith("BU_:"):
                    pattern = "^BU\_\:(.*)"
                    regexp = re.compile(pattern)
                elif l.startswith("VAL_ "):
                    regexp = re.compile("^VAL\_ +(\w+) +(\w+) +(.*);")
                    temp = regexp.match(l)
                    tmpId = temp.group(1)
                    signalName = temp.group(2)
                    tempList = temp.group(3).split('"')
                    for testF in frameList:
                        if testF.id == int(tmpId):
                            for signal in testF.signals:
                                if signal.name == signalName:
                                    for i in range(math.floor(len(tempList) / 2)):
                                        signal.values[tempList[i * 2].strip()] = tempList[i * 2 + 1].strip()
                                    break
                            break
                elif l.startswith("VAL_TABLE_ "):
                    regexp = re.compile("^VAL\_TABLE\_ +(\w+) +(.*);")
                    temp = regexp.match(l)
                elif l.startswith("BA_DEF_ SG_ "):
                    pattern = "^BA\_DEF\_ +SG\_ +\"([A-Za-z0-9\-_]+)\" +(.+);"
                    regexp = re.compile(pattern)
                elif l.startswith("BA_DEF_ BO_ "):
                    pattern = "^BA\_DEF\_ +BO\_ +\"([A-Za-z0-9\-_]+)\" +(.+);"
                    regexp = re.compile(pattern)
                elif l.startswith("BA_DEF_ BU_ "):
                    pattern = "^BA\_DEF\_ +BU\_ +\"([A-Za-z0-9\-_]+)\" +(.+);"
                    regexp = re.compile(pattern)
                elif l.startswith("BA_DEF_ "):
                    pattern = "^BA\_DEF\_ +\"([A-Za-z0-9\-_]+)\" +(.+);"
                    regexp = re.compile(pattern)
                elif l.startswith("BA_ "):
                    regexp = re.compile("^BA\_ +\"[A-Za-z0-9[\-_ .]+\" +(.+)")
                    tempba = regexp.match(l)
                    if tempba.group(1).strip().startswith("BO_ "):
                        regexp = re.compile(r"^BA_ +\"(.*)\" +BO_ +(\w+) +(.+);")
                        temp = regexp.match(l)
                        tempId = temp.group(2)
                        for testF in frameList:
                            if testF.id == int(tempId):
                                frame = testF
                        if temp.group(0).find('GenMsgCycleTime') > -1:
                            tempCys = temp.group(3)
                            frame.cycle = int(tempCys)
                elif l.startswith("SIG_GROUP_ "):
                    regexp = re.compile("^SIG\_GROUP\_ +(\w+) +(\w+) +(\w+) +\:(.*);")
                    temp = regexp.match(l)
                elif l.startswith("SIG_VALTYPE_ "):
                    regexp = re.compile("^SIG\_VALTYPE\_ +(\w+) +(\w+)\s*\:(.*);")
                    temp = regexp.match(l)
                elif l.startswith("BA_DEF_DEF_ "):
                    pattern = "^BA\_DEF\_DEF\_ +\"([A-Za-z0-9\-_\.]+)\" +(.+)\;"
                    regexp = re.compile(pattern)
                elif l.startswith("SG_MUL_VAL_ "):
                    pattern = "^SG\_MUL\_VAL\_ +([0-9]+) +([A-Za-z0-9\-_]+) +([A-Za-z0-9\-_]+) +([0-9]+)\-([0-9]+) *;"
                    regexp = re.compile(pattern)
                elif l.startswith("EV_ "):
                    pattern = "^EV_ +([A-Za-z0-9\-_]+) *\: +([0-9]+) +\[([0-9.+\-eE]+)\|([0-9.+\-eE]+)\] +\"(\w*)\" +([0-9.+\-eE]+) +([0-9.+\-eE]+) +([A-Za-z0-9\-_]+) +(.*);"
                    regexp = re.compile(pattern)
                    temp = regexp.match(l)
                
        return frameList

    def __setFdType(self):
        """Try to guess and set the CAN type for every frame.
        If a Frame is longer than 8 bytes, it must be Flexible Data Rate frame (CAN-FD).
        If not, the Frame type stays unchanged.
        """
        for frame in self.frames:
            # if frame.size == 0:
            frame.calcDLC()
            print(frame.id, frame.size)
            if frame.size > 8:
                frame.is_fd = True
    
    def __setExtended(self):
        for frame in self.frames:
        # extended-flag is implicite in canid, thus repair this:
            if frame.id > 0x80000000:
                frame.id -= 0x80000000
                frame.extended = 1

    def frameById(self, Id, extended=None):
        """Get Frame by its arbitration id.
        :param Id: Frame id as str or int
        :param extended: is it an extended id? None means "doesn't matter"
        :rtype: Frame or None
        """
        Id = int(Id)
        extendedMarker = 0x80000000
        for test in self.frames:
            if test.id == Id:
                if extended is None:
                    # found ID while ignoring extended or standard
                    return test
                elif test.extended == extended:
                    # found ID while checking extended or standard
                    return test
            else:
                if extended is not None:
                    # what to do if Id is not equal and extended is also provided ???
                    pass
                else:
                    if test.extended and Id & extendedMarker:
                        # check regarding common used extended Bit 31
                        if test.id == Id - extendedMarker:
                            return test
        return None

    def __getSignalVal(self, signal:Signal, data='00 01 02 03 04 05 06 07'):
        dataList = data.strip().split(' ')
        _startbit = signal.startBit
        _bitsize = signal.size
        _little = signal.is_little_endian # (1: Intel, 0: Motorola)
        _byteSize = math.ceil((signal.size + _startbit%8)/8)
        _startByte = math.floor(_startbit/8)
        phyvalue = 0
        rawvalue = ''
        base = int('{0:0>8}'.format('1'*_bitsize+'0'*(_startbit%8)), 2)
        _byteNum = 0
        _byteList= []
        while _byteNum < _byteSize:
            # tmpbase = (base >> (8*_byteNum)) & 0xff
            _byteList.append(dataList[_startByte+_byteNum])
            _byteNum += 1
        if _little == 1:
            _byteList.reverse()
        for _byte in _byteList:
            rawvalue += _byte
        rawvalue = ((int(rawvalue,16) & base) >> (_startbit%8))
        return {"phy": signal.raw2phys(rawvalue), "raw": rawvalue}
        # print(_startByte, _byteSize, _bitsize, int(dataList[_startByte], 16), int('{0:0>8}'.format('1'*_bitsize+'0'*(_startbit%8)), 2))
        
    def analyzer(self, msgid=None, data='00 01 02 03 04 05 06 07'):
        '''analysis given data 
        
        Keyword Arguments:
            msgid {int} -- msg id (base 10) (default: {None})
            data {str} -- given data (default: {'00 01 02 03 04 05 06 07'})
        
        Returns:
            dict -- key sorted by signal index
        '''

        ret = {}
        if len(data.strip().split(' ')) != 8 or msgid is None:
            logging.error('wrong data len')
            return ret
        for frame in self.frames:
            if frame.id == int(msgid):
                for i in range(len(frame.signals)):
                    signal = frame.signals[i]
                    ret[i] = {}
                    ret[i]['name'] = signal.name
                    ret[i]['unit'] = signal.unit
                    ret[i]['value'] = self.__getSignalVal(signal, data)
                break
        return ret

if __name__ == '__main__':
    testDbc = DBC("example/test.dbc")
    testDbc.analyzer(msgid=4, data='40 01 C8 00 FF 00 00 00')