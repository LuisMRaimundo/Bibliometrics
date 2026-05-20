"""Integer and fractional summary tables for pipeline export."""

from __future__ import annotations

import numpy as np
import pandas as pd

from bibliometric_analysis.metrics.bootstrap import bootstrap_mncs_with_c0
from bibliometric_analysis.metrics.fractional import explode_multifield_fractional


def build_integer_summary(
    df_norm: pd.DataFrame,
    *,
    bootstrap_b: int = 800,
) -> pd.DataFrame:
    """Summary by domain_label × year with MNCS, PP shares, and bootstrap CI."""
    s_int = (
        df_norm.dropna(subset=["domain_label", "year"])
        .groupby(["domain_label", "year"], as_index=False)
        .agg(
            n=("idx", "count"),
            MNCS=("cf", "mean"),
            PP1=("PPg_top1", "mean"),
            PP10=("PPg_top10", "mean"),
            PP25=("PPg_top25", "mean"),
        )
    )
    rows = []
    for (dom, yr), g in df_norm.groupby(["domain_id", "year"]):
        _, lo, hi = bootstrap_mncs_with_c0(g, B=bootstrap_b)
        rows.append({"domain_id": dom, "year": int(yr), "MNCS_ci_low_boot": lo, "MNCS_ci_high_boot": hi})
    ci_df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["domain_id", "year", "MNCS_ci_low_boot", "MNCS_ci_high_boot"]
    )
    if s_int.empty:
        return s_int
    return (
        s_int.merge(
            df_norm[["domain_label", "domain_id", "year"]].drop_duplicates(),
            on=["domain_label", "year"],
            how="left",
        )
        .merge(ci_df, on=["domain_id", "year"], how="left")
        .drop(columns=["domain_id"])
        .drop_duplicates()
    )


def build_fractional_summary(df_norm: pd.DataFrame, *, level_weight: str = "equal") -> pd.DataFrame:
    """Fractional counting summary by domain_label × year."""
    frac = explode_multifield_fractional(df_norm, level_weight=level_weight)
    if frac.empty:
        return pd.DataFrame()
    frac = frac.copy()
    for col in ("w_total", "cf", "PPg_top1", "PPg_top10", "PPg_top25"):
        frac[col] = pd.to_numeric(frac.get(col), errors="coerce")

    def _agg_series(g: pd.DataFrame) -> pd.Series:
        w = pd.to_numeric(g["w_total"], errors="coerce")
        wsum = float(np.nansum(w))

        def wavg(x):
            x = pd.to_numeric(x, errors="coerce").to_numpy(dtype=float)
            w_ = w.to_numpy(dtype=float)
            m = np.isfinite(x) & np.isfinite(w_)
            if wsum <= 0 or not m.any():
                return np.nan
            return float(np.average(x[m], weights=w_[m]))

        return pd.Series({
            "w_sum": wsum,
            "MNCS_frac": wavg(g["cf"]),
            "PP1_frac": wavg(g["PPg_top1"]),
            "PP10_frac": wavg(g["PPg_top10"]),
            "PP25_frac": wavg(g["PPg_top25"]),
        })

    grp = frac.dropna(subset=["domain_label", "year"]).groupby(
        ["domain_label", "year"], as_index=False, group_keys=False
    )
    try:
        return grp.apply(_agg_series, include_groups=False).reset_index(drop=True)
    except TypeError:
        return grp.apply(_agg_series).reset_index(drop=True)
