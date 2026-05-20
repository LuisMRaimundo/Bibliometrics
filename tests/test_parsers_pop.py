import pandas as pd

from bibliometric_analysis.parsers.pop import looks_like_pop_csv, parse_pop_csv


def test_pop_parse():
    df = parse_pop_csv("tests/fixtures/minimal_pop.csv")
    assert len(df) >= 1
    assert df["cited_by_count"].iloc[0] == 25


def test_looks_like_pop():
    df = pd.read_csv("tests/fixtures/minimal_pop.csv")
    assert looks_like_pop_csv(df)
