"""Multi-field fractional counting by OpenAlex concepts."""

from __future__ import annotations

import json
from typing import Dict, List, Tuple

import pandas as pd


def explode_multifield_fractional(records: pd.DataFrame, level_weight: str) -> pd.DataFrame:
    """
    Expand records by concepts_lvl with fractional weights.

    level_weight: 'equal' or 'score' (proportional to concept scores).
    """
    rows: List[Dict[str, object]] = []

    cols_needed = {
        "idx",
        "year",
        "cf",
        "PPg_top1",
        "PPg_top10",
        "PPg_top25",
        "domain_id",
        "domain_label",
        "n_authors",
        "n_affiliations",
        "concepts_lvl",
    }
    missing = [c for c in cols_needed if c not in records.columns]
    if missing:
        tmp = records.copy()
        for c in missing:
            tmp[c] = pd.NA
        records = tmp

    for _, r in records.iterrows():
        lst: list = []
        try:
            raw = r.get("concepts_lvl")
            if isinstance(raw, str):
                lst = json.loads(raw or "[]")
            elif isinstance(raw, list):
                lst = raw
        except Exception:
            lst = []

        if not lst:
            if pd.notna(r.get("domain_label")) and pd.notna(r.get("domain_id")):
                lst = [(r.get("domain_id"), r.get("domain_label"), 1.0)]
            else:
                continue

        parts: List[Tuple[str, str, float]] = []
        if level_weight == "score":
            total = 0.0
            triples: List[Tuple[str, str, float]] = []
            for item in lst:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    cid, name, s = item[0], item[1], float(item[2])
                elif isinstance(item, dict):
                    cid = item.get("id") or item.get("0")
                    name = item.get("display_name") or item.get("1")
                    s = float(item.get("score", 0.0))
                else:
                    continue
                s = max(0.0, float(s))
                triples.append((str(cid), str(name), s))
                total += s
            if total > 0.0:
                parts = [(cid, name, s / total) for (cid, name, s) in triples]
            elif triples:
                w = 1.0 / len(triples)
                parts = [(cid, name, w) for (cid, name, _) in triples]
        else:
            triples = []
            for item in lst:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    cid, name = item[0], item[1]
                elif isinstance(item, dict):
                    cid = item.get("id") or item.get("0")
                    name = item.get("display_name") or item.get("1")
                else:
                    continue
                triples.append((str(cid), str(name)))
            if triples:
                w = 1.0 / len(triples)
                parts = [(cid, name, w) for (cid, name) in triples]

        if not parts:
            continue

        try:
            na = int(r.get("n_authors") or 1)
        except Exception:
            na = 1
        try:
            nf = int(r.get("n_affiliations") or 1)
        except Exception:
            nf = 1
        w_auth = 1.0 / max(1, na)
        w_aff = 1.0 / max(1, nf)

        for cid, name, w_con in parts:
            rows.append(
                {
                    "idx": r.get("idx"),
                    "year": r.get("year"),
                    "domain_id": cid,
                    "domain_label": name,
                    "cf": r.get("cf"),
                    "PPg_top1": r.get("PPg_top1"),
                    "PPg_top10": r.get("PPg_top10"),
                    "PPg_top25": r.get("PPg_top25"),
                    "w_concept": float(w_con),
                    "w_author": float(w_auth),
                    "w_affil": float(w_aff),
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "idx",
                "year",
                "domain_id",
                "domain_label",
                "cf",
                "PPg_top1",
                "PPg_top10",
                "PPg_top25",
                "w_concept",
                "w_author",
                "w_affil",
                "w_total",
            ]
        )
    df["w_total"] = df["w_concept"] * df["w_author"] * df["w_affil"]
    return df
