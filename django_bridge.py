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

"""
IN:
0:0 CMD_HELLO 0x01
1:- Text Message


0:0 CMD_WRITE_REQUEST = 0x02
1:4 Data Length

0:0 CMD_WRITE_DATA = 0x03
1:4 Sequence Number
5:- Data

0:0 CMD_WRITE_DONE = 0x04
1:4 Data Length
5:9 Sequence Number


OUT:
0:0 CMD_CONFIG = 0x11

0:0 CMD_RECV_STAT = 0x12

0:0 CMD_WRITE_ACK = 0x13

"""

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


config_path = "."
data_path = "."
log_path = "."
log_file = "{}/my_log.log".format(log_path)

xb = None
stop_flag = False
restart_cnt = 0
buffers = {}
seqs = {}
tpe = ThreadPoolExecutor(max_workers=5)

logger = logging.getLogger(__name__)

def write_log(msg):
    logger.info(msg)
    print(msg)

class DJangoBridge():
    def __init__(self, url):
        self.url = url

    def post_django_file(self, address, fileName):
        logger.info("start post_django: {}".format(address))
        img_org = cv2.imread(fileName)
        logger.info("post_django fileName: {} {}".format(fileName, str(img_org)))
        cv2.imwrite(fileName, img_org)
        logger.info("post_django wrote fileName: {}".format(fileName))
        files = { 'file_uploaded': (fileName, open(fileName, 'rb'), 'image/jpeg') }
        logger.info("url:{}, filename:{}".format(self.url, fileName))
        response = requests.post(self.url, files=files)
        logger.info("post response:{}".format(response))

#    def post_django(self, address, data):
#        try:
#            now = datetime.now()
#            write_log("start post_django: {} {} {}".format(address, len(data), os.getcwd()))
#            jpg_as_np = np.frombuffer(bytes(data), dtype=np.uint8)
#            write_log("post_django2: {}".format(jpg_as_np))
#            img_org = cv2.imdecode(jpg_as_np, flags=1)
#            write_log("post_django3")
#            fileName = "{}_{}.jpg".format(address, now.strftime("%m%d%Y_%H%M%S"))
#            if(os.path.exists("data")):
#                fileName = "data/{}".format(fileName)
#            write_log("post_django fileName: {} {}".format(fileName, str(img_org)))
#            # imwrite returns bool
#            ret = cv2.imwrite(fileName, img_org)
#            write_log("post_django wrote fileName: {} {}".format(fileName, ret))
#            files = { 'file_uploaded': (fileName, open(fileName, 'rb'), 'image/jpeg') }
#            write_log("url:{}, filename:{}".format(self.url, fileName))
#            response = requests.post(self.url, files=files)
#            write_log("post response:{}".format(response))
#        except Exception as e:
#            write_log("Exception:{}".format(e))
#
#    def send_missing(addr, missing):
#        global xb, config_path
#
#        try:
#            ss = len(missing)
#            mm = CMD_RECV_STAT.to_bytes(1, 'big') + ss.to_bytes(4, 'big')
#            for i in missing:
#                mm = mm + i.to_bytes(4, 'big')
#                print("missing: {}".format(i)) 
#                logger.info("missing: {}".format(i)) 
#
#            # st = xb.send_data(xbee_message.remote_device, mm)
#            st = xb.send_data(addr, mm)
#        except TransmitException as e:
#            print("xb.send_missing: {}".format(e)) 
#            logger.info("xb.send_missing: {}".format(e)) 
#
#    def send_write_request_ack(addr, req_id, len):
#        global xb
#
#        try:
#            write_log("start send_write_request_ack:[addr:{}][req_id:{}][len:{}][type:{}]".format(addr, req_id, len, req_id)) 
#            mm = CMD_WRITE_REQUEST_ACK.to_bytes(1, 'big') + req_id.to_bytes(1,byteorder='big') + len.to_bytes(4, 'big')
#            st = xb.send_data(addr, mm)
#            write_log("end send_write_request_ack ok:[{}][{}][{}]".format(addr, len, st.transmit_status)) 
#        except TransmitException as e:
#            write_log("send_write_request_ack TransmitException: {}".format(e)) 
#        except Exception as e:
#            write_log("send_write_request_ack Exception: {}".format(e)) 
#
#    def send_write_data_ack(addr, req_id, seq):
#        global xb
#
#        try:
#            write_log("start send_write_data_ack: {} {} {}".format(addr, req_id, seq)) 
#            mm = CMD_WRITE_DATA_ACK.to_bytes(1, 'big') + req_id.to_bytes(1,byteorder='big') + seq.to_bytes(4, 'big')
#            st = xb.send_data(addr, mm) # returns digi.xbee.packets.common.TransmitStatusPacket
#            write_log("end send_write_data_ack ok:[{}][{}][{}][{}]".format(addr, req_id, seq, st.transmit_status)) 
#        except TransmitException as e:
#            write_log("send_write_data_ack TransmitException: {}".format(e)) 
#        except Exception as e:
#            write_log("send_write_data_ack Exception: {}".format(e)) 
#
#    def send_write_done_ack(addr, req_id, ln, seq):
#        global xb
#
#        try:
#            write_log("start send_write_done_ack: {} {} {} {}".format(addr, req_id, ln, seq)) 
#            mm = CMD_WRITE_DONE_ACK.to_bytes(1, 'big') + req_id.to_bytes(1,byteorder='big') + ln.to_bytes(4, 'big') + seq.to_bytes(4, 'big')
#            st = xb.send_data(addr, mm)
#            write_log("end send_write_done_ack ok:[{}][{}]".format(addr, st.transmit_status)) 
#        except TransmitException as e:
#            write_log("send_write_done_ack error: {}".format(e)) 
#        except Exception as e:
#            write_log("send_write_done_ack error: {}".format(e)) 
#
#    def stop_handler(signum, frame):
#        logger.info("signum:{}".format(signum))
#        global stop_flag
#        global restart_cnt
#        restart_cnt = True
#        stop_flag = True


def main():
    global xb
    global config_path, data_path, log_path, log_file

    parser = OptionParser()
    parser.add_option("-z", "--zigbee", dest="zigbee",
                      help="Zig Bee Device path", default='/dev/ttyUSB0')
    parser.add_option("-b", "--baudrate", dest="baudrate",
                      help="Zig Bee Baud Rate", default=115200)
    parser.add_option("-a", "--path", dest="path",
                      help="Application Path", default='.')
    parser.add_option("-d", "--dest", dest="dest",
                      help="Destination URL", default='http://localhost:8000/facedetect/')
    parser.add_option("-f", "--file", dest="file",
                      help="Zig Bee Device Test File", default=None)

    (options, args) = parser.parse_args()

    logger.info("url:{}".format(options.dest))


    config_path = "{}/config".format(options.path)
    data_path = "{}/data".format(options.path)
    log_path = "{}/logs".format(options.path)
    log_file = "{}/my_log.log".format(log_path)

    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=10)
    formatter = logging.Formatter('%(asctime)s %(levelname) -8s :%(lineno) -3s %(funcName)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.info("config_path:{}".format(config_path))
    logger.info("data_path:{}".format(data_path))
    logger.info("log_path:{}".format(log_path))
    logger.info("log_file:{}".format(log_file))

    app = DJangoBridge(options.dest)

    if(options.file):
        app.post_django_file(options.file, options.file)
        return

    logger.info("add SIGINT handler")
    signal.signal(signal.SIGINT, stop_handler)

#    logger.info("ZigBeeDevice {} {}".format(options.zigbee, options.baudrate))
#    xb = ZigBeeDevice(options.zigbee, options.baudrate)

    cnt = 0
    while(not stop_flag):
#        logger.info("ZigBeeDevice.optn()")
#        xb.open()

#        logger.info("add xbee handler.")
#        xb.add_data_received_callback(my_data_received_callback)

        logger.info("start loop.")
        restart_cnt = 0
        while(restart_cnt < 60):
            cnt = cnt + 1
            restart_cnt = restart_cnt + 1
#            if((cnt % 60) == 0):
#                logger.info("sleeping.")
            logger.info("sleeping.")
            time.sleep(1)

        try:
            logger.info("remove xbee handler.")
#            xb.del_data_received_callback(my_data_received_callback)
        except XBeeException as e:
            write_log("XBeeException while removing xbee handler:{}".format(e))
        except Exception as e:
            write_log("Exception while removing xbee handler:{}".format(e))

#        try:
#            xb.close()
#        except Exception as e:
#            write_log("Exception while close xbee:{}".format(e))

if __name__ == "__main__":
    main()

