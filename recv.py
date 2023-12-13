import serial
import time
from binascii import *
from struct import pack

from PIL import Image

def printx(d):
    cnt = 0
    for x in d:
        print("{:#02x}, ".format(x), end='')
        cnt += 1
        if((cnt % 10) == 0):
            print()
    print()

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

class Buffer:
    def __init__(self):
        self.init()
    def init(self):
        self._mcnt = 0
        self._dcnt = 0
        self._mlen = 0
        self._dlen = 0
        self._stat = 'in'
        self._resp_id = None
        self._buff = bytearray()
        self._complete = False
        self.IDX_DATA_START = 18
        self.IDX_MLEN_START = 2
        self.IDX_MLEN_END = 3
        self.IDX_SENDER_STD_ADDR = 4
        self.IDX_CMD = 5
        self.IDX_RESP_ID = 6
        self.IDX_FROM_ADDR_START = 7
        self.IDX_FROM_ADDR_END = 10
        self.IDX_TO_ADDR_START = 11
        self.IDX_TO_ADDR_END = 14
        self.IDX_TO_QUALITY = 15
        self.IDX_DATA_SIZE_START = 16
        self.IDX_DATA_SIZE_END = 17
        self.IDX_DATA_START = 18


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
                if(x[0] == 0x04):
                    self._stat = 'in'
                    self._complete = True
        except:
            self.init()
        self._buff.append(x[0])


    def getMessage(self, idx_start, idx_end):
        return self._buff[idx_start:idx_end]
    def getData(self):
        idx_start = self.IDX_DATA_START
        idx_end = self.IDX_DATA_START + self._dlen
        return self._buff[idx_start:idx_end]
    def getRespID(self):
        return self._buff[self.IDX_RESP_ID]
    def isComplete(self):
        return self._complete
    def toString(self):
        print("_mcnt:{} _dcnt:{} _mlen:{} _dlen:{} _stat:{} _resp_id:{} _buff:{} _complete:{}"
             , self._mcnt, self._dcnt, self._mlen, self._dlen, self._stat, self._resp_id, str(self._buff), self._complete)
            

def convertGrascaleToBmp(data, width, height):
    b = bytearray
    for x in data:
        b.append(x)
        b.append(x)
        b.append(x)

def main():
    print('Hello, World!')

    ser = serial.Serial('/dev/ttyUSB0', 115200)

    seq = 0

    dt = bytearray()
    b = Buffer()
    print('buffer created!')
    while(1):
        x = ser.read(1)
        print('read! {:#02x}'.format(x[0]))

        b.process(x)
        if(b._stat == "dt"):
            print("stat[{}]:{}".format(b.getRespID(), b._stat))
        if(b._stat == "dt"):
            print("process[{}:{:#02x}]:{} {}/{} {}/{}"
                  .format(x, b._buff[-1], b._stat , b._mcnt, b._mlen, b._dcnt, b._dlen))
        if(b.isComplete()):
            data = b.getData()
            printx(data)
            dt += data[0:-1]
            print("datalen:{}".format(len(dt)))
            if(len(data) < 1):
                print('complete but data is 0!')
                b.toString()
            elif(data[-1] > 0):
                print('complete:{}'.format(len(dt)))
                sz = 0
                w = 0
                h = 0
                sz |= dt[0] << 24
                sz |= dt[1] << 16
                sz |= dt[2] << 8
                sz |= dt[3]
                w  |= dt[4] << 9
                w  |= dt[5]
                h  |= dt[6] << 9
                h  |= dt[7]
                print('image_size:{} {}'.format(sz, type(sz)))
                print('width:{}'.format(w))
                print('height:{}'.format(h))

                file_header_size = 14
                core_header_size = 12
                bmp_file_size = (sz * 3) + file_header_size + core_header_size
                file_offset = file_header_size + core_header_size
                bitcount = 8 * 3 # RGB

                print('file_header_size:{} {}'.format(file_header_size, type(file_header_size)))
                print('core_header_size:{} {}'.format(core_header_size, type(file_header_size)))
                print('bmp_file_size:{} {}'.format(bmp_file_size, type(file_header_size)))
                print('file_offset:{} {}'.format(file_offset, type(file_offset)))

                bmp = bytearray()

                # File Header
                # file type 2 bytes, fixed:'BM' (0x43, 0x4D)
                bmp += pack('BB', 0x42, 0x41)
                # file size 4 bytes
                bmp += pack('<i', bmp_file_size)
                # reserved-1 2 bytes - always 0
                bmp += pack('<H', 0)
                # reserved-2 2 bytes - always 0
                bmp += pack('<H', 0)
                # file offset bits (file header + core header)
                bmp += pack('<i', file_offset)

                # Core Header
                # header size 4 bytes
                bmp += pack('<i', core_header_size)
                # bit map width 2 bytes, height 2 bytes
                bmp += pack('<H', w)
                bmp += pack('<H', h)
                # planes 2 bytes
                bmp += pack('<H', 0)
                # bit count
                bmp += pack('>H', bitcount)
                for x in dt[8:]:
                    bmp.append(x)
                    bmp.append(x)
                    bmp.append(x)

                z = bytearray()
                for x in dt[8:]:
                    z.append(x)

                print("image-1")
                img = Image.new('L', (w, h))
                print("image-2")
                img.putdata(z)
                print("image-3")
                img.save('image.png')
                print("write image.png sucessfully")
                img.save('image.bmp')
                print("write image.bmp sucessfully")

                file = "picture_{}.bmp".format(seq)
                f = open(file, 'wb')
                f.write(bmp)
                f.close()
                dt.clear()
                return

if __name__ == '__main__':
    main()




