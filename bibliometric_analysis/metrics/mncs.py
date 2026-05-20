"""MNCS (cf) and global PP top 25/10/1% flag computation."""

from __future__ import annotations

import numpy as np
import pandas as pd

TIES_POLICY_CLOSED = "closed_ge"
TIES_POLICY_OPEN = "open_gt"


def pp_flag(c_use: float, thr: float, ties_policy: str) -> int | float:
    if pd.isna(c_use) or pd.isna(thr):
        return np.nan
    if ties_policy == TIES_POLICY_OPEN:
        return int(c_use > thr)
    return int(c_use >= thr)


def effective_citation_count(df: pd.DataFrame) -> pd.Series:
    """Return c_use_window when present, else c_use."""
    if "c_use_window" in df.columns:
        cwin = pd.to_numeric(df["c_use_window"], errors="coerce")
        cuse = pd.to_numeric(df.get("c_use"), errors="coerce")
        return cwin.where(cwin.notna(), cuse)
    return pd.to_numeric(df.get("c_use"), errors="coerce")


def add_cf_and_pp_global(
    df: pd.DataFrame,
    globals_df: pd.DataFrame,
    *,
    ties_policy: str = TIES_POLICY_CLOSED,
) -> pd.DataFrame:
    """
    Apply global baseline by domain×year and compute:
      - cf = c_use_eff / c0_mean
      - PPg_top{25,10,1} flags
    """
    req = [
        "domain_id",
        "year",
        "c0_mean",
        "thr_top1",
        "thr_top10",
        "thr_top25",
        "c0_n",
        "c0_complete",
        "c0_counts_json",
    ]

    if globals_df is None or (not isinstance(globals_df, pd.DataFrame)):
        globals_df = pd.DataFrame(columns=req)
    else:
        missing = [c for c in req if c not in globals_df.columns]
        for c in missing:
            globals_df[c] = pd.NA
        globals_df = globals_df[req]

    if globals_df.empty:
        out = df.copy()
        for c in [
            "c0_mean",
            "thr_top1",
            "thr_top10",
            "thr_top25",
            "c0_n",
            "c0_complete",
            "c0_counts_json",
        ]:
            if c not in out.columns:
                out[c] = pd.NA
        out["cf"] = pd.NA
        for col in ["PPg_top1", "PPg_top10", "PPg_top25"]:
            out[col] = pd.NA
        return out

    out = df.merge(globals_df, on=["domain_id", "year"], how="left", validate="m:1")
    cu = effective_citation_count(out)
    out["c_use"] = cu

    c0m = pd.to_numeric(out.get("c0_mean"), errors="coerce")
    mask_cf = cu.notna() & c0m.notna() & (c0m > 0)
    out["cf"] = np.nan
    out.loc[mask_cf, "cf"] = (cu[mask_cf] / c0m[mask_cf]).astype(float)

    thr25 = pd.to_numeric(out.get("thr_top25"), errors="coerce")
    thr10 = pd.to_numeric(out.get("thr_top10"), errors="coerce")
    thr1 = pd.to_numeric(out.get("thr_top1"), errors="coerce")

    out["PPg_top25"] = [pp_flag(c, t, ties_policy) for c, t in zip(cu, thr25)]
    out["PPg_top10"] = [pp_flag(c, t, ties_policy) for c, t in zip(cu, thr10)]
    out["PPg_top1"] = [pp_flag(c, t, ties_policy) for c, t in zip(cu, thr1)]

    out["PPg_top25"] = out["PPg_top25"].astype("Int64")
    out["PPg_top10"] = out["PPg_top10"].astype("Int64")
    out["PPg_top1"] = out["PPg_top1"].astype("Int64")
    return out
