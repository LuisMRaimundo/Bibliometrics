
import pandas as pd

from bibliometric_analysis.export.excel import export_excel
from bibliometric_analysis.export.metadata import build_run_metadata, config_hash
from bibliometric_analysis.export.schemas import ALL_SHEETS, SCHEMA_VERSION


def test_schema_version():
    assert SCHEMA_VERSION == "1.0"
    assert len(ALL_SHEETS) == 7


def test_config_hash_deterministic():
    c = {"ties": "closed_ge", "k": 5}
    assert config_hash(c) == config_hash(c)


def test_export_sheets(tmp_path):
    records = pd.DataFrame(
        {
            "idx": [0],
            "title": ["T"],
            "year": [2020],
            "domain_label": ["CS"],
            "domain_id": ["C1"],
            "doi": ["10.1/x"],
            "c_use": [5],
            "cf": [1.0],
            "PPg_top1": [0],
            "PPg_top10": [1],
            "PPg_top25": [1],
        }
    )
    edges = pd.DataFrame(columns=["citer_idx", "cited_idx"])
    meta = build_run_metadata(config={"k_window": 5})
    out = tmp_path / "out.xlsx"
    export_excel(records, edges, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), meta, out)
    xl = pd.ExcelFile(out)
    for s in ["Records+Metrics", "Edges", "Run Metadata"]:
        assert s in xl.sheet_names
