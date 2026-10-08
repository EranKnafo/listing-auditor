from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import set_path


class JsonFileSource:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[dict]:
        data = json.loads(self.path.read_text())
        if not isinstance(data, list):
            raise ValueError(f"{self.path}: expected a JSON array of listings")
        return data


class JsonFileSink:
    """Writes patched listings to a *new* file; the source file is never modified."""

    def __init__(self, source_rows: list[dict], out_path: str | Path):
        self.rows = {str(r["id"]): r for r in source_rows}
        self.out_path = Path(out_path)

    def update(self, listing_id: str, field: str, value: Any) -> None:
        set_path(self.rows[listing_id], field, value)

    def commit(self) -> None:
        self.out_path.write_text(json.dumps(list(self.rows.values()), indent=2) + "\n")
