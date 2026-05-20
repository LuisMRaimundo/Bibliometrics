"""Shared parser utilities."""

from __future__ import annotations

import csv
import re
import unicodedata
from typing import Optional

import pandas as pd

DOI_RE = r"\b10\.\d{4,9}/[^\s;()<>\"']+"
doi_pat = re.compile(rf"({DOI_RE})", re.I)


def norm_doi(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    if not isinstance(s, str):
        s = str(s)
    m = doi_pat.search(s)
    if not m:
        return None
    doi = m.group(0).strip().rstrip(".,;)]}").lstrip("(").lower()
    return doi


def norm_title(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def title_similarity(a: str, b: str) -> float:
    a_set, b_set = set(norm_title(a).split()), set(norm_title(b).split())
    return (len(a_set & b_set) / len(a_set | b_set)) if a_set and b_set else 0.0


def dedupe_by_doi_keep_all_missing(df: pd.DataFrame) -> pd.DataFrame:
    if "doi" not in df.columns:
        return df.reset_index(drop=True)
    m = df["doi"].notna()
    return pd.concat(
        [df.loc[m].drop_duplicates(subset=["doi"]), df.loc[~m]],
        ignore_index=True,
    )


def read_csv_guess(path: str) -> pd.DataFrame:
    """Robust CSV reader for WoS/Scopus/OpenAlex/PoP exports."""
    for enc in ("utf-8-sig", "utf-8", "latin-1", "utf-16"):
        try:
            df = pd.read_csv(path, encoding=enc)
            if len(df) > 0:
                return df
        except Exception:
            continue

    for kwargs in (
        dict(
            engine="python",
            sep=",",
            quotechar='"',
            doublequote=True,
            escapechar="\\",
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        ),
        dict(
            engine="python",
            sep=";",
            quotechar='"',
            doublequote=True,
            escapechar="\\",
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        ),
        dict(
            engine="python",
            sep="\t",
            quotechar='"',
            doublequote=True,
            escapechar="\\",
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        ),
        dict(
            engine="python",
            sep=",",
            quoting=csv.QUOTE_NONE,
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        ),
    ):
        try:
            df = pd.read_csv(path, **kwargs)
            if len(df) > 0:
                return df
        except Exception:
            continue

    return pd.read_csv(path, engine="python", on_bad_lines="skip", dtype=str, keep_default_na=False)


def finalize_parser_df(df: pd.DataFrame) -> pd.DataFrame:
    df = dedupe_by_doi_keep_all_missing(df)
    df["doi"] = df["doi"].astype(object)
    return df.reset_index(drop=True).reset_index().rename(columns={"index": "idx"})
