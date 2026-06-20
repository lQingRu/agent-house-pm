import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

import dateparser


@dataclass
class ParseResult:
    name: str
    expiry_date: date
    category: Optional[str]


_DATE_KEYWORDS = re.compile(
    r"\b(expires?|expiry\s+date|best\s+before|use\s+by|bb)\b",
    re.IGNORECASE,
)
_CATEGORY_PARENS = re.compile(r"\(([^)]+)\)")


def parse_date(text: str) -> Optional[date]:
    """Parse a bare date string; returns None for past or unparseable dates."""
    parsed = dateparser.parse(
        text,
        settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
    )
    if parsed is None:
        return None
    result = parsed.date()
    if result < date.today():
        return None
    return result


def parse_item_message(text: str) -> Optional[ParseResult]:
    # Extract category from parentheses
    category_match = _CATEGORY_PARENS.search(text)
    category = category_match.group(1).strip() if category_match else None
    clean = _CATEGORY_PARENS.sub("", text).strip()

    # Strip expiry keyword and try to parse the remainder as a date
    parts = _DATE_KEYWORDS.split(clean, maxsplit=1)
    name_part = parts[0].strip().rstrip(",").strip()

    date_text = parts[-1].strip() if len(parts) > 1 else clean

    expiry = parse_date(date_text)
    if expiry is None or not name_part:
        return None

    return ParseResult(name=name_part, expiry_date=expiry, category=category)
