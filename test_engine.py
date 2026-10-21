import copy

import pytest

from netarchitect.engine import plan_network, rationale_log
from netarchitect.errors import InvalidParameterError, PhysicalDistanceViolationError
from netarchitect.presets import PRESETS, get_preset
from netarchitect.routing import select_routing


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_presets_plan_with_no_overlap_and_all_categories(name):
    plan = plan_network(get_preset(name))
    subs = sorted(plan.all_subnets(), key=lambda s: s.network)
    for a, b in zip(subs, subs[1:]):
        assert a.broadcast < b.network
    cats = {d.category for d in plan.decisions}
    assert {"L1 media", "Subnetting", "Routing", "Topology tier", "Resiliency", "L2 design"} <= cats
    assert all(d.justification for d in plan.decisions)
    assert "Architectural Rationale Log" in rationale_log(plan)


def test_preset_endpoint_counts_match_spec():
    assert sum(l["hosts"] for l in PRESETS["campus"]["lans"]) == 1600
    assert sum(l["hosts"] for l in PRESETS["wan"]["lans"] if l["name"].startswith("IOT")) == 2000


def test_campus_single_area_ospf_and_wan_bgp():
    assert plan_network(get_preset("campus")).routing.protocol == "ospf-single"
    assert plan_network(get_preset("wan")).routing.protocol == "ospf-multi+ebgp"
    assert plan_network(get_preset("metro")).routing.multi_area


def test_routing_thresholds():
    assert select_routing(49, 1).protocol == "ospf-single"
    assert select_routing(50, 1).protocol == "ospf-multi"
    assert select_routing(10, 1, multi_cloud=True).uses_bgp


def test_configs_have_core_pieces():
    plan = plan_network(get_preset("campus"))
    core = plan.configs["B2-CORE"]
    assert "ip routing" in core and "interface Vlan" in core and "router ospf 1" in core
    assert "ip access-group GUEST_B2_IN in" in core and "deny ip any 10.0.0.0 0.255.255.255" in core
    acc = plan.configs["B2-ACCESS"]
    assert "switchport trunk allowed vlan" in acc and "switchport trunk native vlan 999" in acc
    assert "switchport nonegotiate" in acc and "bpduguard" in acc


def test_wan_has_ipsec_and_bgp():
    plan = plan_network(get_preset("wan"))
    d = plan.configs["DELHI-RTR"]
    assert "crypto isakmp policy" in d and "crypto map VPN-MUMBAI" in d and "router bgp 65001" in d
    assert "IOT_DELHI_IN" in d


def test_custom_copper_over_100m_rejected():
    p = get_preset("campus")
    p["links"][0]["media"] = "copper"
    with pytest.raises(PhysicalDistanceViolationError):
        plan_network(p)


def test_custom_access_run_over_100m_copper_rejected():
    p = get_preset("campus")
    p["lans"][0]["media"] = "copper"
    p["lans"][0]["access_run_m"] = 140
    with pytest.raises(PhysicalDistanceViolationError):
        plan_network(p)


def test_dual_homed_needs_two_links():
    p = get_preset("campus")
    p["links"] = p["links"][:2]  # B2 now has a single link
    with pytest.raises(InvalidParameterError):
        plan_network(p)


@pytest.mark.parametrize("mutate", [
    lambda p: p.pop("root"),
    lambda p: p.update(root="10.0.0.1/16"),
    lambda p: p.update(resiliency="triple"),
    lambda p: p["lans"][0].update(hosts=0),
    lambda p: p["lans"][0].update(site="NOPE"),
    lambda p: p["links"][0].update(distance_m=-1),
    lambda p: p["links"][0].update(b="B1"),
    lambda p: p["lans"].append(copy.deepcopy(p["lans"][0])),
    lambda p: p["sites"][1].update(hq=True),
    lambda p: p["lans"][0].update(acl="weird"),
])
def test_invalid_custom_params(mutate):
    p = get_preset("campus")
    mutate(p)
    with pytest.raises(InvalidParameterError):
        plan_network(p)
