# -*- coding: utf-8 -*-
"""
enrich_entities.py — Author/institution enrichment via OpenAlex (v16)

Uses shared OpenAlex client from bibliometric_analysis.
Outputs: authors.csv, institutions.csv, authorships.csv
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

from bibliometric_analysis.enrichment.harvest import fuzzy_dedupe, harvest_authorships
from bibliometric_analysis.openalex.client import get_default_client, set_max_concurrent


def main(
    xlsx: str,
    mailto: str,
    concurrency: int,
    *,
    sheet: str = "Records+Metrics",
    doi_col: str = "doi",
) -> None:
    rec = pd.read_excel(xlsx, sheet_name=sheet)
    if doi_col not in rec.columns:
        raise ValueError(f"Coluna '{doi_col}' não encontrada na folha '{sheet}'.")

    dois = (
        rec[doi_col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .drop_duplicates()
        .tolist()
    )

    set_max_concurrent(concurrency)
    a, i, e = harvest_authorships(dois, mailto, concurrency=concurrency)

    if not a.empty:
        a = fuzzy_dedupe(a, "author_name", threshold=96)
    if not i.empty:
        i = fuzzy_dedupe(i, "institution", threshold=96)

    a.to_csv("authors.csv", index=False)
    i.to_csv("institutions.csv", index=False)
    e.to_csv("authorships.csv", index=False)

    cache_path = get_default_client().cache
    cache_loc = cache_path.db_path if cache_path else "disabled"
    print("Guardado: authors.csv, institutions.csv, authorships.csv")
    print(f"Cache: {cache_loc} | Concorrência: {concurrency}")


def _positive_int(value: str) -> int:
    try:
        iv = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("tem de ser inteiro") from exc
    if iv <= 0:
        raise argparse.ArgumentTypeError("tem de ser > 0")
    return iv


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Enriquecimento de entidades (OpenAlex) a partir de Excel com DOIs."
    )
    ap.add_argument("xlsx", help="Excel com folha Records+Metrics e coluna doi.")
    ap.add_argument(
        "--mailto",
        required=False,
        default=os.getenv("OPENALEX_MAILTO"),
        help="Email OpenAlex (ou env OPENALEX_MAILTO).",
    )
    ap.add_argument("--concurrency", type=_positive_int, default=6)
    ap.add_argument("--sheet", default="Records+Metrics")
    ap.add_argument("--doi-col", dest="doi_col", default="doi")
    args = ap.parse_args()

    if not args.mailto:
        ap.error("Fornece --mailto ou define OPENALEX_MAILTO.")

    main(args.xlsx, args.mailto, args.concurrency, sheet=args.sheet, doi_col=args.doi_col)
