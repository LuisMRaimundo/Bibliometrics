"""GUI launcher helpers (no subprocess execution in tests)."""

from __future__ import annotations

from pathlib import Path

from bibliometric_analysis.gui import launchers


def test_project_root_resolves():
    root = launchers.project_root()
    assert (root / "software_gui_pro_4.py").exists()
    assert (root / "bibliometric_analysis").is_dir()


def test_streamlit_scripts_exist():
    root = launchers.project_root()
    assert (root / "app_dashboard.py").exists()
    assert (root / "streamlit_pipeline_runner.py").exists()


def test_companion_guis_exist():
    root = launchers.project_root()
    assert (root / "Query_OpenAlex" / "openalex_query_7.py").exists()
    assert (root / "viz_network_interface_2.py").exists()
    assert (root / "openalex_converter.py").exists()


def test_launchers_module_has_no_tkinter():
    text = Path(launchers.__file__).read_text(encoding="utf-8")
    assert "tkinter" not in text
