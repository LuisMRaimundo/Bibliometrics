"""Excel loading helpers for the dashboard."""

from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import pandas as pd


def load_excel_data(xls_bytes: BinaryIO | bytes) -> dict[str, pd.DataFrame]:
    if isinstance(xls_bytes, bytes):
        xls_bytes = BytesIO(xls_bytes)
    xls = pd.ExcelFile(xls_bytes)
    return {name: xls.parse(name) for name in xls.sheet_names}


def get_sheet(sheets_dict: dict[str, pd.DataFrame], *candidates: str) -> pd.DataFrame | None:
    for name in candidates:
        sheet = sheets_dict.get(name)
        if sheet is not None:
            return sheet
    return None


def load_var_records_any(xls: pd.ExcelFile) -> tuple[pd.DataFrame | None, bool]:
    for cand in ["Records+Metrics", "Records + Metrics", "Records & Metrics", "RecordsMetrics"]:
        if cand in xls.sheet_names:
            return xls.parse(cand), True
    for cand in ["Records", "Sheet1", "works", "data"]:
        if cand in xls.sheet_names:
            return xls.parse(cand), False
    return None, False
