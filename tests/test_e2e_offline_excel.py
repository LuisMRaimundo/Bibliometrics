"""End-to-end offline pipeline: fixture input → Excel export (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from bibliometric_analysis.core.config import PipelineConfig
from bibliometric_analysis.core.pipeline import run_offline_metrics_export
from bibliometric_analysis.export.excel import safe_sheet_name
from bibliometric_analysis.export.schemas import (
    SHEET_EDGES,
    SHEET_GLOBALS,
    SHEET_NETWORK,
    SHEET_RECORDS,
    SHEET_RUN_META,
    SHEET_SUMMARY_FRAC,
    SHEET_SUMMARY_INT,
)
from bibliometric_analysis.openalex import client as oa_client_mod
from bibliometric_analysis.parsers.openalex_csv import parse_openalex_csv

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e2e"


def _block_network(monkeypatch):
    def _fail(*args, **kwargs):
        raise RuntimeError("Live network call blocked in offline e2e test")

    monkeypatch.setattr(oa_client_mod.OpenAlexClient, "get", _fail)
    monkeypatch.setattr(oa_client_mod, "http_get", _fail)


def test_e2e_offline_openalex_to_excel(tmp_path, monkeypatch):
    _block_network(monkeypatch)

    fixture = FIXTURES / "minimal_openalex.csv"
    schema_spec = json.loads((FIXTURES / "expected_export_schema.json").read_text(encoding="utf-8"))

    records = parse_openalex_csv(str(fixture))
    records["domain_id"] = "C1"
    records["domain_label"] = "Computer Science"
    records["c_use"] = pd.to_numeric(records["cited_by_count"], errors="coerce")
    records.loc[0, "ref_dois"] = ["10.1000/e2e.b"]
    records.loc[2, "ref_dois"] = ["10.1000/e2e.a"]
    records["n_ref_dois"] = records["ref_dois"].apply(len)

    cfg = PipelineConfig(
        use_local_baseline=True,
        ties_policy="closed_ge",
        k_window=5,
        crosswalk_status="not_populated",
    )
    out = tmp_path / "e2e_out.xlsx"
    run_offline_metrics_export(records, out, config=cfg, input_path=str(fixture))

    assert out.exists()
    xl = pd.ExcelFile(out)
    expected_sheets = [
        safe_sheet_name(SHEET_RECORDS),
        safe_sheet_name(SHEET_EDGES),
        safe_sheet_name(SHEET_NETWORK),
        safe_sheet_name(SHEET_SUMMARY_INT),
        safe_sheet_name(SHEET_SUMMARY_FRAC),
        safe_sheet_name(SHEET_GLOBALS),
        safe_sheet_name(SHEET_RUN_META),
    ]
    for sheet in expected_sheets:
        assert sheet in xl.sheet_names, f"missing sheet {sheet}"
    assert xl.sheet_names == expected_sheets

    rec = xl.parse("Records+Metrics")
    for col in schema_spec["records_columns"]:
        assert col in rec.columns, f"missing column {col}"
    assert len(rec) == 3
    assert rec["cf"].notna().all()

    meta = xl.parse("Run Metadata")
    meta_map = dict(zip(meta["key"], meta["value"]))
    for key in schema_spec["metadata_keys"]:
        assert key in meta_map, f"missing metadata key {key}"
    assert meta_map["config.baseline_mode"] == "local"
    assert meta_map["config.crosswalk_status"] == "not_populated"

    edges = xl.parse("Edges")
    assert len(edges) >= 1
