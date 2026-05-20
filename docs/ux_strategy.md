# UX Strategy (v16)

## Primary UI: Streamlit dashboard

`streamlit run app_dashboard.py` is the **recommended analytical shell** for post-export inspection: overview, PPx recomputation, sensitivity, QA.

## Legacy UI: Tkinter tools (retained)

| Script | Role |
|--------|------|
| `software_gui_pro_4.py` | Full bibliometric pipeline |
| `viz_network_interface_2.py` | Network visualization GUI |
| `Query_OpenAlex/openalex_query_7.py` | OpenAlex query |
| `TEXTS SELECT/select_texts_gui_v7_intelligent.py` | Reading-list selection |

These remain functional; not rewritten in v16.

## CLI tools

- `openalex_converter.py`, `enrich_entities.py`, `viz_network_plus.py`, `semantic_bertopic_preset.py`

## Expected user flow (target)

1. Run main pipeline (`software_gui_pro_4.py` or future Streamlit runner)
2. Upload Excel to Streamlit dashboard
3. Inspect metrics, sensitivity, network HTML
4. Optional: enrichment, BERTopic, text selection via CLI/legacy GUIs

## Path conventions

- New code uses `bibliometric_analysis/` package paths without spaces.
- Legacy folder `TEXTS SELECT/` documented but not renamed (breaking path risk).

## Future work

- Streamlit page for ontology mapping diagnostics
- Streamlit integration with shared `bibliometric_analysis` core (partial in v16)
- Unified launcher app
