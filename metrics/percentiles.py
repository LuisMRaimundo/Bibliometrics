"""Backward-compatible re-export; canonical implementation in bibliometric_analysis."""

from bibliometric_analysis.metrics.percentiles import _pp_col_name, compute_ppx

__all__ = ["compute_ppx", "_pp_col_name"]
