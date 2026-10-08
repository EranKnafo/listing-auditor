"""Pricing sanity: fee and discount bands, by inferred stay class.

Nothing here auto-fixes. Every pricing patch is ``safe=False``: it is a suggestion for a human.
"""
from __future__ import annotations

from typing import Iterable

from ..models import Finding, Listing, Patch, Severity
from ..registry import Context, check

NAME = "pricing"
SHORT_TERM, LONG_TERM = "short_term", "long_term"


def infer_stay_class(lst: Listing, ctx: Context) -> str | None:
    """Short-term if licensed; long-term if the minimum stay is long enough; otherwise unknown.

    Returning ``None`` (rather than guessing) is deliberate: the discount bands differ by class,
    so a wrong guess would produce confident, wrong findings. Ambiguity is surfaced for a human.
    """
    if str(lst.get("license_number") or "").strip():
        return SHORT_TERM
    min_nights = lst.get("terms.min_nights")
    if isinstance(min_nights, int) and min_nights >= ctx.config["pricing"]["long_term_min_nights"]:
        return LONG_TERM
    return None


def _out_of_band(value: float, band: list[float]) -> bool:
    return not (band[0] - 1e-9 <= value <= band[1] + 1e-9)


def _fmt(band: list[float]) -> str:
    return f"{band[0]:g}-{band[1]:g}"


@check(NAME)
def pricing(lst: Listing, ctx: Context) -> Iterable[Finding]:
    cfg = ctx.config["pricing"]

    def f(code: str, sev: Severity, msg: str, patch: Patch | None = None) -> Finding:
        return Finding(NAME, code, sev, msg, lst.id, patch)

    base = lst.get("prices.base_price")
    if not isinstance(base, (int, float)) or base <= 0:
        yield f("BASE_PRICE_INVALID", Severity.CRITICAL, f"base price is {base!r}")
        return

    stay_class = infer_stay_class(lst, ctx)
    if stay_class is None:
        yield f("STAY_CLASS_AMBIGUOUS", Severity.MEDIUM,
                "no license and minimum stay under the long-term threshold; discount bands cannot be chosen")
    for key in ("weekly_factor", "monthly_factor"):
        value = lst.get(f"prices.{key}")
        if value is None:
            continue
        if stay_class is not None:
            band, label = cfg["stay_classes"][stay_class][key], stay_class
        else:
            # Class unknown: still catch values that are wrong under *every* class (the union of bands).
            bands = [c[key] for c in cfg["stay_classes"].values()]
            band, label = [min(b[0] for b in bands), max(b[1] for b in bands)], "any stay class"
        if _out_of_band(value, band):
            suggested = round(min(max(value, band[0]), band[1]), 2)
            yield f("DISCOUNT_OUT_OF_BAND", Severity.MEDIUM,
                    f"{key}={value:g} outside {_fmt(band)} for {label}",
                    Patch(lst.id, f"prices.{key}", value, suggested, "clamp to nearest allowed value", safe=False))

    weekend = lst.get("prices.weekend_factor")
    if weekend is not None and _out_of_band(weekend, cfg["weekend_factor"]):
        yield f("WEEKEND_FACTOR_OUT_OF_BAND", Severity.MEDIUM,
                f"weekend_factor={weekend:g} outside {_fmt(cfg['weekend_factor'])}")

    beds = max(int(lst.get("bedrooms") or 1), 1)
    lo, hi = (b * beds for b in cfg["cleaning_fee_per_bedroom"])
    cleaning = lst.get("prices.cleaning_fee")
    if cleaning is None or cleaning <= 0:
        yield f("CLEANING_FEE_OUT_OF_BAND", Severity.HIGH, "cleaning fee is missing or zero")
    elif _out_of_band(cleaning, [lo, hi]):
        yield f("CLEANING_FEE_OUT_OF_BAND", Severity.MEDIUM,
                f"cleaning fee {cleaning:g} outside {lo:g}-{hi:g} for {beds} bedroom(s)")

    occ = lst.get("accommodates")
    fee = lst.get("prices.extra_guest_fee")
    if isinstance(occ, int) and fee is not None:
        tier = next(t for t in cfg["extra_guest_fee_tiers"] if occ <= t["max_occupancy"])
        if _out_of_band(fee, tier["fee"]):
            suggested = min(max(fee, tier["fee"][0]), tier["fee"][1])
            yield f("EXTRA_GUEST_FEE_OUT_OF_BAND", Severity.MEDIUM,
                    f"extra guest fee {fee:g} outside {_fmt(tier['fee'])} for occupancy {occ}",
                    Patch(lst.id, "prices.extra_guest_fee", fee, suggested, "clamp to tier range", safe=False))
