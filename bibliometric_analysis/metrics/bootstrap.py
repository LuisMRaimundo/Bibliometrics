"""Bootstrap confidence intervals for MNCS."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd


def bootstrap_mncs_with_c0(df_group: pd.DataFrame, B: int = 1000) -> tuple[float, float, float]:
    g = df_group.dropna(subset=["c_use", "c0_mean"])
    if g.empty:
        return (np.nan, np.nan, np.nan)
    c0 = float(g["c0_mean"].iloc[0])
    c0_complete = bool(g["c0_complete"].iloc[0]) if "c0_complete" in g.columns else False
    c_vals = pd.to_numeric(g["c_use"], errors="coerce").fillna(0).to_numpy(dtype=float)
    n = len(c_vals)

    counts: dict = {}
    if "c0_counts_json" in g.columns and isinstance(g["c0_counts_json"].iloc[0], str):
        try:
            counts = json.loads(g["c0_counts_json"].iloc[0] or "{}")
        except Exception:
            counts = {}

    if counts:
        k_vals = np.array([int(k) for k in counts.keys()], dtype=float)
        w_vals = np.array([int(counts[str(int(k))]) for k in k_vals], dtype=float)
        p_vals = w_vals / w_vals.sum()
    else:
        k_vals = np.array([], dtype=float)
        p_vals = np.array([], dtype=float)

    rng = np.random.default_rng(12345)
    boots = np.empty(B, dtype=float)
    for _ in range(B):
        idx = rng.integers(0, n, size=n)
        num = float(np.mean(c_vals[idx]))
        if c0_complete or p_vals.size == 0:
            den = c0
        else:
            m = int(min(10000, int(w_vals.sum()) if counts else 0) or 0)
            if m <= 0:
                den = c0
            else:
                draw_idx = rng.choice(len(k_vals), size=m, replace=True, p=p_vals)
                den = float(np.mean(k_vals[draw_idx])) if len(draw_idx) > 0 else c0
            if den <= 0:
                den = c0
        boots[_] = num / max(1e-12, den)
    mncs = float(np.mean(c_vals) / max(1e-12, c0))
    return (mncs, float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975)))
