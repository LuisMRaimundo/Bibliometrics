# Ontology / Crosswalk Data

These CSV files define the schema for field/category crosswalks between classification schemes.

**Status (v16):** Template files only — **not populated** with real ASJC/WoS↔OpenAlex mappings.

Do not claim formal ontology alignment until curated mappings are added with provenance.

## Files

| File | Purpose |
|------|---------|
| `openalex_levels.csv` | Documents OpenAlex concept levels (schema reference) |
| `asjc_openalex_crosswalk.csv` | ASJC → OpenAlex (empty template) |
| `wos_openalex_crosswalk.csv` | WoS categories → OpenAlex (empty template) |

## Required columns (crosswalk tables)

- `source_scheme`, `source_id`, `source_label`
- `target_scheme`, `target_id`, `target_label`
- `mapping_type`: exact | close | broad | narrow | related | manual | unknown
- `confidence`: high | medium | low | unknown
- `provenance`, `version`, `notes`

## Usage

```python
from bibliometric_analysis.ontology import CrosswalkRegistry

registry = CrosswalkRegistry()
assert not registry.is_populated("asjc_openalex_crosswalk")
result = registry.map_label("ASJC", "Computer Science", "OpenAlex")
# result.warning indicates missing crosswalk
```
