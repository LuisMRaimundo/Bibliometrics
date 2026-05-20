from bibliometric_analysis.ontology import CrosswalkRegistry, normalize_label, simplify_area_name_heuristic
from bibliometric_analysis.ontology.normalize import unaccent


def test_unaccent():
    assert "acao" in unaccent("ação").lower() or unaccent("ação") == "acao"


def test_normalize_label():
    assert normalize_label("  Hello   World  ") == "Hello World"


def test_crosswalk_not_populated():
    from bibliometric_analysis.ontology.crosswalk import report_mapping_status

    reg = CrosswalkRegistry()
    assert not reg.is_populated("asjc_openalex_crosswalk")
    r = reg.map_label("ASJC", "Computer Science")
    assert r.warning is not None
    assert r.target_id is None
    status = report_mapping_status()
    assert status.get("asjc_openalex_crosswalk") in ("not_populated", "schema_only")


def test_heuristic_low_confidence():
    name, conf = simplify_area_name_heuristic("Computer Vision")
    assert name == "Computer Science"
    assert conf == "low"
