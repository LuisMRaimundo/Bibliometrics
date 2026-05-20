"""Excel export with stable sheet names."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from bibliometric_analysis.export.schemas import (
    RECORDS_CORE_COLUMNS,
    SHEET_EDGES,
    SHEET_GLOBALS,
    SHEET_NETWORK,
    SHEET_RECORDS,
    SHEET_RUN_META,
    SHEET_SUMMARY_FRAC,
    SHEET_SUMMARY_INT,
)

INVALID_XLS_SHEETCHARS = re.compile(r"[\[\]\:\*\?\/\\]")


def safe_sheet_name(name: str, max_len: int = 31) -> str:
    name = INVALID_XLS_SHEETCHARS.sub(" ", str(name)).strip()
    return (name[:max_len] or "Sheet1")


def summarize_by_unit(df: pd.DataFrame, unit_col: str) -> pd.DataFrame:
    x = df[~df.get("is_retracted", False).fillna(False)].copy()
    for c in ("PPg_top10", "PPg_top1", "cf", "c_use"):
        if c not in x.columns:
            x[c] = pd.NA
    g = x.groupby(unit_col, dropna=False)
    out = pd.DataFrame(
        {
            unit_col: g.size().index,
            "n_docs": g.size().values,
            "mncs": g["cf"].mean().values,
            "pp10_share": g["PPg_top10"].mean().values,
            "pp1_share": g["PPg_top1"].mean().values,
            "c_use_sum": g["c_use"].sum().values,
        }
    )
    out["pp10_share"] = (100 * out["pp10_share"]).round(1)
    out["pp1_share"] = (100 * out["pp1_share"]).round(1)
    out["mncs"] = out["mncs"].round(3)
    out = out.sort_values(
        ["mncs", "pp10_share", "c_use_sum", "n_docs"],
        ascending=[False, False, False, False],
        ignore_index=True,
    )
    return out


def export_excel(
    records: pd.DataFrame,
    edges: pd.DataFrame,
    net_metrics: pd.DataFrame,
    s_int: pd.DataFrame,
    s_frac: pd.DataFrame,
    globals_df: pd.DataFrame,
    runmeta: pd.DataFrame,
    out_path: Path | str,
) -> None:
    out_path = Path(out_path)
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as xw:
        cols = [c for c in RECORDS_CORE_COLUMNS if c in records.columns]
        records[cols].to_excel(xw, sheet_name=safe_sheet_name(SHEET_RECORDS), index=False)
        edges.to_excel(xw, sheet_name=safe_sheet_name(SHEET_EDGES), index=False)
        net_metrics.to_excel(xw, sheet_name=safe_sheet_name(SHEET_NETWORK), index=False)
        s_int.to_excel(xw, sheet_name=safe_sheet_name(SHEET_SUMMARY_INT), index=False)
        s_frac.to_excel(xw, sheet_name=safe_sheet_name(SHEET_SUMMARY_FRAC), index=False)
        globals_df.to_excel(xw, sheet_name=safe_sheet_name(SHEET_GLOBALS), index=False)
        runmeta.to_excel(xw, sheet_name=safe_sheet_name(SHEET_RUN_META), index=False)
