"""Engine: build portfolio context once, run every check on every listing, score the result.

A check that raises never takes down the run; it becomes a CHECK_ERROR finding so the
failure is visible in the report instead of silently skipping a listing.
"""
from __future__ import annotations

import logging
from typing import Iterable

from .config import load_config
from .models import AuditResult, Finding, Listing, ListingReport, Severity
from .registry import Context, get_checks

log = logging.getLogger(__name__)


def build_context(listings: list[Listing], config: dict) -> Context:
    ctx = Context(config=config)
    for lst in listings:
        price = lst.get("prices.base_price")
        beds = lst.get("bedrooms")
        if not isinstance(price, (int, float)) or price <= 0 or beds is None:
            continue
        ctx.by_city_beds.setdefault((lst.get("address.city"), beds), {})[lst.id] = float(price)
        ctx.by_beds.setdefault(beds, {})[lst.id] = float(price)
    return ctx


def score(findings: Iterable[Finding], config: dict) -> int:
    penalties = config["scoring"]["penalties"]
    total = sum(penalties[f.severity.name] for f in findings)
    return max(0, 100 - total)


def audit(
    raw_listings: list[dict],
    config: dict | None = None,
    only: Iterable[str] | None = None,
) -> AuditResult:
    config = config or load_config()
    listings = [Listing(id=str(r.get("id", f"row-{i}")), raw=r) for i, r in enumerate(raw_listings)]
    checks = get_checks(only)
    ctx = build_context(listings, config)

    reports: list[ListingReport] = []
    for lst in listings:
        findings: list[Finding] = []
        for name, fn in checks.items():
            try:
                findings.extend(fn(lst, ctx))
            except Exception as exc:  # isolate: one bad listing/check must not abort the run
                log.exception("check %s failed on %s", name, lst.id)
                findings.append(
                    Finding(name, "CHECK_ERROR", Severity.HIGH, f"{type(exc).__name__}: {exc}", lst.id)
                )
        findings.sort(key=lambda f: (-f.severity, f.check, f.code))
        reports.append(ListingReport(lst.id, lst.name, score(findings, config), findings))
    return AuditResult(reports)
