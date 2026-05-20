from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

TiesPolicy = Literal[">=threshold", ">threshold"]


def _pp_col_name(p: float) -> str:
    top_pct = (1.0 - p) * 100.0
    if abs(top_pct - round(top_pct)) < 1e-12:
        top_str = str(int(round(top_pct)))
    else:
        top_str = f"{top_pct:.1f}".rstrip("0").rstrip(".")
    return f"pp{top_str}"


def compute_ppx(
    df: pd.DataFrame,
    score_col: str,
    by=None,
    p: float = 0.90,
    ties: TiesPolicy = ">=threshold",
) -> pd.DataFrame:
    if by is None:
        by = []
    if not 0.0 < p <= 1.0:
        raise ValueError("p must be in (0,1].")
    if ties not in (">=threshold", ">threshold"):
        raise ValueError('ties must be one of {">=threshold", ">threshold"}.')
    if score_col not in df.columns:
        raise KeyError(f"score_col '{score_col}' not found in DataFrame.")
    out = df.copy()
    scores = pd.to_numeric(out[score_col], errors="coerce")
    out["_score_numeric_"] = scores
    if by:
        grp = out.groupby(by, dropna=False)
        thresholds = grp["_score_numeric_"].transform(
            lambda s: s.dropna().quantile(p, interpolation="linear") if s.notna().any() else np.nan
        )
    else:
        val = scores.dropna().quantile(p, interpolation="linear") if scores.notna().any() else np.nan
        thresholds = pd.Series(np.full(len(out), val), index=out.index)
    out["ppx_threshold"] = thresholds
    flag = (
        (out["_score_numeric_"] >= out["ppx_threshold"])
        if ties == ">=threshold"
        else (out["_score_numeric_"] > out["ppx_threshold"])
    ).astype("Int64")
    flag = flag.fillna(0).astype(int)
    pp_col = _pp_col_name(p)
    out[pp_col] = flag
    out.drop(columns=["_score_numeric_"], inplace=True)
    return out
