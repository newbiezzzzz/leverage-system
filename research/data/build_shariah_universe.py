#!/usr/bin/env python3
"""Build point-in-time SC Shariah universe snapshots.

The script discovers historical PDF links from the SC's public list page,
downloads them, extracts Table 1 stock codes, and writes a normalized
snapshot file. It deliberately does not backfill today's membership into
earlier dates.
"""
from __future__ import annotations
import io, re, hashlib
from pathlib import Path
import requests
import pandas as pd
from bs4 import BeautifulSoup
import fitz

SC_PAGE = "https://www.sc.com.my/development/icm/shariah-compliant-securities/list-of-shariah-compliant-securities"
OUT = Path("data/shariah")
OUT.mkdir(parents=True, exist_ok=True)

def discover_pdfs():
    html = requests.get(SC_PAGE, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = " ".join(a.stripped_strings)
        if "download.ashx" in href.lower() or href.lower().endswith(".pdf"):
            if href.startswith("/"):
                href = "https://www.sc.com.my" + href
            if href.startswith("http"):
                links.append((text, href))
    # Preserve page order and remove duplicates.
    seen, result = set(), []
    for text, href in links:
        if href not in seen:
            seen.add(href)
            result.append((text, href))
    return result

def pdf_text(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def effective_date(text):
    m = re.search(r"\b(\d{1,2}\s+(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{4})\b", text.upper())
    if not m:
        raise ValueError("No effective date found")
    return pd.to_datetime(m.group(1), format="%d %B %Y").date().isoformat()

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
    # SC stock codes are 4 or 5 digits; leading zeroes are significant in
    # source records and are retained in raw_code.
    codes = re.findall(r"(?<!\d)(\d{4,5})(?!\d)", section)
    # Remove obvious table numbering/page artifacts by requiring code-like
    # values to be in the range normally used by Bursa codes.
    out = []
    for c in codes:
        if c not in out and not (c.startswith("20") and len(c) == 4 and c in {"2020","2021","2022","2023","2024","2025","2026"}):
            out.append(c)
    return out

def main():
    rows = []
    for label, url in discover_pdfs():
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            content = r.content
            text = pdf_text(content)
            date = effective_date(text)
            codes = table1_codes(text)
            sha = hashlib.sha256(content).hexdigest()
            for raw in codes:
                rows.append({
                    "effective_date": date,
                    "raw_code": raw,
                    "yahoo_symbol": raw.lstrip("0") + ".KL",
                    "source_url": url,
                    "source_sha256": sha,
                })
            print(date, len(codes), url)
        except Exception as exc:
            print("SKIP", label, url, repr(exc))
    if not rows:
        raise SystemExit("No snapshots extracted")
    df = pd.DataFrame(rows).drop_duplicates(["effective_date","raw_code"])
    df = df.sort_values(["effective_date","raw_code"])
    df.to_csv(OUT / "shariah_snapshots.csv", index=False)
    print("Wrote", len(df), "snapshot rows to", OUT / "shariah_snapshots.csv")

if __name__ == "__main__":
    main()
