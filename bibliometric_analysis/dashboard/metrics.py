"""Dashboard metric helpers backed by package percentiles."""

from __future__ import annotations

import pandas as pd

from bibliometric_analysis.metrics.percentiles import compute_ppx


def agg_mncs_pp(df: pd.DataFrame, unit_col: str, cf_col: str, pp_cols: list[str]) -> pd.DataFrame:
    g = df.groupby(unit_col, dropna=False)
    out = g[cf_col].mean().to_frame("MNCS")
    for c in pp_cols:
        if c in df.columns:
            out[c] = g[c].mean()
    return out.reset_index()


def summarize_unit(df: pd.DataFrame, unit_col: str) -> pd.DataFrame:
    x = df.copy()
    cf_col = "c_f" if "c_f" in x.columns else ("cf" if "cf" in x.columns else None)
    if cf_col is None:
        x["__cf__"] = pd.NA
        cf_col = "__cf__"
    x[cf_col] = pd.to_numeric(x[cf_col], errors="coerce")
    has_pp10 = "PPg_top10" in x.columns
    if has_pp10:
        x["PPg_top10"] = pd.to_numeric(x["PPg_top10"], errors="coerce")
    g = x.groupby(unit_col, dropna=False)
    mncs = g[cf_col].mean()
    out = pd.DataFrame({unit_col: mncs.index, "n_docs": g.size().values, "mncs": mncs.values})
    if has_pp10:
        out["pp10_share"] = (100.0 * g["PPg_top10"].mean()).values
        out["pp10_share"] = out["pp10_share"].round(1)
    out["mncs"] = out["mncs"].round(3)
    sort_cols = [c for c in ["mncs", "pp10_share", "n_docs"] if c in out.columns]
    return out.sort_values(sort_cols, ascending=[False] * len(sort_cols), ignore_index=True)


def ensure_min_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    has_pp10 = "PPg_top10" in out.columns
    has_mncs = ("c_f" in out.columns) or ("cf" in out.columns)
    score_col = "c_use_window" if "c_use_window" in out.columns else ("c_use" if "c_use" in out.columns else None)
    by = [c for c in ("year", "domain_label", "domain_id", "field", "concept_label", "concept_id") if c in out.columns]
    if not has_pp10 and score_col and by:
        tmp = compute_ppx(out, score_col=score_col, by=by[:2] or by, p=0.90, ties=">=threshold")
        pp_col = [c for c in tmp.columns if c.startswith("pp")][-1]
        out = tmp.rename(columns={pp_col: "PPg_top10"})
    if not has_mncs and ("c0_mean" in out.columns) and score_col:
        s = pd.to_numeric(out[score_col], errors="coerce")
        c0 = pd.to_numeric(out["c0_mean"], errors="coerce")
        out["c_f"] = (s / c0).where(c0 > 0)
    return out


def compute_dashboard_metrics(
    df_records: pd.DataFrame,
    df_global: pd.DataFrame | None = None,
    *,
    err_target: float = 5.0,
) -> dict:
    """Pure summary metrics for the overview tab."""
    n_docs = len(df_records) if df_records is not None else 0
    mncs_series = pd.to_numeric(
        df_records.get("c_f", df_records.get("cf", pd.Series(dtype="float"))),
        errors="coerce",
    )
    mncs = float(mncs_series.mean()) if mncs_series.notna().any() else float("nan")
    pp10 = pd.to_numeric(df_records.get("PPg_top10", pd.Series(dtype="float")), errors="coerce")
    pp10_share = float(100.0 * pp10.mean()) if len(pp10) else float("nan")

    err_cols = ["err_c0_pct", "err_thr25_pct", "err_thr10_pct", "err_thr1_pct"]
    err_vals = {c: float("nan") for c in err_cols}
    if df_global is not None and not df_global.empty:
        for c in err_cols:
            if c in df_global.columns:
                s = pd.to_numeric(df_global[c], errors="coerce")
                if s.notna().any():
                    err_vals[c] = float(s.mean())

    pp_realized = {}
    if all(pd.isna(v) for v in err_vals.values()):
        for col in ("PPg_top25", "PPg_top10", "PPg_top1"):
            if col in df_records.columns:
                s = pd.to_numeric(df_records[col], errors="coerce")
                if s.notna().any():
                    pp_realized[col] = 100.0 * float(s.mean())

    return {
        "n_docs": n_docs,
        "mncs": mncs,
        "pp10_share": pp10_share,
        "err_target": err_target,
        "err_vals": err_vals,
        "pp_realized": pp_realized,
    }
