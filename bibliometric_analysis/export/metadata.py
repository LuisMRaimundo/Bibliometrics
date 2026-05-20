"""Run metadata and reproducibility helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from bibliometric_analysis import __schema_version__, __version__
from bibliometric_analysis.export.schemas import SCHEMA_VERSION


def config_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def file_hash(path: str | None) -> str:
    if not path:
        return ""
    try:
        data = open(path, "rb").read()
        return hashlib.sha256(data).hexdigest()[:16]
    except OSError:
        return ""


def build_run_metadata(
    *,
    config: dict[str, Any],
    input_path: str | None = None,
    warnings: list[str] | None = None,
    optional_deps: dict[str, bool] | None = None,
) -> pd.DataFrame:
    rows = [
        ("software_version", __version__),
        ("metric_schema_version", SCHEMA_VERSION),
        ("export_schema_version", __schema_version__),
        ("run_timestamp_utc", datetime.now(timezone.utc).isoformat()),
        ("input_file_hash", file_hash(input_path)),
        ("config_hash", config_hash(config)),
    ]
    for k, v in config.items():
        rows.append((f"config.{k}", v))
    if optional_deps:
        for k, v in optional_deps.items():
            rows.append((f"optional.{k}", v))
    if warnings:
        for i, w in enumerate(warnings):
            rows.append((f"warning.{i}", w))
    return pd.DataFrame(rows, columns=["key", "value"])
