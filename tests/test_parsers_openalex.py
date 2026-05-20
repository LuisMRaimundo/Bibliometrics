import pandas as pd

from bibliometric_analysis.parsers.openalex_csv import looks_like_openalex_csv, parse_openalex_csv


def test_openalex_parse():
    df = parse_openalex_csv("tests/fixtures/minimal_openalex.csv")
    assert len(df) == 1
    assert df["doi"].iloc[0] == "10.1000/test.oa3"


def test_looks_like_openalex():
    df = pd.read_csv("tests/fixtures/minimal_openalex.csv")
    assert looks_like_openalex_csv(df)
