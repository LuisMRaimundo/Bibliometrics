# Architecture (v16)

```
Bibliometric analysis_15/
├── bibliometric_analysis/          # Canonical importable package
│   ├── openalex/                   # Shared HTTP cache + client
│   ├── baselines/                  # Histogram c₀, quantiles
│   ├── metrics/                    # MNCS, PP, bootstrap, fractional
│   ├── parsers/                    # WoS, Scopus, OpenAlex, PoP
│   ├── network/                    # Edges, PageRank, communities
│   ├── export/                     # Excel + run metadata
│   ├── ontology/                   # Crosswalk registry (templates)
│   └── enrichment/                 # Author/institution harvest
├── software_gui_pro_4.py           # Legacy entry; partial re-exports
├── app_dashboard.py                # Streamlit (primary analytics UI)
├── metrics/                        # Compatibility shim → package
├── data/ontology/                  # Crosswalk CSV templates
├── tests/                          # 59+ unit tests
└── docs/                           # v16 documentation
```

## Data flow (unchanged semantically)

Input → parsers → corpus + OpenAlex enrichment → baselines → MNCS/PP → network → Excel export + metadata.

## Compatibility

Root scripts and `metrics.percentiles` import paths preserved.
