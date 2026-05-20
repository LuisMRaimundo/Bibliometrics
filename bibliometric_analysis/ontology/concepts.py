"""OpenAlex concept level selection."""

from __future__ import annotations

from typing import Any


def select_domain_concept(concepts: list[dict[str, Any]], top_level: int = 0) -> tuple[str | None, str | None]:
    """Select domain_id and domain_label from OpenAlex concept list at given level."""
    if not concepts:
        return (None, None)
    cand = [c for c in concepts if c.get("level") == top_level] or concepts
    cand = sorted(cand, key=lambda c: c.get("score", 0), reverse=True)
    best = cand[0]
    cid = best.get("id")
    label = best.get("display_name")
    return (str(label) if label else None, str(cid) if cid else None)


def extract_level_concepts(concepts: list[dict[str, Any]], level: int) -> list[tuple[str, str, float]]:
    out = []
    for c in concepts or []:
        if c.get("level") == level:
            out.append((str(c.get("id", "")), str(c.get("display_name", "")), float(c.get("score", 0.0))))
    return out


def select_openalex_level(concepts: list[dict[str, Any]], level: int) -> tuple[str | None, str | None]:
    """Return (label, id) for the highest-scoring concept at the given OpenAlex level."""
    items = extract_level_concepts(concepts, level)
    if not items:
        return (None, None)
    items.sort(key=lambda x: x[2], reverse=True)
    cid, label, _ = items[0]
    return (label or None, cid or None)
