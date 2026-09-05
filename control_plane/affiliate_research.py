"""RM0-first demand research collector for the Affiliate Project.

Collects public RSS signals, normalizes them into a common research schema,
deduplicates repeated stories/questions, and writes evidence-backed records.
This stage discovers demand only; product/offer selection belongs to B4.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "affiliate_research_config.json"
OUTPUT_PATH = ROOT / "affiliate_research_queue.json"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def fetch_feed(source: dict, config: dict) -> tuple[list[dict], dict | None]:
    req = Request(source["url"], headers={"User-Agent": config["research"]["user_agent"]})
    try:
        with urlopen(req, timeout=config["research"]["timeout_seconds"]) as response:
            root = ET.fromstring(response.read())
    except (HTTPError, URLError, TimeoutError, ET.ParseError, OSError) as exc:
        return [], {"source": source["name"], "kind": source["kind"], "error": str(exc)}

    items: list[dict] = []
    # RSS 2.0 and Atom are both supported.
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1].lower()
        if tag not in {"item", "entry"}:
            continue
        values: dict[str, str] = {}
        for child in list(node):
            ctag = child.tag.rsplit("}", 1)[-1].lower()
            if ctag == "link":
                values.setdefault("link", child.attrib.get("href", "") or clean(child.text))
            else:
                values.setdefault(ctag, clean(child.text))
        title = values.get("title", "")
        summary = values.get("description", "") or values.get("summary", "") or values.get("content", "")
        published = values.get("pubdate", "") or values.get("published", "") or values.get("updated", "")
        if title:
            items.append({"title": title, "summary": summary, "url": values.get("link", ""), "published": published})
    return items[: config["research"]["max_items_per_source"]], None


def demand_signal(title: str, summary: str, kind: str, keywords: list[str]) -> dict:
    text = f"{title} {summary}".lower()
    hits = sorted({kw for kw in keywords if kw.lower() in text})
    intent_terms = {"buy", "beli", "recommend", "cadang", "worth", "berbaloi", "review", "price", "harga", "compare", "vs"}
    problem_terms = {"problem", "masalah", "issue", "broken", "repair", "rosak", "maintenance", "servis", "service", "battery", "bateri", "tyre", "tayar"}
    intent = min(5, 1 + sum(term in text for term in intent_terms))
    problem = min(5, 1 + sum(term in text for term in problem_terms))
    content = min(5, 1 + (len(hits) >= 2) + (kind == "reddit") + ("how" in text or "cara" in text))
    return {"keyword_hits": hits, "buyer_intent": intent, "problem_strength": problem, "content_potential": content}


def make_record(source: dict, item: dict, config: dict) -> dict:
    title = clean(item["title"])
    summary = clean(item.get("summary"))
    evidence = summary[:600] if summary else title
    published_dt = parse_date(item.get("published"))
    signal = demand_signal(title, summary, source["kind"], config["research"]["keywords"])
    canonical = re.sub(r"\W+", " ", f"{title} {source['name']}".lower()).strip()
    record_id = "r-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return {
        "id": record_id,
        "project": config["project"],
        "problem": title,
        "source": source["name"],
        "source_kind": source["kind"],
        "evidence": evidence,
        "evidence_url": item.get("url", ""),
        "demand_signal": signal,
        "recurrence": "unknown",
        "buyer_intent": signal["buyer_intent"],
        "content_potential": signal["content_potential"],
        "product_potential": signal["problem_strength"],
        "freshness": published_dt.isoformat() if published_dt else now_utc().isoformat(),
        "status": "new",
        "collected_at": now_utc().isoformat(),
    }


def dedupe(records: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result = []
    for record in records:
        key = hashlib.sha256(re.sub(r"\W+", " ", record["problem"].lower()).strip().encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def run() -> int:
    config = load_config()
    collected: list[dict] = []
    errors: list[dict] = []
    for group in config["sources"].values():
        for source in group:
            items, error = fetch_feed(source, config)
            if error:
                errors.append(error)
            collected.extend(make_record(source, item, config) for item in items)

    records = dedupe(collected)
    cutoff = now_utc() - timedelta(days=config["research"]["freshness_days"])
    for record in records:
        dt = parse_date(record["freshness"])
        record["freshness_status"] = "fresh" if not dt or dt >= cutoff else "stale"

    payload = {
        "version": 1,
        "project": config["project"],
        "generated_at": now_utc().isoformat(),
        "scope": config["niche"],
        "record_count": len(records),
        "source_errors": errors,
        "records": records,
        "next_stage": "B3 Opportunity Engine",
        "boundary": "B2 discovers and evidences demand. It does not select affiliate products or offers.",
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "records": len(records), "source_errors": len(errors), "output": str(OUTPUT_PATH)}))
    return 0


if __name__ == "__main__":
    sys.exit(run())
