import pytest

from netarchitect.errors import InvalidParameterError, PhysicalDistanceViolationError
from netarchitect.media import recommend_media


@pytest.mark.parametrize("d", [1, 50, 100])
def test_copper_up_to_100m(d):
    r = recommend_media(d)
    assert r.standard == "10GBASE-T" and "802.3an" in r.justification


@pytest.mark.parametrize("d", [100.01, 101, 250, 400])
def test_om4_between_101_and_400(d):
    r = recommend_media(d)
    assert r.standard == "10GBASE-SR" and "850 nm" in r.justification


@pytest.mark.parametrize("d,optic", [(401, "10GBASE-LR"), (10000, "10GBASE-LR"),
                                     (10001, "10GBASE-ER"), (40000, "10GBASE-ER")])
def test_smf_beyond_400m(d, optic):
    r = recommend_media(d)
    assert r.medium == "OS2 single-mode fibre" and r.standard == optic
    assert "exceeds the 400 m attenuation limit of OM4" in r.justification


def test_spec_example_sentence():
    r = recommend_media(22000)
    assert "Selected OS2 Single-Mode Fiber because link distance (22 km) exceeds the 400 m" in r.justification


@pytest.mark.parametrize("d", [100.5, 101, 5000])
def test_copper_over_100m_raises(d):
    with pytest.raises(PhysicalDistanceViolationError) as e:
        recommend_media(d, requested="copper")
    assert "attenuation" in str(e.value) and "100" in str(e.value)


def test_copper_exactly_100m_ok():
    assert recommend_media(100, requested="copper").standard == "10GBASE-T"


def test_mmf_over_400m_raises():
    with pytest.raises(PhysicalDistanceViolationError):
        recommend_media(401, requested="mmf")


@pytest.mark.parametrize("bad", [0, -5, "90", None, True])
def test_bad_distance(bad):
    with pytest.raises(InvalidParameterError):
        recommend_media(bad)


def test_optical_budget_warning_and_margin():
    r = recommend_media(40000)          # ER at 40 km: 10 + 1 = 11 dB == budget
    assert r.margin_db == pytest.approx(0.0, abs=1e-9)
    assert r.warnings


def test_beyond_unamplified_reach_uses_carrier():
    r = recommend_media(1_150_000)
    assert "Carrier" in r.medium and r.warnings
