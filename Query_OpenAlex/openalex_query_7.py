# -*- coding: utf-8 -*-
"""
OpenAlex Query Tool — GUI (tkinter) + exports (CSV, BibTeX, HTML)

Robusto e fiável:
- Filtros no servidor: language, from_/to_publication_date
- Ordenação por publication_date (asc/desc)
- Retry/backoff com Session (respeita Retry-After)
- Deduplicação (DOI → id → título+1º autor+ano) antes de export
- Reconstrução de abstract + regex robustas (exclusões)
- Validação e preview da query
- GUI: barra de progresso, botões desativados durante a pesquisa
- OR corretos:
  * Dentro de cada filtro (.search) com '|'
  * Entre campos (título OU abstract) via união cliente (duas queries + dedup)
"""

from __future__ import annotations

# Standard library
import csv
import html
import json
import logging
import random
import re
import threading
import time
import unicodedata
from datetime import date, datetime
from typing import Callable, Dict, Iterable, List, Optional, Tuple

# Third-party
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from bibliometric_analysis.openalex.client import OpenAlexClient
from bibliometric_analysis.openalex.query_fetch import fetch_union as _fetch_union_shared
from bibliometric_analysis.openalex.query_fetch import fetch_works_paged as _fetch_works_paged_shared


# ---------------------- OpenAlex ----------------------
BASE_URL = "https://api.openalex.org/works"

# ---------------------- Texto/regex utils ----------------------
_WS_RE = re.compile(r"\s+", re.UNICODE)

def unaccent_lower(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return t.lower()

def normalize_space(text: str) -> str:
    return _WS_RE.sub(" ", text or "").strip()

def compile_regex_list(patterns: List[str]) -> List[re.Pattern]:
    out: List[re.Pattern] = []
    for p in patterns or []:
        p = (p or "").strip()
        if not p:
            continue
        try:
            out.append(re.compile(p, flags=re.IGNORECASE))
        except re.error:
            # Ignorar padrões inválidos (não bloqueia a pesquisa)
            pass
    return out

# ---------------------- Abstract & deduplicação ----------------------
def reconstruct_abstract(work: dict, normalize: bool = True, unaccent: bool = False) -> str:
    inv = work.get("abstract_inverted_index")
    if not inv or not isinstance(inv, dict):
        return ""
    tokens: List[Tuple[int, str]] = []
    for tok, pos_list in inv.items():
        for p in pos_list or []:
            tokens.append((p, tok))
    if not tokens:
        return ""
    tokens.sort(key=lambda x: x[0])
    txt = " ".join(tok for _, tok in tokens)
    if normalize:
        txt = normalize_space(txt)
    if unaccent:
        txt = unaccent_lower(txt)
    return txt

def display_date(work: dict) -> str:
    d = (work.get("publication_date") or "").strip()
    if d:
        return d
    b = work.get("biblio") or {}
    y = b.get("publication_year")
    if y:
        try:
            return str(int(y))
        except Exception:
            pass
    return ""

def _norm_title(title: str) -> str:
    if not title:
        return ""
    t = unaccent_lower(title)
    t = re.sub(r"[^\w\s]", " ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t

def _first_author_lastname(work: dict) -> str:
    auths = work.get("authorships") or []
    if not auths:
        return ""
    name = (auths[0].get("author") or {}).get("display_name") or ""
    if not name:
        return ""
    return unaccent_lower(name).split()[-1] if name.strip() else ""

def _year_from_pubdate(work: dict) -> str:
    d = (work.get("publication_date") or "").strip()
    if d and len(d) >= 4 and d[:4].isdigit():
        return d[:4]
    y = str((work.get("biblio") or {}).get("publication_year") or "")
    return y if y.isdigit() else ""

def deduplicate_works(works: Iterable[dict]) -> Tuple[List[dict], dict]:
    seen = set()
    out: List[dict] = []
    stats = {"input": 0, "kept": 0, "dup_doi": 0, "dup_id": 0, "dup_title_author_year": 0, "no_key": 0}
    for w in works:
        stats["input"] += 1
        doi = (w.get("doi") or "").strip().lower()
        wid = (w.get("id") or "").strip()
        if doi:
            key = ("doi", doi)
        elif wid:
            key = ("id", wid)
        else:
            t = _norm_title(w.get("display_name") or w.get("title") or "")
            a = _first_author_lastname(w)
            y = _year_from_pubdate(w)
            if not (t and a and y):
                stats["no_key"] += 1
                key = ("orph", f"{t}|{a}|{y}|{stats['input']}")
            else:
                key = ("tay", f"{t}|{a}|{y}")
        if key in seen:
            if key[0] == "doi":
                stats["dup_doi"] += 1
            elif key[0] == "id":
                stats["dup_id"] += 1
            elif key[0] == "tay":
                stats["dup_title_author_year"] += 1
            continue
        seen.add(key)
        out.append(w)
        stats["kept"] += 1
    return out, stats

# ---------------------- Build params / OR helpers ----------------------
SORT_LABELS = ["relevance (desc)", "citations (desc)", "date (desc)", "date (asc)"]

def _split_clean(s: str) -> List[str]:
    if not s:
        return []
    return [t.strip() for t in s.split(",") if t.strip()]

def _terms_or(s: str) -> List[str]:
    """
    Converte input do utilizador em itens para OR dentro do mesmo filtro.
    - vírgula => separa filtros (AND)
    - ' OR ' ou '|' dentro do item => OR dentro do MESMO filtro
    """
    out: List[str] = []
    for raw in _split_clean(s):
        t = re.sub(r"\s+\bOR\b\s+", "|", raw, flags=re.IGNORECASE)
        t = t.strip("| ").strip()
        if t:
            out.append(t)
    return out

def validate_ui_state(ui: dict) -> tuple[dict, list[str]]:
    msgs = []
    ui = dict(ui)
    mt = (ui.get("mailto") or "").strip()
    # Não bloqueia se inválido; recomenda
    if "@" not in mt:
        msgs.append("Recomendado definir um e-mail válido (mailto) para melhor quota de API.")
    ui["mailto"] = mt

    # anos
    yf, yt = ui.get("year_from"), ui.get("year_to")
    try:
        yf = int(yf) if yf not in (None, "") else None
    except Exception:
        msgs.append("year_from inválido; ignorado."); yf = None
    try:
        yt = int(yt) if yt not in (None, "") else None
    except Exception:
        msgs.append("year_to inválido; ignorado."); yt = None
    if yf is not None and yt is not None and yf > yt:
        yf, yt = yt, yf
        msgs.append("Intervalo de anos invertido; corrigido automaticamente.")
    ui["year_from"], ui["year_to"] = yf, yt

    # línguas
    langs = ui.get("languages") or ""
    langs = ",".join(s.strip() for s in langs.replace("|", ",").split(",") if s.strip())
    ui["languages"] = langs
    return ui, msgs

def build_params(ui_state: dict) -> tuple[dict, str]:
    parts: List[str] = []

    # title.search — AND entre itens (vírgula), OR dentro do item com '|'
    for t in _terms_or(ui_state.get("title_include", "")):
        parts.append(f"title.search:{t}")

    # abstract.search — idem
    for a in _terms_or(ui_state.get("abstract_include", "")):
        parts.append(f"abstract.search:{a}")

    # language
    langs_raw = ui_state.get("languages", "")
    if langs_raw:
        langs = [s.strip() for s in langs_raw.replace("|", ",").split(",") if s.strip()]
        if langs:
            parts.append(f"language:{'|'.join(langs)}")

    # datas
    yf = ui_state.get("year_from")
    yt = ui_state.get("year_to")
    if isinstance(yf, int):
        parts.append(f"from_publication_date:{yf}-01-01")
    if isinstance(yt, int):
        parts.append(f"to_publication_date:{yt}-12-31")

    # tipo
    type_map = {
        "all": None,
        "article": "journal-article",
        "review": "review-article",
        "preprint": "posted-content",
        "dissertation": "dissertation",
        "book": "book",
        "dataset": "dataset",
    }
    api_type = type_map.get(ui_state.get("pub_type", "all"))
    if api_type:
        parts.append(f"type:{api_type}")

    # flags
    if ui_state.get("has_abstract"):
        parts.append("has_abstract:true")
    if ui_state.get("is_oa"):
        parts.append("is_oa:true")
    if ui_state.get("has_doi"):
        parts.append("has_doi:true")

    params: Dict[str, str] = {}
    if parts:
        params["filter"] = ",".join(parts)

    sort_key = ui_state.get("sort_key", "relevance (desc)")
    if sort_key == "relevance (desc)":
        params["sort"] = "relevance_score:desc"
    elif sort_key == "citations (desc)":
        params["sort"] = "cited_by_count:desc"
    elif sort_key == "date (desc)":
        params["sort"] = "publication_date:desc"
    elif sort_key == "date (asc)":
        params["sort"] = "publication_date:asc"
    else:
        params["sort"] = "relevance_score:desc"

    params["select"] = ",".join([
        "id","title","display_name","doi","type","language",
        "publication_date","cited_by_count",
        "primary_location","best_oa_location","locations",
        "authorships","abstract_inverted_index","biblio"
    ])



    return params, sort_key

def params_preview(params: dict) -> str:
    parts = []
    if "filter" in params: parts.append(f"filter={params['filter']}")
    if "sort" in params: parts.append(f"sort={params['sort']}")
    if "select" in params: parts.append(f"select={params['select']}")
    return " | ".join(parts)

# ---------------------- Networking: shared OpenAlex client ----------------------
def make_session(mailto: str):
    """
    Deprecated compatibility stub. HTTP is handled by ``OpenAlexClient``.
    Returns an ``OpenAlexClient`` instance (not a requests.Session).
    """
    import warnings
    warnings.warn(
        "make_session is deprecated; use OpenAlexClient via fetch_until_max",
        DeprecationWarning,
        stacklevel=2,
    )
    return OpenAlexClient(cache_path=None, user_agent=f"OpenAlexQueryTool/1.0 (+{mailto})" if mailto else "OpenAlexQueryTool/1.0")


def fetch_until_max(
    base_params: dict,
    mailto: str,
    per_page: int,
    max_results: int,
    logger: Optional[logging.Logger] = None,
    progress_cb: Optional[Callable[[int, int, int, bool], None]] = None,
    connect_timeout: float = 10.0,
    read_timeout: float = 60.0,
    *,
    client: Optional[OpenAlexClient] = None,
) -> List[dict]:
    """Paginated fetch via shared ``OpenAlexClient`` (dedupe by DOI/id)."""
    del connect_timeout, read_timeout  # handled by client.timeout
    log = logger or logging.getLogger(__name__)
    client = client or OpenAlexClient(
        cache_path=None,
        user_agent=f"OpenAlexQueryTool/1.0 (+{mailto})" if mailto else "OpenAlexQueryTool/1.0",
    )
    results = _fetch_works_paged_shared(
        base_params,
        mailto,
        per_page=per_page,
        max_results=max_results,
        client=client,
        logger=log,
        progress_cb=progress_cb,
        dedupe=True,
    )
    log.info("Total obtido: %d", len(results))
    return results


def fetch_union(
    params_list: List[dict],
    mailto: str,
    per_page: int,
    max_results: int,
    logger: Optional[logging.Logger] = None,
    *,
    client: Optional[OpenAlexClient] = None,
) -> List[dict]:
    """OR between fields via shared client with union deduplication."""
    log = logger or logging.getLogger(__name__)
    client = client or OpenAlexClient(
        cache_path=None,
        user_agent=f"OpenAlexQueryTool/1.0 (+{mailto})" if mailto else "OpenAlexQueryTool/1.0",
    )
    return _fetch_union_shared(
        params_list, mailto, per_page=per_page, max_results=max_results, client=client, logger=log
    )

# ---------------------- Transformação p/ tabela/CSV ----------------------
def work_row_minimal(work: dict, include_abstract: bool = True) -> dict:
    title = work.get("title") or work.get("display_name") or ""
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    ploc = work.get("primary_location") or {}
    if ploc.get("landing_page_url"):
        url_direct = ploc["landing_page_url"]
    elif ploc.get("pdf_url"):
        url_direct = ploc["pdf_url"]
    else:
        url_direct = work.get("id") or ""
    type_ = work.get("type") or ""
    lang = (work.get("language") or "").lower()
    venue = (work.get("host_venue") or {}).get("display_name") or ""
    pub_date = display_date(work)
    year = pub_date[:4] if pub_date else ""
    cited_by = int(work.get("cited_by_count") or 0)
    authors = []
    for a in work.get("authorships") or []:
        name = (a.get("author") or {}).get("display_name")
        if name:
            authors.append(name)
    authors_str = "; ".join(authors)
    abstract = reconstruct_abstract(work) if include_abstract else ""
    wid = (work.get("id") or "").replace("https://openalex.org/", "")
    openalex_url = f"https://openalex.org/{wid}" if wid else ""
    return {
        "id": wid,
        "openalex_url": openalex_url,
        "title": title,
        "authors": authors_str,
        "year": year,
        "publication_date": pub_date,
        "venue": venue,
        "type": type_,
        "language": lang,
        "cited_by": cited_by,
        "doi": doi,
        "url": url_direct,
        "abstract": abstract,
    }

def local_sort(works: List[dict], sort_key: str) -> List[dict]:
    if sort_key == "citations (desc)":
        return sorted(works, key=lambda w: int(w.get("cited_by_count") or 0), reverse=True)

    def _parse_date(d: str | None) -> date:
        if not d:
            return date.min
        try:
            return datetime.fromisoformat(d).date()
        except Exception:
            try:
                return date(int(d[:4]), 12, 31)
            except Exception:
                return date.min

    if sort_key == "date (desc)":
        return sorted(works, key=lambda w: (_parse_date(w.get("publication_date")), int(w.get("cited_by_count") or 0), (w.get("id") or "")), reverse=True)
    if sort_key == "date (asc)":
        return sorted(works, key=lambda w: (_parse_date(w.get("publication_date")), -int(w.get("cited_by_count") or 0), (w.get("id") or "")))
    return works  # relevance (desc) — já vem do servidor

# ---------------------- GUI ----------------------
FIELDNAMES = ["id","openalex_url","title","authors","year","publication_date","venue","type","language","cited_by","doi","url","abstract"]

import threading, csv, json, html, re
from datetime import datetime
from typing import List, Optional
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class OpenAlexQueryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenAlex Query Tool — versão robusta (OR + União)")
        self.geometry("1280x860")

        # Estado/UI
        self.email_var = tk.StringVar(value="")
        self.title_include_var = tk.StringVar(value="")
        self.abstract_include_var = tk.StringVar(value="")
        self.exclude_title_var = tk.StringVar(value="")
        self.exclude_abstract_var = tk.StringVar(value="")
        self.lang_var = tk.StringVar(value="")
        self.year_from_var = tk.StringVar(value="")
        self.year_to_var = tk.StringVar(value="")
        self.pub_type_var = tk.StringVar(value="all")
        self.union_title_abstract_var = tk.BooleanVar(value=False)

        self.has_abstract_var = tk.BooleanVar(value=True)
        self.is_oa_var = tk.BooleanVar(value=False)
        self.has_doi_var = tk.BooleanVar(value=True)

        self.per_page_var = tk.IntVar(value=200)
        self.max_results_var = tk.IntVar(value=500)
        self.sort_var = tk.StringVar(value="relevance (desc)")

        self.results: List[dict] = []

        self.status_var = tk.StringVar(value="Pronto.")
        self.query_preview_var = tk.StringVar(value="")

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        frm = ttk.Frame(nb); nb.add(frm, text="Pesquisa")

        row = 0
        ttk.Label(frm, text="Email (mailto):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.email_var, width=40).grid(row=row, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(frm, text="Ordenar:").grid(row=row, column=2, sticky="e")
        ttk.Combobox(frm, textvariable=self.sort_var, state="readonly",
                     values=SORT_LABELS, width=18).grid(row=row, column=3, sticky="w", padx=4, pady=4)

        row += 1
        ttk.Label(frm, text="Incluir no TÍTULO (vírgulas; usa OR ou |):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.title_include_var, width=60)\
            .grid(row=row, column=1, columnspan=3, sticky="we", padx=4, pady=4)

        row += 1
        ttk.Label(frm, text="Incluir no ABSTRACT (vírgulas; usa OR ou |):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.abstract_include_var, width=60)\
            .grid(row=row, column=1, columnspan=3, sticky="we", padx=4, pady=4)

        row += 1
        ttk.Label(frm, text="EXCLUIR do TÍTULO (vírgulas, regex ok):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.exclude_title_var, width=60)\
            .grid(row=row, column=1, columnspan=3, sticky="we", padx=4, pady=4)

        row += 1
        ttk.Label(frm, text="EXCLUIR do ABSTRACT (vírgulas, regex ok):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.exclude_abstract_var, width=60)\
            .grid(row=row, column=1, columnspan=3, sticky="we", padx=4, pady=4)

        row += 1
        ttk.Checkbutton(frm, text="OR entre campos (título OU abstract) via união",
                        variable=self.union_title_abstract_var)\
            .grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=4)

        row += 1
        ttk.Label(frm, text="Idiomas (ex.: en, pt):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.lang_var, width=20).grid(row=row, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(frm, text="Ano (de):").grid(row=row, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.year_from_var, width=8).grid(row=row, column=3, sticky="w", padx=4, pady=4)

        row += 1
        ttk.Label(frm, text="Ano (até):").grid(row=row, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.year_to_var, width=8).grid(row=row, column=3, sticky="w", padx=4, pady=4)

        row += 1
        ttk.Label(frm, text="Tipo:").grid(row=row, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=self.pub_type_var, state="readonly",
                     values=["all","article","review","preprint","dissertation","book","dataset"], width=16)\
            .grid(row=row, column=1, sticky="w", padx=4, pady=4)
        ttk.Checkbutton(frm, text="has_abstract", variable=self.has_abstract_var)\
            .grid(row=row, column=2, sticky="w", padx=4, pady=4)
        ttk.Checkbutton(frm, text="is_oa", variable=self.is_oa_var)\
            .grid(row=row, column=3, sticky="w", padx=4, pady=4)

        row += 1
        ttk.Checkbutton(frm, text="has_doi", variable=self.has_doi_var)\
            .grid(row=row, column=2, sticky="w", padx=4, pady=4)
        ttk.Label(frm, text="per-page (≤200):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.per_page_var, width=8)\
            .grid(row=row, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(frm, text="Máx. resultados:").grid(row=row, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.max_results_var, width=10)\
            .grid(row=row, column=3, sticky="w", padx=4, pady=4)

        row += 1
        self.progress = ttk.Progressbar(frm, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=4, sticky="we", padx=4, pady=4)

        row += 1
        ttk.Label(frm, text="Query (preview):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.query_preview_var, state="readonly")\
            .grid(row=row, column=1, columnspan=3, sticky="we", padx=4, pady=4)

        row += 1
        self.search_btn = ttk.Button(frm, text="Pesquisar", command=self.on_search)
        self.search_btn.grid(row=row, column=0, padx=4, pady=8, sticky="we")
        ttk.Button(frm, text="Limpar resultados", command=self.on_clear)\
            .grid(row=row, column=1, padx=4, pady=8, sticky="we")
        self.export_csv_btn = ttk.Button(frm, text="Exportar CSV", command=self.export_csv, state="disabled")
        self.export_csv_btn.grid(row=row, column=2, padx=4, pady=8, sticky="we")
        self.export_bib_btn = ttk.Button(frm, text="Exportar BibTeX", command=self.export_bibtex, state="disabled")
        self.export_bib_btn.grid(row=row, column=3, padx=4, pady=8, sticky="we")

        row += 1
        self.export_html_btn = ttk.Button(frm, text="Exportar HTML", command=self.export_html, state="disabled")
        self.export_html_btn.grid(row=row, column=0, padx=4, pady=8, sticky="we")

        # Botão Diagnóstico
        self.diag_btn = ttk.Button(frm, text="Diagnóstico", command=self.run_diag)
        self.diag_btn.grid(row=row, column=1, padx=4, pady=8, sticky="we")

        # Tabela
        columns = tuple(FIELDNAMES[:-1])  # sem abstract na grelha
        self.tree = ttk.Treeview(frm, columns=columns, show="headings", height=22)
        for col in columns:
            self.tree.heading(col, text=col)
            default_w = 160
            if col == "title":
                default_w = 480
            elif col in ("authors", "openalex_url", "url"):
                default_w = 280
            self.tree.column(col, width=default_w, anchor="w")
        row += 1
        self.tree.grid(row=row, column=0, columnspan=4, sticky="nsew", padx=4, pady=4)
        vsb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        vsb.grid(row=row, column=4, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        row += 1
        ttk.Label(frm, textvariable=self.status_var).grid(row=row, column=0, columnspan=4,
                                                          sticky="w", padx=4, pady=4)

        # expand
        frm.grid_columnconfigure(1, weight=1)
        frm.grid_rowconfigure(row-1, weight=1)

    # ---------- Callbacks de progresso ----------
    def _progress_tick(self, page: int, added: int, total: int, has_next: bool) -> None:
        self.after(0, lambda: self.status_var.set(
            f"Página {page} | adicionados {added} | total {total}" + (" | a continuar..." if has_next else "")
        ))

    # ---------- Ações ----------
    def on_search(self):
        try:
            per_page = int(self.per_page_var.get() or 200)
        except Exception:
            per_page = 200
        per_page = max(1, min(per_page, 200))

        try:
            max_results = int(self.max_results_var.get() or 500)
        except Exception:
            max_results = 500
        max_results = max(1, max_results)

        email = (self.email_var.get() or "").strip()
        if "@" not in email:
            messagebox.showerror("Configuração obrigatória",
                                 "Indique um e-mail válido em 'Email (mailto)' para evitar bloqueios na API.")
            return

        ui_state = {
            "mailto": email,
            "title_include": self.title_include_var.get(),
            "abstract_include": self.abstract_include_var.get(),
            "languages": self.lang_var.get(),
            "year_from": self.year_from_var.get().strip() or None,
            "year_to": self.year_to_var.get().strip() or None,
            "pub_type": self.pub_type_var.get(),
            "has_abstract": bool(self.has_abstract_var.get()),
            "is_oa": bool(self.is_oa_var.get()),
            "has_doi": bool(self.has_doi_var.get()),
            "sort_key": self.sort_var.get(),
        }
        ui_state, warnings = validate_ui_state(ui_state)

        # Construção base
        params, _ = build_params(ui_state)
        preview = params_preview(params)

        # União (título OU abstract) se ativado e ambos preenchidos
        union_mode = bool(self.union_title_abstract_var.get()) and ui_state.get("title_include") and ui_state.get("abstract_include")
        if union_mode:
            ui_t = dict(ui_state); ui_t["abstract_include"] = ""
            ui_a = dict(ui_state); ui_a["title_include"] = ""
            params_t, _ = build_params(ui_t)
            params_a, _ = build_params(ui_a)
            preview = "UNION{ " + params_preview(params_t) + "  ||  " + params_preview(params_a) + " }"
            target = self._do_search_union_thread
            targs = (ui_state, [params_t, params_a], per_page, max_results)
        else:
            target = self._do_search_thread
            targs = (ui_state, params, per_page, max_results)

        self.query_preview_var.set(preview)
        if warnings:
            self.status_var.set(" ; ".join(warnings))

        # bloquear UI e lançar
        self.search_btn.config(state="disabled")
        self.export_csv_btn.config(state="disabled")
        self.export_bib_btn.config(state="disabled")
        self.export_html_btn.config(state="disabled")
        self.progress.start(10)
        self.status_var.set("A pesquisar...")
        threading.Thread(target=target, args=targs, daemon=True).start()

    def _do_search_thread(self, ui_state, params, per_page, max_results):
        try:
            mailto = ui_state["mailto"]
            batch = fetch_until_max(
                params, mailto=mailto, per_page=per_page, max_results=max_results,
                logger=None, progress_cb=self._progress_tick
            )

            sort_key = ui_state.get("sort_key", "relevance (desc)")
            if sort_key != "relevance (desc)":
                batch = local_sort(batch, sort_key)

            exclude_title_rx = compile_regex_list(_split_clean(self.exclude_title_var.get()))
            exclude_abs_rx   = compile_regex_list(_split_clean(self.exclude_abstract_var.get()))

            kept: List[dict] = []
            rows: List[dict] = []
            for w in batch:
                title_norm = normalize_space(w.get("display_name") or w.get("title") or "")
                abs_norm   = reconstruct_abstract(w, normalize=True, unaccent=False)
                if exclude_title_rx and any(rx.search(title_norm) for rx in exclude_title_rx):
                    continue
                if exclude_abs_rx and any(rx.search(abs_norm) for rx in exclude_abs_rx):
                    continue
                kept.append(w)
                rows.append(work_row_minimal(w, include_abstract=True))

            self.results = kept
            self.after(0, lambda: self._populate_tree(rows, n_in=len(batch)))

        except Exception as e:
            self.after(0, lambda: self._on_search_finished(False, f"Erro: {e}", 0))

    def _do_search_union_thread(self, ui_state, params_list, per_page, max_results):
        try:
            mailto = ui_state["mailto"]
            batch = fetch_union(
                params_list, mailto=mailto, per_page=per_page, max_results=max_results,
                logger=None,
            )

            sort_key = ui_state.get("sort_key", "relevance (desc)")
            if sort_key != "relevance (desc)":
                batch = local_sort(batch, sort_key)

            exclude_title_rx = compile_regex_list(_split_clean(self.exclude_title_var.get()))
            exclude_abs_rx   = compile_regex_list(_split_clean(self.exclude_abstract_var.get()))

            kept: List[dict] = []
            rows: List[dict] = []
            for w in batch:
                title_norm = normalize_space(w.get("display_name") or w.get("title") or "")
                abs_norm   = reconstruct_abstract(w, normalize=True, unaccent=False)
                if exclude_title_rx and any(rx.search(title_norm) for rx in exclude_title_rx):
                    continue
                if exclude_abs_rx and any(rx.search(abs_norm) for rx in exclude_abs_rx):
                    continue
                kept.append(w)
                rows.append(work_row_minimal(w, include_abstract=True))

            self.results = kept
            self.after(0, lambda: self._populate_tree(rows, n_in=len(batch)))

        except Exception as e:
            self.after(0, lambda: self._on_search_finished(False, f"Erro: {e}", 0))

    # ---------- Pós-pesquisa ----------
    def _populate_tree(self, rows: List[dict], n_in: int = 0):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            vals = [r.get(col, "") for col in self.tree["columns"]]
            self.tree.insert("", "end", values=tuple(vals))
        self._on_search_finished(True, f"{len(rows)} registos carregados (de {n_in} recebidos).", len(rows))

    def _on_search_finished(self, ok: bool, msg: str, n: int):
        self.progress.stop()
        self.search_btn.config(state="normal")
        self.export_csv_btn.config(state="normal" if ok and n > 0 else "disabled")
        self.export_bib_btn.config(state="normal" if ok and n > 0 else "disabled")
        self.export_html_btn.config(state="normal" if ok and n > 0 else "disabled")
        self.status_var.set(msg or ("Concluído" if ok else "Falhou"))

    def on_clear(self):
        self.results = []
        self.tree.delete(*self.tree.get_children())
        self.status_var.set("Resultados limpos.")

    # ---------- Exportações ----------
    def _ensure_rows(self) -> Optional[tuple[list[dict], dict]]:
        if not getattr(self, "results", None):
            messagebox.showwarning("Aviso", "Não há resultados para exportar.")
            return None
        deduped, dstats = deduplicate_works(self.results)
        rows = [work_row_minimal(w, include_abstract=True) for w in deduped]
        if not rows:
            messagebox.showwarning("Aviso", "Após deduplicação não restaram registos exportáveis.")
            return None
        return rows, dstats

    def export_csv(self):
        res = self._ensure_rows()
        if res is None:
            return
        rows, dstats = res
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            fieldnames = FIELDNAMES
            def _ensure_fields(r: dict) -> dict:
                return {k: r.get(k, "") for k in fieldnames}
            rows = [_ensure_fields(r) for r in rows]
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            meta = {"timestamp": datetime.now().isoformat(timespec="seconds"), "dedup_stats": dstats, "fieldnames": fieldnames}
            with open(path + ".meta.json", "w", encoding="utf-8") as m:
                json.dump(meta, m, ensure_ascii=False, indent=2)
            messagebox.showinfo("Exportação", (f"CSV gravado em:\n{path}\n\n"
                                               f"Deduplicação — entrada: {dstats['input']}, mantidos: {dstats['kept']}, "
                                               f"dup_doi: {dstats['dup_doi']}, dup_id: {dstats['dup_id']}, "
                                               f"dup_título+autor+ano: {dstats['dup_title_author_year']}, sem chave: {dstats['no_key']}"))
        except (OSError, PermissionError) as e:
            messagebox.showerror("Erro de ficheiro", f"{e}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha a gravar CSV: {e}")

    # --- BibTeX helpers ---
    TYPE_MAP_BIB = {
        "journal-article": "article",
        "review-article": "article",
        "posted-content": "misc",
        "dissertation": "phdthesis",
        "book": "book",
        "book-chapter": "incollection",
        "proceedings-article": "inproceedings",
        "dataset": "misc",
    }
    def bibtex_escape(self, s: str) -> str:
        if s is None:
            return ""
        return (s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
                .replace('"', '\\"').replace("%", "\\%"))
    def protect_acronyms(self, title: str) -> str:
        def repl(m): return "{" + m.group(0) + "}"
        return re.sub(r"\b([A-Z]{2,6})\b", repl, title or "")
    def authors_bibtex_list(self, work: dict) -> list[str]:
        out = []
        for a in (work.get("authorships") or []):
            name = ((a.get("author") or {}).get("display_name") or "").strip()
            if name:
                parts = name.split()
                if len(parts) >= 2:
                    last = parts[-1]; first = " ".join(parts[:-1])
                    out.append(f"{last}, {first}")
                else:
                    out.append(name)
        return out
    
    
    def hostvenue_fields(self, work: dict) -> dict:
        def pick_source(w: dict) -> dict:
            pl = (w.get("primary_location") or {}).get("source")
            if pl: return pl
            boa = (w.get("best_oa_location") or {}).get("source")
            if boa: return boa
            for loc in (w.get("locations") or []):
                src = (loc or {}).get("source")
                if src: return src
            return {}

        src = pick_source(work)
        b   = work.get("biblio") or {}
        fields = {}

        venue = (src.get("display_name") or "").strip()
        if work.get("type") in ("journal-article", "review-article"):
            if venue: fields["journal"] = venue
        elif work.get("type") in ("proceedings-article", "book-chapter"):
            if venue: fields["booktitle"] = venue

        publisher = (src.get("publisher") or "").strip()
        if publisher:
            fields["publisher"] = publisher

        if b.get("volume"): fields["volume"] = str(b.get("volume"))
        if b.get("issue"):  fields["number"] = str(b.get("issue"))
        if b.get("first_page") or b.get("last_page"):
            fp = str(b.get("first_page") or ""); lp = str(b.get("last_page") or "")
            fields["pages"] = f"{fp}--{lp}" if fp and lp else (fp or lp)

        return fields

    
    
    def to_bibtex_entry(self, work: dict) -> str:
        wtype = work.get("type") or ""; entry_type = self.TYPE_MAP_BIB.get(wtype, "misc")
        year = ""; d = (work.get("publication_date") or "")
        if d and len(d) >= 4 and d[:4].isdigit(): year = d[:4]
        auths = self.authors_bibtex_list(work); firstkey = auths[0].split(",")[0] if auths else ""
        title = (work.get("display_name") or work.get("title") or "").strip()
        key_title = unaccent_lower(title).split(); key_title = "".join(key_title[:3]) if key_title else "noTitle"
        bibkey = f"{firstkey}{year}{key_title}"
        fields = {"title": self.protect_acronyms(title), "year": year}
        doi = (work.get("doi") or "").strip()
        if doi: fields["doi"] = doi
        wid = (work.get("id") or "").replace("https://openalex.org/", "")
        if wid: fields["url"] = f"https://openalex.org/{wid}"
        if auths: fields["author"] = " and ".join(auths)
        fields.update(self.hostvenue_fields(work))
        if work.get("language"): fields["language"] = work["language"]
        if work.get("cited_by_count") is not None: fields["note"] = f"Cited by {work['cited_by_count']} (OpenAlex)"
        lines = [f"@{entry_type}{{{bibkey},"] + [
            f"  {k} = {{{self.bibtex_escape(v)}}}," for k, v in fields.items() if v
        ]
        if lines[-1].endswith(","):
            lines[-1] = lines[-1][:-1]
        lines.append("}")
        return "\n".join(lines)

    def export_bibtex(self):
        if not getattr(self, "results", None):
            messagebox.showwarning("Aviso", "Não há resultados para exportar."); return
        deduped, dstats = deduplicate_works(self.results)
        path = filedialog.asksaveasfilename(defaultextension=".bib", filetypes=[("BibTeX", "*.bib")])
        if not path: return
        try:
            entries = [self.to_bibtex_entry(w) for w in deduped]
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(entries) + "\n")
            messagebox.showinfo("Exportação", (f"BibTeX gravado em:\n{path}\n\n"
                                               f"Deduplicação — entrada: {dstats['input']}, mantidos: {dstats['kept']}"))
        except (OSError, PermissionError) as e:
            messagebox.showerror("Erro de ficheiro", f"{e}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha a gravar BibTeX: {e}")

    def export_html(self):
        res = self._ensure_rows()
        if res is None: return
        rows, _ = res
        path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("<!doctype html><meta charset='utf-8'><title>OpenAlex Results</title>\n")
                f.write("<table border='1' cellspacing='0' cellpadding='6'>\n")
                headers = FIELDNAMES
                f.write("<tr>"); [f.write(f"<th>{html.escape(h)}</th>") for h in headers]; f.write("</tr>\n")
                for r in rows:
                    f.write("<tr>")
                    for h in headers:
                        val = r.get(h, "")
                        if h in ("openalex_url", "url") and val:
                            cell = f"<a href='{html.escape(val)}' target='_blank'>link</a>"
                        else:
                            cell = html.escape(str(val))
                        f.write(f"<td>{cell}</td>")
                    f.write("</tr>\n")
                f.write("</table>")
            messagebox.showinfo("Exportação", f"HTML gravado em:\n{path}")
        except (OSError, PermissionError) as e:
            messagebox.showerror("Erro de ficheiro", f"{e}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha a gravar HTML: {e}")

    # ---------- Diagnóstico ----------
    def run_diag(self):
        try:
            params = {"search": "texture", "sort": "publication_date:desc", "per-page": 5, "select": "id,title"}
            batch = fetch_until_max(params, mailto=(self.email_var.get() or ""), per_page=5, max_results=5,
                                    logger=None, progress_cb=self._progress_tick)
            messagebox.showinfo("Diagnóstico", f"OK: recebi {len(batch)} itens.")
        except Exception as e:
            import logging
            logging.exception("Diagnóstico falhou")
            messagebox.showerror("Diagnóstico", f"Falhou: {e}")


# ---------------------- main ----------------------
logging.basicConfig(
    level=logging.DEBUG,  # durante diagnóstico
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("openalex_query.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    app = OpenAlexQueryApp()
    app.mainloop()

