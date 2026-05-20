# External Validation

**Status: template / pending external reference data**

This project is **bibliometric/scientometric research software with OpenAlex-based normalization, percentile indicators, network analysis, entity enrichment, and semantic tooling.**

## Policy

- **No equivalence claims** to SciVal, Dimensions, Leiden Ranking, VOSviewer, Citespace, or bibliometrix unless a completed validation notebook documents tolerances and methodological alignment.
- **No fabricated validation results** in documentation or notebooks.
- **No live dataset downloads** in CI or default tests.

## Artifacts

| Path | Purpose |
|------|---------|
| `notebooks/external_validation_template.ipynb` | Jupyter template (sections only; no results) |
| `notebooks/external_validation/README.md` | Extended scaffold notes |
| `notebooks/external_validation/templates/validation_notebook_template.md` | Checklist for future runs |

## Template notebook sections

1. Load reference benchmark (manual / curated file)
2. Load system Excel export
3. Align records by DOI or OpenAlex ID
4. Compare MNCS/cf
5. Compare PP top 25/10/1 indicators
6. Compare baseline thresholds (c₀, q75/q90/q99)
7. Compare field/year assignments
8. Compare network metrics (if applicable)
9. Report deviations and methodological incompatibilities

## Offline smoke (no reference data)

```python
from bibliometric_analysis.core.pipeline import run_offline_metrics_export
from bibliometric_analysis.core.config import PipelineConfig
import pandas as pd

records = pd.read_csv("tests/fixtures/synthetic_corpus_metrics.csv")
run_offline_metrics_export(records, "tmp_validation_out.xlsx", config=PipelineConfig())
```

## When validation is complete

Update this document with:

- Reference source and version
- Fixture paths
- Tolerance table per metric
- Known non-comparable dimensions
- Link to executed notebook with commit hash

Do not update marketing or roadmap to claim 90+ until validation criteria are met.
