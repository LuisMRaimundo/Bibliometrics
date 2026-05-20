"""Scopus CSV parser with OpenAlex/PoP auto-detection."""

from __future__ import annotations

import re

import pandas as pd

from .common import doi_pat, finalize_parser_df, norm_doi, read_csv_guess
from .openalex_csv import looks_like_openalex_csv, parse_openalex_csv
from .pop import looks_like_pop_csv, parse_pop_csv


def parse_scopus_csv(path: str) -> pd.DataFrame:
    df0 = read_csv_guess(path)
    if df0.empty:
        return parse_pop_csv(path)
    if looks_like_openalex_csv(df0):
        return parse_openalex_csv(path)
    if looks_like_pop_csv(df0):
        return parse_pop_csv(path)

    df = df0
    norm_cols = {c: re.sub(r"\s+", "_", str(c).strip().lower()) for c in df.columns}
    df.rename(columns=norm_cols, inplace=True)

    if "doi" not in df.columns or df["doi"].isna().all():
        df["doi"] = pd.Series([None] * len(df))
        for c in df.columns:
            if df[c].dtype == "O":
                m = df[c].astype(str).str.extract(doi_pat, expand=False)
                df["doi"] = df["doi"].fillna(m)
    df["doi"] = df["doi"].apply(norm_doi)

    def pick(*cands):
        for c in cands:
            if c in df.columns:
                return c
        return None

    c_title = pick("title", "document_title", "document_title_")
    c_year = pick("year", "publication_year")
    c_doi = pick("doi")
    c_auth = pick("authors", "author_names", "authors_with_affiliations")
    c_abst = pick("abstract", "description", "abstract_keywords")
    c_source = pick("source_title", "publication_title", "journal")
    c_cited = pick("cited_by", "citedby", "cited_by_count")
    c_refs = pick("references", "reference", "refs")

    title = (df[c_title] if c_title else pd.Series([""] * len(df))).astype(str).str.strip().replace({"nan": ""})
    year = df[c_year] if c_year else pd.Series([None] * len(df))
    doi = df[c_doi].apply(norm_doi) if c_doi else pd.Series([None] * len(df))
    auth = df[c_auth] if c_auth else pd.Series([None] * len(df))
    abstr = df[c_abst] if c_abst else pd.Series([None] * len(df))
    src = df[c_source] if c_source else pd.Series([None] * len(df))
    cited = pd.to_numeric(df[c_cited], errors="coerce") if c_cited else pd.Series([pd.NA] * len(df))
    refs = df[c_refs] if c_refs else pd.Series([None] * len(df))

    ref_dois_col = []
    for x in refs.fillna("").astype(str):
        found = [m.group(0).lower() for m in doi_pat.finditer(x)]
        if found:
            seen = set()
            uniq = []
            for d in found:
                if d not in seen:
                    seen.add(d)
                    uniq.append(d)
            ref_dois_col.append(uniq)
        else:
            ref_dois_col.append([])

    out = pd.DataFrame(
        {
            "title": title,
            "doi": doi,
            "source": src,
            "year": year,
            "authors": auth,
            "abstract": abstr,
            "cited_by_count": cited,
            "ref_dois": ref_dois_col,
        }
    )
    out["n_ref_dois"] = out["ref_dois"].apply(len)
    return finalize_parser_df(out)
