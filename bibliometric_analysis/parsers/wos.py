"""Web of Science tagged .txt parser."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .common import finalize_parser_df, norm_doi


def parse_wos_txt(path: str) -> pd.DataFrame:
    txt = Path(path).read_text(encoding="utf-8", errors="ignore")
    blocks = re.split(r"\r?\nER\s*\r?\n", txt)
    blocks = [b for b in blocks if b.strip()]

    def extract_multiline(rec, tag):
        lines = rec.splitlines()
        out, cur = [], None
        for ln in lines:
            if ln.startswith(tag + " "):
                if cur is not None:
                    out.append(cur)
                cur = ln[len(tag) :].strip()
            elif ln.startswith("   ") and cur is not None:
                cur += " " + ln.strip()
        if cur is not None:
            out.append(cur)
        return out

    def extract_single(rec, tag):
        vals = extract_multiline(rec, tag)
        if not vals:
            return None
        return " | ".join(vals)

    rows = []
    for rec in blocks:
        ti = extract_single(rec, "TI")
        di_raw = extract_single(rec, "DI")
        doi = norm_doi(di_raw) if di_raw else None
        so = extract_single(rec, "SO")
        py = extract_single(rec, "PY")
        au = "; ".join(extract_multiline(rec, "AU")) or None
        ab = extract_single(rec, "AB")
        cr_list = extract_multiline(rec, "CR")
        ref_dois = []
        for cr in cr_list or []:
            d = norm_doi(cr)
            if d:
                ref_dois.append(d)
        rows.append(
            {
                "title": ti,
                "doi": doi,
                "source": so,
                "year": py,
                "authors": au,
                "abstract": ab,
                "ref_dois": list(dict.fromkeys(ref_dois)),
                "n_ref_dois": len(set(ref_dois)),
            }
        )
    return finalize_parser_df(pd.DataFrame(rows))
