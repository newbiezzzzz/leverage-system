"""Leverage Digital Product Worker.

Builds the selected first digital product without ChatGPT or external APIs.
The artifact is a macro-free XLSX profit-and-quoting toolkit for small
fabrication, welding and machine/job shops.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.sax.saxutils as xml

ROLE = "digital product creation and packaging"
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _escape(value: object) -> str:
    return xml.escape("" if value is None else str(value))


def _column_name(number: int) -> str:
    letters = []
    while number:
        number, remainder = divmod(number - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def _cell(ref: str, value: object = None, formula: str | None = None) -> str:
    if formula is not None:
        return f'<c r="{ref}"><f>{_escape(formula)}</f><v>0</v></c>'
    if value in (None, ""):
        return f'<c r="{ref}"/>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{_escape(value)}</t></is></c>'


def _sheet_xml(rows: list[list[object]], formulas: dict[str, str] | None = None) -> str:
    formulas = formulas or {}
    body = []
    for row_index, row in enumerate(rows, 1):
        cells = []
        for col_index, value in enumerate(row, 1):
            ref = _column_name(col_index) + str(row_index)
            cells.append(_cell(ref, value, formulas.get(ref)))
        body.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
        '<sheetData>' + "".join(body) + '</sheetData></worksheet>'
    )


def _xlsx_package(sheets: dict[str, tuple[list[list[object]], dict[str, str]]], target: Path) -> None:
    sheet_entries, rel_entries, override_entries = [], [], []
    for index, (name, _content) in enumerate(sheets.items(), 1):
        sheet_entries.append(f'<sheet name="{_escape(name)}" sheetId="{index}" r:id="rId{index}"/>')
        rel_entries.append(f'<Relationship Id="rId{index}" Type="{NS_REL}/worksheet" Target="worksheets/sheet{index}.xml"/>')
        override_entries.append(f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(override_entries) + '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
        '<calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/> '
        '<sheets>' + "".join(sheet_entries) + '</sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rel_entries) + '</Relationships>'
    )
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for index, (_name, (rows, formulas)) in enumerate(sheets.items(), 1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(rows, formulas))


def build_quote_workbook(output_path: str) -> dict:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    quote_rows = [
        ["FABRICATION SHOP PROFIT & QUOTE SYSTEM"],
        ["Calculate shop rate, job cost, quote, expected profit and learn from actual results."],
        ["Quote ID", "Q-0001", "Customer", "", "Job", ""],
        ["Quantity", 1, "Target Margin %", 30, "Status", "Draft"],
        [],
        ["QUOTE LINES", "", "", "", "", "", "", ""],
        ["Category", "Description", "Qty", "Unit", "Rate (RM)", "Markup %", "Line Cost (RM)", "Sell Price (RM)"],
        ["Material", "", 1, "kg", 0, 15, 0, 0],
        ["Labour", "", 1, "hr", 0, 0, 0, 0],
        ["Consumable", "", 1, "job", 0, 10, 0, 0],
        ["Outside", "", 1, "job", 0, 10, 0, 0],
    ]
    quote_rows += [["", "", "", "", "", "", 0, 0] for _ in range(16)]
    quote_rows += [
        [],
        ["PROFIT SUMMARY"],
        ["Direct Cost", 0],
        ["Overhead %", 8],
        ["Overhead", 0],
        ["Target Quote", 0],
        ["Gross Profit", 0],
        ["Gross Margin %", 0],
    ]
    quote_formulas = {}
    for row in range(8, 28):
        quote_formulas[f"G{row}"] = f"C{row}*E{row}"
        quote_formulas[f"H{row}"] = f"G{row}*(1+F{row}/100)"
    quote_formulas.update({
        "B30": "SUM(G8:G27)",
        "B32": "B30*B31/100",
        "B33": "(B30+B32)/(1-D4/100)",
        "B34": "B33-B30-B32",
        "B35": "IF(B33=0,0,B34/B33)",
    })

    rate_rows = [
        ["SHOP RATE CALCULATOR"],
        ["Enter your actual monthly costs and realistic productive hours. The sheet calculates an indicative burdened shop rate."],
        ["Parameter", "Value", "Unit", "Notes"],
        ["Monthly direct labour cost", 5000, "RM/month", "Wages attributable to production"],
        ["Monthly machine/equipment cost", 2000, "RM/month", "Recovery/lease/depreciation allowance"],
        ["Monthly shop overhead", 1500, "RM/month", "Rent, utilities, admin, software, etc."],
        ["Productive labour hours/month", 160, "hours", "Realistic billable/production hours"],
        ["Productive machine hours/month", 100, "hours", "Realistic machine utilisation"],
        ["Labour burden rate", 0, "RM/hour", "Calculated"],
        ["Machine recovery rate", 0, "RM/hour", "Calculated"],
        ["Overhead rate per labour hour", 0, "RM/hour", "Calculated"],
        ["Indicative loaded labour shop rate", 0, "RM/hour", "Labour + overhead burden"],
        ["Target gross margin", 30, "%", "Default quote target"],
        ["Material markup", 15, "%", "Default quote markup"],
        ["Consumable markup", 10, "%", "Default quote markup"],
        ["Outside-service markup", 10, "%", "Default quote markup"],
        ["Overhead allowance on direct cost", 8, "%", "Quote fallback allowance"],
    ]
    rate_formulas = {
        "B11": "IF(B7=0,0,B4/B7)",
        "B12": "IF(B8=0,0,B5/B8)",
        "B13": "IF(B7=0,0,B6/B7)",
        "B14": "B11+B13",
    }

    actual_rows = [["JOB LOG — QUOTED VS ACTUAL"], ["Job ID", "Customer", "Job", "Qty", "Quoted Sales", "Actual Material", "Actual Labour", "Actual Consumables", "Actual Outside", "Actual Overhead", "Actual Total Cost", "Actual Profit", "Actual Margin %", "Status"]]
    actual_formulas = {}
    for i in range(1, 21):
        row = i + 2
        actual_rows.append([f"JOB-{i:03d}", "", "", "", "", "", "", "", "", "", 0, 0, 0, "Open"])
        actual_formulas[f"K{row}"] = f"SUM(F{row}:J{row})"
        actual_formulas[f"L{row}"] = f"E{row}-K{row}"
        actual_formulas[f"M{row}"] = f"IF(E{row}=0,0,L{row}/E{row})"

    change_rows = [["CHANGE ORDER REGISTER"], ["Job ID", "Change ID", "Description", "Added Sales", "Added Cost", "Added Profit", "Approved?", "Notes"]]
    change_formulas = {}
    for i in range(1, 16):
        row = i + 2
        change_rows.append(["", f"CHG-{i:03d}", "", 0, 0, 0, "No", ""])
        change_formulas[f"F{row}"] = f"D{row}-E{row}"

    sheets = {
        "Quote": (quote_rows, quote_formulas),
        "Shop_Rates": (rate_rows, rate_formulas),
        "Job_Log": (actual_rows, actual_formulas),
        "Change_Orders": (change_rows, change_formulas),
    }
    _xlsx_package(sheets, target)
    return {
        "artifact": str(target),
        "format": "xlsx",
        "product_name": "Fabrication Shop Profit & Quote System",
        "sheets": list(sheets),
        "formula_count": sum(len(formulas) for _, formulas in sheets.values()),
        "external_dependencies": [],
        "cost_rm": 0,
    }


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
    return {
        "worker": "digital-product-worker",
        "role": ROLE,
        "status": "healthy",
        "product": "Fabrication Shop Profit & Quote System",
        "capabilities": ["xlsx-workbook", "csv-template", "artifact-packaging"],
        "external_dependencies": [],
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
