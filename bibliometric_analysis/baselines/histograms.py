"""Citation-count histogram baseline statistics (c₀, quantile thresholds)."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

DEFAULT_BOOTSTRAP_B = 800


def mean_from_hist(values: np.ndarray, counts: np.ndarray) -> float:
    total = counts.sum()
    if total == 0:
        return np.nan
    return float((values * counts).sum() / total)


def quantile_from_hist(
    values: np.ndarray,
    counts: np.ndarray,
    p: float,
    method: str = "cdf_min",
) -> float:
    assert len(values) == len(counts)
    n = int(counts.sum())
    if n == 0:
        return np.nan
    cum = np.cumsum(counts)
    if method == "hazen":
        target = p * n + 0.5
        idx = np.searchsorted(cum, target, side="left")
    else:  # cdf_min
        target = p * n
        idx = np.searchsorted(cum, target, side="left")
    idx = min(idx, len(values) - 1)
    return float(values[idx])


def baseline_errors_from_hist(
    values: np.ndarray,
    counts: np.ndarray,
    p_list: List[float],
    method: str = "cdf_min",
    B: int = DEFAULT_BOOTSTRAP_B,
    random_state: int = 42,
) -> Dict[str, float]:
    rng = np.random.default_rng(random_state)
    n = int(counts.sum())
    if n == 0:
        out: Dict[str, float] = {"err_c0_pct": np.nan}
        for p in p_list:
            out[f"err_thr_{int(p * 100)}_pct"] = np.nan
        return out

    probs = counts / n
    c0_hat = mean_from_hist(values, counts)
    thr_hat = {p: quantile_from_hist(values, counts, p, method=method) for p in p_list}

    c0_boot = np.empty(B, dtype=float)
    thr_boot = {p: np.empty(B, dtype=float) for p in p_list}

    for b in range(B):
        boot_counts = rng.multinomial(n, probs)
        c0_boot[b] = mean_from_hist(values, boot_counts)
        for p in p_list:
            thr_boot[p][b] = quantile_from_hist(values, boot_counts, p, method=method)

    eps = 1e-12
    out = {"err_c0_pct": float(np.std(c0_boot, ddof=1) / max(abs(c0_hat), eps) * 100.0)}
    for p in p_list:
        denom = max(abs(thr_hat[p]), eps)
        out[f"err_thr_{int(p * 100)}_pct"] = float(np.std(thr_boot[p], ddof=1) / denom * 100.0)
    return out


def distribution_from_counts(
    counts: dict[int, int],
    *,
    ties_policy: str = "closed_ge",
) -> dict:
    """Compute mean and top-percentile thresholds from a discrete count dict."""
    if not counts or sum(counts.values()) == 0:
        return {
            "counts": {},
            "N": 0,
            "complete": False,
            "mean": np.nan,
            "q75": np.nan,
            "q90": np.nan,
            "q99": np.nan,
        }

    keys = np.array(sorted(counts.keys()), dtype=float)
    freqs = np.array([counts[int(k)] for k in keys], dtype=float)
    quant_method = "hazen" if ties_policy == "hazen" else "cdf_min"

    return {
        "counts": {int(k): int(v) for k, v in counts.items()},
        "N": int(freqs.sum()),
        "complete": True,
        "mean": float(mean_from_hist(keys, freqs)),
        "q75": float(quantile_from_hist(keys, freqs, 0.75, method=quant_method)),
        "q90": float(quantile_from_hist(keys, freqs, 0.90, method=quant_method)),
        "q99": float(quantile_from_hist(keys, freqs, 0.99, method=quant_method)),
    }
