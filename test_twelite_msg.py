import pytest
import twelite_utils as tu
import twelite_msg as tm

def test_create_ext_msg():
    address = 0x79
    seq = 0
    cmd = 1
    params = [1,2]
    data = bytearray([7, 8, 9])
    m = tm.create_ext_msg(address, seq, cmd, params, data)
