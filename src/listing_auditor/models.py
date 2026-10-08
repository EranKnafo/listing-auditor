"""Core domain types. Everything else in the package depends on these and nothing else."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


def get_path(data: dict, path: str, default: Any = None) -> Any:
    """Read a dotted path (``"prices.base_price"``) from nested dicts."""
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def set_path(data: dict, path: str, value: Any) -> None:
    """Write a dotted path, creating intermediate dicts as needed."""
    parts = path.split(".")
    cur = data
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


@dataclass(frozen=True)
class Patch:
    """A proposed change to one field of one listing.

    ``safe`` patches are low-risk (formatting, typos) and may be auto-applied.
    Unsafe patches (anything touching price or policy) are only ever proposed.
    ``old`` is recorded so a stale patch is detected instead of clobbering newer data.
    """

    listing_id: str
    field: str
    old: Any
    new: Any
    reason: str
    safe: bool = True


@dataclass(frozen=True)
class Finding:
    check: str
    code: str
    severity: Severity
    message: str
    listing_id: str
    patch: Patch | None = None


@dataclass(frozen=True)
class Listing:
    id: str
    raw: dict

    def get(self, path: str, default: Any = None) -> Any:
        return get_path(self.raw, path, default)

    @property
    def name(self) -> str:
        return self.raw.get("nickname") or self.raw.get("title") or self.id


@dataclass
class ListingReport:
    listing_id: str
    name: str
    score: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class AuditResult:
    reports: list[ListingReport]

    @property
    def average_score(self) -> float:
        return sum(r.score for r in self.reports) / len(self.reports) if self.reports else 100.0

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.reports for f in r.findings]

    def counts_by_code(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.code] = out.get(f.code, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    def counts_by_severity(self) -> dict[str, int]:
        out = {s.name: 0 for s in sorted(Severity, reverse=True)}
        for f in self.findings:
            out[f.severity.name] += 1
        return out
