# Roadmap to Legitimate 90+

**Verified 2026-05-20.** Current honest score: **~88/100** (not 90+).

Project identity: **bibliometric/scientometric research software with OpenAlex-based normalization, percentile indicators, network analysis, entity enrichment, and semantic tooling.**

**Baseline:** 99 tests passed; package coverage **76.4%**; `openalex_baselines.py` **≥92%**; GUI **245 lines** (was **869**); ruff clean on CI scope.

---

## Completed (this pass)

| Task | Status |
|------|--------|
| 1. Slim `software_gui_pro_4.py` (<600 lines) | **Done** — 245 lines; thin Tkinter shell |
| 2. Online pipeline in `core/pipeline.py` | **Done** — `run_online_pipeline`, `run_metrics_export`, `run_offline_metrics_export`, **`run_analysis`** |
| 3. ASJC/WoS crosswalks | **Deferred** — schema-only; `not_populated`; no fabricated mappings |
| 4. External validation scaffold | **Done** — `notebooks/external_validation_template.ipynb`, `docs/external_validation.md` |
| 5. `openalex_baselines.py` coverage | **Done** — module ≥92%; mocked global-fetch tests |
| 6. Streamlit pipeline runner | **Done** — `streamlit_pipeline_runner.py`, `dashboard/runner.py` |
| 7. `app_dashboard.py` import-safe | **Done** — `main()` guard; package helpers |
| 8. Package coverage ≥70% | **Done** — 76.4% |
| 9. Roadmap / docs | **Updated** |

## GUI call path

```
software_gui_pro_4.App.run()
  → PipelineConfig from GUI widgets
  → bibliometric_analysis.core.pipeline.run_online_pipeline(...)
    → parse_input / build_corpus / baselines / run_metrics_export / export_excel
```

## Online pipeline entry points

- `bibliometric_analysis.core.pipeline.run_analysis` (unified)
- `run_online_pipeline` (file path + OpenAlex)
- `run_offline_metrics_export` (records DataFrame, no network)
- `bibliometric_analysis.dashboard.runner.run_pipeline_from_upload` (Streamlit upload)

## Crosswalk status

| File | Status |
|------|--------|
| `asjc_openalex_crosswalk.csv` | `not_populated` (header only) |
| `wos_openalex_crosswalk.csv` | `not_populated` (header only) |
| `openalex_levels.csv` | schema reference only |

No formal ASJC/WoS↔OpenAlex alignment is claimed.

## Remaining blockers to legitimate 90+

1. Curated ASJC/WoS crosswalks with row-level provenance (real sources only)
2. **Executed** external validation notebook on reference data (template exists; not run)
3. Optional: repo-wide ruff (268 issues outside CI scope in legacy scripts)
4. UX consolidation (Tkinter + two Streamlit entry points)

## Commands

```bash
pytest tests/ -q
pytest tests/ --cov=bibliometric_analysis --cov-fail-under=70
pytest tests/test_e2e_offline_excel.py -q
python software_gui_pro_4.py
streamlit run streamlit_pipeline_runner.py
```

## Formulas & export schema

**Unchanged** in this pass. MNCS/cf, PP top 25/10/1, `compute_ppx`, histogram/quantile logic, Excel schema v1.0.
