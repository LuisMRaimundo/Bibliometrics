# Dependencies

See `pyproject.toml` for authoritative dependency groups.

## Core (required)

| Package | Purpose |
|---------|---------|
| pandas | DataFrames, Excel I/O |
| numpy | Numerical metrics |
| requests | OpenAlex HTTP |
| tqdm | Progress (optional in GUI) |
| XlsxWriter | Excel export |
| openpyxl | Excel read |
| networkx | Citation networks |

## Optional extras

| Extra | Packages | Used by |
|-------|----------|---------|
| `network` | pyvis, python-louvain, igraph, leidenalg | Network viz, Leiden/Louvain |
| `dashboard` | streamlit, scikit-learn | `app_dashboard.py` |
| `enrichment` | rapidfuzz | Entity deduplication |
| `topic` | sentence-transformers, umap-learn, hdbscan, bertopic | BERTopic pipeline |
| `dev` | pytest, pytest-cov, ruff | Tests and lint |

## Install

```bash
pip install -e .
pip install -e ".[dashboard,network,enrichment,topic,dev]"
```

Legacy root `requirements.txt` lists core packages only.
