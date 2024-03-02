import pytest
import twelite_utils as tu
import twelite_msg as tm

def test_create_ext_msg():
    cs = 0x2b
    expected = bytearray([0xa5, 0x5a, 0x80, 0xd, 0x79, 0xa0, 0x0, 0x1, 0x2, 0xa, 0xff, 0x1, 0x1, 0x2, 0x7, 0x8, 0x9, cs])
    address = 0x79
    seq = 0
    cmd = 1
    params = [1,2]
    data = bytearray([7, 8, 9])
    m = tm.create_ext_msg(address, seq, cmd, params, data)

    tu.printx(m)

    assert(m == expected)


