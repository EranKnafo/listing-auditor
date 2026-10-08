"""Config loading: packaged defaults, optionally deep-merged with a user JSON file, then validated.

Thresholds live in JSON so operations can tune them without a code change.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).with_name("default_config.json")


class ConfigError(ValueError):
    pass


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def _check_band(name: str, band: Any) -> None:
    if not (isinstance(band, list) and len(band) == 2 and band[0] <= band[1]):
        raise ConfigError(f"{name} must be a [low, high] pair with low <= high, got {band!r}")


def validate(cfg: dict) -> dict:
    for section in ("scoring", "completeness", "marketing", "pricing", "policy", "anomaly"):
        if section not in cfg:
            raise ConfigError(f"missing config section: {section}")
    pricing = cfg["pricing"]
    for cls, bands in pricing["stay_classes"].items():
        for key, band in bands.items():
            _check_band(f"pricing.stay_classes.{cls}.{key}", band)
    _check_band("pricing.weekend_factor", pricing["weekend_factor"])
    _check_band("pricing.cleaning_fee_per_bedroom", pricing["cleaning_fee_per_bedroom"])
    last = 0
    for tier in pricing["extra_guest_fee_tiers"]:
        _check_band("pricing.extra_guest_fee_tiers[].fee", tier["fee"])
        if tier["max_occupancy"] <= last:
            raise ConfigError("extra_guest_fee_tiers must be sorted by increasing max_occupancy")
        last = tier["max_occupancy"]
    if cfg["anomaly"]["mad_z_threshold"] <= 0:
        raise ConfigError("anomaly.mad_z_threshold must be positive")
    if not 0 <= cfg["anomaly"]["min_relative_deviation"] < 1:
        raise ConfigError("anomaly.min_relative_deviation must be in [0, 1)")
    return cfg


def load_config(path: str | Path | None = None) -> dict:
    cfg = json.loads(DEFAULT_PATH.read_text())
    if path:
        cfg = _merge(cfg, json.loads(Path(path).read_text()))
    return validate(cfg)
