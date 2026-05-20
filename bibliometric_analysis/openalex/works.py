"""OpenAlex work lookup, citers, and minimal record extraction."""

from __future__ import annotations

import json
import time
from typing import Callable, List, Optional, Set

from bibliometric_analysis.ontology.concepts import extract_level_concepts, select_domain_concept
from bibliometric_analysis.parsers.common import title_similarity

DEFAULT_BASE = "https://api.openalex.org"
DEFAULT_SLEEP = 0.2


def oa_work_by_doi(
    doi: str,
    mailto: str,
    *,
    http_get: Callable,
    base_url: str = DEFAULT_BASE,
) -> dict | None:
    try:
        j = http_get(f"{base_url}/works/doi:{doi}", mailto=mailto)
        if isinstance(j, dict) and j.get("_status") == 404:
            return None
        return j
    except Exception:
        return None


def minimal_record_from_oa(j: dict, top_level: int) -> dict:
    doi = (j.get("doi") or "").lower() if j.get("doi") else None
    concepts = j.get("concepts") or []
    authorships = j.get("authorships") or []
    author_ids = [a.get("author", {}).get("id") for a in authorships if a.get("author")]
    inst_ids = []
    for a in authorships:
        for inst in a.get("institutions") or []:
            if inst.get("id"):
                inst_ids.append(inst.get("id"))
    dom_lbl, dom_id = select_domain_concept(concepts, top_level)
    lvl_concepts = extract_level_concepts(concepts, top_level)
    n_authors = len(authorships) or 1
    n_affils = sum(len(a.get("institutions") or []) for a in authorships) or 1
    return {
        "oa_id": j.get("id"),
        "title": j.get("title"),
        "year": j.get("publication_year"),
        "doi": doi,
        "referenced_works": j.get("referenced_works") or [],
        "cited_by_count": j.get("cited_by_count") or 0,
        "is_retracted": bool(j.get("is_retracted", False)),
        "domain_label": dom_lbl,
        "domain_id": dom_id,
        "concepts_lvl": json.dumps(lvl_concepts, ensure_ascii=False),
        "n_authors": n_authors,
        "n_affiliations": n_affils,
        "author_ids": json.dumps(author_ids, ensure_ascii=False),
        "inst_ids": json.dumps(inst_ids, ensure_ascii=False),
        "type": j.get("type"),
    }


def oa_search_by_title_year(
    title: str,
    year: Optional[str],
    mailto: str,
    *,
    http_get: Callable,
    base_url: str = DEFAULT_BASE,
    k: int = 10,
    pages_limit: int = 5,
    min_sim: float = 0.60,
    sleep: float = DEFAULT_SLEEP,
) -> dict | None:
    def _search_with_filter(filt: Optional[str]) -> Optional[dict]:
        params = {"search": title, "per_page": int(k), "cursor": "*"}
        if filt:
            params["filter"] = filt
        best, best_sim = None, 0.0
        pages = 0
        while True:
            j = http_get(f"{base_url}/works", params=params, mailto=mailto)
            if isinstance(j, dict) and j.get("_status") == 404:
                break
            for w in j.get("results", []) or []:
                sim = title_similarity(title, w.get("title", "") or "")
                if w.get("doi") and sim > best_sim:
                    best, best_sim = w, sim
            nxt = (j.get("meta") or {}).get("next_cursor")
            if not nxt or pages >= (pages_limit - 1):
                break
            params["cursor"] = nxt
            pages += 1
            time.sleep(sleep)
        return best if (best and best.get("doi") and best_sim >= float(min_sim)) else None

    if year:
        try:
            y = int(str(year)[:4])
            filt = f"from_publication_date:{y-1}-01-01,to_publication_date:{y+1}-12-31"
            hit = _search_with_filter(filt)
            if hit:
                return hit
        except Exception:
            pass
    return _search_with_filter(None)


def oa_fetch_citers(
    openalex_id: str,
    mailto: str,
    *,
    http_get: Callable,
    base_url: str = DEFAULT_BASE,
    types_filter: Optional[Set[str]] = None,
    sleep: float = DEFAULT_SLEEP,
) -> List[dict]:
    meta = http_get(
        openalex_id if openalex_id.startswith(base_url) else f"{base_url}/works/{openalex_id}",
        mailto=mailto,
    )
    if isinstance(meta, dict) and meta.get("_status") == 404:
        return []
    url = meta.get("cited_by_api_url") or f"{base_url}/works"
    params = {"per_page": 200, "cursor": "*"}
    if url.endswith("/works"):
        params["filter"] = f"cites:{meta.get('id')}"
    out = []
    while True:
        j = http_get(url, params=params, mailto=mailto)
        if isinstance(j, dict) and j.get("_status") == 404:
            break
        for w in j.get("results", []):
            if types_filter and w.get("type") not in types_filter:
                continue
            out.append(w)
        nxt = (j.get("meta") or {}).get("next_cursor")
        if not nxt:
            break
        params["cursor"] = nxt
        time.sleep(sleep)
    return out
