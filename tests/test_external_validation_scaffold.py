"""External validation scaffold presence tests."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_external_validation_notebook_exists():
    nb = ROOT / "notebooks" / "external_validation_template.ipynb"
    assert nb.exists()
    text = nb.read_text(encoding="utf-8")
    assert "pending external reference data" in text.lower()
    assert "NotImplementedError" in text or "TODO" in text


def test_external_validation_docs_exist():
    doc = ROOT / "docs" / "external_validation.md"
    assert doc.exists()
    body = doc.read_text(encoding="utf-8")
    assert "no equivalence claims" in body.lower() or "No equivalence claims" in body
    assert "fabricated" in body.lower() or "No fabricated" in body
