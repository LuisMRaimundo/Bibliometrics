"""Extended baseline module tests (offline / mocked)."""

from __future__ import annotations

import pandas as pd
import pytest

from bibliometric_analysis.baselines.openalex_baselines import (
    make_local_globals_from_df,
    try_histogram,
)
from bibliometric_analysis.metrics.bootstrap import bootstrap_mncs_with_c0
from bibliometric_analysis.ontology.concepts import select_openalex_level


def test_make_local_globals_from_df():
    records = pd.DataFrame({
        "domain_id": ["C1", "C1", "C1"],
        "year": [2020, 2020, 2020],
        "c_use": [10, 4, 20],
    })
    g = make_local_globals_from_df(records)
    assert len(g) == 1
    assert g.iloc[0]["c0_mean"] == pytest.approx(34 / 3)
    assert "thr_top10" in g.columns


def test_try_histogram_mock():
    def http_get(url, params=None, mailto=None, **kwargs):
        return {
            "group_by": [
                {"key": 0, "count": 50},
                {"key": 1, "count": 30},
                {"key": 2, "count": 20},
            ],
            "meta": {"count": 100},
        }

    out = try_histogram("C1", 2020, "t@example.com", None, http_get=http_get)
    assert out is not None
    assert out["N"] == 100


def test_bootstrap_mncs_with_c0():
    df = pd.DataFrame({"c_use": [2, 4, 6], "c0_mean": [2, 2, 2]})
    mncs, lo, hi = bootstrap_mncs_with_c0(df, B=50)
    assert mncs == pytest.approx(4 / 2)
    assert lo <= hi


def test_select_openalex_level():
    concepts = [
        {"id": "C1", "display_name": "Broad", "level": 0, "score": 0.5},
        {"id": "C2", "display_name": "Narrow", "level": 1, "score": 0.9},
    ]
    lbl, cid = select_openalex_level(concepts, 1)
    assert lbl == "Narrow"
    assert cid == "C2"
