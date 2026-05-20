"""Corpus construction from input records + OpenAlex enrichment."""

from __future__ import annotations

import concurrent.futures
import json
import time
from typing import Callable, Dict, List, Optional, Set

import pandas as pd

from bibliometric_analysis.openalex.works import (
    minimal_record_from_oa,
    oa_fetch_citers,
    oa_search_by_title_year,
    oa_work_by_doi,
)

DEFAULT_SLEEP = 0.2


def ensure_idx(df: pd.DataFrame) -> pd.DataFrame:
    if "idx" not in df.columns:
        df = df.reset_index(drop=True).reset_index().rename(columns={"index": "idx"})
    try:
        df["idx"] = pd.to_numeric(df["idx"], errors="coerce").astype("Int64")
    except Exception:
        pass
    return df


def refs_to_dois(lst, id_to_doi: dict) -> list:
    if not isinstance(lst, list):
        return []
    out, seen = [], set()
    for wid in lst:
        d = id_to_doi.get(wid)
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def build_corpus(
    df_in: pd.DataFrame,
    expand: bool,
    mailto: str,
    top_level: int,
    types_filter: Optional[Set[str]],
    k_window: int,
    drop_self_citations: bool,
    drop_retracted: bool,
    *,
    http_get: Callable,
    max_concurrent: int = 6,
    sleep: float = DEFAULT_SLEEP,
    base_url: str = "https://api.openalex.org",
    progress_iter=None,
) -> pd.DataFrame:
    _iter = progress_iter or (lambda x, **kw: x)

    focais = sorted({d for d in df_in["doi"].dropna().astype(str) if d})
    if len(focais) == 0:
        miss = df_in[df_in["doi"].isna() & df_in["title"].notna()]
        recovered = []
        for _, r in _iter(miss.iterrows(), total=len(miss), desc="Fallback título/ano"):
            cand = oa_search_by_title_year(
                str(r["title"]),
                str(r.get("year")) if pd.notna(r.get("year")) else None,
                mailto,
                http_get=http_get,
                base_url=base_url,
                sleep=sleep,
            )
            if cand and cand.get("doi"):
                recovered.append(str(cand["doi"]).lower())
            time.sleep(sleep)
        focais = sorted(set(recovered))
    if not focais:
        raise RuntimeError("Nenhum DOI encontrado (e não foi possível recuperar por título/ano).")

    def _get_minimal(doi):
        j = oa_work_by_doi(doi, mailto, http_get=http_get, base_url=base_url)
        return minimal_record_from_oa(j, top_level) if j else None

    focals = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as ex:
        for res in _iter(ex.map(_get_minimal, focais), total=len(focais), desc="OpenAlex focais"):
            if res:
                focals.append(res)
    focals_df = pd.DataFrame(focals)
    if drop_retracted and not focals_df.empty:
        focals_df = focals_df.loc[~focals_df["is_retracted"].astype(bool)].copy()
    focals_df = focals_df.drop_duplicates(subset=["doi"]).drop_duplicates(subset=["oa_id"])
    focals_df["is_focal"] = True

    citers_by_focal: Dict[str, List[dict]] = {}
    if expand and not focals_df.empty:
        def _citers_of(row):
            try:
                return (
                    row["oa_id"],
                    oa_fetch_citers(
                        row["oa_id"], mailto,
                        http_get=http_get, base_url=base_url,
                        types_filter=types_filter, sleep=sleep,
                    ),
                )
            except Exception:
                return (row["oa_id"], [])

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, max_concurrent // 2)) as ex:
            rows = [r for _, r in focals_df.iterrows()]
            for oa_id, lst in _iter(ex.map(_citers_of, rows), total=len(rows), desc="Citantes/focal"):
                if drop_retracted:
                    lst = [w for w in lst if not bool(w.get("is_retracted", False))]
                citers_by_focal[oa_id] = lst

    citer_rows = []
    for lst in citers_by_focal.values():
        for w in lst:
            mr = minimal_record_from_oa(w, top_level)
            if drop_retracted and mr["is_retracted"]:
                continue
            citer_rows.append(mr)
    citers_df = pd.DataFrame(citer_rows) if citer_rows else pd.DataFrame()
    if not citers_df.empty:
        citers_df["is_focal"] = False

    corpus = pd.concat([focals_df, citers_df], ignore_index=True) if not citers_df.empty else focals_df
    corpus = corpus.drop_duplicates(subset=["doi"]).drop_duplicates(subset=["oa_id"]).reset_index(drop=True)

    focal_authors = {}
    for _, r in focals_df.iterrows():
        try:
            focal_authors[r["oa_id"]] = set(json.loads(r["author_ids"] or "[]"))
        except Exception:
            focal_authors[r["oa_id"]] = set()

    corpus["c_use"] = pd.to_numeric(corpus.get("cited_by_count"), errors="coerce")
    corpus["c_use_window"] = pd.NA
    if expand and k_window > 0:
        oa_to_year = {
            r["oa_id"]: (int(r["year"]) if pd.notna(r["year"]) else None)
            for _, r in focals_df.iterrows()
        }
        win_counts = {}
        for oa_id, lst in citers_by_focal.items():
            base_year = oa_to_year.get(oa_id)
            c = 0
            focal_auth = focal_authors.get(oa_id, set())
            for w in lst or []:
                wy = w.get("publication_year")
                if not (wy and base_year and base_year <= int(wy) <= base_year + k_window - 1):
                    continue
                if drop_self_citations:
                    citer_auth = set()
                    for a in w.get("authorships") or []:
                        if a.get("author") and a["author"].get("id"):
                            citer_auth.add(a["author"]["id"])
                    if focal_auth & citer_auth:
                        continue
                c += 1
            win_counts[oa_id] = c
        corpus["c_use_window"] = corpus["oa_id"].map(win_counts)
        m = corpus["c_use_window"].notna()
        corpus.loc[m, "c_use"] = corpus.loc[m, "c_use_window"]

    id_to_doi = {row["oa_id"]: row["doi"] for _, row in corpus.iterrows()}
    corpus["ref_dois"] = corpus["referenced_works"].apply(lambda lst: refs_to_dois(lst, id_to_doi))
    corpus["n_ref_dois"] = corpus["ref_dois"].apply(len)
    return corpus
