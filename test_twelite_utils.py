import pytest
import twelite_utils as tu

def test_create_missing_list():
    stats = {}
    stats[0] = 1
    stats[1] = 1
    stats[2] = 0
    stats[3] = 1

    ll = tu.create_missing_list(stats, 4)
    print(ll)
    assert(len(ll)==1)
    assert(ll[0]==2)
