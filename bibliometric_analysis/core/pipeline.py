"""Full analysis pipeline: parse → corpus → metrics → export."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from bibliometric_analysis.baselines.openalex_baselines import (
    compute_global_baselines_and_thresholds,
    make_local_globals_from_df,
)
from bibliometric_analysis.core.config import PipelineConfig
from bibliometric_analysis.core.inputs import parse_input, target_pairs_from_corpus
from bibliometric_analysis.core.summaries import build_fractional_summary, build_integer_summary
from bibliometric_analysis.corpus.build import build_corpus, ensure_idx
from bibliometric_analysis.export.excel import export_excel
from bibliometric_analysis.export.metadata import build_run_metadata
from bibliometric_analysis.metrics.mncs import add_cf_and_pp_global
from bibliometric_analysis.network.build import build_edges_by_doi
from bibliometric_analysis.network.metrics import community_detection
from bibliometric_analysis.openalex.client import http_get


def _safe_mean(df: pd.DataFrame, col: str) -> float:
    if col in df.columns:
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().any():
            return float(s.mean())
    return float("nan")


def run_metrics_export(
    records: pd.DataFrame,
    out_path: Path | str,
    *,
    config: Optional[PipelineConfig] = None,
    globals_df: Optional[pd.DataFrame] = None,
    input_path: Optional[str] = None,
    mailto: str = "",
    comm_algo: str = "greedy",
    comm_gamma: float = 1.0,
    comm_seed: int = 42,
    comm_n_runs: int = 5,
    level_weight: str = "equal",
    optional_deps: Optional[dict[str, bool]] = None,
) -> dict:
    """Apply baselines, MNCS/PP, network, summaries, and export Excel."""
    cfg = config or PipelineConfig()
    rec = ensure_idx(records.copy())

    if globals_df is None and cfg.use_local_baseline:
        globals_df = make_local_globals_from_df(rec, ties_policy=cfg.ties_policy)
    elif globals_df is None:
        globals_df = pd.DataFrame()

    rec = add_cf_and_pp_global(rec, globals_df, ties_policy=cfg.ties_policy)
    edges = build_edges_by_doi(rec)
    net = community_detection(rec, edges, comm_algo, comm_gamma, comm_seed, comm_n_runs) if not edges.empty else pd.DataFrame()

    s_int = build_integer_summary(rec, bootstrap_b=cfg.baseline_bootstrap_b)
    s_frac = build_fractional_summary(rec, level_weight=level_weight)

    meta_cfg = {
        "baseline_mode": "local" if cfg.use_local_baseline else "global",
        "ties_policy": cfg.ties_policy,
        "k_window": cfg.k_window,
        "self_citation_excluded": cfg.drop_self_citations,
        "retractions_excluded": cfg.drop_retracted,
        "concept_level": cfg.concept_level,
        "crosswalk_status": cfg.crosswalk_status,
        "quantile_method": "cdf_min" if cfg.ties_policy != "hazen" else "hazen",
        "communities_algo": comm_algo,
        "gamma": comm_gamma,
        "seed": comm_seed,
        "level_weight": level_weight,
        "mailto": mailto,
        "prefer_histogram": cfg.prefer_histogram,
        "max_pages_fallback": cfg.max_pages,
        "baseline_error_c0_pct": _safe_mean(globals_df, "err_c0_pct"),
        "baseline_error_thr25_pct": _safe_mean(globals_df, "err_thr25_pct"),
        "baseline_error_thr10_pct": _safe_mean(globals_df, "err_thr10_pct"),
        "baseline_error_thr1_pct": _safe_mean(globals_df, "err_thr1_pct"),
    }
    meta_cfg.update(cfg.extra)
    runmeta = build_run_metadata(config=meta_cfg, input_path=input_path, optional_deps=optional_deps)

    export_excel(rec, edges, net, s_int, s_frac, globals_df, runmeta, out_path)
    return {
        "records": rec,
        "edges": edges,
        "net_metrics": net,
        "globals": globals_df,
        "summary_int": s_int,
        "summary_frac": s_frac,
        "runmeta": runmeta,
    }


def run_offline_metrics_export(
    records: pd.DataFrame,
    out_path: Path | str,
    *,
    config: Optional[PipelineConfig] = None,
    globals_df: Optional[pd.DataFrame] = None,
    input_path: Optional[str] = None,
) -> dict:
    """Offline path: records already built; no OpenAlex corpus fetch."""
    return run_metrics_export(
        records, out_path, config=config, globals_df=globals_df, input_path=input_path,
        comm_algo="greedy",
    )


def run_online_pipeline(
    input_path: str | Path,
    out_path: str | Path | None = None,
    *,
    config: Optional[PipelineConfig] = None,
    source: str = "auto",
    mailto: str = "",
    expand: bool = True,
    http_get_fn: Callable = http_get,
    max_concurrent: int = 6,
    sleep: float = 0.2,
    base_url: str = "https://api.openalex.org",
    progress_iter=None,
    comm_algo: str = "auto",
    comm_gamma: float = 1.0,
    comm_seed: int = 42,
    comm_n_runs: int = 5,
    level_weight: str = "equal",
    global_workers: int = 3,
    log: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Full online pipeline: parse input → OpenAlex corpus → baselines → export.

    No Tkinter/Streamlit dependencies. Intended for GUI and Streamlit runners.
    """
    cfg = config or PipelineConfig()
    input_path = Path(input_path)
    out_path = Path(out_path) if out_path else input_path.with_name(f"{input_path.stem}_metrics_pro.xlsx")
    _log = log or (lambda _msg: None)

    _log(f"Parsing {source} input …")
    df_in = parse_input(input_path, source=source)
    _log(f"Records: {len(df_in)}; DOIs: {df_in['doi'].notna().sum()}")

    if cfg.k_window > 0 and not expand:
        _log("Warning: k>0 without expand → c_use uses total cited_by_count.")

    _log("Building corpus (OpenAlex) …")
    corpus = build_corpus(
        df_in,
        expand,
        mailto,
        cfg.concept_level,
        cfg.types_filter,
        cfg.k_window,
        cfg.drop_self_citations,
        cfg.drop_retracted,
        http_get=http_get_fn,
        max_concurrent=max_concurrent,
        sleep=sleep,
        base_url=base_url,
        progress_iter=progress_iter,
    )
    corpus = ensure_idx(corpus)

    if comm_algo == "auto":
        try:
            import igraph  # noqa: F401
            import leidenalg  # noqa: F401
            comm_algo = "leiden"
        except Exception:
            try:
                import community  # noqa: F401
                comm_algo = "louvain"
            except Exception:
                comm_algo = "greedy"

    globals_df: pd.DataFrame
    if cfg.use_local_baseline:
        _log("Local baselines from corpus …")
        globals_df = make_local_globals_from_df(corpus, ties_policy=cfg.ties_policy)
    else:
        _log("Global OpenAlex baselines …")
        pairs = target_pairs_from_corpus(corpus)
        if not pairs:
            _log("Warning: no (domain_id, year) pairs for global baselines.")
        globals_df = compute_global_baselines_and_thresholds(
            corpus,
            mailto,
            pairs,
            cfg.types_filter,
            cfg.prefer_histogram,
            global_workers,
            cfg.max_pages,
            ties_policy=cfg.ties_policy,
            http_get=http_get_fn,
            bootstrap_b=cfg.baseline_bootstrap_b,
            base_url=base_url,
            sleep=sleep,
        )

    _log("Computing MNCS/PP and exporting …")
    result = run_metrics_export(
        corpus,
        out_path,
        config=cfg,
        globals_df=globals_df,
        input_path=str(input_path),
        mailto=mailto,
        comm_algo=comm_algo,
        comm_gamma=comm_gamma,
        comm_seed=comm_seed,
        comm_n_runs=comm_n_runs,
        level_weight=level_weight,
    )
    result["out_path"] = out_path
    _log(f"Done: {out_path}")
    return result


def run_analysis(
    input_path_or_df: str | Path | pd.DataFrame,
    out_path: Path | str | None = None,
    *,
    config: Optional[PipelineConfig] = None,
    offline: bool = False,
    **kwargs,
) -> dict:
    """
    Unified pipeline entry point (online or offline).

    Accepts a file path (online by default) or a pre-built records DataFrame (offline).
    Additional kwargs are forwarded to ``run_online_pipeline`` or ``run_offline_metrics_export``.
    """
    if isinstance(input_path_or_df, pd.DataFrame):
        if out_path is None:
            raise ValueError("out_path is required when input is a DataFrame")
        return run_offline_metrics_export(input_path_or_df, out_path, config=config, **kwargs)
    if offline:
        from bibliometric_analysis.core.inputs import parse_input

        cfg = config or PipelineConfig()
        source = kwargs.pop("source", "auto")
        records = parse_input(input_path_or_df, source=source)
        if "c_use" not in records.columns and "cited_by_count" in records.columns:
            records["c_use"] = records["cited_by_count"]
        out = Path(out_path) if out_path else Path(input_path_or_df).with_name(
            f"{Path(input_path_or_df).stem}_metrics_pro.xlsx"
        )
        return run_offline_metrics_export(
            records, out, config=cfg, input_path=str(input_path_or_df), **kwargs
        )
    return run_online_pipeline(input_path_or_df, out_path, config=config, **kwargs)
