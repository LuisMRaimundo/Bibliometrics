"""OpenAlex Works CSV parser."""

from __future__ import annotations

import re

import pandas as pd

from .common import finalize_parser_df, norm_doi, read_csv_guess


def looks_like_openalex_csv(df: pd.DataFrame) -> bool:
    cols = {c.strip().lower() for c in df.columns}
    needed = {"id", "title", "doi", "publication_year", "cited_by_count"}
    return needed.issubset(cols)


def parse_openalex_csv(path: str) -> pd.DataFrame:
    df = read_csv_guess(path)
    norm = {c: re.sub(r"\s+", "_", str(c).strip().lower()) for c in df.columns}
    df.rename(columns=norm, inplace=True)
    title = df.get("title")
    year = df.get("publication_year")
    doi = df.get("doi").apply(norm_doi) if "doi" in df.columns else pd.Series([None] * len(df))
    cited = (
        pd.to_numeric(df.get("cited_by_count"), errors="coerce")
        if "cited_by_count" in df.columns
        else pd.Series([pd.NA] * len(df))
    )
    is_retracted = df.get("is_retracted")
    refs = df.get("referenced_works")
    out = pd.DataFrame(
        {
            "title": title,
            "doi": doi,
            "year": year,
            "cited_by_count": cited,
            "is_retracted": is_retracted,
            "referenced_works": refs,
        }
    )
    out["authors"] = None
    out["abstract"] = None
    out["source"] = None
    out["ref_dois"] = [[] for _ in range(len(out))]
    out["n_ref_dois"] = 0
    return finalize_parser_df(out)
