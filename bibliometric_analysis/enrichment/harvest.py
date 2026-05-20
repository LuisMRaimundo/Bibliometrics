"""Author and institution enrichment via OpenAlex (mockable)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from bibliometric_analysis.openalex.client import OpenAlexClient, get_default_client

try:
    from rapidfuzz import fuzz, process

    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


def extract_authorship_rows(work: dict[str, Any]) -> tuple[list[dict], list[dict], list[dict]]:
    out_auth, out_inst, out_edge = [], [], []
    if not work:
        return out_auth, out_inst, out_edge
    doi = (work.get("doi") or "").lower()
    for a in work.get("authorships", []):
        au = a.get("author") or {}
        orcid = (au.get("orcid") or "").replace("https://orcid.org/", "") if au.get("orcid") else None
        out_auth.append(
            {
                "author_id": au.get("id"),
                "author_name": au.get("display_name"),
                "orcid": orcid,
                "provenance": "openalex",
                "confidence": "high",
            }
        )
        out_edge.append(
            {
                "doi": doi,
                "author_id": au.get("id"),
                "author_name": au.get("display_name"),
            }
        )
        for inst in a.get("institutions", []):
            out_inst.append(
                {
                    "ror_id": inst.get("ror"),
                    "institution": inst.get("display_name"),
                    "country_code": inst.get("country_code"),
                    "type": inst.get("type"),
                    "provenance": "openalex",
                    "confidence": "high",
                }
            )
    return out_auth, out_inst, out_edge


def harvest_authorships(
    dois: list[str],
    mailto: str,
    *,
    concurrency: int = 6,
    client: OpenAlexClient | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    client = client or get_default_client()
    client.set_max_concurrent(concurrency)

    def _one(doi: str):
        j = client.get_work_by_doi(doi, mailto)
        return extract_authorship_rows(j or {})

    rows_auth, rows_inst, rows_edge = [], [], []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(_one, d): d for d in dois if isinstance(d, str) and d}
        for fut in as_completed(futs):
            try:
                a, i, e = fut.result()
                rows_auth.extend(a)
                rows_inst.extend(i)
                rows_edge.extend(e)
            except Exception:
                continue

    a_df = pd.DataFrame(rows_auth).drop_duplicates() if rows_auth else pd.DataFrame(
        columns=["author_id", "author_name", "orcid", "provenance", "confidence"]
    )
    i_df = pd.DataFrame(rows_inst).drop_duplicates() if rows_inst else pd.DataFrame(
        columns=["ror_id", "institution", "country_code", "type", "provenance", "confidence"]
    )
    e_df = pd.DataFrame(rows_edge).drop_duplicates() if rows_edge else pd.DataFrame(
        columns=["doi", "author_id", "author_name"]
    )
    return a_df, i_df, e_df


def fuzzy_dedupe(df: pd.DataFrame, col: str, threshold: int = 95) -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return df
    if not HAS_RAPIDFUZZ:
        df[col + "_canonical"] = df[col]
        df["fuzzy_cluster_id"] = df[col]
        return df
    names = df[col].fillna("").astype(str).unique().tolist()
    canon: dict[str, str] = {}
    for n in names:
        if not n or n in canon:
            continue
        matches = process.extract(n, names, scorer=fuzz.token_sort_ratio, limit=50)
        cluster = [m for m, score, _ in matches if score >= threshold]
        for m in cluster:
            canon[m] = n
    df[col + "_canonical"] = df[col].map(lambda x: canon.get(str(x), x))
    df["fuzzy_cluster_id"] = df[col + "_canonical"]
    return df
