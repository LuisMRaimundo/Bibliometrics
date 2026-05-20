"""Pipeline runner helpers (import-safe; no Streamlit)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from bibliometric_analysis.core.config import PipelineConfig
from bibliometric_analysis.core.pipeline import run_offline_metrics_export, run_online_pipeline
from bibliometric_analysis.ontology.crosswalk import report_mapping_status


def build_pipeline_config(
    *,
    ties_policy: str = "closed_ge",
    use_local_baseline: bool = True,
    k_window: int = 5,
    drop_self_citations: bool = True,
    drop_retracted: bool = True,
    concept_level: int = 1,
    prefer_histogram: bool = True,
    max_pages: int = 9999,
    types_filter: Optional[set[str]] = None,
    baseline_bootstrap_b: int = 800,
) -> PipelineConfig:
    status = report_mapping_status()
    crosswalk_status = "not_populated" if all(v in ("not_populated", "schema_only", "missing_file") for v in status.values()) else "partial"
    return PipelineConfig(
        ties_policy=ties_policy,
        use_local_baseline=use_local_baseline,
        k_window=k_window,
        drop_self_citations=drop_self_citations,
        drop_retracted=drop_retracted,
        concept_level=concept_level,
        prefer_histogram=prefer_histogram,
        max_pages=max_pages,
        types_filter=types_filter,
        baseline_bootstrap_b=baseline_bootstrap_b,
        crosswalk_status=crosswalk_status,
    )


def run_pipeline_from_upload(
    input_bytes: bytes,
    filename: str,
    out_dir: Path | str,
    *,
    offline: bool = True,
    source: str = "auto",
    mailto: str = "",
    config: Optional[PipelineConfig] = None,
    log: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Save uploaded bytes to a temp file and run offline or online pipeline.
    Offline mode skips OpenAlex corpus fetch (uses parsed records only).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    in_path = out_dir / filename
    in_path.write_bytes(input_bytes)
    out_path = out_dir / f"{in_path.stem}_metrics_pro.xlsx"
    cfg = config or build_pipeline_config()

    if offline:
        from bibliometric_analysis.core.inputs import parse_input
        records = parse_input(in_path, source=source)
        records["c_use"] = records.get("cited_by_count")
        if "domain_id" not in records.columns:
            records["domain_id"] = "unknown"
        if "domain_label" not in records.columns:
            records["domain_label"] = "unknown"
        return run_offline_metrics_export(records, out_path, config=cfg, input_path=str(in_path))

    return run_online_pipeline(
        in_path,
        out_path,
        config=cfg,
        source=source,
        mailto=mailto,
        expand=True,
        log=log,
    )
