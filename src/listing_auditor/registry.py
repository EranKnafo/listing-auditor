"""Check registry. A check is a plain function; registering it is one decorator.

    @check("pricing")
    def pricing(listing: Listing, ctx: Context) -> Iterable[Finding]: ...

Adding a rule family never requires touching the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from .models import Finding, Listing
from .stats import robust_z


@dataclass
class Context:
    """Read-only inputs every check receives: config, plus portfolio-level data for peer comparisons."""

    config: dict
    # peer groups keyed by (city, bedrooms) and by bedrooms alone: {listing_id: base_price}
    by_city_beds: dict[tuple, dict[str, float]] = field(default_factory=dict)
    by_beds: dict[int, dict[str, float]] = field(default_factory=dict)

    def peer_prices(self, listing: Listing) -> list[float]:
        """Prices of comparable listings (excluding this one), widening the group if it is too small."""
        min_peers = self.config["anomaly"]["min_peers"]
        city = listing.get("address.city")
        beds = listing.get("bedrooms")
        for group in (self.by_city_beds.get((city, beds), {}), self.by_beds.get(beds, {})):
            peers = [p for lid, p in group.items() if lid != listing.id]
            if len(peers) >= min_peers:
                return peers
        return []

    def price_z(self, listing: Listing, price: float) -> tuple[float, list[float]]:
        peers = self.peer_prices(listing)
        return (robust_z(price, peers + [price]) if peers else 0.0), peers


CheckFn = Callable[[Listing, Context], Iterable[Finding]]
_REGISTRY: dict[str, CheckFn] = {}


def check(name: str) -> Callable[[CheckFn], CheckFn]:
    def deco(fn: CheckFn) -> CheckFn:
        if name in _REGISTRY:
            raise ValueError(f"duplicate check name: {name}")
        _REGISTRY[name] = fn
        return fn

    return deco


def get_checks(names: Iterable[str] | None = None) -> dict[str, CheckFn]:
    from . import checks  # noqa: F401  (importing the package registers every check)

    if names is None:
        return dict(_REGISTRY)
    missing = [n for n in names if n not in _REGISTRY]
    if missing:
        raise KeyError(f"unknown check(s): {', '.join(missing)}; available: {', '.join(sorted(_REGISTRY))}")
    return {n: _REGISTRY[n] for n in names}
