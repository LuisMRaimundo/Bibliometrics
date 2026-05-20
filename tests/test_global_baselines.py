"""Global OpenAlex baseline fetch paths (mocked HTTP, no live calls)."""

from __future__ import annotations

import pandas as pd
import pytest

from bibliometric_analysis.baselines.openalex_baselines import (
    compute_global_baselines_and_thresholds,
    global_distribution,
    group_by_paged,
    sweep_full_distribution,
    try_histogram,
)


def test_group_by_paged_accumulates_pages():
    calls = []

    def http_get(url, params=None, mailto=None, **kwargs):
        calls.append(params.get("cursor"))
        if params.get("cursor") == "*":
            return {"group_by": [{"key": 0, "count": 10}, {"key": 1, "count": 5}], "meta": {"next_cursor": "c2"}}
        return {"group_by": [{"key": 1, "count": 3}], "meta": {}}

    out = group_by_paged("filter", "t@example.com", http_get=http_get, sleep=0)
    assert out["N"] == 18
    assert out["counts"][0] == 10
    assert out["counts"][1] == 8
    assert len(calls) == 2


def test_try_histogram_uses_buckets():
    def http_get(url, params=None, mailto=None, **kwargs):
        if "histogram" in (params or {}):
            return {"histograms": [{"buckets": [{"key": 0, "count": 40}, {"key": 2, "count": 10}]}]}
        raise AssertionError("should not fall back to group_by")

    out = try_histogram("C1", 2020, "t@example.com", None, http_get=http_get, sleep=0)
    assert out is not None
    assert out["N"] == 50
    assert out["complete"] is True


def test_try_histogram_falls_back_to_group_by():
    def http_get(url, params=None, mailto=None, **kwargs):
        if "histogram" in (params or {}):
            return {}
        return {"group_by": [{"key": 0, "count": 7}], "meta": {}}

    out = try_histogram("C1", 2020, "t@example.com", {"journal-article"}, http_get=http_get, sleep=0)
    assert out["N"] == 7


def test_sweep_full_distribution_respects_max_pages():
    pages = {"n": 0}

    def http_get(url, params=None, mailto=None, **kwargs):
        pages["n"] += 1
        return {
            "results": [{"cited_by_count": 1}, {"cited_by_count": 3}],
            "meta": {"next_cursor": "next"} if pages["n"] < 5 else None,
        }

    out = sweep_full_distribution("C1", 2020, "t@example.com", None, max_pages=2, http_get=http_get, sleep=0)
    assert out["N"] == 4
    assert pages["n"] == 2
    assert out["complete"] is False


def test_global_distribution_empty_counts():
    def http_get(url, params=None, mailto=None, **kwargs):
        return {"group_by": [], "meta": {}}

    d = global_distribution("C1", 2020, "t@example.com", None, True, 10, ties_policy="closed_ge", http_get=http_get, sleep=0)
    assert d["N"] == 0
    assert pd.isna(d["mean"])


def test_sweep_full_distribution_404():
    def http_get(url, params=None, mailto=None, **kwargs):
        return {"_status": 404}

    out = sweep_full_distribution("C1", 2020, "t@example.com", None, max_pages=5, http_get=http_get, sleep=0)
    assert out["N"] == 0
    assert out["complete"] is False


def test_global_distribution_sweep_fallback_quantiles():
    def http_get(url, params=None, mailto=None, **kwargs):
        if "histogram" in (params or {}):
            return {}
        return {
            "results": [{"cited_by_count": 0}, {"cited_by_count": 2}, {"cited_by_count": 2}],
            "meta": {},
        }

    d = global_distribution(
        "C1", 2020, "t@example.com", None, prefer_histogram=True, max_pages=1,
        ties_policy="closed_ge", http_get=http_get, sleep=0,
    )
    assert d["N"] == 3
    assert d["mean"] == pytest.approx(4 / 3)
    assert d["q90"] >= d["q75"]


def test_compute_global_baselines_empty_pairs():
    df = compute_global_baselines_and_thresholds(
        pd.DataFrame(),
        "t@example.com",
        [],
        None,
        True,
        1,
        10,
        ties_policy="closed_ge",
        http_get=lambda *a, **k: {},
        sleep=0,
    )
    assert df.empty


def test_compute_global_baselines_and_thresholds_mock():
    fixture = {
        "histograms": [{"buckets": [{"key": 0, "count": 50}, {"key": 5, "count": 50}]}],
    }

    def http_get(url, params=None, mailto=None, **kwargs):
        return fixture

    df = compute_global_baselines_and_thresholds(
        pd.DataFrame({"domain_id": ["C1"], "year": [2020]}),
        "t@example.com",
        [("C1", 2020)],
        None,
        True,
        1,
        10,
        ties_policy="closed_ge",
        http_get=http_get,
        bootstrap_b=100,
        sleep=0,
    )
    assert len(df) == 1
    assert df.iloc[0]["c0_mean"] == 2.5
    assert "thr_top10" in df.columns
