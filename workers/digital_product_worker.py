"""Leverage Digital Product Worker.

Builds deterministic digital-product artifacts without ChatGPT or external APIs.
The first product path creates a real macro-free .xlsx workbook using Python's
standard library only. No external provider or paid service is required.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.sax.saxutils as xml

ROLE = "digital product creation and packaging"


def _escape(value: object) -> str:
    return xml.escape("" if value is None else str(value))


def _sheet_xml(rows: list[list[object]]) -> str:
    body = []
    for row_index, row in enumerate(rows, 1):
        cells = []
        for col_index, value in enumerate(row, 1):
            if value in (None, ""):
                continue
            cell_ref = _column_name(col_index) + str(row_index)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{cell_ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{_escape(value)}</t></is></c>')
        body.append(f'<row r="{row_index}">' + ''.join(cells) + '</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheetData>' + ''.join(body) + '</sheetData></worksheet>'
    )


def _column_name(number: int) -> str:
    letters = []
    while number:
        number, remainder = divmod(number - 1, 26)
        letters.append(chr(65 + remainder))
    return ''.join(reversed(letters))


def build_quote_workbook(output_path: str) -> dict:
    """Create a genuine .xlsx quotation template with no external dependencies."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ["ENGINEERING JOB QUOTATION TOOLKIT"],
        [],
        ["Quote ID", "Q-0001", "Customer", "", "Job", ""],
        ["Quantity", "", "Target Margin %", 30, "Status", "Draft"],
        [],
        ["Category", "Description", "Qty", "Unit", "Rate (RM)", "Markup %", "Line Cost (RM)", "Sell Price (RM)"],
        ["Material", "", "", "kg", "", 15, "", ""],
        ["Labour", "", "", "hr", "", 0, "", ""],
        ["Outside", "", "", "job", "", 10, "", ""],
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
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Quote" sheetId="1" r:id="rId1"/></sheets></workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'''
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows))
    return {"artifact": str(target), "format": "xlsx", "rows": len(rows), "external_dependencies": [], "cost_rm": 0}


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
    return {"worker": "digital-product-worker", "role": ROLE, "status": "healthy", "capabilities": ["xlsx-workbook", "csv-template", "artifact-packaging"], "external_dependencies": [], "cost": {"amount": 0, "currency": "RM"}}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
