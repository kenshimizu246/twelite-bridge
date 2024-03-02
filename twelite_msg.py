
from struct import pack

class Commands():
    CMD_HELLO = 0x01
    CMD_WRITE_REQUEST = 0x02
    CMD_WRITE_DATA = 0x03
    CMD_WRITE_DONE = 0x04
    CMD_GET_CONFIG = 0x05
    CMD_CONFIG = 0x11
    CMD_RECV_STAT = 0x12
    CMD_WRITE_REQUEST_ACK = 0x13
    CMD_WRITE_DATA_ACK = 0x14
    CMD_WRITE_DONE_ACK = 0x15
    CMD_WRITE_RESEND = 0x16
    CMD_ARDUCAM_CMD = 0x17

# stat:
# h1 - header 1
# h2 - header 2
# l1 - length 1
# l2 - length 2
# ..
# mq - message quality
# d1 - data size 1
# d2 - data size 2
# dt - data
# cs - checksum
# in - end of message 0x04

class Consts:
    IDX_MLEN_START = 2
    IDX_MLEN_END = 3
    IDX_SENDER_STD_ADDR = 4
    IDX_A0 = 5
    IDX_RESP_ID = 6
    IDX_FROM_ADDR_START = 7
    IDX_FROM_ADDR_END = 10
    IDX_TO_ADDR_START = 11
    IDX_TO_ADDR_END = 14
    IDX_TO_QUALITY = 15
    IDX_DATA_SIZE_START = 16
    IDX_DATA_SIZE_END = 17
    IDX_DATA_START = 18


def GenPkt( address, ID, number ):
    ID = ID.lower()
    # '>' stands for big-endian
    # 'B' stands for unsigned char
    # 'H' stands for unsigned short
    # 's' stands for char[]
    if ID == 'c':
        # p = pack( '>BBBBBB', address, 0xA0, 0x00, 0x01, 0xFF, 0x01  )
        p = pack( '>BBBBB', address, 0x00, 0x11, 0x22, 0x33 )
    elif ID == 's':
        p = pack( '>BBBBBH', address, 0xA0, 0x01, 0x01, 0xFF, number )
    elif ID == 'q':
        p = pack( '>BBBBBBB3s', address, 0xA0, 0x03, 0x01, 0x02, 0x0F,  0xFF, 'end'  )
    xor = 0
    for i in range(0, len(p)):
        xor ^= p[i]
    # %d (number) + s (char)
    return pack(">HH%dsB" % len(p), 0xa55a, 0x8000 + len(p), p, xor)


def create_ext_msg(address, seq, cmd, params, data):
    ll = len(data) + 1 + len(params)
    data_len = (11 - 4) + ll
    # s = 11 + ll + 1
    p = pack('>BBBBBBBBBBB', 0xA5, 0x5A, 0x80, data_len, address, 0xA0, seq, 0x01, 0x02, 0x0A, 0xFF)
    p += pack('>B', cmd)
    for x in params:
        p += pack('>B', x)
    if(data):
        p += data
    x = 0
    for i in range(0, len(p)):
        # print("{:#02x}".format(p[i]), end=', ')
        # print("{}:{:#02x}".format(i, p[i]))
        if(i > 3):
            x ^= p[i]
    print("")
    print("x:{:#02x}".format(x))
    p += pack('>B', x)
    return p

class Buffer:
    def __init__(self):
        self.init()

    def init(self):
        self._mcnt = 0
        self._dcnt = 0
        self._mlen = 0
        self._dlen = 0
        self._checksum = None
        self._stat = 'in'
        self._resp_id = None
        self._buff = bytearray()
        self._complete = False
        self._failed_stat = None

    def process(self, x):
        try:
            if(type(x) is not bytes):
                raise Exception("first parameter must be bytes!")
            
            if(self._stat == 'in'):
                if(x[0] == 0xA5):
                    self.init()
                    self._stat = 'h1'
                else:
                    raise Exception()
            elif(self._stat == 'h1'):
                if(x[0] == 0x5A):
                    self._stat = 'h2'
                else:
                    raise Exception()
            elif(self._stat == 'h2'):
                if((x[0] & 0xF0) == 0x80):
                    self._stat = 'l1'
                else:
                    raise Exception()
            elif(self._stat == 'l1'):
                self._stat = 'mh' # message header
                self._mlen = x[0]
                self._mcnt = 0
            elif(self._stat == 'mh'):
                self._mcnt += 1
                if(self._mcnt == 13): # data size 1
                    self._dlen = x[0]<<8
                elif(self._mcnt == 14): # data size 2
                    self._stat = 'dt' # data
                    self._dlen = self._dlen | x[0]
            elif(self._stat == 'dt'):
                self._mcnt += 1
                self._dcnt += 1
                if(self._dcnt == self._dlen):
                    self._stat = 'cs' # checksum
            elif(self._stat == 'cs'):
                self._checksum = x[0]
                self._checksum_status = (checksum(self._buff[4:]) == x[0])
                if(not self._checksum_status):
                    logger.info("checksumx:{:#02x}:{:#02x}".format(x[0], self._checksum))
                self._stat = 'tm'
            elif(self._stat == 'tm'):
                if(x[0] == 0x04):
                    self._stat = 'in'
                    self._complete = True
        except:
            self.init()
        self._buff.append(x[0])

    def getData(self):
        idx_start = Consts.IDX_DATA_START
        idx_end = Consts.IDX_DATA_START + self._dlen
        return self._buff[idx_start:idx_end]

    def getDataAndCmd(self):
        idx_cmd = Consts.IDX_DATA_START
        idx_start = Consts.IDX_DATA_START + 1
        idx_end = Consts.IDX_DATA_START + self._dlen
        return (self._buff[idx_cmd], self._buff[idx_start:idx_end])

    def getRawData(self):
        return self._buff

    def getRespID(self):
        return self._buff[Consts.IDX_RESP_ID]

    def getAddress(self):
        return self._buff[Consts.IDX_SENDER_STD_ADDR]

    def isComplete(self):
        return self._complete

    def create_resp_msg(self):
        address = self.getAddress()
        seq = self.getRespID()
        cmd = Commands.CMD_WRITE_DATA_ACK
        params = None
        data = None
        # msg = create_ext_msg(address, seq, cmd, params, data)

    def toString(self):
        print("_mcnt:{} _dcnt:{} _mlen:{} _dlen:{} _stat:{} _resp_id:{} _buff:{} _complete:{}"
             , self._mcnt, self._dcnt, self._mlen, self._dlen, self._stat, self._resp_id, str(self._buff), self._complete)
            

