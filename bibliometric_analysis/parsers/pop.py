"""Publish or Perish / Google Scholar CSV parser."""

from __future__ import annotations

import re

import pandas as pd

from .common import doi_pat, finalize_parser_df, norm_doi, read_csv_guess


def looks_like_pop_csv(df: pd.DataFrame) -> bool:
    cols = {str(c).strip().lower() for c in df.columns}
    return {"gsrank", "cites", "articleurl", "querydate"}.intersection(cols) >= {"gsrank", "cites"}


def parse_pop_csv(path: str) -> pd.DataFrame:
    df = read_csv_guess(path)
    norm = {c: re.sub(r"\s+", "_", str(c).strip().lower()) for c in df.columns}
    df.rename(columns=norm, inplace=True)

    title = df.get("title")
    year = df.get("year")
    src = df.get("source")
    auth = df.get("authors")
    abstr = df.get("abstract")
    cited = pd.to_numeric(df.get("cites"), errors="coerce")

    if "doi" not in df.columns or df["doi"].isna().all():
        df["doi"] = pd.Series([None] * len(df))
        for c in df.columns:
            if df[c].dtype == "O":
                m = df[c].astype(str).str.extract(doi_pat, expand=False)
                df["doi"] = df["doi"].fillna(m)
    doi = df["doi"].apply(norm_doi)

    out = pd.DataFrame(
        {
            "title": (title.astype(str) if title is not None else pd.Series([None] * len(df))),
            "doi": doi.astype(object),
            "year": year if year is not None else pd.Series([None] * len(df)),
            "authors": auth if auth is not None else pd.Series([None] * len(df)),
            "abstract": abstr if abstr is not None else pd.Series([None] * len(df)),
            "source": src if src is not None else pd.Series([None] * len(df)),
            "cited_by_count": cited if cited is not None else pd.Series([pd.NA] * len(df)),
        }
    )
    out["ref_dois"] = [[] for _ in range(len(out))]
    out["n_ref_dois"] = 0
    out["is_retracted"] = False
    return finalize_parser_df(out)
