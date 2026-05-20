"""Crosswalk loading and mapping with provenance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

MappingType = Literal["exact", "close", "broad", "narrow", "related", "manual", "unknown"]
Confidence = Literal["high", "medium", "low", "unknown"]
MappingPolicy = Literal["all", "best"]

CROSSWALK_COLUMNS = [
    "source_scheme",
    "source_id",
    "source_label",
    "target_scheme",
    "target_id",
    "target_label",
    "mapping_type",
    "confidence",
    "provenance",
    "version",
    "notes",
]

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "ontology"
KNOWN_CROSSWALKS = ("asjc_openalex_crosswalk", "wos_openalex_crosswalk", "openalex_levels")


@dataclass
class MappingResult:
    target_id: str | None
    target_label: str | None
    mapping_type: MappingType
    confidence: Confidence
    provenance: str
    warning: str | None = None


def validate_crosswalk_schema(df: pd.DataFrame) -> list[str]:
    """Return list of schema validation errors (empty if valid)."""
    errors: list[str] = []
    for col in CROSSWALK_COLUMNS:
        if col not in df.columns:
            errors.append(f"missing column: {col}")
    if df.empty:
        return errors
    valid_mt = {"exact", "close", "broad", "narrow", "related", "manual", "unknown", ""}
    valid_conf = {"high", "medium", "low", "unknown", ""}
    if "mapping_type" in df.columns:
        bad = df[~df["mapping_type"].astype(str).isin(valid_mt)]
        if not bad.empty:
            errors.append(f"invalid mapping_type values: {bad['mapping_type'].unique()[:5].tolist()}")
    if "confidence" in df.columns:
        bad = df[~df["confidence"].astype(str).isin(valid_conf)]
        if not bad.empty:
            errors.append(f"invalid confidence values: {bad['confidence'].unique()[:5].tolist()}")
    return errors


def load_crosswalk(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=CROSSWALK_COLUMNS)
    df = pd.read_csv(path)
    for c in CROSSWALK_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df


def report_mapping_status(data_dir: Path | None = None) -> dict[str, str]:
    """Report population status for each known crosswalk file."""
    root = Path(data_dir or DEFAULT_DATA_DIR)
    status: dict[str, str] = {}
    for name in KNOWN_CROSSWALKS:
        path = root / f"{name}.csv"
        if not path.exists():
            status[name] = "missing_file"
            continue
        df = load_crosswalk(path)
        errs = validate_crosswalk_schema(df)
        if errs and df.empty:
            status[name] = "schema_only"
        elif errs:
            status[name] = f"invalid_schema:{len(errs)}"
        elif df.empty:
            status[name] = "not_populated"
        else:
            status[name] = "populated"
    return status


class CrosswalkRegistry:
    """Load crosswalk CSV tables; returns warnings when tables are empty or unmapped."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        self._tables: dict[str, pd.DataFrame] = {}

    def load(self, name: str) -> pd.DataFrame:
        if name in self._tables:
            return self._tables[name]
        path = self.data_dir / f"{name}.csv"
        df = load_crosswalk(path)
        self._tables[name] = df
        return df

    def is_populated(self, name: str) -> bool:
        df = self.load(name)
        return not df.empty

    def mapping_status(self) -> dict[str, str]:
        return report_mapping_status(self.data_dir)

    def map_label(
        self,
        source_scheme: str,
        source_label: str,
        target_scheme: str = "OpenAlex",
        *,
        table_name: str | None = None,
        policy: MappingPolicy = "best",
    ) -> MappingResult | list[MappingResult]:
        results = map_concept(
            source_scheme, source_label=source_label, target_scheme=target_scheme,
            table_name=table_name, registry=self, policy=policy,
        )
        if policy == "best":
            return results[0] if isinstance(results, list) and results else MappingResult(
                None, None, "unknown", "unknown", "crosswalk:empty", warning="No mapping."
            )
        return results

    def map_id(
        self,
        source_scheme: str,
        source_id: str,
        target_scheme: str = "OpenAlex",
        *,
        table_name: str | None = None,
        policy: MappingPolicy = "best",
    ) -> MappingResult | list[MappingResult]:
        results = map_concept(
            source_scheme, source_id=source_id, target_scheme=target_scheme,
            table_name=table_name, registry=self, policy=policy,
        )
        if policy == "best":
            return results[0] if isinstance(results, list) and results else MappingResult(
                None, None, "unknown", "unknown", "crosswalk:empty", warning="No mapping."
            )
        return results


def _row_to_result(row: pd.Series, table_name: str) -> MappingResult:
    return MappingResult(
        str(row["target_id"]) if pd.notna(row["target_id"]) and str(row["target_id"]).strip() else None,
        str(row["target_label"]) if pd.notna(row["target_label"]) and str(row["target_label"]).strip() else None,
        (row.get("mapping_type") or "unknown") or "unknown",
        (row.get("confidence") or "unknown") or "unknown",
        str(row.get("provenance") or f"crosswalk:{table_name}"),
    )


def _confidence_rank(c: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(str(c), 0)


def map_concept(
    source_scheme: str,
    *,
    source_id: str | None = None,
    source_label: str | None = None,
    target_scheme: str = "OpenAlex",
    table_name: str | None = None,
    registry: CrosswalkRegistry | None = None,
    policy: MappingPolicy = "best",
) -> list[MappingResult]:
    """Map a source concept to target scheme. Returns empty list with warning if unpopulated."""
    registry = registry or CrosswalkRegistry()
    table_name = table_name or f"{source_scheme.lower()}_{target_scheme.lower()}_crosswalk"
    df = registry.load(table_name)
    if df.empty:
        return [MappingResult(
            None, None, "unknown", "unknown", f"crosswalk:{table_name}",
            warning=f"Crosswalk '{table_name}' is not populated.",
        )]

    mask = (df["source_scheme"] == source_scheme) & (df["target_scheme"] == target_scheme)
    if source_id is not None:
        mask &= df["source_id"].astype(str) == str(source_id)
    elif source_label is not None:
        from bibliometric_analysis.ontology.normalize import normalize_label
        norm = normalize_label(source_label).lower()
        mask &= df["source_label"].astype(str).str.lower().map(normalize_label).str.lower() == norm
    else:
        return [MappingResult(None, None, "unknown", "unknown", f"crosswalk:{table_name}",
                              warning="Provide source_id or source_label.")]

    match = df[mask]
    if match.empty:
        key = source_id or source_label
        return [MappingResult(
            None, None, "unknown", "unknown", f"crosswalk:{table_name}",
            warning=f"No mapping for {source_scheme}:{key!r}.",
        )]

    results = [_row_to_result(row, table_name) for _, row in match.iterrows()]
    if policy == "best":
        results.sort(key=lambda r: _confidence_rank(r.confidence), reverse=True)
        return [results[0]]
    return results
