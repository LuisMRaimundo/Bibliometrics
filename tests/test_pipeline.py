"""Pipeline module tests (offline / mocked online)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bibliometric_analysis.core.config import PipelineConfig
from bibliometric_analysis.core.inputs import parse_input, target_pairs_from_corpus
from bibliometric_analysis.core.pipeline import run_online_pipeline
from bibliometric_analysis.core.summaries import build_integer_summary
from bibliometric_analysis.dashboard.runner import build_pipeline_config, run_pipeline_from_upload


def test_parse_input_wos_fixture():
    path = Path(__file__).parent / "fixtures" / "minimal_wos.txt"
    df = parse_input(path, source="wos")
    assert len(df) >= 1
    assert "doi" in df.columns


def test_target_pairs_from_corpus():
    corpus = pd.DataFrame({"domain_id": ["C1", "C1"], "year": [2020, 2020]})
    pairs = target_pairs_from_corpus(corpus)
    assert pairs == [("C1", 2020)]


def test_build_integer_summary():
    df = pd.DataFrame({
        "idx": [0, 1],
        "domain_label": ["CS", "CS"],
        "domain_id": ["C1", "C1"],
        "year": [2020, 2020],
        "cf": [1.0, 2.0],
        "PPg_top1": [0, 1],
        "PPg_top10": [1, 1],
        "PPg_top25": [1, 1],
        "c_use": [5, 10],
        "c0_mean": [5, 5],
    })
    s = build_integer_summary(df, bootstrap_b=50)
    assert "MNCS" in s.columns


def test_run_online_pipeline_mocked(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "minimal_wos.txt"
    corpus = pd.DataFrame({
        "idx": [0],
        "title": ["T"],
        "year": [2020],
        "doi": ["10.1/x"],
        "domain_id": ["C1"],
        "domain_label": ["CS"],
        "cited_by_count": [5],
        "c_use": [5],
        "is_retracted": [False],
        "ref_dois": [[]],
        "referenced_works": [[]],
        "oa_id": ["W1"],
        "is_focal": [True],
    })

    monkeypatch.setattr(
        "bibliometric_analysis.core.pipeline.build_corpus",
        lambda *a, **k: corpus.copy(),
    )
    monkeypatch.setattr(
        "bibliometric_analysis.core.pipeline.parse_input",
        lambda *a, **k: pd.DataFrame({"doi": ["10.1/x"], "title": ["T"], "year": [2020]}),
    )

    out = tmp_path / "out.xlsx"
    result = run_online_pipeline(fixture, out, config=PipelineConfig(), mailto="t@example.com", expand=False)
    assert out.exists()
    assert "records" in result


def test_runner_offline_upload(tmp_path):
    csv = Path(__file__).parent / "fixtures" / "minimal_openalex.csv"
    result = run_pipeline_from_upload(
        csv.read_bytes(),
        "minimal_openalex.csv",
        tmp_path,
        offline=True,
        source="openalex",
    )
    assert (tmp_path / "minimal_openalex_metrics_pro.xlsx").exists()
    assert "records" in result


def test_build_pipeline_config_crosswalk_status():
    cfg = build_pipeline_config()
    assert cfg.crosswalk_status in ("not_populated", "partial", "populated")
