# Upgrade Audit v16 — Bibliometric Analysis System

**Date:** 2026-05-20  
**Baseline version:** v15  
**Target:** research-software profile toward 90+ (honest assessment)

---

## 1. Baseline Test Results (pre-upgrade)

| Metric | Value |
|--------|-------|
| Tests collected | 9 |
| Passed | 9 |
| Failed | 0 |
| Import errors | 0 |
| Dependency errors | 0 |

Command: `pytest tests/ -q`

---

## 2. Active Modules

| Module | Role | Lines (approx.) |
|--------|------|-----------------|
| `software_gui_pro_4.py` | Main Tkinter engine (monolith) | ~1,600 |
| `app_dashboard.py` | Streamlit post-analysis dashboard | ~475 |
| `openalex_converter.py` | OpenAlex CSV → Scopus-like CSV | ~280 |
| `enrich_entities.py` | Author/institution enrichment | ~290 |
| `viz_network_plus.py` | CLI network visualization | ~260 |
| `viz_network_interface_2.py` | Tkinter network GUI | ~340 |
| `semantic_bertopic_preset.py` | BERTopic topic modelling | ~170 |
| `Query_OpenAlex/openalex_query_7.py` | OpenAlex query GUI | ~1,080 |
| `TEXTS SELECT/select_texts_gui_v7_intelligent.py` | Text selection GUI | ~540 |
| `TEXTS SELECT/excel_analyzer.py` | Excel quality analyzer | ~400 |
| `metrics/percentiles.py` | PPx computation | ~45 |
| `tests/` | Unit tests | 9 tests |

## 3. Legacy / Compatibility (retained)

- Root-level scripts remain as entry points during incremental migration.
- `TEXTS SELECT/` folder (space in path) — legacy; documented, not renamed in v16 pass.
- PDF manuals (`Manual_bibliometria.pdf`, etc.) — retained; not archived.

## 4. Duplicated Infrastructure

| Component | Locations |
|-----------|-----------|
| SQLite HTTP cache | `software_gui_pro_4.py`, `enrich_entities.py` |
| `http_get` + backoff | `software_gui_pro_4.py`, `enrich_entities.py` |
| Network metrics | `software_gui_pro_4.py`, `viz_network_plus.py` |
| Column synonym resolution | `app_dashboard.py`, `select_texts_gui_v7`, `excel_analyzer.py` |
| Abstract inverted-index rebuild | `openalex_converter.py`, `openalex_query_7.py` |

## 5. Public Entry Points

| Entry | Type |
|-------|------|
| `python software_gui_pro_4.py` | Tkinter GUI (main pipeline) |
| `streamlit run app_dashboard.py` | Streamlit dashboard |
| `python openalex_converter.py` | CLI/GUI converter |
| `python enrich_entities.py` | CLI enrichment |
| `python viz_network_plus.py` | CLI network viz |
| `python viz_network_interface_2.py` | Tkinter network GUI |
| `python semantic_bertopic_preset.py` | CLI BERTopic |
| `python Query_OpenAlex/openalex_query_7.py` | OpenAlex query GUI |
| `python TEXTS SELECT/select_texts_gui_v7_intelligent.py` | Text selection GUI |

## 6. Exported Excel Sheet Names (stable — do not change)

1. `Records+Metrics`
2. `Edges`
3. `Network Metrics`
4. `Summary (integer)`
5. `Summary (fractional)`
6. `Global Dist/Thresholds`
7. `Run Metadata`

## 7. Metric Formulas and Names (regression boundary)

| Metric | Formula / rule |
|--------|----------------|
| MNCS (`cf`, `c_f`) | `c_use_eff / c0_mean` where `c_use_eff = c_use_window` if present else `c_use` |
| PP top 25% (`PPg_top25`) | `c_use_eff >= thr_top25` (ties: `closed_ge` default) |
| PP top 10% (`PPg_top10`) | `c_use_eff >= thr_top10` |
| PP top 1% (`PPg_top1`) | `c_use_eff >= thr_top1` |
| Baseline c₀ | Mean from citation-count histogram |
| Thresholds | Quantiles at p=0.75, 0.90, 0.99 (`cdf_min` or `hazen`) |
| Fractional weights | `w_concept × w_author × w_affil` |

Ties policies: `closed_ge`, `open_gt`, `hazen` (maps to quantile method).

## 8. Dependency Gaps (pre-upgrade)

**`requirements.txt` listed:** pandas, requests, tqdm, XlsxWriter

**Actually required (core):** pandas, numpy, requests, tqdm, XlsxWriter, openpyxl, networkx

**Optional groups:** pyvis, python-louvain, igraph, leidenalg, streamlit, scikit-learn, rapidfuzz, sentence-transformers, umap-learn, hdbscan, bertopic

## 9. Missing Tests (pre-upgrade)

- MNCS / cf computation
- Histogram mean/quantile
- Bootstrap MNCS
- Fractional counting
- WoS/Scopus/OpenAlex/PoP parsers
- Network edge building / PageRank / communities
- OpenAlex HTTP cache/client
- Entity enrichment
- Export schema / metadata
- Ontology crosswalk
- Dashboard import smoke (partial via test_imports)

## 10. Ontology Gaps

- No ASJC / WoS / OpenAlex crosswalk tables
- `simplify_area_name()` uses substring heuristics only
- OpenAlex concept level selection inline in main engine
- No provenance metadata on field mappings

## 11. UX Entry Points (fragmented)

- 4+ Tkinter GUIs
- 1 Streamlit dashboard
- 6+ CLI scripts
- Folder `TEXTS SELECT` with space in path

## 12. High-Risk Refactors

| Risk | Mitigation |
|------|------------|
| Changing MNCS/PP formulas | Golden fixtures + regression tests before any change |
| Breaking Excel schema | Schema version + export tests |
| Moving GUI code | Compatibility re-exports in `software_gui_pro_4.py` |
| OpenAlex API behaviour change | Shared client with mocked tests only |
| Package import paths | Keep root `metrics.percentiles` shim |

## 13. Safe First Extractions (v16 pass)

1. `pyproject.toml` + dependency extras
2. `bibliometric_analysis/openalex/{cache,client}.py`
3. `bibliometric_analysis/baselines/histograms.py`
4. `bibliometric_analysis/metrics/{mncs,bootstrap,fractional}.py`
5. `bibliometric_analysis/parsers/*` + `parsers/common.py`
6. `bibliometric_analysis/network/{build,metrics}.py`
7. `bibliometric_analysis/export/{excel,metadata,schemas}.py`
8. `bibliometric_analysis/ontology/*` (scaffolding only)
9. `enrich_entities.py` → shared client + artifact cleanup
10. CI + expanded test suite

## 14. Documentation Claims (pre-upgrade)

- TECHNICAL_MANUAL.md describes v15 architecture accurately
- Manual lists full dependency set (broader than requirements.txt)
- No false claims of SciVal/Dimensions equivalence
- Self-evaluation docs in TEXTS SELECT/ (v6 score 78/100)

## 15. Copy-Paste Artifacts

Found in `enrich_entities.py` lines 129, 137, 176, 192, 242: `:contentReference[oaicite:...]` — **to be removed in v16**.

---

*This document is the regression boundary reference for the v16 upgrade pass.*
