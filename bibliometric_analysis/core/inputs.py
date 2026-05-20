"""Input parsing dispatch for the analysis pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bibliometric_analysis.parsers.openalex_csv import looks_like_openalex_csv, parse_openalex_csv
from bibliometric_analysis.parsers.pop import looks_like_pop_csv, parse_pop_csv
from bibliometric_analysis.parsers.scopus import parse_scopus_csv
from bibliometric_analysis.parsers.wos import parse_wos_txt


def parse_input(path: str | Path, source: str = "auto") -> pd.DataFrame:
    """
    Parse bibliometric input file.

    source: ``wos``, ``scopus``, ``openalex``, ``pop``, or ``auto`` (detect CSV flavour).
    """
    path = Path(path)
    src = source.lower().strip()
    if src == "wos":
        return parse_wos_txt(str(path))
    if src in ("scopus", "csv"):
        return parse_scopus_csv(str(path))
    if src == "openalex":
        return parse_openalex_csv(str(path))
    if src in ("pop", "publish_or_perish"):
        return parse_pop_csv(str(path))

    # auto-detect
    if path.suffix.lower() == ".txt":
        return parse_wos_txt(str(path))
    sample = pd.read_csv(path, nrows=5, engine="python", on_bad_lines="skip")
    if looks_like_pop_csv(sample):
        return parse_pop_csv(str(path))
    if looks_like_openalex_csv(sample):
        return parse_openalex_csv(str(path))
    return parse_scopus_csv(str(path))


def target_pairs_from_corpus(corpus: pd.DataFrame) -> list[tuple[str, int]]:
    pairs_df = corpus.dropna(subset=["domain_id", "year"])[["domain_id", "year"]].drop_duplicates()
    seen: set[tuple[str, int]] = set()
    out: list[tuple[str, int]] = []
    for dom, yr in pairs_df.itertuples(index=False, name=None):
        key = (str(dom), int(yr))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out
