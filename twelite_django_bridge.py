
import serial
import time
from binascii import *
from struct import pack

import os
import time
import signal
import logging
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
import requests
from optparse import OptionParser

from PIL import Image
import cv2
import torch
from torch import nn
from torchvision import models, transforms
from time import sleep
import numpy as np

logger = logging.getLogger(__name__)

tpe = ThreadPoolExecutor(max_workers=5)

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

def printx(d):
    str = ""
    cnt = 0
    for x in d:
        str += "{:#02x}, ".format(x)
        cnt += 1
        if((cnt % 10) == 0):
            logger.info(str)
            str = ""
    if(len(str) > 0):
        logger.info(str)

def post_django_file(address, fileName):
    global url
    logger.info("start post_django: {}".format(address))
    img_org = cv2.imread(fileName)
    logger.info("post_django fileName: {} {}".format(fileName, str(img_org)))
    cv2.imwrite(fileName, img_org)
    logger.info("post_django wrote fileName: {}".format(fileName))
    files = { 'file_uploaded': (fileName, open(fileName, 'rb'), 'image/jpeg') }
    logger.info("url:{}, filename:{}".format(url, fileName))
    response = requests.post(url, files=files)
    logger.info("post response:{}".format(response))

def post_django(address, data):
    global url
    try:
        now = datetime.now()
        write_log("start post_django: {} {} {}".format(address, len(data), os.getcwd()))
        jpg_as_np = np.frombuffer(bytes(data), dtype=np.uint8)
        write_log("post_django2: {}".format(jpg_as_np))
        img_org = cv2.imdecode(jpg_as_np, flags=1)
        write_log("post_django3")
        fileName = "{}_{}.jpg".format(address, now.strftime("%m%d%Y_%H%M%S"))
        if(os.path.exists("data")):
            fileName = "data/{}".format(fileName)
        write_log("post_django fileName: {} {}".format(fileName, str(img_org)))
        # imwrite returns bool
        ret = cv2.imwrite(fileName, img_org)
        write_log("post_django wrote fileName: {} {}".format(fileName, ret))
        files = { 'file_uploaded': (fileName, open(fileName, 'rb'), 'image/jpeg') }
        write_log("url:{}, filename:{}".format(url, fileName))
        response = requests.post(url, files=files)
        write_log("post response:{}".format(response))
    except Exception as e:
        write_log("Exception:{}".format(e))

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

def create_missing_list(address, stats, seq_len):
    l = list
    for i in range(0, seq_len):
        if(stats[i] < 1):
            l.append(i)
    return l

def create_missing_msg(address, missing):
    return None

def checksum(data):
    x = 0;
    for i in range(0, len(data)):
        x ^= data[i]
    return x

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
            

def main():
    global url
    parser = OptionParser()
    parser.add_option("-z", "--twelite", dest="twelite",
                      help="TWELITE Device path", default='/dev/ttyUSB0')
    parser.add_option("-b", "--baudrate", dest="baudrate",
                      help="TWELITE Baud Rate", default=115200)
#                      help="TWELITE Baud Rate", default=38400)
    parser.add_option("-a", "--path", dest="path",
                      help="Application Path", default='.')
    parser.add_option("-d", "--dest", dest="dest",
                      help="Destination URL", default='http://localhost:8000/facedetect/')
    parser.add_option("-f", "--file", dest="file",
                      help="TWELITE Device Test File", default=None)

    (options, args) = parser.parse_args()

    config_path = "{}/config".format(options.path)
    data_path = "{}/data".format(options.path)
    log_path = "{}/logs".format(options.path)
    log_file = "{}/my_log.log".format(log_path)

    os.makedirs(data_path, exist_ok=True)
    os.makedirs(log_path, exist_ok=True)

    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=10)
    formatter = logging.Formatter('%(asctime)s %(levelname) -8s :%(lineno) -3s %(funcName)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.info("config_path:{}".format(config_path))
    logger.info("data_path:{}".format(data_path))
    logger.info("log_path:{}".format(log_path))
    logger.info("log_file:{}".format(log_file))

    url = options.dest
    logger.info("url:{}".format(url))

    if(options.file):
        post_django_file(options.file, options.file)
        x = ser.read(1)
        return

    logger.info("serial path:{}".format(options.twelite))
    logger.info("serial baudrate:{}".format(options.baudrate))

    ser = serial.Serial(options.twelite, options.baudrate)

    seq = 0

    stats = {}
    dt = bytearray()
    b = Buffer()
    logger.info('buffer created!')
    while(1):
        # logger.info('try read...')
        x = ser.read(1)
        # if(len(dt) > 6000):
        #     logger.info("read! {:#02x}".format(x[0]))

        b.process(x)
        # if(b._stat == "dt"):
        #     logger.info("stat[{}]:{}".format(b.getRespID(), b._stat))
        # if(b._stat == "dt"):
        # if(len(dt) > 6000):
        #     logger.info("process[{}:{:#02x}]:{} {}/{} {}/{}"
        #           .format(x, b._buff[-1], b._stat , b._mcnt, b._mlen, b._dcnt, b._dlen))
        if(b.isComplete()):
            (cmd, data) = b.getDataAndCmd()
            # printx(data)
            if(len(data) < 1):
                logger.info('complete but data is 0!')
                continue

            # if(len(dt) > 11000):
            #     logger.info('complete! {}'.format(len(dt)))
            if(cmd == Commands.CMD_WRITE_REQUEST):
                # dt.clear()
                # dt = bytearray()
                seq_len = data[0] << 8
                seq_len |= data[1]
                # dt += data[2:]
                dt = data[2:]
                stats[0] = 1
                logger.info("seq_len:{}".format(seq_len))
                printx(data[2:])
            elif(cmd == Commands.CMD_WRITE_DATA and len(dt) > 0):
                msg_seq = data[0] << 8
                msg_seq |= data[1]
                dt += data[2:]
                stats[msg_seq] = 1
                if((seq_len - msg_seq) < 30):
                    logger.info("msg_seq:{}/{}".format(msg_seq, seq_len))
                    printx(b.getRawData())
                # logger.info("msg_seq:{}/{}".format(msg_seq, seq_len))
                # msg = b.create_resp_msg()
                # ser.write(msg)
            elif(cmd == Commands.CMD_WRITE_DONE and len(dt) > 0):
                msg_seq = data[0] << 8
                msg_seq |= data[1]
                dt += data[2:]
                stats[msg_seq] = 1
                logger.info("msg_seq:{}/{}".format(msg_seq, seq_len))
                logger.info('complete:{}'.format(len(dt)))
                printx(dt[2:12])
                sz = 0
                w = 0
                h = 0
                sz |= dt[0] << 24
                sz |= dt[1] << 16
                sz |= dt[2] << 8
                sz |= dt[3]
                w  |= dt[4] << 8
                w  |= dt[5]
                h  |= dt[6] << 8
                h  |= dt[7]

                logger.info('image_size:{} {}'.format(sz, type(sz)))
                logger.info('width:{}'.format(w))
                logger.info('height:{}'.format(h))

                # z = bytearray()
                # for x in dt[8:]:
                #     z.append(x)

                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%s")
                img = Image.new('L', (w, h))
                # img.putdata(z)
                img.putdata(dt[8:])
                # fname_p = "{}/image_{}.png".format(data_path, ts)
                # fname_b = "{}/image_{}.bmp".format(data_path, ts)
                # img.save(fname_p)
                # img.save(fname_b)

                # to jpg, it needs following.
                img = img.convert("RGB")
                fname_j = "{}/image_{}.jpg".format(data_path, ts)
                img.save(fname_j)
                logger.info("save image:{}".format(fname_j))

                tpe.submit(post_django_file, 'x', fname_j)
                # post_django_file('x', fname_j)

                logger.info("stats:")
                for i in range(0, seq_len):
                    x = None
                    if(i in stats):
                        x = stats[i]
                    if(x != 1):
                        logger.info("stats[{}]:{}".format(i, x))
                dt.clear()

    logger.info('end loop!')

if __name__ == '__main__':
    main()




