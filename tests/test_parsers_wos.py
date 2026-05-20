from pathlib import Path

from bibliometric_analysis.parsers.wos import parse_wos_txt

FIX = Path("tests/fixtures/minimal_wos.txt")


def test_wos_parse_count():
    df = parse_wos_txt(str(FIX))
    assert len(df) == 2


def test_wos_doi():
    df = parse_wos_txt(str(FIX))
    assert "10.1000/test.wos1" in df["doi"].values


def test_wos_refs():
    df = parse_wos_txt(str(FIX))
    row = df[df["doi"] == "10.1000/test.wos1"].iloc[0]
    assert "10.1000/test.wos2" in row["ref_dois"]
