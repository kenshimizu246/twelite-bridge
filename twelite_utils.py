
import logging

logger = logging.getLogger(__name__)



def printx(d):
    ss = ""
    cnt = 0
    for x in d:
        ss += "{:#02x}, ".format(x)
        cnt += 1
        if((cnt % 10) == 0):
            logger.info(ss)
            print(ss)
            ss = ""
    if(len(ss) > 0):
        logger.info(ss)
        print(ss)

def checksum(data):
    x = 0;
    for i in range(0, len(data)):
        x ^= data[i]
    return x

def create_missing_list(stats, seq_len):
    l = []
    for i in range(0, seq_len):
        if(stats[i] < 1):
            l.append(i)
    return l

