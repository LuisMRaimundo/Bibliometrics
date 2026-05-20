"""Dashboard package helpers and import safety."""

import importlib

import pandas as pd

from bibliometric_analysis.dashboard import (
    compute_dashboard_metrics,
    compute_goldset_qa,
    compute_sensitivity_table,
    ensure_min_metrics,
)


def test_app_dashboard_import_safe():
    mod = importlib.import_module("app_dashboard")
    assert hasattr(mod, "main")
    assert callable(mod.main)


def test_compute_dashboard_metrics():
    df = pd.DataFrame({
        "c_f": [1.0, 2.0],
        "PPg_top10": [1, 0],
        "PPg_top25": [1, 1],
    })
    m = compute_dashboard_metrics(df, None)
    assert m["n_docs"] == 2
    assert m["mncs"] == 1.5


def test_goldset_qa():
    gd = pd.DataFrame({"match": [1, 0, 1], "y_pred": [1, 0, 0]})
    qa = compute_goldset_qa(gd, "match", "y_pred")
    assert 0 <= qa["f1"] <= 1


def test_sensitivity_table():
    base = pd.DataFrame({
        "institution": ["Uni A", "Uni B"],
        "c_f": [1.0, 2.0],
        "PPg_top10": [1, 0],
    })
    var = pd.DataFrame({
        "affiliation": ["Uni A", "Uni C"],
        "c_f": [1.5, 0.5],
        "PPg_top10": [1, 1],
    })
    comp = compute_sensitivity_table(base, var, "institution")
    assert comp is not None
    assert "Δ_MNCS" in comp.columns


def test_ensure_min_metrics_adds_pp10():
    df = pd.DataFrame({
        "year": [2020, 2020],
        "domain_id": ["C1", "C1"],
        "c_use": [10, 2],
        "c0_mean": [5, 5],
    })
    out = ensure_min_metrics(df)
    assert "PPg_top10" in out.columns
    assert "c_f" in out.columns
