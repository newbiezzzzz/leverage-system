"""Leverage Digital Product Worker.

Builds deterministic digital-product artifacts without ChatGPT or external APIs.
The first implementation targets Excel-compatible workbooks using Python's
standard library only: it emits a SpreadsheetML .xml workbook that opens in
Excel/LibreOffice and can be zipped/packaged by a later delivery worker.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
import xml.sax.saxutils as xml

ROLE = "digital product creation and packaging"


def _cell(value: object) -> str:
    text = "" if value is None else str(value)
    return f'<Cell><Data ss:Type="String">{xml.escape(text)}</Data></Cell>'


def build_quote_workbook(output_path: str) -> dict:
    """Create a macro-free Excel-readable quotation template."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ["ENGINEERING JOB QUOTATION TOOLKIT"],
        [],
        ["Quote ID", "Q-0001", "Customer", "", "Job", ""],
        ["Quantity", "", "Target Margin %", "30", "Status", "Draft"],
        [],
        ["Category", "Description", "Qty", "Unit", "Rate (RM)", "Markup %", "Line Cost (RM)", "Sell Price (RM)"],
        ["Material", "", "", "kg", "", "15", "", ""],
        ["Labour", "", "", "hr", "", "0", "", ""],
        ["Outside", "", "", "job", "", "10", "", ""],
        [],
        ["SUMMARY"],
        ["Direct Cost", ""],
        ["Target Quote", ""],
        ["Gross Profit", ""],
        ["Gross Margin %", ""],
        [],
        ["Instructions"],
        ["Enter customer/job details and line costs. Verify supplier and labour rates before sending any commercial quote."],
    ]
    header = '<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?>'
    workbook = (
        header
        + '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
        + 'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
        + '<Worksheet ss:Name="Quote"><Table>'
        + ''.join('<Row>' + ''.join(_cell(v) for v in row) + '</Row>' for row in rows)
        + '</Table></Worksheet></Workbook>'
    )
    target.write_text(workbook, encoding="utf-8")
    return {"artifact": str(target), "format": "SpreadsheetML XML", "rows": len(rows), "external_dependencies": [], "cost_rm": 0}


def build_job_log_csv(output_path: str, rows: int = 20) -> dict:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Job ID", "Customer", "Job", "Qty", "Quoted Sales", "Actual Cost", "Actual Profit", "Actual Margin %", "Status"])
        for index in range(1, rows + 1):
            writer.writerow([f"JOB-{index:03d}", "", "", "", "", "", "", "", "Open"])
    return {"artifact": str(target), "format": "CSV", "rows": rows + 1, "external_dependencies": [], "cost_rm": 0}


def self_test() -> dict:
    return {"worker": "digital-product-worker", "role": ROLE, "status": "healthy", "capabilities": ["spreadsheet-template", "csv-template", "artifact-packaging"], "external_dependencies": [], "cost": {"amount": 0, "currency": "RM"}}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
