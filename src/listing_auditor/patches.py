"""Patch collection and application.

Principles:
  * Only ``safe`` patches are ever applied automatically; the rest are proposals.
  * Patches are applied to a deep copy. The input is never mutated.
  * A patch whose recorded ``old`` value no longer matches is skipped as stale, never forced.
  * Applying is dry-run friendly: ``apply_patches`` is pure; writing goes through a ``ListingSink``.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Iterable

from .models import AuditResult, Patch, get_path, set_path

_MISSING = object()


@dataclass
class ApplyOutcome:
    rows: list[dict]
    applied: list[Patch] = field(default_factory=list)
    skipped_stale: list[Patch] = field(default_factory=list)
    skipped_unknown: list[Patch] = field(default_factory=list)


def collect_patches(result: AuditResult, include_unsafe: bool = False) -> list[Patch]:
    patches = [f.patch for f in result.findings if f.patch is not None]
    return patches if include_unsafe else [p for p in patches if p.safe]


def apply_patches(rows: list[dict], patches: Iterable[Patch]) -> ApplyOutcome:
    out = ApplyOutcome(rows=copy.deepcopy(rows))
    by_id = {str(r.get("id")): r for r in out.rows}
    seen: list[Patch] = []
    for p in patches:
        if p in seen:  # several findings may share one patch; apply it once
            continue
        seen.append(p)
        row = by_id.get(p.listing_id)
        if row is None:
            out.skipped_unknown.append(p)
            continue
        if get_path(row, p.field, _MISSING) != p.old:
            out.skipped_stale.append(p)
            continue
        set_path(row, p.field, copy.deepcopy(p.new))
        out.applied.append(p)
    return out


def render_diff(patches: Iterable[Patch]) -> str:
    lines = []
    for p in patches:
        tag = "auto" if p.safe else "review"
        lines.append(f"[{tag}] {p.listing_id} {p.field}: {p.old!r} -> {p.new!r}  ({p.reason})")
    return "\n".join(lines)
