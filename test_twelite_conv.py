import pytest
import twelite_utils as tu
import twelite_msg as tm
import twelite_conv as conv

from struct import pack

def test_conv_basic():
    cnv = conv.Conversation()

    p1 = pack( '>BBBBB', 0x00, 0x03, 0x01, 0x02, 0x03 )
    p2 = pack( '>BBBBB', 0x00, 0x01, 0x04, 0x05, 0x06 )
    p3 = pack( '>BBBBB', 0x00, 0x02, 0x07, 0x08, 0x09 )

    dt = p1[2:]
    dt += p2[2:]
    dt += p3[2:]

    cnv.handler_write_request(p1)

    assert(cnv._seq_len == 3)

    cnv.handler_write_data(p2)

    assert(cnv._last_seq == 1)

    cnv.handler_write_done(p3)

    assert(cnv._last_seq == 2)
    assert(cnv.is_complete)

    dd = cnv.get_data()

    assert(dd == dt)


def test_conv_missing_list():
    cnv = conv.Conversation()

    p1 = pack( '>BBBBB', 0x00, 0x05, 0x01, 0x01, 0x01 )
    p2 = pack( '>BBBBB', 0x00, 0x01, 0x02, 0x02, 0x02 )
    p3 = pack( '>BBBBB', 0x00, 0x02, 0x03, 0x03, 0x03 )
    p4 = pack( '>BBBBB', 0x00, 0x03, 0x04, 0x04, 0x04 )
    p5 = pack( '>BBBBB', 0x00, 0x04, 0x05, 0x05, 0x05 )

    cnv.handler_write_request(p1)
    cnv.handler_write_data(p2)
    cnv.handler_write_done(p5)

    assert(not cnv.is_complete()) 
    assert(cnv.get_missing_seqs() == [2,3])


def test_conv_missing_last():
    cnv = conv.Conversation()

    p1 = pack( '>BBBBB', 0x00, 0x05, 0x01, 0x01, 0x01 )
    p2 = pack( '>BBBBB', 0x00, 0x01, 0x02, 0x02, 0x02 )
    p3 = pack( '>BBBBB', 0x00, 0x02, 0x03, 0x03, 0x03 )
    p4 = pack( '>BBBBB', 0x00, 0x03, 0x04, 0x04, 0x04 )
    p5 = pack( '>BBBBB', 0x00, 0x04, 0x05, 0x05, 0x05 )

    cnv.handler_write_request(p1)
    cnv.handler_write_data(p2)
    cnv.handler_write_data(p3)
    cnv.handler_write_data(p4)

    assert(not cnv.is_complete()) 
    assert(cnv.get_missing_seqs() == [4])







