"""Text normalization for concept/field labels."""

from __future__ import annotations

import re
import unicodedata

_WS_RE = re.compile(r"\s+", re.UNICODE)


def normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text or "").strip()


def unaccent(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in t if not unicodedata.combining(ch))


def normalize_label(text: str, *, unaccent_lower: bool = False) -> str:
    t = normalize_whitespace(text)
    if unaccent_lower:
        t = unaccent(t).lower()
    return t
