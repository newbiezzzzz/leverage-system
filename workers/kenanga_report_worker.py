"""Audit Kenanga FCPO Daily Preview PDFs for extraction readiness.

This is an experimental/supporting-source worker. It does not turn ambiguous
PDF layout into guessed OHLCV values. It extracts only fields that can be
identified safely from a PDF text layer and reports what is missing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional worker dependency
    PdfReader = None

DATE_RE = re.compile(r"(?:DAILY PREVIEW\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}", re.I)
FCPO_RE = re.compile(r"CPO Futures 3rd month daily chart", re.I)


def extract_text(pdf_path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed; install it only for the experimental PDF worker")
    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def audit_pdf(pdf_path: Path) -> dict:
    text = extract_text(pdf_path)
    has_fcpo_chart = bool(FCPO_RE.search(text))
    dates = DATE_RE.findall(text)
    # Deliberately conservative: the text layer often loses table geometry.
    missing_fields = ["open", "unambiguous_target_contract_volume"]
    return {
        "file": str(pdf_path),
        "report_date": dates[0] if dates else None,
        "fcpo_3rd_month_chart_detected": has_fcpo_chart,
        "safe_ohlcv_extraction": False,
        "missing_or_ambiguous_fields": missing_fields,
        "decision": "supporting_source_only",
    }


def audit_directory(directory: Path) -> dict:
    reports = sorted(directory.glob("*.pdf"))
    results = [audit_pdf(p) for p in reports]
    return {
        "worker": "kenanga-report-worker",
        "source": "Kenanga Futures FCPO Daily Preview",
        "reports_seen": len(results),
        "reports": results,
        "production_ready": False,
        "reason": "PDF text extraction is not reliable enough to reconstruct complete daily FCPO OHLCV without guessing table layout.",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_directory(args.directory), indent=2))
