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
from optparse import OptionParser

tpe = ThreadPoolExecutor(max_workers=5)

def printx(d):
    str = ""
    cnt = 0
    for x in d:
        str += "{:#02x}, ".format(x)
        cnt += 1
        if((cnt % 10) == 0):
            print(str)
            str = ""
    if(len(str) > 0):
        print(str)

def read_reply(id, ser):
    while(1):
        x = ser.read(1)
        print("{} : {:#02x}".format(id, x[0]))

def create_ext_msg(address, data):
    ll = len(data)
    data_len = (11 - 4) + ll;
    s = 11 + ll + 1;
    p = pack('>BBBBBBBBBBB', 0xA5, 0x5A, 0x80, data_len, address, 0xA0, 0x01, 0x01, 0x02, 0x0A, 0xFF)
    p += data
    for i in range(0, len(p)):
        print("{:#02x}".format(p[i]), end=', ')
    print("")
    x = 0;
    for i in range(4, len(p)):
        print("{:#02x}".format(p[i]), end=', ')
        x ^= p[i];
    print("")
    p += pack('>B', x)
    return p

# void send_ext_msg(unsigned char address, uint16_t seq, unsigned char cmd, unsigned char *params, int params_len, unsigned char *data, int len){
def create_ext_msg2(address, seq, cmd, params, data):
    ll = len(data) + 1 + len(params)
    data_len = (11 - 4) + ll;
    # s = 11 + ll + 1;
    p = pack('>BBBBBBBBBBB', 0xA5, 0x5A, 0x80, data_len, address, 0xA0, seq, 0x01, 0x02, 0x0A, 0xFF)
    p += pack('>B', cmd)
    for x in params:
        p += pack('>B', x)
    p += data
    x = 0;
    for i in range(0, len(p)):
        # print("{:#02x}".format(p[i]), end=', ')
        print("{}:{:#02x}".format(i, p[i]))
        if(i > 3):
            x ^= p[i];
    print("")
    print("x:{:#02x}".format(x))
    p += pack('>B', x)
    return p

def main():
    parser = OptionParser()
    parser.add_option("-c", "--command", dest="command",
                      help="command", default="send")
    parser.add_option("-f", "--from_addr", dest="from_addr",
                      help="address", default=None)
    parser.add_option("-t", "--to_addr", dest="to_addr",
                      help="to address", default=None)
    parser.add_option("-m", "--msg", dest="msg",
                      help="message", default=None)
    parser.add_option("-r", "--read_only", dest="ro_dev",
                      help="read only", default=None)
    parser.add_option("-s", "--send", dest="send_str",
                      help="send only", default=None)

    (options, args) = parser.parse_args()

    cmd = options.command
    to_id = None
    from_id = None

    to_str = options.to_addr
    if(to_str is not None):
        if(":" not in to_str):
            print("The format must be '/dev/ttyUSB0:01'!")
            return
        (to_dev, to_id) = to_str.split(":")
        to_id = int(to_id)

    from_str = options.from_addr
    if(from_str is not None):
        if(from_str is not None and ":" not in from_str):
            print("The format must be '/dev/ttyUSB0:01'!")
            return
        (from_dev, from_id) = from_str.split(":")
        from_id = int(from_id)

    if(options.ro_dev is not None):
        to_dev = options.ro_dev
        cmd = "read"

    if(options.send_str is not None):
        send_str = options.send_str
        if(":" not in send_str):
             print("The format must be '/dev/ttyUSB0:01'!")
             return
        (from_dev, to_id) = send_str.split(":")
        to_id = int(to_id)
        cmd = "send"

    if(from_id is not None and from_id == to_id):
        print("error same id not allowed!")
        return 

    if("read" in cmd):
        print("read from {}".format(to_dev))
        to_ser = serial.Serial(to_dev, 115200)
        tpe.submit(read_reply, "to", to_ser)

    if("send" in cmd):
        print("send from {} : {}".format(from_dev, to_id))
        # msg = create_ext_msg(to_id, b'hello!')
        msg = create_ext_msg2(to_id, 0, 0x02, [0x01], b'hello!')
        from_ser = serial.Serial(from_dev, 115200)
        from_ser.write(msg)


#    if(options.ro is None):
#        print("{}:{}:{}".format(type(from_id), from_id, smap[from_id]))
#        ser_f = serial.Serial(smap[from_id], 115200)
#        tpe.submit(read_reply, "from", ser_f)
#
#    print("{}:{}:{}".format(type(to_id), to_id, smap[to_id]))
#    ser_t = serial.Serial(smap[to_id], 115200)
#    tpe.submit(read_reply, "to", ser_t)
#
#    if(options.ro is None):
#        msg = create_ext_msg(to_id, b'hello!')
#        ser_f.write(msg)


if __name__ == '__main__':
    main()


