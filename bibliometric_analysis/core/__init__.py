from .config import DEFAULT_TIES_POLICY, PipelineConfig

__all__ = [
    "PipelineConfig",
    "DEFAULT_TIES_POLICY",
    "run_offline_metrics_export",
    "run_online_pipeline",
    "run_metrics_export",
    "run_analysis",
]


def __getattr__(name: str):
    if name in ("run_offline_metrics_export", "run_online_pipeline", "run_metrics_export", "run_analysis"):
        from . import pipeline
        return getattr(pipeline, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
