"""Dashboard helpers (import-safe; no Streamlit)."""

from .data import get_sheet, load_excel_data, load_var_records_any
from .metrics import agg_mncs_pp, compute_dashboard_metrics, ensure_min_metrics, summarize_unit
from .qa import as_binary_int, compute_goldset_qa, read_gold_csv
from .sensitivity import compute_sensitivity_table, norm_key, resolve_unit_col

__all__ = [
    "load_excel_data",
    "get_sheet",
    "load_var_records_any",
    "agg_mncs_pp",
    "ensure_min_metrics",
    "summarize_unit",
    "compute_dashboard_metrics",
    "resolve_unit_col",
    "norm_key",
    "compute_sensitivity_table",
    "read_gold_csv",
    "as_binary_int",
    "compute_goldset_qa",
]
