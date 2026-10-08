"""Adapter interfaces. The engine only ever sees plain dicts; where they come from is an adapter's job.

To audit a real property-management system, implement ``ListingSource`` (fetch + paginate + map to
the dict schema in docs/SCHEMA.md) and, optionally, ``ListingSink`` (push approved patches back).
Nothing else in the package needs to change.
"""
from __future__ import annotations

from typing import Any, Iterable, Protocol


class ListingSource(Protocol):
    def load(self) -> list[dict]: ...


class ListingSink(Protocol):
    def update(self, listing_id: str, field: str, value: Any) -> None: ...

    def commit(self) -> None: ...
