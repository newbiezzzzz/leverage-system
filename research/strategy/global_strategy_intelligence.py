#!/usr/bin/env python3
"""Global Trading Strategy Intelligence.

Collects fresh public trading research signals without requiring paid APIs:
- Google News RSS searches across several regional editions.
- arXiv Atom API for quantitative/trading research.
- deterministic theme extraction -> research hypotheses.

This is idea discovery, not evidence of profitability. Every generated idea must
still pass the Strategy Hunter's historical, cost, risk, OOS, replication and
paper-validation gates.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "results"
OUT.mkdir(parents=True, exist_ok=True)
STATE = OUT / "global_strategy_intelligence.json"

REFRESH_HOURS = float(os.getenv("INTELLIGENCE_REFRESH_HOURS", "6"))
MAX_ITEMS_PER_QUERY = 8
MAX_TOTAL_ITEMS = 180

SEARCHES = [
    ("professional_trader", "pro trader systematic trading strategy"),
    ("professional_trader", "trading setup risk management professional trader"),
    ("indicator", "new technical indicator stock trading"),
    ("indicator", "technical analysis indicator research trading"),
    ("quant", "quantitative trading strategy stock market"),
    ("factor", "factor investing momentum value quality volatility"),
    ("pattern", "price volume pattern trading research"),
    ("breakout", "breakout trend following volume trading"),
    ("mean_reversion", "mean reversion trading stock research"),
    ("momentum", "momentum trading research equities"),
    ("volume", "volume price trading indicator research"),
    ("regime", "market regime trading strategy volatility"),
    ("wyckoff", "Wyckoff trading strategy spring sign of strength"),
    ("turtle", "Turtle trading trend following"),
    ("minervini", "Mark Minervini trading methodology"),
    ("connors", "Larry Connors mean reversion trading"),
    ("livermore", "Jesse Livermore trading rules"),
    ("al_brooks", "price action trading methodology"),
]

ARXIV_QUERIES = [
    "all:"technical analysis" AND (cat:q-fin.TR OR cat:q-fin.PM)",
    "all:"momentum" AND (cat:q-fin.TR OR cat:q-fin.PM)",
    "all:"market regime" AND (cat:q-fin.TR OR cat:q-fin.ST)",
    "all:"mean reversion" AND (cat:q-fin.TR OR cat:q-fin.PM)",
    "all:"financial time series" AND (cat:q-fin.TR OR cat:stat.ML)",
]


def _strip(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()


def _get(url: str, timeout: int = 12) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Leverage-Strategy-Research/1.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def _news_items(theme: str, query: str, gl: str) -> list[dict]:
    params = urllib.parse.urlencode(
        {"q": query, "hl": "en-US", "gl": gl, "ceid": f"{gl}:en"}
    )
    url = "https://news.google.com/rss/search?" + params
    try:
        root = ET.fromstring(_get(url))
    except Exception:
        return []
    out = []
    for item in root.findall(".//item")[:MAX_ITEMS_PER_QUERY]:
        title = _strip(item.findtext("title"))
        link = _strip(item.findtext("link"))
        summary = _strip(item.findtext("description"))
        pub = _strip(item.findtext("pubDate"))
        if not title or not link:
            continue
        out.append(
            {
                "source_type": "news",
                "region": gl,
                "theme": theme,
                "title": title,
                "summary": summary[:1400],
                "url": link,
                "published": pub,
            }
        )
    return out


def _arxiv_items(query: str) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": MAX_ITEMS_PER_QUERY,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = "https://export.arxiv.org/api/query?" + params
    try:
        root = ET.fromstring(_get(url))
    except Exception:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for entry in root.findall("a:entry", ns)[:MAX_ITEMS_PER_QUERY]:
        title = _strip(entry.findtext("a:title", default="", namespaces=ns))
        summary = _strip(entry.findtext("a:summary", default="", namespaces=ns))
        published = _strip(entry.findtext("a:published", default="", namespaces=ns))
        link = ""
        for el in entry.findall("a:link", ns):
            href = el.attrib.get("href", "")
            if href and el.attrib.get("rel", "alternate") == "alternate":
                link = href
                break
        if not link:
            link = entry.findtext("a:id", default="", namespaces=ns)
        if title and link:
            out.append(
                {
                    "source_type": "arxiv",
                    "region": "global",
                    "theme": "quant_research",
                    "title": title,
                    "summary": summary[:1800],
                    "url": link,
                    "published": published,
                }
            )
    return out


THEMES = {
    "momentum": ["momentum", "relative strength", "trend following", "continuation"],
    "mean_reversion": ["mean reversion", "oversold", "reversal", "contrarian"],
    "breakout": ["breakout", "donchian", "range expansion", "squeeze"],
    "volume": ["volume", "on-balance", "obv", "volume profile"],
    "volatility": ["volatility", "atr", "bollinger", "variance", "vol regime"],
    "moving_average": ["moving average", "ema", "sma", "macd", "cross"],
    "oscillator": ["rsi", "stochastic", "oscillator", "cci", "adx"],
    "market_regime": ["regime", "bull market", "bear market", "state switching"],
    "price_action": ["price action", "candlestick", "support", "resistance", "pattern"],
    "wyckoff": ["wyckoff", "spring", "sign of strength", "accumulation"],
    "risk_management": ["stop loss", "position sizing", "risk management", "drawdown"],
    "machine_learning": ["machine learning", "deep learning", "random forest", "gradient boosting"],
}


def _themes(text: str) -> list[str]:
    low = text.lower()
    found = [name for name, words in THEMES.items() if any(w in low for w in words)]
    return found or ["general"]


def _make_hypotheses(items: list[dict]) -> list[dict]:
    templates = {
        "momentum": "Test relative-strength/momentum entry conditioned on a longer-term trend.",
        "mean_reversion": "Test short-horizon oversold reversal only when the longer-term trend remains positive.",
        "breakout": "Test range breakout with volume and volatility confirmation.",
        "volume": "Test whether abnormal volume confirms subsequent price continuation or reversal.",
        "volatility": "Test volatility contraction/expansion as a state filter for entries.",
        "moving_average": "Test trend-transition and moving-average slope/cross conditions.",
        "oscillator": "Test oscillator thresholds and threshold-cross events conditioned on trend.",
        "market_regime": "Test separate entry logic by market breadth/volatility regime.",
        "price_action": "Test repeatable price/volume bar structures rather than subjective chart patterns.",
        "wyckoff": "Test mechanically defined Spring/SOS-style price/volume events.",
        "risk_management": "Test whether adaptive stops/holding horizons improve net expectancy without increasing drawdown.",
        "machine_learning": "Treat ML/feature interactions as hypothesis generators, then validate on untouched data.",
        "general": "Extract a testable rule from the source and require independent evidence before adoption.",
    }
    grouped: dict[str, list[dict]] = {}
    for item in items:
        for theme in _themes(item["title"] + " " + item.get("summary", "")):
            grouped.setdefault(theme, []).append(item)

    hypotheses = []
    for theme, sources in grouped.items():
        sources = sorted(sources, key=lambda x: (x.get("published") or "", x["url"]), reverse=True)[:20]
        digest = hashlib.sha256((theme + "|" + "|".join(s["url"] for s in sources)).encode()).hexdigest()[:12]
        hypotheses.append(
            {
                "hypothesis_id": f"GI-{digest}",
                "theme": theme,
                "hypothesis": templates[theme],
                "source_count": len(sources),
                "source_urls": [s["url"] for s in sources[:8]],
                "evidence_type": "idea_only",
                "backtest_required": True,
            }
        )
    return sorted(hypotheses, key=lambda x: (-x["source_count"], x["theme"]))


def main() -> None:
    now = time.time()
    if STATE.exists():
        try:
            old = json.loads(STATE.read_text(encoding="utf-8"))
            age = now - float(old.get("fetched_at_epoch", 0))
            if age < REFRESH_HOURS * 3600 and old.get("items"):
                old["status"] = "cached"
                STATE.write_text(json.dumps(old, indent=2) + "\n", encoding="utf-8")
                print(json.dumps({"status": "cached", "items": len(old.get("items", [])), "hypotheses": len(old.get("hypotheses", []))}))
                return
        except Exception:
            pass

    items: list[dict] = []
    for theme, query in SEARCHES:
        for gl in ("US", "GB", "SG", "MY", "JP", "HK"):
            items.extend(_news_items(theme, query, gl))

    for idx, query in enumerate(ARXIV_QUERIES):
        if idx:
            time.sleep(3)
        items.extend(_arxiv_items(query))

    dedup: dict[str, dict] = {}
    for item in items:
        key = item["url"].split("&utm_", 1)[0]
        dedup[key] = item
    items = list(dedup.values())
    items = sorted(items, key=lambda x: (x.get("published") or "", x["url"]), reverse=True)[:MAX_TOTAL_ITEMS]

    for item in items:
        item["detected_themes"] = _themes(item["title"] + " " + item.get("summary", ""))

    hypotheses = _make_hypotheses(items)
    payload = {
        "status": "fresh" if items else "degraded_no_external_items",
        "fetched_at_epoch": now,
        "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "source_count": len(items),
        "news_regions": ["US", "GB", "SG", "MY", "JP", "HK"],
        "queries": [q for _, q in SEARCHES],
        "items": items,
        "hypotheses": hypotheses,
        "safety": "External material is hypothesis input only; no source is treated as proof of profitability.",
    }
    STATE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = ["# Global Strategy Intelligence", "", f"Status: {payload['status']}", f"Fetched: {payload['fetched_at_utc']}", f"Items: {len(items)}", "", "## Research hypotheses"]
    for h in hypotheses:
        md.append(f"- **{h['theme']}** — {h['hypothesis']} ({h['source_count']} sources)")
    md += ["", "## Recent research/material"]
    for item in items[:40]:
        md.append(f"- [{item['title']}]({item['url']}) — {item.get('source_type')} / {item.get('region')}")
    (OUT / "global_strategy_intelligence.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "global_strategy_hypotheses.json").write_text(json.dumps(hypotheses, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "items": len(items), "hypotheses": len(hypotheses)}))


if __name__ == "__main__":
    main()
