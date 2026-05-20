from bibliometric_analysis.parsers.scopus import parse_scopus_csv


def test_scopus_parse():
    df = parse_scopus_csv("tests/fixtures/minimal_scopus.csv")
    assert len(df) == 2
    assert "doi" in df.columns


def test_scopus_titles():
    df = parse_scopus_csv("tests/fixtures/minimal_scopus.csv")
    assert df["title"].notna().any()
