"""Launch companion tools from the main GUI (subprocess or in-process helpers)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

LogFn = Callable[[str], None]


def project_root() -> Path:
    """Project root (directory containing pyproject.toml or software_gui_pro_4.py)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() or (parent / "software_gui_pro_4.py").exists():
            return parent
    return Path.cwd()


def _launch_python_script(relative: str) -> subprocess.Popen[str]:
    root = project_root()
    script = root / relative
    if not script.exists():
        raise FileNotFoundError(f"Script not found: {script}")
    kwargs: dict = {"cwd": str(root)}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
    return subprocess.Popen([sys.executable, str(script)], **kwargs)


def launch_streamlit_app(relative: str) -> subprocess.Popen[str]:
    """Start a Streamlit app (opens browser). Requires streamlit installed."""
    if shutil.which("streamlit") is None:
        # fallback: python -m streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", str(project_root() / relative)]
    else:
        cmd = ["streamlit", "run", str(project_root() / relative)]
    root = project_root()
    script = root / relative
    if not script.exists():
        raise FileNotFoundError(f"Streamlit app not found: {script}")
    kwargs: dict = {"cwd": str(root)}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
    return subprocess.Popen(cmd, **kwargs)


def launch_openalex_query() -> subprocess.Popen[str]:
    return _launch_python_script("Query_OpenAlex/openalex_query_7.py")


def launch_network_viz() -> subprocess.Popen[str]:
    return _launch_python_script("viz_network_interface_2.py")


def launch_openalex_converter() -> subprocess.Popen[str]:
    return _launch_python_script("openalex_converter.py")


def run_enrichment(
    xlsx: str,
    mailto: str,
    concurrency: int = 6,
    *,
    log: LogFn | None = None,
) -> None:
    """Run entity enrichment in-process (same logic as enrich_entities.py CLI)."""
    from enrich_entities import main as enrich_main

    if log:
        log(f"[enrichment] A processar {xlsx} …")
    enrich_main(xlsx, mailto, concurrency)
    if log:
        log("[enrichment] Guardado: authors.csv, institutions.csv, authorships.csv")
