"""Pipeline configuration (no GUI dependencies)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set

DEFAULT_TIES_POLICY = "closed_ge"
BASELINE_BOOTSTRAP_B = 800


@dataclass
class PipelineConfig:
    ties_policy: str = DEFAULT_TIES_POLICY
    use_local_baseline: bool = True
    k_window: int = 5
    drop_self_citations: bool = True
    drop_retracted: bool = True
    concept_level: int = 1
    prefer_histogram: bool = True
    max_pages: int = 9999
    types_filter: Optional[Set[str]] = None
    baseline_bootstrap_b: int = BASELINE_BOOTSTRAP_B
    crosswalk_status: str = "not_populated"
    extra: dict = field(default_factory=dict)
