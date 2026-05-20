"""Tests for OpenAlex query tool (shared client, no live network)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

QUERY_PATH = Path(__file__).resolve().parents[1] / "Query_OpenAlex" / "openalex_query_7.py"


def _load_query_module():
    spec = importlib.util.spec_from_file_location("openalex_query_7", QUERY_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_build_params_filters():
    mod = _load_query_module()
    ui = {
        "title_include": "machine learning|deep learning",
        "abstract_include": "",
        "languages": "en",
        "year_from": 2018,
        "year_to": 2020,
        "pub_type": "article",
        "has_abstract": True,
        "is_oa": False,
        "has_doi": True,
        "sort_key": "date (desc)",
    }
    params, sort_key = mod.build_params(ui)
    assert "filter" in params
    assert "title.search:" in params["filter"]
    assert "language:en" in params["filter"]
    assert "from_publication_date:2018-01-01" in params["filter"]
    assert "type:journal-article" in params["filter"]
    assert "has_abstract:true" in params["filter"]
    assert params["sort"] == "publication_date:desc"
    assert sort_key == "date (desc)"


def test_fetch_until_max_uses_mock_client(monkeypatch):
    mod = _load_query_module()
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def get(self, url, params, allow_cache=True):
            calls.append((url, params))
            if params.get("cursor") == "*":
                return {
                    "results": [{"id": "W1", "doi": "https://doi.org/10.1/x", "title": "T"}],
                    "meta": {"next_cursor": None},
                }
            return {"results": [], "meta": {}}

    monkeypatch.setattr(mod, "OpenAlexClient", FakeClient)
    batch = mod.fetch_until_max({"filter": "has_doi:true"}, "test@example.com", 50, 10)
    assert len(batch) == 1
    assert batch[0]["id"] == "W1"
    assert calls


def test_work_row_minimal_export_fields():
    mod = _load_query_module()
    work = {
        "id": "https://openalex.org/W1",
        "title": "Sample",
        "doi": "https://doi.org/10.1/sample",
        "publication_date": "2020-01-01",
        "cited_by_count": 3,
        "abstract_inverted_index": {"Hello": [0], "world": [1]},
        "authorships": [],
        "primary_location": {},
    }
    row = mod.work_row_minimal(work)
    assert row["title"] == "Sample"
    assert row.get("doi")
