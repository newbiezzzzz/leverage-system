#!/usr/bin/env python3
"""Build point-in-time SC Shariah universe snapshots from the SC archive."""
from __future__ import annotations
import re, hashlib
from pathlib import Path
import requests
import pandas as pd
from bs4 import BeautifulSoup
import fitz

SC_PAGE = "https://www.sc.com.my/development/icm/shariah-compliant-securities/list-of-shariah-compliant-securities"
OUT = Path("data/shariah")
OUT.mkdir(parents=True, exist_ok=True)
DATE_RE = re.compile(r"\b(\d{1,2}\s+(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{4})\b", re.I)
MONTH_YEAR_RE = re.compile(r"\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{4})\b", re.I)

def discover_pdfs():
    html = requests.get(SC_PAGE, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "download.ashx" not in href.lower() and not href.lower().endswith(".pdf"):
            continue
        if href.startswith("/"):
            href = "https://www.sc.com.my" + href
        if not href.startswith("http"):
            continue
        # Keep broad discovery; actual PDF content is validated below.
        parts = []
        node = a
        for _ in range(3):
            if node:
                parts.append(" ".join(node.stripped_strings))
                node = node.parent
        links.append((" ".join(parts), href))
    seen, result = set(), []
    for label, href in links:
        if href not in seen:
            seen.add(href)
            result.append((label, href))
    return result

def pdf_text(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def effective_date(context, text):
    # Prefer an exact date from the archive context/PDF.
    for source in (context, text[:20000]):
        m = DATE_RE.search(source.upper())
        if m:
            return pd.to_datetime(m.group(1), format="%d %B %Y").date().isoformat()
    # SC lists are issued on the final Friday of May/November. If the PDF
    # only prints "May 2026", derive that scheduled effective date.
    m = MONTH_YEAR_RE.search(text[:20000].upper())
    if m and m.group(1) in {"MAY", "NOVEMBER"}:
        month = pd.to_datetime(m.group(1), format="%B").month
        year = int(m.group(2))
        dates = pd.date_range(f"{year}-{month:02d}-01", f"{year}-{month:02d}-28") if month == 2 else pd.date_range(f"{year}-{month:02d}-01", f"{year}-{month:02d}-31")
        fridays = [d for d in dates if d.weekday() == 4]
        if fridays:
            return fridays[-1].date().isoformat()
    raise ValueError("No effective date found")

def table1_codes(text):
    upper = text.upper()
    starts = [upper.find("TABLE 1: SECURITIES CLASSIFIED AS SHARIAH-COMPLIANT"),
              upper.find("TABLE 1: SECURITIES CLASSIFIED AS SHARIAH COMPLIANT")]
    starts = [x for x in starts if x >= 0]
    if not starts:
        raise ValueError("Table 1 heading not found")
    start = min(starts)
    end = upper.find("TABLE 2:", start)
    if end < 0:
        raise ValueError("Table 2 boundary not found")
    section = text[start:end]
    codes = re.findall(r"(?<!\d)(\d{4,5})(?!\d)", section)
    return list(dict.fromkeys(c for c in codes if c not in {"2020","2021","2022","2023","2024","2025","2026"}))

def main():
    rows = []
    links = discover_pdfs()
    print("Candidate PDFs:", len(links))
    for context, url in links:
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            content = r.content
            text = pdf_text(content)
            if "LIST OF SHARIAH-COMPLIANT SECURITIES" not in text.upper() and "LIST OF SHARIAH COMPLIANT SECURITIES" not in text.upper():
                raise ValueError("Not an SC Shariah securities list")
            date = effective_date(context, text)
            codes = table1_codes(text)
            if not codes:
                raise ValueError("No stock codes extracted from Table 1")
            sha = hashlib.sha256(content).hexdigest()
            for raw in codes:
                rows.append({"effective_date": date, "raw_code": raw, "yahoo_symbol": raw.lstrip("0") + ".KL", "source_url": url, "source_sha256": sha})
            print(date, len(codes), url)
        except Exception as exc:
            print("SKIP", url, repr(exc))
    if not rows:
        raise SystemExit("No snapshots extracted")
    df = pd.DataFrame(rows).drop_duplicates(["effective_date","raw_code"]).sort_values(["effective_date","raw_code"])
    df.to_csv(OUT / "shariah_snapshots.csv", index=False)
    print("Wrote", len(df), "snapshot rows")
if __name__ == "__main__":
    main()
