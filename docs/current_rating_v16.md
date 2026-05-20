# Current Rating v16 — Honest Assessment

**Project:** Bibliometric/scientometric research software with OpenAlex-based normalization, percentile indicators, network analysis, entity enrichment, and semantic tooling.

**Date:** 2026-05-20  
**Version assessed:** 16.0.0 (upgrade pass from v15)

---

## Rubric (100 points)

| Criterion | Max | Score | Evidence |
|-----------|-----|-------|----------|
| Bibliometric methodology | 25 | **23** | MNCS/PP/baselines preserved; formulas regression-tested; no external benchmark validation |
| Software architecture | 20 | **16** | Package `bibliometric_analysis/`; partial GUI decomposition; main GUI still ~1,200 lines |
| Tests & reproducibility | 15 | **13** | 59 tests (was 9); fixtures; CI workflow; no live API tests; coverage not yet ≥80% |
| Ontologies & linguistics | 15 | **10** | Crosswalk scaffolding + provenance; **templates not populated**; heuristic macro-areas retained |
| UX / web design | 10 | **7** | Streamlit-first strategy documented; Tkinter fragmentation unchanged |
| Documentation | 10 | **9** | README, audit, export schema, dependencies, UX strategy; manual partially updated |
| Packaging / maintainability | 5 | **5** | pyproject.toml, optional extras, ruff, shared OpenAlex client |
| **Total** | **100** | **83** | |

---

## Verdict

**Score: 83 / 100** — meaningful upgrade from ~81 (v15 review), **not yet legitimate 90+**.

**Doctoral percentile (bibliometric research software): ~90th** — improved testability and structure; still below field-standard platforms.

---

## What improved in v16

- Installable package with optional dependency groups
- Shared OpenAlex HTTP/cache (`bibliometric_analysis/openalex/`)
- Extracted metrics, baselines, parsers, network, export modules
- `enrich_entities.py` cleaned (no citation artifacts; shared client)
- Ontology crosswalk **schema** with honest empty templates
- 59 automated tests, GitHub Actions CI, ruff
- Excel schema documented and tested
- `software_gui_pro_4.py` partially decomposed (HTTP, metrics, export)

---

## Remaining blockers to 90+

1. **Complete GUI decomposition** — parsers, OpenAlex corpus build, community detection still in monolith
2. **Query tool** not on shared client
3. **Crosswalk tables not populated** — no formal ASJC/WoS alignment
4. **Dashboard** executes at import; not refactored to core modules
5. **Integration tests** for full pipeline on fixture Excel end-to-end
6. **Coverage ≥70%** on `bibliometric_analysis/`
7. **Streamlit pipeline runner** not implemented
8. **No validation study** against CWTS/Leiden/bibliometrix reference outputs (and none claimed)

---

## Formulas changed?

**No.** MNCS, PP flags, histogram quantiles, fractional counting, and export columns unchanged. Verified by unit/golden tests.

---

## False claims avoided

- Not equivalent to SciVal, Dimensions, VOSviewer, Citespace, or bibliometrix
- Not a commercial analytics platform
- Crosswalk alignment not claimed until tables are curated

See `docs/upgrade_roadmap_to_90.md` for next steps.
