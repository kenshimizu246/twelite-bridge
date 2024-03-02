
import logging

logger = logging.getLogger(__name__)

class Conversation:
    def __init__(self):
        self._seq_len = 0
        self._data_list = {}
        self._last_seq = -1

    def handler_write_request(self, data):
        sqlen = data[0] << 8
        sqlen |= data[1]
        self._seq_len = sqlen
        self._last_seq = 0

        self._data_list[0] = data[2:]
        logger.info("seq_len:{}".format(sqlen))
        # printx(data[2:])
        return sqlen

    def handler_write_data(self, data):
        msg_seq = data[0] << 8
        msg_seq |= data[1]
        self._data_list[msg_seq] = data[2:]

        if(msg_seq > self._last_seq):
            self._last_seq = msg_seq
        return msg_seq

    def handler_write_done(self, data):
        msg_seq = data[0] << 8
        msg_seq |= data[1]
        self._last_seq = msg_seq
        self._data_list[msg_seq] = data[2:]
        logger.info("msg_seq:{}/{}".format(msg_seq, self._seq_len))
        logger.info('complete:{}'.format(len(self._data_list)))

    def is_complete(self):
        for i in range(self._seq_len):
            if(i not in self._data_list):
                return False
        return true

    def get_data(self):
        data = None
        for i in range(self._last_seq + 1):
            if(i not in self._data_list):
                return None
            if(data is None):
                data = self._data_list[i]
            else:
                data += self._data_list[i]
        return data

    def get_missing_seqs(self):
        ll = []
        for i in range(self._seq_len):
            if(i not in self._data_list):
                ll.append(i)
        return ll

