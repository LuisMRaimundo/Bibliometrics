
# tests/test_percentiles.py
import numpy as np
import pandas as pd

from metrics.percentiles import _pp_col_name, compute_ppx


def test_pp_col_name():
    assert _pp_col_name(0.90) == "pp10"
    assert _pp_col_name(0.99) == "pp1"
    assert _pp_col_name(0.995) == "pp0.5"

def test_basic_group_thresholds():
    df = pd.DataFrame({
        "year": [2020]*5 + [2021]*5,
        "field": ["A"]*10,
        "score": [0,1,2,3,4,  10,20,30,40,50]
    })
    out = compute_ppx(df, "score", by=["year","field"], p=0.80, ties=">=threshold")
    assert "pp20" in out.columns
    thr_2020 = out.loc[out["year"]==2020, "ppx_threshold"].iloc[0]
    assert np.isclose(thr_2020, 3.2)
    thr_2021 = out.loc[out["year"]==2021, "ppx_threshold"].iloc[0]
    assert np.isclose(thr_2021, 42.0)
    assert out.loc[(out["year"]==2020) & (out["score"]==4), "pp20"].iloc[0] == 1
    assert out.loc[(out["year"]==2020) & (out["score"]==3), "pp20"].iloc[0] == 0

def test_ties_policy_strict():
    df = pd.DataFrame({
        "year": [2020]*5,
        "field": ["A"]*5,
        "score": [1,2,3,4,5]
    })
    out = compute_ppx(df, "score", by=["year","field"], p=0.80, ties=">threshold")
    assert out["pp20"].sum() == 1
    assert out.loc[out["score"]==5, "pp20"].iloc[0] == 1

def test_missing_scores_and_empty_groups():
    df = pd.DataFrame({
        "year": [2020,2020,2021,2021],
        "field": ["A","A","B","B"],
        "score": [np.nan, np.nan, 10, np.nan]
    })
    out = compute_ppx(df, "score", by=["year","field"], p=0.90)
    assert out.loc[(out["year"]==2020)&(out["field"]=="A"), "pp10"].sum() == 0
    assert out.loc[(out["year"]==2020)&(out["field"]=="A"), "ppx_threshold"].isna().all()
    assert out.loc[(out["year"]==2021)&(out["field"]=="B"), "pp10"].sum() == 1

def test_no_groups_global_threshold():
    df = pd.DataFrame({"score": [0, 1, 2, 3, 4]})
    out = compute_ppx(df, "score", by=[], p=0.60)
    assert out["pp40"].sum() == 2
    assert np.isclose(out["ppx_threshold"].iloc[0], 2.4)
