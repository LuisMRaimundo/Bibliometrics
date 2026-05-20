"""Shared OpenAlex HTTP client with cache, retry, and offline/test support."""

from __future__ import annotations

import random
import threading
import time
from pathlib import Path
from typing import Any, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache import HTTPCache, cache_key

DEFAULT_BASE_URL = "https://api.openalex.org"
DEFAULT_TIMEOUT = 30
DEFAULT_CACHE_PATH = Path.home() / ".openalex_cache" / "openalex_cache.sqlite3"
DEFAULT_USER_AGENT = "bibliometric-analysis/16.0"


class OpenAlexClient:
    """
    OpenAlex GET client with SQLite cache, concurrency limit, and injectable transport.

    Set ``offline=True`` to allow only cache hits (raises ``RuntimeError`` on miss).
    Pass ``transport`` in tests to mock HTTP without live calls.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        cache_path: Path | str | None = DEFAULT_CACHE_PATH,
        max_concurrent: int = 6,
        user_agent: str = DEFAULT_USER_AGENT,
        offline: bool = False,
        transport: Callable[..., requests.Response] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent
        self.offline = offline
        self.transport = transport
        self._cache: HTTPCache | None = None
        if cache_path is not None:
            self._cache = HTTPCache(cache_path)
        self._max_concurrent = max(1, max_concurrent)
        self._sem = threading.Semaphore(self._max_concurrent)

    @property
    def cache(self) -> HTTPCache | None:
        return self._cache

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    def set_max_concurrent(self, n: int) -> None:
        self._max_concurrent = max(1, int(n))
        self._sem = threading.Semaphore(self._max_concurrent)

    def get(
        self,
        url: str,
        params: dict | None = None,
        *,
        mailto: str | None = None,
        tries: int = 7,
        allow_cache: bool = True,
    ) -> dict[str, Any]:
        params = dict(params or {})
        if mailto and "mailto" not in params:
            params["mailto"] = mailto

        key = cache_key(url, params)
        if allow_cache and self._cache is not None:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        if self.offline:
            raise RuntimeError(f"Offline mode: cache miss for {url}")

        backoff = 1.0
        last_status: int | None = None
        last_text = ""
        for _ in range(tries):
            with self._sem:
                try:
                    r = self._do_request(url, params)
                    last_status = r.status_code
                    if r.status_code in (429,) or (500 <= r.status_code < 600):
                        time.sleep(backoff + random.uniform(0, 0.25))
                        backoff = min(backoff * 2.0, 16.0)
                        continue
                    if r.status_code == 404:
                        payload: dict[str, Any] = {"_status": 404}
                        if allow_cache and self._cache is not None:
                            self._cache.set(key, url, params, payload)
                        return payload
                    r.raise_for_status()
                    payload = r.json()
                    if allow_cache and self._cache is not None:
                        self._cache.set(key, url, params, payload)
                    return payload
                except requests.RequestException as exc:
                    last_text = str(exc)[:200]
                    time.sleep(backoff + random.uniform(0, 0.25))
                    backoff = min(backoff * 2.0, 16.0)
        raise RuntimeError(
            f"Falhou GET {url} após {tries} tentativas; "
            f"último status={last_status}; corpo≈{last_text!r}"
        )

    def get_work_by_doi(self, doi: str, mailto: str) -> dict[str, Any] | None:
        j = self.get(f"{self.base_url}/works/doi:{doi}", mailto=mailto)
        if isinstance(j, dict) and j.get("_status") == 404:
            return None
        return j

    def _do_request(self, url: str, params: dict) -> requests.Response:
        headers = {"User-Agent": f"{self.user_agent} (+{params.get('mailto', 'no-mailto')})"}
        if self.transport is not None:
            return self.transport(url, params=params, timeout=self.timeout, headers=headers)
        sess = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        sess.mount("https://", HTTPAdapter(max_retries=retry))
        sess.mount("http://", HTTPAdapter(max_retries=retry))
        return sess.get(url, params=params, timeout=self.timeout, headers=headers)


# Module-level default client (shared by enrich_entities compatibility layer)
_default_client: OpenAlexClient | None = None


def get_default_client() -> OpenAlexClient:
    global _default_client
    if _default_client is None:
        _default_client = OpenAlexClient()
    return _default_client


def set_default_client(client: OpenAlexClient) -> None:
    global _default_client
    _default_client = client


def http_get(
    url: str,
    params: dict | None = None,
    mailto: str | None = None,
    tries: int = 7,
    allow_cache: bool = True,
) -> dict[str, Any]:
    """Compatibility shim matching legacy ``http_get`` signature."""
    return get_default_client().get(url, params, mailto=mailto, tries=tries, allow_cache=allow_cache)


def set_max_concurrent(n: int) -> None:
    get_default_client().set_max_concurrent(n)
