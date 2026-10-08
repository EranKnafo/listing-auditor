"""Completeness: is the listing fully filled in, with usable media and channel links?"""
from __future__ import annotations

from typing import Iterable

from ..models import Finding, Listing, Severity
from ..registry import Context, check

NAME = "completeness"


def _f(lst: Listing, code: str, sev: Severity, msg: str) -> Finding:
    return Finding(NAME, code, sev, msg, lst.id)


def _blank(v: object) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


@check(NAME)
def completeness(lst: Listing, ctx: Context) -> Iterable[Finding]:
    cfg = ctx.config["completeness"]

    for path in cfg["required_fields"]:
        if _blank(lst.get(path)):
            yield _f(lst, "MISSING_FIELD", Severity.HIGH, f"required field '{path}' is empty")

    photos = lst.get("photos") or []
    if len(photos) < cfg["min_photos"]:
        sev = Severity.HIGH if len(photos) < cfg["min_photos"] // 2 else Severity.MEDIUM
        yield _f(lst, "PHOTOS_FEW", sev, f"{len(photos)} photos; at least {cfg['min_photos']} expected")

    if photos:
        hero = photos[0]
        w, h = hero.get("width") or 0, hero.get("height") or 0
        if h > w or w < cfg["min_hero_width"]:
            yield _f(
                lst, "HERO_PHOTO_QUALITY", Severity.MEDIUM,
                f"hero photo is {w}x{h}; needs landscape and >= {cfg['min_hero_width']}px wide",
            )
        uncaptioned = sum(1 for p in photos if _blank(p.get("caption")))
        if uncaptioned:
            yield _f(lst, "PHOTO_CAPTIONS", Severity.LOW, f"{uncaptioned} of {len(photos)} photos have no caption")

    have = set(lst.get("amenities") or [])
    missing = [a for a in cfg["required_amenities"] if a not in have]
    if missing:
        yield _f(lst, "AMENITIES_MISSING", Severity.MEDIUM, f"missing baseline amenities: {', '.join(missing)}")

    links = lst.get("ota_links") or {}
    for platform in cfg["required_ota_platforms"]:
        if _blank(links.get(platform)):
            yield _f(lst, "OTA_LINK_MISSING", Severity.LOW, f"no {platform} link")
