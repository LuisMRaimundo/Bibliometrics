import numpy as np
import pandas as pd

from bibliometric_analysis.metrics.mncs import add_cf_and_pp_global, effective_citation_count, pp_flag


def _globals_df():
    return pd.DataFrame(
        {
            "domain_id": ["C1", "C2"],
            "year": [2020, 2021],
            "c0_mean": [5.0, 1.0],
            "thr_top25": [8, 1],
            "thr_top10": [9, 2],
            "thr_top1": [15, 5],
            "c0_n": [100, 50],
            "c0_complete": [True, True],
            "c0_counts_json": ["", ""],
        }
    )


def test_pp_flag_closed():
    assert pp_flag(10, 10, "closed_ge") == 1
    assert pp_flag(9, 10, "closed_ge") == 0


def test_pp_flag_open():
    assert pp_flag(10, 10, "open_gt") == 0
    assert pp_flag(11, 10, "open_gt") == 1


def test_pp_flag_nan():
    assert np.isnan(pp_flag(np.nan, 5, "closed_ge"))


def test_mncs_cf():
    df = pd.DataFrame(
        {
            "domain_id": ["C1", "C1", "C2"],
            "year": [2020, 2020, 2021],
            "c_use": [10, 4, 2],
        }
    )
    out = add_cf_and_pp_global(df, _globals_df(), ties_policy="closed_ge")
    assert np.isclose(out.loc[0, "cf"], 2.0)
    assert np.isclose(out.loc[1, "cf"], 0.8)
    assert np.isclose(out.loc[2, "cf"], 2.0)


def test_pp_top_flags():
    df = pd.DataFrame(
        {
            "domain_id": ["C1", "C1"],
            "year": [2020, 2020],
            "c_use": [20, 4],
        }
    )
    out = add_cf_and_pp_global(df, _globals_df(), ties_policy="closed_ge")
    assert out.loc[0, "PPg_top10"] == 1
    assert out.loc[1, "PPg_top10"] == 0


def test_c0_zero_no_cf():
    df = pd.DataFrame({"domain_id": ["X"], "year": [2020], "c_use": [5]})
    g = pd.DataFrame(
        {
            "domain_id": ["X"],
            "year": [2020],
            "c0_mean": [0],
            "thr_top25": [1],
            "thr_top10": [2],
            "thr_top1": [3],
            "c0_n": [1],
            "c0_complete": [True],
            "c0_counts_json": [""],
        }
    )
    out = add_cf_and_pp_global(df, g)
    assert pd.isna(out.loc[0, "cf"])


def test_effective_citation_window():
    df = pd.DataFrame({"c_use": [1], "c_use_window": [99]})
    assert effective_citation_count(df).iloc[0] == 99


def test_golden_fixture_match():
    raw = pd.read_csv("tests/fixtures/synthetic_corpus_metrics.csv")
    g = raw[
        [
            "domain_id",
            "year",
            "c0_mean",
            "thr_top25",
            "thr_top10",
            "thr_top1",
            "c0_n",
            "c0_complete",
            "c0_counts_json",
        ]
    ].drop_duplicates()
    inp = raw[["domain_id", "year", "c_use"]]
    out = add_cf_and_pp_global(inp, g, ties_policy="closed_ge")
    assert list(out["cf"].round(1)) == [2.0, 0.8, 4.0, 2.0]
    assert list(out["PPg_top10"].astype(int)) == [1, 0, 1, 1]
    assert out.loc[out["c_use"] == 20, "PPg_top1"].iloc[0] == 1
    assert out.loc[out["c_use"] == 4, "PPg_top25"].iloc[0] == 0
