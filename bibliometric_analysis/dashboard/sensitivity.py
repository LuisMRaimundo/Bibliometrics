"""Sensitivity comparison helpers."""

from __future__ import annotations

import pandas as pd

from .metrics import summarize_unit

UNIT_SYNS = {
    "institution": [
        "institution", "instituição", "instituicao", "affiliation", "affiliations",
        "organization", "organisation", "org", "unit", "unit_name", "unit_id", "inst", "inst_name",
    ],
    "author": ["author", "authors", "autor", "autores"],
    "country": ["country", "país", "pais"],
}


def norm_key(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def resolve_unit_col(df: pd.DataFrame, canonical: str) -> str | None:
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    low = {c.lower(): c for c in cols}
    for cand in UNIT_SYNS.get(canonical, [canonical]):
        if cand in low:
            return low[cand]
    for c in cols:
        lc = c.lower()
        if any(sub in lc for sub in UNIT_SYNS.get(canonical, [canonical])):
            return c
    return None


def compute_sensitivity_table(
    baseline_records: pd.DataFrame,
    variant_records: pd.DataFrame,
    unit_canon: str,
) -> pd.DataFrame | None:
    base_col = resolve_unit_col(baseline_records, unit_canon)
    var_col = resolve_unit_col(variant_records, unit_canon)
    if not base_col or not var_col:
        return None

    base_sum = summarize_unit(baseline_records, base_col).rename(
        columns={base_col: unit_canon, "n_docs": "n_docs_base", "mncs": "mncs_base", "pp10_share": "pp10_base"}
    )
    base_sum[unit_canon] = norm_key(base_sum[unit_canon])

    var_sum = summarize_unit(variant_records, var_col).rename(
        columns={var_col: unit_canon, "n_docs": "n_docs_var", "mncs": "mncs_var", "pp10_share": "pp10_var"}
    )
    var_sum[unit_canon] = norm_key(var_sum[unit_canon])

    comp = base_sum.merge(var_sum, on=unit_canon, how="outer")
    comp["Δ_MNCS"] = comp["mncs_var"] - comp["mncs_base"]
    if "pp10_var" in comp.columns and "pp10_base" in comp.columns:
        comp["Δ_PP10 (pp)"] = comp["pp10_var"] - comp["pp10_base"]
    sort_cols = [c for c in ["Δ_MNCS", "Δ_PP10 (pp)"] if c in comp.columns]
    return comp.sort_values(sort_cols, ascending=[False] * len(sort_cols), na_position="last").reset_index(drop=True)
