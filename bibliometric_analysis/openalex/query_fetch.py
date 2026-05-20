"""Paginated OpenAlex works fetch using shared client."""

from __future__ import annotationsimport loggingimport randomimport timefrom typing import Callable, List, Optionalfrom bibliometric_analysis.openalex.client import DEFAULT_BASE_URL, OpenAlexClientBASE_URL = f"{DEFAULT_BASE_URL}/works"


def work_dedup_key(work: dict) -> str:
    doi = (work.get("doi") or "").strip().lower()
    wid = (work.get("id") or "").strip()
    return doi or wid


def fetch_works_paged(
    base_params: dict,
    mailto: str,
    per_page: int = 200,
    max_results: int = 1000,
    *,
    client: Optional[OpenAlexClient] = None,
    logger: Optional[logging.Logger] = None,
    progress_cb: Optional[Callable[[int, int, int, bool], None]] = None,
    dedupe: bool = True,
) -> List[dict]:
    """Fetch works via cursor pagination using OpenAlexClient (mockable, no raw Session)."""
    log = logger or logging.getLogger(__name__)
    client = client or OpenAlexClient(cache_path=None)
    results: List[dict] = []
    seen: set[str] = set()
    cursor = "*"
    total = 0
    per_page = min(max(1, int(per_page)), 200)
    fetched_pages = 0

    while cursor and total < max_results:
        params = {**base_params, "per-page": per_page, "cursor": cursor, "mailto": mailto}
        try:
            data = client.get(BASE_URL, params, allow_cache=True)
        except RuntimeError as e:
            sleep_s = min(30.0, 1.5 ** (fetched_pages + 1)) + random.uniform(0.0, 2.0)
            log.warning("Fetch failed: %s. Backoff %.1fs", e, sleep_s)
            time.sleep(sleep_s)
            continue

        if isinstance(data, dict) and data.get("_status") == 404:
            break

        batch = data.get("results", []) or []
        added = 0
        for w in batch:
            if total >= max_results:
                break
            if dedupe:
                key = work_dedup_key(w)
                if not key or key in seen:
                    continue
                seen.add(key)
            results.append(w)
            total += 1
            added += 1

        fetched_pages += 1
        nxt = (data.get("meta") or {}).get("next_cursor")
        has_next = bool(nxt and total < max_results)
        if progress_cb:
            progress_cb(fetched_pages, added, total, has_next)
        if not has_next:
            break
        cursor = nxt

    return results


def fetch_union(
    params_list: List[dict],
    mailto: str,
    per_page: int = 200,
    max_results: int = 1000,
    *,
    client: Optional[OpenAlexClient] = None,
    logger: Optional[logging.Logger] = None,
) -> List[dict]:
    """OR between field queries: union with DOI/id deduplication."""
    log = logger or logging.getLogger(__name__)
    client = client or OpenAlexClient(cache_path=None)
    results: List[dict] = []
    seen: set[str] = set()
    for base_params in params_list:
        batch = fetch_works_paged(
            base_params, mailto, per_page=per_page, max_results=max_results - len(results),
            client=client, logger=log, dedupe=False,
        )
        for w in batch:
            key = work_dedup_key(w)
            if not key or key in seen:
                continue
            seen.add(key)
            results.append(w)
            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break
    return results[:max_results]
