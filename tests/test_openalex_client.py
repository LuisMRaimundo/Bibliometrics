import json
from pathlib import Path

import pytest
import requests

from bibliometric_analysis.openalex.cache import HTTPCache, cache_key
from bibliometric_analysis.openalex.client import OpenAlexClient


@pytest.fixture
def tmp_cache(tmp_path):
    return HTTPCache(tmp_path / "cache.sqlite3")


def test_cache_key_deterministic():
    k1 = cache_key("http://x", {"b": 2, "a": 1})
    k2 = cache_key("http://x", {"a": 1, "b": 2})
    assert k1 == k2


def test_cache_miss_hit(tmp_cache):
    key = "k1"
    assert tmp_cache.get(key) is None
    tmp_cache.set(key, "http://x", {}, {"ok": True})
    assert tmp_cache.get(key) == {"ok": True}


def test_404_memoization(tmp_path):
    calls = []

    def transport(url, params=None, timeout=30, headers=None):
        calls.append(1)
        r = requests.Response()
        r.status_code = 404
        return r

    client = OpenAlexClient(cache_path=tmp_path / "c.sqlite3", transport=transport, offline=False)
    out = client.get("http://example.test/works/doi:10.1/none", mailto="t@t.com")
    assert out.get("_status") == 404
    out2 = client.get("http://example.test/works/doi:10.1/none", mailto="t@t.com")
    assert out2.get("_status") == 404
    assert len(calls) == 1


def test_offline_raises(tmp_path):
    client = OpenAlexClient(cache_path=tmp_path / "c.sqlite3", offline=True)
    with pytest.raises(RuntimeError, match="Offline mode"):
        client.get("http://example.test/x")


def test_mailto_in_params(tmp_path):
    seen = {}

    def transport(url, params=None, timeout=30, headers=None):
        seen.update(params or {})
        r = requests.Response()
        r.status_code = 200
        r._content = b"{}"
        return r

    client = OpenAlexClient(cache_path=tmp_path / "c.sqlite3", transport=transport)
    client.get("http://example.test/x", mailto="user@test.edu")
    assert seen.get("mailto") == "user@test.edu"


def test_fixture_json_parse():
    data = json.loads(Path("tests/fixtures/openalex_work_authorships.json").read_text())
    assert data["authorships"][0]["author"]["display_name"] == "Alice Smith"
