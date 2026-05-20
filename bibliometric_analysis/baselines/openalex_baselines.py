"""OpenAlex citation-count baseline distributions (histogram / group_by / sweep)."""

from __future__ import annotations

import concurrent.futures
import json
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from bibliometric_analysis.baselines.histograms import (
    baseline_errors_from_hist,
    mean_from_hist,
    quantile_from_hist,
)
from bibliometric_analysis.core.config import BASELINE_BOOTSTRAP_B
from bibliometric_analysis.metrics.percentiles import compute_ppx

DEFAULT_BASE = "https://api.openalex.org"
DEFAULT_SLEEP = 0.2


def group_by_paged(
    filter_str: str,
    mailto: str,
    *,
    http_get: Callable,
    base_url: str = DEFAULT_BASE,
    sleep: float = DEFAULT_SLEEP,
) -> dict:
    params = {"filter": filter_str, "group_by": "cited_by_count", "per_page": 200, "cursor": "*"}
    counts, total = {}, 0
    while True:
        j2 = http_get(f"{base_url}/works", params=params, mailto=mailto)
        gb = (j2.get("group_by") or []) if isinstance(j2, dict) else []
        for g in gb:
            try:
                k = int(g.get("key", 0))
                v = int(g.get("count", 0))
            except Exception:
                continue
            counts[k] = counts.get(k, 0) + v
            total += v
        nxt = (j2.get("meta") or {}).get("next_cursor") if isinstance(j2, dict) else None
        if not nxt:
            break
        params["cursor"] = nxt
        time.sleep(sleep)
    return {"counts": counts, "N": total, "complete": True}


def try_histogram(
    domain_id: str,
    year: int,
    mailto: str,
    types_filter: Optional[Set[str]],
    *,
    http_get: Callable,
    base_url: str = DEFAULT_BASE,
    sleep: float = DEFAULT_SLEEP,
) -> dict | None:
    filter_str = f"from_publication_date:{year}-01-01,to_publication_date:{year}-12-31,concepts.id:{domain_id}"
    if types_filter:
        filter_str += "," + ",".join(f"type:{t}" for t in types_filter)
    j = http_get(
        f"{base_url}/works",
        params={"filter": filter_str, "histogram": "cited_by_count"},
        mailto=mailto,
    )
    if isinstance(j, dict) and j.get("histograms"):
        h = j["histograms"][0].get("buckets") or []
        counts, total = {}, 0
        for b in h:
            k = int(b["key"])
            v = int(b["count"])
            counts[k] = counts.get(k, 0) + v
            total += v
        return {"counts": counts, "N": total, "complete": True}
    result = group_by_paged(filter_str, mailto, http_get=http_get, base_url=base_url, sleep=sleep)
    if result.get("N", 0) == 0:
        return None
    return result


def sweep_full_distribution(
    domain_id: str,
    year: int,
    mailto: str,
    types_filter: Optional[Set[str]],
    max_pages: int,
    *,
    http_get: Callable,
    base_url: str = DEFAULT_BASE,
    sleep: float = DEFAULT_SLEEP,
) -> dict:
    filter_str = (
        f"from_publication_date:{year}-01-01,"
        f"to_publication_date:{year}-12-31,concepts.id:{domain_id}"
    )
    if types_filter:
        filter_str += "," + ",".join(f"type:{t}" for t in types_filter)

    params = {"filter": filter_str, "per_page": 200, "cursor": "*"}
    counts: Dict[int, int] = {}
    total = 0
    pages = 0

    while True:
        j = http_get(f"{base_url}/works", params=params, mailto=mailto)
        if isinstance(j, dict) and j.get("_status") == 404:
            break
        results = (j.get("results") or []) if isinstance(j, dict) else []
        for w in results:
            try:
                c = int(w.get("cited_by_count") or 0)
            except Exception:
                c = 0
            counts[c] = counts.get(c, 0) + 1
            total += 1
        pages += 1
        nxt = (j.get("meta") or {}).get("next_cursor") if isinstance(j, dict) else None
        if not nxt or pages >= max_pages:
            break
        params["cursor"] = nxt
        time.sleep(sleep)

    return {"counts": counts, "N": total, "complete": False, "pages": pages}


def global_distribution(
    domain_id: str,
    year: int,
    mailto: str,
    types_filter: Optional[Set[str]],
    prefer_histogram: bool,
    max_pages: int,
    *,
    ties_policy: str,
    http_get: Callable,
    base_url: str = DEFAULT_BASE,
    sleep: float = DEFAULT_SLEEP,
) -> dict:
    info = None
    if prefer_histogram:
        info = try_histogram(
            domain_id, year, mailto, types_filter,
            http_get=http_get, base_url=base_url, sleep=sleep,
        )
    if info is None:
        info = sweep_full_distribution(
            domain_id, year, mailto, types_filter, max_pages,
            http_get=http_get, base_url=base_url, sleep=sleep,
        )

    counts = info["counts"]
    if not counts or sum(counts.values()) == 0:
        return {
            "counts": {},
            "N": 0,
            "complete": bool(info.get("complete", False)),
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
        "complete": bool(info.get("complete", False)),
        "mean": float(mean_from_hist(keys, freqs)),
        "q75": float(quantile_from_hist(keys, freqs, 0.75, method=quant_method)),
        "q90": float(quantile_from_hist(keys, freqs, 0.90, method=quant_method)),
        "q99": float(quantile_from_hist(keys, freqs, 0.99, method=quant_method)),
    }


def make_local_globals_from_df(
    records: pd.DataFrame,
    by_cols=("domain_id", "year"),
    score_col: str = "c_use",
    ties_policy: str = "closed_ge",
) -> pd.DataFrame:
    df = records.copy()
    score = pd.to_numeric(df.get(score_col), errors="coerce")
    df["_score_"] = score

    g = df.groupby(list(by_cols), dropna=False)["_score_"]
    c0 = g.mean().rename("c0_mean").reset_index()
    n = g.count().rename("c0_n").reset_index()

    t25 = compute_ppx(df, "_score_", by=list(by_cols), p=0.75, ties=">=threshold")[
        list(by_cols) + ["ppx_threshold"]
    ]
    t25 = t25.drop_duplicates(subset=list(by_cols)).rename(columns={"ppx_threshold": "thr_top25"})
    t10 = compute_ppx(df, "_score_", by=list(by_cols), p=0.90, ties=">=threshold")[
        list(by_cols) + ["ppx_threshold"]
    ]
    t10 = t10.drop_duplicates(subset=list(by_cols)).rename(columns={"ppx_threshold": "thr_top10"})
    t01 = compute_ppx(df, "_score_", by=list(by_cols), p=0.99, ties=">=threshold")[
        list(by_cols) + ["ppx_threshold"]
    ]
    t01 = t01.drop_duplicates(subset=list(by_cols)).rename(columns={"ppx_threshold": "thr_top1"})

    out = c0.merge(n, on=list(by_cols), how="outer")
    out = out.merge(t25, on=list(by_cols), how="outer")
    out = out.merge(t10, on=list(by_cols), how="outer")
    out = out.merge(t01, on=list(by_cols), how="outer")

    out["c0_complete"] = True
    out["c0_counts_json"] = ""
    out["err_c0_pct"] = out["err_thr25_pct"] = out["err_thr10_pct"] = out["err_thr1_pct"] = np.nan
    out["quantile_method"] = "linear"
    tie_map = {"open_gt": ">threshold", "closed_ge": ">=threshold", "hazen": ">=threshold"}
    out["ties_policy"] = tie_map.get(ties_policy, ">=threshold")

    cols = [
        "domain_id", "year", "c0_mean", "thr_top1", "thr_top10", "thr_top25",
        "c0_n", "c0_complete", "c0_counts_json",
        "err_c0_pct", "err_thr25_pct", "err_thr10_pct", "err_thr1_pct",
        "quantile_method", "ties_policy",
    ]
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out[cols]


def compute_global_baselines_and_thresholds(
    records: pd.DataFrame,
    mailto: str,
    target_pairs: List[Tuple[str, int]],
    types_filter: Optional[Set[str]],
    prefer_histogram: bool,
    workers: int,
    max_pages: int,
    *,
    ties_policy: str,
    http_get: Callable,
    bootstrap_b: int = BASELINE_BOOTSTRAP_B,
    base_url: str = DEFAULT_BASE,
    sleep: float = DEFAULT_SLEEP,
) -> pd.DataFrame:
    required_cols = [
        "domain_id", "year", "c0_mean", "thr_top1", "thr_top10", "thr_top25",
        "c0_n", "c0_complete", "c0_counts_json",
        "err_c0_pct", "err_thr25_pct", "err_thr10_pct", "err_thr1_pct",
        "quantile_method", "ties_policy",
    ]

    if target_pairs:
        seen, dedup = set(), []
        for dom, yr in target_pairs:
            key = (str(dom), int(yr))
            if key not in seen:
                seen.add(key)
                dedup.append(key)
        target_pairs = dedup

    if not target_pairs:
        return pd.DataFrame(columns=required_cols)

    quant_method = "hazen" if ties_policy == "hazen" else "cdf_min"

    def work(pair: Tuple[str, int]) -> Optional[Dict[str, object]]:
        dom, yr = pair
        d = global_distribution(
            dom, yr, mailto, types_filter, prefer_histogram, max_pages,
            ties_policy=ties_policy, http_get=http_get, base_url=base_url, sleep=sleep,
        )
        if not d or int(d.get("N", 0)) == 0:
            return None
        counts_dict = d["counts"]
        values = np.array(sorted(counts_dict.keys()), dtype=float)
        counts = np.array([counts_dict[int(k)] for k in values], dtype=float)
        errs = baseline_errors_from_hist(
            values, counts, p_list=[0.75, 0.90, 0.99],
            method=quant_method, B=bootstrap_b,
        )
        return {
            "domain_id": str(dom),
            "year": int(yr),
            "c0_mean": float(mean_from_hist(values, counts)),
            "c0_n": int(d.get("N", int(counts.sum()))),
            "c0_complete": bool(d.get("complete", False)),
            "thr_top25": float(quantile_from_hist(values, counts, 0.75, method=quant_method)),
            "thr_top10": float(quantile_from_hist(values, counts, 0.90, method=quant_method)),
            "thr_top1": float(quantile_from_hist(values, counts, 0.99, method=quant_method)),
            "c0_counts_json": json.dumps({int(k): int(v) for k, v in counts_dict.items()}, ensure_ascii=False),
            "err_c0_pct": float(errs.get("err_c0_pct", np.nan)),
            "err_thr25_pct": float(errs.get("err_thr_75_pct", np.nan)),
            "err_thr10_pct": float(errs.get("err_thr_90_pct", np.nan)),
            "err_thr1_pct": float(errs.get("err_thr_99_pct", np.nan)),
            "quantile_method": quant_method,
            "ties_policy": ties_policy,
        }

    rows: List[Dict[str, object]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(work, target_pairs):
            if res is not None:
                rows.append(res)

    if not rows:
        return pd.DataFrame(columns=required_cols)

    df = pd.DataFrame(rows)
    for c in required_cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df[required_cols]
