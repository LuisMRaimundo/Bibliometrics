"""Heuristic macro-area simplification (legacy; low confidence)."""

from __future__ import annotations

MACRO_AREA_RULES = [
    (("physic", "astro"), "Physics & Astronomy"),
    (("math", "algebra", "geometry"), "Mathematics"),
    (("computer", "computat", "intelligence", "software"), "Computer Science"),
    (("bio", "medic", "genet", "clini"), "Biology & Medicine"),
    (("chem", "material", "polymer"), "Chemistry & Materials"),
    (("engin", "mechan", "electr"), "Engineering"),
    (("geo", "earth", "envir"), "Earth & Environmental"),
    (("social", "econ", "psych", "educ"), "Social Sciences"),
]


def simplify_area_name_heuristic(area_name: str) -> tuple[str, str]:
    """
    Returns (macro_area, confidence) where confidence is 'low' for heuristic rules.
    Prefer CrosswalkRegistry when populated crosswalks exist.
    """
    s = str(area_name).lower()
    for keywords, macro in MACRO_AREA_RULES:
        if any(kw in s for kw in keywords):
            return macro, "low"
    return area_name, "unknown"
