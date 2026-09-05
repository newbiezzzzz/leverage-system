"""B3 Opportunity Engine for Leverage's Affiliate Project.

Turns B2 research signals into ranked, evidence-backed automotive opportunities.
B3 prioritizes problems and content opportunities only; product/offer selection
remains a B4 responsibility.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "affiliate_research_queue.json"
CONFIG_PATH = ROOT / "affiliate_opportunity_config.json"
OUTPUT_PATH = ROOT / "affiliate_opportunity_queue.json"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", text.lower())
        if token not in {"the", "and", "for", "with", "this", "that", "from", "yang", "untuk", "atau"}
    }


def normalized_problem(record: dict) -> str:
    text = record.get("problem", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


def source_weight(kind: str, config: dict) -> float:
    return float(config["scoring"]["source_weights"].get(kind, 0.5))


def freshness_factor(status: str, config: dict) -> float:
    return float(config["scoring"]["freshness_weights"].get(status, 0.6))


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def cluster_records(records: list[dict], threshold: float) -> list[list[dict]]:
    clusters: list[list[dict]] = []
    for record in records:
        problem = normalized_problem(record)
        best = None
        best_similarity = 0.0
        for index, cluster in enumerate(clusters):
            candidate = cluster[0]
            score = similarity(problem, normalized_problem(candidate))
            if score > best_similarity:
                best_similarity = score
                best = index
        if best is not None and best_similarity >= threshold:
            clusters[best].append(record)
        else:
            clusters.append([record])
    return clusters


def aggregate(cluster: list[dict], config: dict) -> dict:
    primary = max(
        cluster,
        key=lambda r: (
            int(r.get("buyer_intent", 0)),
            int(r.get("problem_potential", r.get("product_potential", 0))),
            int(r.get("content_potential", 0)),
        ),
    )
    kinds = {r.get("source_kind", "unknown") for r in cluster}
    source_score = max(source_weight(kind, config) for kind in kinds)
    intent = max(int(r.get("buyer_intent", 0)) for r in cluster)
    problem = max(int(r.get("product_potential", 0)) for r in cluster)
    content = max(int(r.get("content_potential", 0)) for r in cluster)
    fresh = max(freshness_factor(r.get("freshness_status", "unknown"), config) for r in cluster)
    recurrence = min(len(cluster), int(config["scoring"]["recurrence_cap"]))
    recurrence_bonus = min(float(config["scoring"]["recurrence_bonus_max"]), recurrence * float(config["scoring"]["recurrence_bonus_per_signal"]))
    multi_source_bonus = float(config["scoring"]["multi_source_bonus"]) if len(kinds) > 1 else 0.0

    raw = (
        intent * 22
        + problem * 18
        + content * 15
        + source_score * 15
        + fresh * 10
        + recurrence_bonus
        + multi_source_bonus
    )
    score = round(min(100.0, raw), 1)
    evidence = [
        {
            "source": r.get("source"),
            "url": r.get("evidence_url"),
            "excerpt": r.get("evidence", "")[:500],
        }
        for r in cluster[: int(config["output"]["max_evidence_per_opportunity"])]
    ]
    opportunity_id = "opp-" + hashlib.sha256(normalized_problem(primary).encode("utf-8")).hexdigest()[:16]
    return {
        "id": opportunity_id,
        "project": "affiliate-project",
        "problem": primary.get("problem", ""),
        "normalized_problem": normalized_problem(primary),
        "opportunity_score": score,
        "priority": "high" if score >= 70 else "medium" if score >= 50 else "low",
        "signals": {
            "buyer_intent": intent,
            "problem_strength": problem,
            "content_potential": content,
            "source_strength": round(source_score, 2),
            "freshness_factor": round(fresh, 2),
            "recurrence": recurrence,
            "source_count": len(kinds),
            "evidence_count": len(cluster),
        },
        "evidence": evidence,
        "status": "candidate" if score >= float(config["output"]["minimum_candidate_score"]) else "watch",
        "next_stage": "B4 Product & Affiliate Engine",
        "created_at": now_utc().isoformat(),
    }


def run() -> int:
    config = load_json(CONFIG_PATH)
    research = load_json(INPUT_PATH)
    records = [r for r in research.get("records", []) if r.get("project") == "affiliate-project"]
    clusters = cluster_records(records, float(config["scoring"]["dedupe_similarity_threshold"]))
    opportunities = [aggregate(cluster, config) for cluster in clusters]
    opportunities.sort(key=lambda item: (-item["opportunity_score"], item["problem"]))
    limit = int(config["output"]["max_opportunities"])
    opportunities = opportunities[:limit]
    for index, opportunity in enumerate(opportunities, start=1):
        opportunity["rank"] = index

    payload = {
        "version": 1,
        "project": "affiliate-project",
        "generated_at": now_utc().isoformat(),
        "input_generated_at": research.get("generated_at"),
        "record_count": len(records),
        "cluster_count": len(clusters),
        "opportunity_count": len(opportunities),
        "opportunities": opportunities,
        "next_stage": "B4 Product & Affiliate Engine",
        "boundary": "B3 ranks demand opportunities. It does not select products, affiliate networks, offers, or make purchases.",
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "research_records": len(records), "clusters": len(clusters), "opportunities": len(opportunities), "output": str(OUTPUT_PATH)}))
    return 0


if __name__ == "__main__":
    sys.exit(run())
