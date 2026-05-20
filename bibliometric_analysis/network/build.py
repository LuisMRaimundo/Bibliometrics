"""Citation edge construction."""

from __future__ import annotations

import pandas as pd


def build_edges_by_doi(records: pd.DataFrame) -> pd.DataFrame:
    doi_to_idx = dict(zip(records["doi"], records["idx"]))
    edges = []
    for _, row in records.iterrows():
        refset = set(row.get("ref_dois") or [])
        src_idx = int(row["idx"])
        for d in refset.intersection(doi_to_idx.keys()):
            dst_idx = int(doi_to_idx[d])
            if src_idx != dst_idx:
                edges.append((src_idx, dst_idx))
    return pd.DataFrame(edges, columns=["citer_idx", "cited_idx"])
