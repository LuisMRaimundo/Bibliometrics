import json
from pathlib import Path

from bibliometric_analysis.enrichment.harvest import extract_authorship_rows, harvest_authorships
from bibliometric_analysis.openalex.client import OpenAlexClient


def test_extract_authorship_rows():
    data = json.loads(Path("tests/fixtures/openalex_work_authorships.json").read_text())
    a, i, e = extract_authorship_rows(data)
    assert len(a) == 1
    assert a[0]["author_name"] == "Alice Smith"
    assert a[0]["orcid"] == "0000-0001-2345-6789"
    assert i[0]["institution"] == "Test University"


def test_harvest_mocked(tmp_path):
    fixture = json.loads(Path("tests/fixtures/openalex_work_authorships.json").read_text())

    def transport(url, params=None, timeout=30, headers=None):
        r = __import__("requests").Response()
        r.status_code = 200
        r._content = json.dumps(fixture).encode()
        return r

    client = OpenAlexClient(cache_path=tmp_path / "c.sqlite3", transport=transport)
    a, i, e = harvest_authorships(["10.1000/test.enrich1"], "t@test.edu", client=client)
    assert not a.empty
    assert "provenance" in a.columns
    assert len(e) == 1
