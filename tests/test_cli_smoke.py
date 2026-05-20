import bibliometric_analysis
from metrics.percentiles import compute_ppx


def test_package_import():
    assert bibliometric_analysis.__version__ == "16.0.0"


def test_legacy_percentiles_import():
    import pandas as pd
    df = pd.DataFrame({"score": [1, 2, 3]})
    out = compute_ppx(df, "score", by=[], p=0.5)
    assert "pp50" in out.columns
