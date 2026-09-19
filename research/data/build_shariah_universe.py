#!/usr/bin/env python3
"""Build point-in-time SC Shariah equity snapshots from official SC PDFs."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import fitz
import pandas as pd
import requests
from bs4 import BeautifulSoup

SC_PAGE = (
    "https://www.sc.com.my/development/icm/shariah-compliant-securities/"
    "list-of-shariah-compliant-securities"
)
OUT = Path("data/shariah")
OUT.mkdir(parents=True, exist_ok=True)

DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|"
    r"AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{4})\b", re.I
)
MONTH_YEAR_RE = re.compile(
    r"\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|"
    r"SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{4})\b", re.I
)

OFFICIAL_SEED_PDFS = [
    ("29 May 2026", "https://www.sc.com.my/api/documentms/download.ashx?id=9f03c706-607f-4fbe-b4c7-91afc352ee49"),
    ("28 November 2025", "https://www.sc.com.my/api/documentms/download.ashx?id=5f0bb08b-802c-49a0-b093-d6f0edf6c276"),
    ("30 May 2025", "https://www.sc.com.my/api/documentms/download.ashx?id=2671e073-8b4c-4291-af90-7cb34ad7715f"),
    ("29 November 2024", "https://www.sc.com.my/api/documentms/download.ashx?id=1920c06f-61e5-46d7-8016-28a918acd4c8"),
    ("31 May 2024", "https://www.sc.com.my/api/documentms/download.ashx?id=d540937f-6840-41e1-b4ec-b3681b11bedf"),
    ("24 November 2023", "https://www.sc.com.my/api/documentms/download.ashx?id=c39e4960-6720-40da-92f3-633e6c86c36e"),
    ("26 May 2023", "https://www.sc.com.my/api/documentms/download.ashx?id=e6cffd45-ccdc-42f5-ac1c-d10d670e86bd"),
    ("25 November 2022", "https://www.sc.com.my/api/documentms/download.ashx?id=d167b551-2f93-4d28-a08f-e4bf9804b09a"),
    ("27 May 2022", "https://www.sc.com.my/api/documentms/download.ashx?id=f594c8f5-17a1-4007-9334-4db1330e705f"),
    ("26 November 2021", "https://www.sc.com.my/api/documentms/download.ashx?id=03897690-c1cd-4748-b221-204052582c75"),
    ("28 May 2021", "https://www.sc.com.my/api/documentms/download.ashx?id=48a2810f-415f-48e7-bfac-ff77dc473c0e"),
    ("27 November 2020", "https://www.sc.com.my/api/documentms/download.ashx?id=7b5e5a18-0108-48fe-8d2e-1f6bfc78f217"),
    ("29 May 2020", "https://www.sc.com.my/api/documentms/download.ashx?id=dd80630a-6dd5-45ae-bedb-75f0586fe3ec"),
    ("29 November 2019", "https://www.sc.com.my/api/documentms/download.ashx?id=cc27f516-5d68-4794-a09b-da905973315e"),
    ("31 May 2019", "https://www.sc.com.my/api/documentms/download.ashx?id=bcbbac70-81c3-4d09-9699-11f411dda781"),
    ("30 November 2018", "https://www.sc.com.my/api/documentms/download.ashx?id=f325b375-67e9-49c3-a45d-4864c8a6be7f"),
    ("25 May 2018", "https://www.sc.com.my/api/documentms/download.ashx?id=905d3f69-ea7d-4b12-86ab-e3937cd8eb1e"),
    ("24 November 2017", "https://www.sc.com.my/api/documentms/download.ashx?id=dffafea8-b441-4ac1-8b62-9268394db56f"),
    ("26 May 2017", "https://www.sc.com.my/api/documentms/download.ashx?id=4e29ed43-98f5-4cd6-a724-4edc58d21eea"),
    ("25 November 2016", "https://www.sc.com.my/api/documentms/download.ashx?id=77ef86e2-0718-478e-b381-b4f65d240c57"),
    ("27 May 2016", "https://www.sc.com.my/api/documentms/download.ashx?id=a4781f4e-b6c4-4f40-bb1c-17d5aded73f6"),
]

# SC full-list rows look like "1. 7086 Ablegroup Bhd".  Warrants may carry
# alphabetic suffixes in the security code; those are not ordinary equities.
CODE_ROW_RE = re.compile(
    r"(?<!\d)\d{1,3}\s*[\.)]\s*(\d{4,5}[A-Z]{0,3})(?![A-Z0-9])",
    re.I,
)


def discover_pdfs():
    html = requests.get(SC_PAGE, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    links = list(OFFICIAL_SEED_PDFS)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "download.ashx" not in href.lower() and not href.lower().endswith(".pdf"):
            continue
        if href.startswith("/"):
            href = "https://www.sc.com.my" + href
        if not href.startswith("http"):
            continue
        context = []
        node = a
        for _ in range(3):
            if node:
                context.append(" ".join(node.stripped_strings))
                node = node.parent
        links.append((" ".join(context), href))
    seen, result = set(), []
    for label, href in links:
        if href not in seen:
            seen.add(href)
            result.append((label, href))
    return result


def pdf_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def effective_date(context: str, text: str) -> str:
    for source in (context, text[:20000]):
        m = DATE_RE.search(source.upper())
        if m:
            return pd.to_datetime(m.group(1), format="%d %B %Y").date().isoformat()

    m = MONTH_YEAR_RE.search(text[:20000].upper())
    if m and m.group(1) in {"MAY", "NOVEMBER"}:
        month = pd.to_datetime(m.group(1), format="%B").month
        year = int(m.group(2))
        dates = pd.date_range(
            f"{year}-{month:02d}-01", f"{year}-{month:02d}-31", freq="D"
        )
        fridays = [d for d in dates if d.weekday() == 4]
        if fridays:
            return fridays[-1].date().isoformat()
    raise ValueError("No effective date found")


def expected_universe_count(text: str) -> int | None:
    # Table 3 rows use "Total <shariah-count> <all-count> <percentage>".
    m = re.search(
        r"(?:TOTAL|Total)\s*\n\s*(?:Jumlah\s*)?(?:\n\s*)?"
        r"([0-9][0-9,]{2,4})\s+([0-9][0-9,]{2,5})\s+([0-9]{1,3})",
        text,
        flags=re.I,
    )
    if m:
        return int(m.group(1).replace(",", ""))

    values = [
        int(x.replace(",", ""))
        for x in re.findall(
            r"\b(?:total|complete list(?: of the)?|featured a total of)\s*"
            r"(?:the\s+)?([0-9][0-9,]{2,4})\s+"
            r"(?:Shariah[-\s]*compliant|SHARIAH[-\s]*COMPLIANT)\s+securities",
            text,
            flags=re.I,
        )
    ]
    return max(values) if values else None


def extract_full_universe_codes(text: str) -> tuple[list[str], int | None, str]:
    upper = text.upper()
    expected = expected_universe_count(text)

    candidates = []
    for pattern in (
        r"LIST OF SHARIAH[\s\W]{0,20}COMPLIANT SECURITIES",
        r"APPENDIX\s+II",
        r"MAIN MARKET",
    ):
        candidates.extend(m.start() for m in re.finditer(pattern, upper))

    if not candidates:
        raise ValueError("No full-list anchor found")

    candidates = sorted(set(candidates))
    best = None

    for start in candidates:
        tail = text[start:]
        all_codes = list(dict.fromkeys(CODE_ROW_RE.findall(tail)))
        equity_codes = [c for c in all_codes if c.isdigit()]
        n = len(equity_codes)

        if expected:
            distance = abs(n - expected) / expected
            score = distance + (0.05 if start < len(text) * 0.30 else 0.0)
            if best is None or score < best[0]:
                best = (score, start, equity_codes, n, len(all_codes) - n)
        else:
            score = (-n, 0 if start >= len(text) * 0.30 else 1)
            if best is None or score < best[0]:
                best = (score, start, equity_codes, n, len(all_codes) - n)

    _, start, codes, n, excluded_non_equity = best

    if expected and not (0.95 * expected <= n <= 1.05 * expected):
        raise ValueError(
            f"Extracted {n} equity codes; SC-reported universe is {expected}"
        )
    if n < 500:
        raise ValueError(f"Suspiciously small equity universe: {n} codes")

    return (
        codes,
        expected,
        text[start : start + 160].replace("\n", " "),
    )


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

            if (
                "LIST OF SHARIAH" not in text.upper()
                or "COMPLIANT" not in text.upper()
            ):
                raise ValueError("Not an SC Shariah securities list")

            date = effective_date(context, text)
            codes, expected, anchor = extract_full_universe_codes(text)
            sha = hashlib.sha256(content).hexdigest()

            for raw in codes:
                rows.append(
                    {
                        "effective_date": date,
                        "raw_code": raw,
                        "yahoo_symbol": raw + ".KL",
                        "source_url": url,
                        "source_sha256": sha,
                    }
                )

            print(
                date,
                "equity_codes=", len(codes),
                "expected=", expected,
                "anchor=", anchor,
                url,
            )
        except Exception as exc:
            print("SKIP", url, repr(exc))

    if not rows:
        raise SystemExit("No snapshots extracted")

    df = (
        pd.DataFrame(rows)
        .drop_duplicates(["effective_date", "raw_code"])
        .sort_values(["effective_date", "raw_code"])
    )
    df.to_csv(OUT / "shariah_snapshots.csv", index=False)
    print(
        "Wrote", len(df), "snapshot rows across",
        df.effective_date.nunique(), "effective dates",
    )


if __name__ == "__main__":
    main()
