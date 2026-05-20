"""Stable Excel export sheet and column definitions."""

from __future__ import annotations

SCHEMA_VERSION = "1.0"

SHEET_RECORDS = "Records+Metrics"
SHEET_EDGES = "Edges"
SHEET_NETWORK = "Network Metrics"
SHEET_SUMMARY_INT = "Summary (integer)"
SHEET_SUMMARY_FRAC = "Summary (fractional)"
SHEET_GLOBALS = "Global Dist/Thresholds"
SHEET_RUN_META = "Run Metadata"

ALL_SHEETS = [
    SHEET_RECORDS,
    SHEET_EDGES,
    SHEET_NETWORK,
    SHEET_SUMMARY_INT,
    SHEET_SUMMARY_FRAC,
    SHEET_GLOBALS,
    SHEET_RUN_META,
]

RECORDS_CORE_COLUMNS = [
    "idx",
    "title",
    "year",
    "domain_label",
    "domain_id",
    "doi",
    "cited_by_count",
    "c_use",
    "c_use_window",
    "is_retracted",
    "c0_mean",
    "cf",
    "PPg_top1",
    "PPg_top10",
    "PPg_top25",
    "n_authors",
    "n_affiliations",
    "is_focal",
]

EDGE_COLUMNS = ["citer_idx", "cited_idx"]

NETWORK_COLUMNS = [
    "idx",
    "deg_in",
    "deg_out",
    "deg",
    "pagerank",
    "betweenness",
    "community",
    "community_label",
    "algo",
    "gamma",
    "stability_nmi",
]
