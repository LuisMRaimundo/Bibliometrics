# Export Schema (v1.0)

Stable Excel export from the main pipeline. **Do not rename sheets or core columns without a schema version bump.**

## Sheets

| Sheet | Required | Description |
|-------|----------|-------------|
| Records+Metrics | Yes | One row per work; MNCS and PP flags |
| Edges | Yes | Citation edges (`citer_idx`, `cited_idx`) |
| Network Metrics | Yes | Per-node network statistics (may be empty) |
| Summary (integer) | Yes | Unit summaries (integer counting; may be empty) |
| Summary (fractional) | Yes | Unit summaries (fractional counting; may be empty) |
| Global Dist/Thresholds | Yes | Baseline c₀ and thresholds (may be empty for local-only runs) |
| Run Metadata | Yes | Reproducibility key/value pairs |

## Records+Metrics core columns

`idx`, `title`, `year`, `domain_label`, `domain_id`, `doi`, `cited_by_count`, `c_use`, `c_use_window`, `is_retracted`, `c0_mean`, `cf`, `PPg_top1`, `PPg_top10`, `PPg_top25`, `n_authors`, `n_affiliations`, `is_focal`

## Metric definitions (unchanged in v16)

- **cf (MNCS):** `c_use_eff / c0_mean` where `c_use_eff = c_use_window` if present else `c_use`
- **PPg_top25/10/1:** Compare `c_use_eff` to `thr_top25/10/1` with ties policy `closed_ge` by default

## Run Metadata keys (v16+)

- `software_version`, `metric_schema_version`, `export_schema_version`
- `run_timestamp_utc`, `input_file_hash`, `config_hash`
- `config.*` — pipeline settings
- `optional.*` — availability of optional dependencies
- `warning.*` — non-fatal issues

Implementation: `bibliometric_analysis/export/`
