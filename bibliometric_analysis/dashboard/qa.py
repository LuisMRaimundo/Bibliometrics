"""Gold-set QA helpers."""

from __future__ import annotations

import csv
import io

import pandas as pd


def read_gold_csv(data: bytes) -> pd.DataFrame:
    sample = data[:4096].decode("utf-8", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        sep = dialect.delimiter
    except Exception:
        sep = None
    bio = io.BytesIO(data)
    try:
        return pd.read_csv(bio, sep=sep, engine="python")
    except Exception:
        bio.seek(0)
        return pd.read_csv(bio, sep=sep or ",", engine="python", on_bad_lines="skip")


def as_binary_int(s: pd.Series) -> tuple[pd.Series, int]:
    if s.dtype == bool:
        return s.astype("Int64"), 0
    coerced = 0
    if s.dtype == "O":
        mapping = {
            "true": 1, "false": 0, "yes": 1, "no": 0, "y": 1, "n": 0, "t": 1, "f": 0,
            "sim": 1, "não": 0, "nao": 0, "verdadeiro": 1, "falso": 0,
        }
        s = s.astype(str).str.strip().str.lower().map(mapping).where(lambda x: x.notna(), s)
    s = pd.to_numeric(s, errors="coerce")
    coerced = int(s.isna().sum())
    s = s.fillna(0).clip(0, 1).astype("Int64")
    return s, coerced


def compute_goldset_qa(gold_df: pd.DataFrame, y_true_col: str, y_pred_col: str) -> dict:
    from sklearn.metrics import f1_score, precision_score, recall_score

    y_true, c_true = as_binary_int(gold_df[y_true_col])
    y_pred, c_pred = as_binary_int(gold_df[y_pred_col])
    yt = y_true.fillna(0)
    yp = y_pred.fillna(0)
    return {
        "precision": float(precision_score(yt, yp, zero_division=0)),
        "recall": float(recall_score(yt, yp, zero_division=0)),
        "f1": float(f1_score(yt, yp, zero_division=0)),
        "coerced_true": c_true,
        "coerced_pred": c_pred,
    }
