# Testing

## Run all tests

```bash
pytest tests/ -q
```

## With coverage (CI gate)

```bash
pytest tests/ --cov=bibliometric_analysis --cov-fail-under=70 --cov-report=term-missing
```

## External validation

Template only — see `docs/external_validation.md` and `notebooks/external_validation_template.ipynb`. No equivalence claims until executed on reference data.

## End-to-end offline test

```bash
pytest tests/test_e2e_offline_excel.py -q
```

Fixture path: `tests/fixtures/e2e/minimal_openalex.csv` → parse → local baseline → Excel. Network calls are monkeypatched to fail.

## Dashboard import safety

```bash
python -c "import app_dashboard; print('ok')"
```

Streamlit UI runs only when executing `streamlit run app_dashboard.py` (via `main()`).

## Lint

```bash
ruff check bibliometric_analysis tests metrics
```

## Policies

- **No live OpenAlex calls** in unit tests (mocked transport or fixtures)
- Optional deps: tests skip or fallback when igraph/leiden/rapidfuzz absent
- Golden metrics tests use synthetic CSV fixtures under `tests/fixtures/`

## CI

GitHub Actions workflow: `.github/workflows/tests.yml` (pytest + ruff on Python 3.10/3.11)
