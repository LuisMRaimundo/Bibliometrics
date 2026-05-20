# Ontology Layer (v16)

## Status: scaffolding only

Crosswalk CSV files under `data/ontology/` define schema but contain **no curated mappings**.

## Components

| Module | Role |
|--------|------|
| `ontology/normalize.py` | NFKD unaccent, whitespace normalization |
| `ontology/concepts.py` | OpenAlex concept level selection |
| `ontology/crosswalk.py` | `CrosswalkRegistry` with provenance + warnings |
| `ontology/provenance.py` | Heuristic macro-areas (low confidence) |

## Usage

```python
from bibliometric_analysis.ontology import CrosswalkRegistry, simplify_area_name_heuristic

reg = CrosswalkRegistry()
result = reg.map_label("WoS", "Computer Science")
# result.warning when table empty

macro, confidence = simplify_area_name_heuristic("Machine Learning")
# confidence == "low"
```

## Export metadata (future)

When crosswalks are populated, exports should include: `concept_scheme`, `mapping_type`, `confidence`, `provenance`.

## Limitations (honest)

- No SKOS/Wikidata integration in v16
- No validation against ASJC or WoS official taxonomies
- Heuristic `simplify_area_name` remains in text-selection tools until crosswalks replace it
