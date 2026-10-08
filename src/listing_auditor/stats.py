"""Small robust-statistics helpers. Median/MAD resist the very outliers we are hunting."""
from __future__ import annotations

from statistics import median
from typing import Sequence

# Scales MAD so that, for normally distributed data, it estimates the standard deviation.
_MAD_SCALE = 0.6745


def mad(values: Sequence[float]) -> float:
    m = median(values)
    return median([abs(v - m) for v in values])


def robust_z(x: float, values: Sequence[float]) -> float:
    """Modified z-score (Iglewicz & Hoaglin). Returns 0.0 when the peers have no spread."""
    if len(values) < 2:
        return 0.0
    spread = mad(values)
    if spread == 0:
        return 0.0
    return _MAD_SCALE * (x - median(values)) / spread
