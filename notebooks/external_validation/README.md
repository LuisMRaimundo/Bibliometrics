# External validation scaffold

This folder holds **optional** validation notebooks comparing outputs against external reference tools.

## Status: scaffold only — no equivalence claims

This project is **bibliometric/scientometric research software with OpenAlex-based normalization, percentile indicators, network analysis, entity enrichment, and semantic tooling.**

We do **not** claim equivalence to SciVal, Dimensions, Leiden Ranking, VOSviewer, Citespace, or bibliometrix unless a notebook here documents a reproducible benchmark with:

1. Public input fixture(s)
2. Reference tool version and parameters
3. Side-by-side metric definitions
4. Documented tolerances and known divergences
5. Signed provenance (date, author, commit hash)

## Planned notebooks (not yet executed)

| Notebook | Purpose | Blocker |
|----------|---------|---------|
| `01_mncs_pp_synthetic.ipynb` | MNCS/cf and PP flags on synthetic corpus vs hand-calculated reference | Needs curated public fixture |
| `02_bibliometrix_local.ipynb` | Compare local-baseline MNCS on tiny WoS export vs bibliometrix R | Needs bibliometrix install + fixture |
| `03_openalex_baseline_histogram.ipynb` | Histogram quantiles vs OpenAlex API snapshot (frozen JSON) | Needs frozen API fixture |

## How to add a validation notebook

1. Add fixture under `tests/fixtures/validation/`
2. Copy `templates/validation_notebook_template.md` checklist
3. Record software version from `bibliometric_analysis.__version__`
4. Never fabricate crosswalk or baseline mappings
5. Update `docs/upgrade_roadmap_to_90.md` only after notebook passes locally

## Run offline pipeline in a notebook (smoke)

```python
from pathlib import Path
import pandas as pd
from bibliometric_analysis.core.pipeline import run_offline_metrics_export
from bibliometric_analysis.core.config import PipelineConfig

records = pd.read_csv("tests/fixtures/synthetic_corpus_metrics.csv")
run_offline_metrics_export(records, "tmp_validation_out.xlsx", config=PipelineConfig())
```
