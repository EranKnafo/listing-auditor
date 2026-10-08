from __future__ import annotations

import re

_TIME_RE = re.compile(r"^\s*(\d{1,2})(?::?(\d{2}))?\s*([ap])\.?m?\.?\s*$|^\s*(\d{1,2})(?::?(\d{2}))?\s*$", re.I)


def normalize_time(value: object) -> str | None:
    """Parse '3pm', '3:30 PM', '1500', '15:00' into 'HH:MM'. Returns None if unparseable."""
    if not isinstance(value, str):
        return None
    m = _TIME_RE.match(value)
    if not m:
        return None
    if m.group(3):  # 12-hour clock with am/pm
        hour, minute, meridiem = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if meridiem == "p" else 0)
    else:
        hour, minute = int(m.group(4)), int(m.group(5) or 0)
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def smart_title(text: str) -> str:
    """Title-case that leaves tokens mixing digits and letters (``3BR``, ``2BA``) upper-case."""
    out = []
    for word in text.split():
        has_digit = any(c.isdigit() for c in word)
        has_alpha = any(c.isalpha() for c in word)
        out.append(word.upper() if has_digit and has_alpha else word.capitalize())
    return " ".join(out)
