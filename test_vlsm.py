import pytest

from netarchitect.errors import AddressSpaceExhaustedError, InvalidParameterError
from netarchitect.vlsm import (allocate, int_to_ip, ip_to_int, parse_cidr, prefix_for_hosts,
                               summarize, wildcard_from_prefix)


@pytest.mark.parametrize("prefix,wc", [(0, "255.255.255.255"), (8, "0.255.255.255"),
                                       (16, "0.0.255.255"), (23, "0.0.1.255"), (24, "0.0.0.255"),
                                       (25, "0.0.0.127"), (27, "0.0.0.31"), (30, "0.0.0.3"),
                                       (31, "0.0.0.1"), (32, "0.0.0.0")])
def test_wildcard_masks(prefix, wc):
    assert int_to_ip(wildcard_from_prefix(prefix)) == wc


def test_wildcard_never_negative():
    for p in range(33):
        assert 0 <= wildcard_from_prefix(p) <= 0xFFFFFFFF


@pytest.mark.parametrize("hosts,prefix", [(1, 30), (2, 30), (3, 29), (6, 29), (7, 28), (14, 28),
                                          (30, 27), (31, 26), (62, 26), (126, 25), (127, 24),
                                          (254, 24), (255, 23), (510, 23), (511, 22)])
def test_prefix_for_hosts_boundaries(hosts, prefix):
    assert prefix_for_hosts(hosts) == prefix


@pytest.mark.parametrize("bad", [0, -1, 1.5, "10", None])
def test_prefix_for_hosts_invalid(bad):
    with pytest.raises(InvalidParameterError):
        prefix_for_hosts(bad)


def test_ip_roundtrip_and_validation():
    assert int_to_ip(ip_to_int("192.168.10.200")) == "192.168.10.200"
    for bad in ("256.1.1.1", "1.2.3", "a.b.c.d", "1.2.3.4.5", "-1.0.0.0"):
        with pytest.raises(InvalidParameterError):
            ip_to_int(bad)


def test_host_bits_rejected():
    with pytest.raises(InvalidParameterError):
        parse_cidr("10.0.0.5/24")


REQ = [{"name": "A", "hosts": 50}, {"name": "B", "hosts": 500}, {"name": "C", "hosts": 2},
       {"name": "D", "hosts": 120}, {"name": "E", "hosts": 2}]


def test_allocation_descending_no_overlap_aligned():
    subs = allocate("10.0.0.0/16", REQ)
    assert [s.hosts_requested for s in subs] == [500, 120, 50, 2, 2]
    spans = sorted((s.network, s.broadcast) for s in subs)
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        assert a1 < b0
    for s in subs:
        assert s.network % s.size == 0
        assert s.usable >= s.hosts_requested
        assert s.usable < 2 * s.hosts_requested + 2 or s.prefix == 30


def test_broadcast_gateway_values():
    s = allocate("192.168.1.0/24", [{"name": "X", "hosts": 100}])[0]
    assert (s.cidr(), int_to_ip(s.broadcast), int_to_ip(s.gateway)) == \
        ("192.168.1.0/25", "192.168.1.127", "192.168.1.1")
    assert int_to_ip(s.last_host) == "192.168.1.126"


def test_exact_fit_then_exhaustion():
    subs = allocate("10.0.0.0/24", [{"name": "A", "hosts": 126}, {"name": "B", "hosts": 126}])
    assert [s.cidr() for s in subs] == ["10.0.0.0/25", "10.0.0.128/25"]
    with pytest.raises(AddressSpaceExhaustedError):
        allocate("10.0.0.0/24", [{"name": "A", "hosts": 126}, {"name": "B", "hosts": 126},
                                 {"name": "C", "hosts": 2}])


def test_exhaustion_single_oversize():
    with pytest.raises(AddressSpaceExhaustedError):
        allocate("10.0.0.0/24", [{"name": "BIG", "hosts": 300}])


def test_exhaustion_message_names_subnet():
    with pytest.raises(AddressSpaceExhaustedError) as e:
        allocate("10.0.0.0/30", [{"name": "WHOLE", "hosts": 10}])
    assert "WHOLE" in str(e.value)


def test_empty_request_rejected():
    with pytest.raises(InvalidParameterError):
        allocate("10.0.0.0/16", [])


def test_summarize():
    subs = allocate("10.1.0.0/16", [{"name": "A", "hosts": 250}, {"name": "B", "hosts": 250}])
    net, p = summarize(subs)
    assert (int_to_ip(net), p) == ("10.1.0.0", 23)
