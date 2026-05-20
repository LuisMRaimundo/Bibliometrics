"""Corpus build tests with mocked OpenAlex."""

from __future__ import annotations

import pandas as pd
import pytest

from bibliometric_analysis.corpus.build import build_corpus, ensure_idx, refs_to_dois


def _work(doi: str, oa_id: str, year=2020, cited=3):
    return {
        "id": oa_id,
        "doi": f"https://doi.org/{doi}",
        "title": f"Paper {doi}",
        "publication_year": year,
        "cited_by_count": cited,
        "is_retracted": False,
        "concepts": [{"id": "C1", "display_name": "CS", "level": 0, "score": 1.0}],
        "authorships": [],
        "referenced_works": [],
        "type": "journal-article",
    }


def test_ensure_idx():
    df = pd.DataFrame({"title": ["A"]})
    out = ensure_idx(df)
    assert "idx" in out.columns


def test_refs_to_dois():
    mapping = {"W2": "10.1/b"}
    assert refs_to_dois(["W2", "W2", "W3"], mapping) == ["10.1/b"]


def test_build_corpus_no_expand():
    df_in = pd.DataFrame({"doi": ["10.1/a"], "title": ["A"], "year": [2020]})
    works = {"10.1/a": _work("10.1/a", "W1")}

    def http_get(url, mailto=None, **kwargs):
        for doi, w in works.items():
            if doi in url:
                return w
        return {"_status": 404}

    corpus = build_corpus(
        df_in, expand=False, mailto="t@example.com", top_level=0,
        types_filter=None, k_window=5, drop_self_citations=True, drop_retracted=True,
        http_get=http_get, max_concurrent=1, sleep=0,
    )
    assert len(corpus) == 1
    assert bool(corpus.iloc[0]["is_focal"])
    assert corpus.iloc[0]["c_use"] == 3


def test_build_corpus_no_doi_raises():
    df_in = pd.DataFrame({"doi": [None], "title": [None], "year": [None]})
    with pytest.raises(RuntimeError):
        build_corpus(
            df_in, False, "t@example.com", 0, None, 5, True, True,
            http_get=lambda *a, **k: {"_status": 404}, sleep=0,
        )
