"""GUI shell and wrapper regression tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import software_gui_pro_4 as gui


def test_gui_line_count_under_600():
    lines = Path(gui.__file__).read_text(encoding="utf-8").splitlines()
    assert len(lines) < 600, f"GUI shell is {len(lines)} lines; target <600"


def test_gui_imports_legacy_exports():
    assert hasattr(gui, "compute_ppx")
    assert hasattr(gui, "doi_pat")
    assert hasattr(gui, "add_cf_and_pp_global")
    assert hasattr(gui, "export_excel")


def test_add_cf_and_pp_global_wrapper_matches_package():
    from bibliometric_analysis.metrics.mncs import add_cf_and_pp_global as pkg_fn

    records = pd.DataFrame({
        "domain_id": ["C1"],
        "year": [2020],
        "c_use": [10],
    })
    globals_df = pd.DataFrame({
        "domain_id": ["C1"],
        "year": [2020],
        "c0_mean": [5],
        "thr_top1": [15],
        "thr_top10": [9],
        "thr_top25": [8],
    })
    a = gui.add_cf_and_pp_global(records.copy(), globals_df.copy())
    b = pkg_fn(records.copy(), globals_df.copy(), ties_policy=gui.TIES_POLICY)
    assert float(a.iloc[0]["cf"]) == float(b.iloc[0]["cf"])


def test_package_modules_do_not_import_tkinter():
    root = Path(__file__).resolve().parents[1] / "bibliometric_analysis"
    for rel in ("core/pipeline.py", "baselines/openalex_baselines.py", "corpus/build.py"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "tkinter" not in text


def test_run_analysis_import():
    from bibliometric_analysis.core.pipeline import run_analysis
    assert callable(run_analysis)
