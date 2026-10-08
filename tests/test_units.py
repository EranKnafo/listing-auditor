import pytest

from listing_auditor.config import ConfigError, load_config, validate
from listing_auditor.models import get_path, set_path
from listing_auditor.stats import mad, robust_z
from listing_auditor.util import normalize_time, smart_title


@pytest.mark.parametrize("raw,expected", [
    ("15:00", "15:00"), ("3pm", "15:00"), ("3PM", "15:00"), ("3:30 PM", "15:30"), ("12am", "00:00"),
    ("12pm", "12:00"), ("1500", "15:00"), ("9", "09:00"), ("25:00", None), ("13pm", None), ("noon", None), (None, None),
])
def test_normalize_time(raw, expected):
    assert normalize_time(raw) == expected


def test_dotted_paths():
    d = {}
    set_path(d, "a.b.c", 1)
    assert d == {"a": {"b": {"c": 1}}} and get_path(d, "a.b.c") == 1 and get_path(d, "a.x", "dflt") == "dflt"


def test_robust_z_resists_outliers():
    peers = [100, 102, 98, 101, 99, 100, 103]
    assert abs(robust_z(101, peers)) < 1
    assert robust_z(350, peers + [350]) > 10
    assert robust_z(5, [3, 3, 3, 3]) == 0.0  # no spread -> no signal, not a divide-by-zero
    assert mad([1, 2, 3, 4, 100]) == 1


def test_config_merge_overrides_only_what_is_given(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"completeness": {"min_photos": 30}}')
    cfg = load_config(p)
    assert cfg["completeness"]["min_photos"] == 30
    assert cfg["completeness"]["min_hero_width"] == 1600  # untouched default survives


def test_config_rejects_inverted_band(config):
    import copy
    bad = copy.deepcopy(config)
    bad["pricing"]["weekend_factor"] = [1.5, 1.0]
    with pytest.raises(ConfigError):
        validate(bad)


def test_smart_title_keeps_unit_tokens():
    assert smart_title("SUNNY 3BR CABIN IN PINECREST") == "Sunny 3BR Cabin In Pinecrest"
