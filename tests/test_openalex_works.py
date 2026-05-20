"""Tests for OpenAlex work helpers (mocked HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

from bibliometric_analysis.openalex.works import (
    minimal_record_from_oa,
    oa_search_by_title_year,
    oa_work_by_doi,
)

FIXTURE = Path(__file__).parent / "fixtures" / "openalex_work_authorships.json"


def test_minimal_record_from_oa():
    work = {
        "id": "https://openalex.org/W1",
        "doi": "https://doi.org/10.1/x",
        "title": "Test Paper",
        "publication_year": 2020,
        "cited_by_count": 5,
        "is_retracted": False,
        "concepts": [{"id": "C1", "display_name": "CS", "level": 0, "score": 0.9}],
        "authorships": [{"author": {"id": "A1"}, "institutions": [{"id": "I1"}]}],
        "referenced_works": ["https://openalex.org/W2"],
    }
    rec = minimal_record_from_oa(work, top_level=0)
    assert rec["doi"] == "https://doi.org/10.1/x"
    assert rec["domain_label"] == "CS"
    assert rec["n_authors"] == 1


def test_oa_work_by_doi_mock():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def http_get(url, mailto=None, **kwargs):
        if "10.1000/test.enrich1" in url:
            return fixture
        return {"_status": 404}

    j = oa_work_by_doi("10.1000/test.enrich1", "t@example.com", http_get=http_get)
    assert j is not None
    assert j["id"].endswith("W99")


def test_oa_search_by_title_year_mock():
    def http_get(url, params=None, mailto=None, **kwargs):
        return {
            "results": [{
                "id": "W1",
                "title": "Exact Title Match",
                "publication_year": 2019,
                "doi": "https://doi.org/10.1/find",
            }],
            "meta": {},
        }

    hit = oa_search_by_title_year("Exact Title Match", "2019", "t@example.com", http_get=http_get)
    assert hit is not None
    assert "10.1/find" in hit["doi"]
