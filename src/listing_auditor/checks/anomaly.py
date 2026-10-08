"""Statistical anomaly: is this listing's base price an outlier against comparable listings?

Rules catch violations you can write down. This catches the ones you can't: a price that is
legal under every band but wildly unlike its peers (typo, wrong unit, stale rate).
Peers are same city + bedroom count, widening to bedroom count alone if the group is too small.
Uses a median/MAD modified z-score so the outliers being hunted don't distort the baseline.

A z-score alone over-fires on tight peer groups (tiny MAD makes a 7% gap look extreme), so a
finding also requires a material relative gap from the median (``min_relative_deviation``).
"""
from __future__ import annotations

from statistics import median
from typing import Iterable

from ..models import Finding, Listing, Severity
from ..registry import Context, check

NAME = "anomaly"


@check(NAME)
def anomaly(lst: Listing, ctx: Context) -> Iterable[Finding]:
    price = lst.get("prices.base_price")
    if not isinstance(price, (int, float)) or price <= 0:
        return
    z, peers = ctx.price_z(lst, float(price))
    cfg = ctx.config["anomaly"]
    if not peers:
        return
    ratio = price / median(peers)
    if abs(z) >= cfg["mad_z_threshold"] and abs(ratio - 1) >= cfg["min_relative_deviation"]:
        yield Finding(
            NAME, "PRICE_OUTLIER", Severity.MEDIUM,
            f"base price {price:g} is {ratio:.2f}x the peer median ({median(peers):g}, n={len(peers)}); "
            f"robust z={z:+.1f}",
            lst.id,
        )
