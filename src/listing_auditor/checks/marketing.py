"""Marketing copy: title hygiene, description depth, and claims that contradict structured data."""
from __future__ import annotations

import re
from typing import Iterable

from ..models import Finding, Listing, Patch, Severity
from ..registry import Context, check
from ..util import smart_title

NAME = "marketing"


@check(NAME)
def marketing(lst: Listing, ctx: Context) -> Iterable[Finding]:
    cfg = ctx.config["marketing"]
    title = lst.get("title")

    if isinstance(title, str) and title.strip():
        # --- safe, mechanical fixes -------------------------------------------------
        # Both fixes touch the same field, so they share ONE combined patch (original -> final).
        # Independent patches on one field would depend on application order.
        cleaned = " ".join(title.split())
        shouting = len(cleaned) > 8 and cleaned.isupper()
        final = smart_title(cleaned) if shouting else cleaned
        fix = Patch(lst.id, "title", title, final, "normalise whitespace and ALL CAPS") if final != title else None
        if cleaned != title:
            yield Finding(NAME, "TITLE_WHITESPACE", Severity.LOW, "stray or repeated whitespace in title", lst.id, fix)
        if shouting:
            yield Finding(NAME, "TITLE_CAPS", Severity.LOW, "title is all caps", lst.id, fix)
        title = final
        # --- rules that need a human --------------------------------------------------
        if len(title) > cfg["title_max_chars"]:
            yield Finding(NAME, "TITLE_TOO_LONG", Severity.MEDIUM,
                          f"title is {len(title)} chars; limit is {cfg['title_max_chars']}", lst.id)
        for pattern in cfg["banned_title_patterns"]:
            m = re.search(pattern, title)
            if m:
                code = "TITLE_PHONE" if re.search(r"\d{3}", m.group(0)) else "TITLE_BANNED_PHRASE"
                yield Finding(NAME, code, Severity.HIGH, f"title contains disallowed text: '{m.group(0)}'", lst.id)

    desc = lst.get("description")
    if isinstance(desc, str) and desc.strip():
        if len(desc) < cfg["description_min_chars"]:
            yield Finding(NAME, "DESCRIPTION_SHORT", Severity.MEDIUM,
                          f"description is {len(desc)} chars; at least {cfg['description_min_chars']} expected", lst.id)
        # Cross-field consistency: the copy promises something the structured data does not list.
        have = list(lst.get("amenities") or [])
        low = desc.lower()
        for phrase, amenity in cfg["claim_keywords"].items():
            if phrase in low and amenity not in have:
                yield Finding(NAME, "AMENITY_CLAIM_MISMATCH", Severity.MEDIUM,
                              f"description mentions '{phrase}' but amenity '{amenity}' is not listed", lst.id,
                              Patch(lst.id, "amenities", have, have + [amenity],
                                    f"add '{amenity}' (or remove the claim from the description)", safe=False))
