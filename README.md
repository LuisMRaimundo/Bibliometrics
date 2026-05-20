# Bibliometric Analysis System v16

Bibliometric/scientometric research software with OpenAlex-based normalization, percentile indicators, network analysis, entity enrichment, and semantic tooling.

**Repository:** [github.com/LuisMRaimundo/Bibliometrics](https://github.com/LuisMRaimundo/Bibliometrics)

**Not** a commercial analytics platform. Not validated against SciVal, Dimensions, VOSviewer, Citespace, or bibliometrix.

## Quick start (no Python experience)

| Platform | Install (once) | Run |
|----------|----------------|-----|
| **Windows 10/11** | Double-click **`install.bat`** | Double-click **`run.bat`** |
| **macOS** | Double-click **`install-mac.command`** | `./run.sh` in Terminal |
| **Linux** | `./install.sh` | `./run.sh` |

See **[INSTALL.md](INSTALL.md)** for troubleshooting and details.

## Install (developers)

```bash
git clone https://github.com/LuisMRaimundo/Bibliometrics.git
cd Bibliometrics
pip install -e .
pip install -e ".[dashboard,network,enrichment,topic,dev]"  # optional groups
```

## Applications

```bash
# Main Tkinter pipeline (tool launcher buttons for Streamlit, OpenAlex query, etc.)
python software_gui_pro_4.py

# Streamlit dashboard (post-export analysis)
streamlit run app_dashboard.py

# Streamlit pipeline runner (upload → Excel)
streamlit run streamlit_pipeline_runner.py

# Enrichment (CLI)
python enrich_entities.py dataset.xlsx --mailto you@institution.edu
```

## Tests

```bash
pytest tests/ -q
pytest tests/ --cov=bibliometric_analysis --cov-fail-under=70
pytest tests/test_e2e_offline_excel.py -q
ruff check bibliometric_analysis tests metrics
```

Coverage gate: **≥70%** on `bibliometric_analysis/` (see `pyproject.toml`).

## Package layout

Core logic lives in `bibliometric_analysis/` including `dashboard/` (Streamlit helpers), `core/pipeline.py` (`run_analysis`, `run_online_pipeline`, offline export), and `openalex/` (shared client). Root scripts remain compatibility entry points.

**Formulas and Excel export schema v1.0 are unchanged** in recent refactors. The Tkinter GUI is a thin caller into `core/pipeline.py`. ASJC/WoS crosswalks are **deferred** (schema-only; see `docs/ontology_layer.md`). External validation is **template only** — no equivalence claims (see `docs/external_validation.md`).

- `software_gui_pro_4.py` — Tkinter GUI + thin wrappers
- `app_dashboard.py` — import-safe Streamlit shell (`main()`)
- `Query_OpenAlex/openalex_query_7.py` — query GUI (shared OpenAlex client)

See `docs/upgrade_roadmap_to_90.md`, `TECHNICAL_MANUAL.md`, and `docs/export_schema.md`.

## License

MIT — see [LICENSE](LICENSE).
