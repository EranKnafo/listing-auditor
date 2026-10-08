"""Policy and compliance: occupancy, licensing, stay limits, cancellation policy, check-in/out times."""
from __future__ import annotations

from typing import Iterable

from ..models import Finding, Listing, Patch, Severity
from ..registry import Context, check
from ..util import normalize_time

NAME = "policy"


@check(NAME)
def policy(lst: Listing, ctx: Context) -> Iterable[Finding]:
    cfg = ctx.config["policy"]

    def f(code: str, sev: Severity, msg: str, patch: Patch | None = None) -> Finding:
        return Finding(NAME, code, sev, msg, lst.id, patch)

    beds, occ = lst.get("bedrooms"), lst.get("accommodates")
    if isinstance(beds, int) and isinstance(occ, int) and beds > 0:
        cap = beds * cfg["max_guests_per_bedroom"]
        if occ > cap:
            yield f("OCCUPANCY_EXCEEDED", Severity.HIGH,
                    f"sleeps {occ} with {beds} bedroom(s); limit is {cap} ({cfg['max_guests_per_bedroom']}/bedroom)")

    min_n, max_n = lst.get("terms.min_nights"), lst.get("terms.max_nights")
    if isinstance(min_n, int) and isinstance(max_n, int) and min_n > max_n:
        yield f("MIN_GT_MAX", Severity.CRITICAL, f"minimum stay ({min_n}) exceeds maximum stay ({max_n})")

    city = lst.get("address.city")
    licensed = bool(str(lst.get("license_number") or "").strip())
    long_term_min = ctx.config["pricing"]["long_term_min_nights"]
    if city in cfg["license_required_cities"] and not licensed and isinstance(min_n, int) and min_n < long_term_min:
        yield f("LICENSE_REQUIRED", Severity.CRITICAL,
                f"short-term stays in {city} require a license number; none on file")

    cancel = lst.get("terms.cancellation_policy")
    if cancel not in cfg["allowed_cancellation_policies"]:
        yield f("CANCELLATION_POLICY_INVALID", Severity.MEDIUM, f"cancellation policy {cancel!r} is not recognised")

    times = {}
    for key in ("check_in_time", "check_out_time"):
        raw = lst.get(f"terms.{key}")
        norm = normalize_time(raw)
        if norm is None:
            yield f("TIME_INVALID", Severity.MEDIUM, f"{key} {raw!r} is missing or unparseable")
        elif norm != raw:
            yield f("TIME_FORMAT", Severity.LOW, f"{key} {raw!r} is not HH:MM",
                    Patch(lst.id, f"terms.{key}", raw, norm, "normalise to 24h HH:MM"))
        times[key] = norm
    if times.get("check_in_time") and times.get("check_out_time"):
        if times["check_out_time"] >= times["check_in_time"]:
            yield f("TIME_ORDER", Severity.MEDIUM,
                    f"checkout {times['check_out_time']} is not before check-in {times['check_in_time']}")
