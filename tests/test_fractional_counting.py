import json

import pandas as pd

from bibliometric_analysis.metrics.fractional import explode_multifield_fractional


def _record(concepts, n_auth=2, n_aff=2):
    return pd.DataFrame(
        [
            {
                "idx": 1,
                "year": 2020,
                "cf": 1.5,
                "PPg_top1": 0,
                "PPg_top10": 1,
                "PPg_top25": 1,
                "domain_id": "D0",
                "domain_label": "Root",
                "n_authors": n_auth,
                "n_affiliations": n_aff,
                "concepts_lvl": json.dumps(concepts),
            }
        ]
    )


def test_fractional_equal():
    rec = _record([["C1", "Field A"], ["C2", "Field B"]])
    out = explode_multifield_fractional(rec, "equal")
    assert len(out) == 2
    assert abs(out["w_concept"].sum() - 1.0) < 1e-9


def test_fractional_score():
    rec = _record([["C1", "A", 3], ["C2", "B", 1]])
    out = explode_multifield_fractional(rec, "score")
    w = out.set_index("domain_id")["w_concept"]
    assert abs(w["C1"] - 0.75) < 1e-9


def test_fractional_w_total():
    rec = _record([["C1", "A"]])
    out = explode_multifield_fractional(rec, "equal")
    assert out["w_total"].iloc[0] > 0
