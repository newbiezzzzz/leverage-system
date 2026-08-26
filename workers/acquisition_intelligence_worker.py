"""Leverage Acquisition Intelligence Worker.

Analyzes verified public telemetry and turns it into acquisition recommendations.
An OpenAI-compatible LLM endpoint is optional; when unavailable, a deterministic
rule engine produces evidence-backed recommendations instead.

The worker never invents metrics, moves money, publishes externally, or sends
outreach. It only produces analysis and a next-action recommendation.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

ROLE = "acquisition intelligence and evidence interpretation"


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def deterministic_analysis(metrics: dict[str, Any]) -> dict[str, Any]:
    visitors = _num(metrics.get("unique_visitors"))
    page_views = _num(metrics.get("page_views"))
    quotes = _num(metrics.get("calculated_quotes"))
    clicks = _num(metrics.get("pro_clicks"))
    conversion = _num(metrics.get("conversion_rate"))
    events = _num(metrics.get("events"))
    sources = metrics.get("traffic_sources") or []

    evidence = []
    recommendations = []
    confidence = "low"

    if visitors is None and page_views is None:
        evidence.append("No verified traffic totals are available yet.")
        recommendations.append("Keep the public telemetry live and wait for verified traffic evidence before scaling acquisition.")
    else:
        confidence = "medium"
        evidence.append(
            f"Verified traffic: {int(page_views or 0)} page views and "
            f"{int(visitors or 0)} unique visitors."
        )
        if quotes is not None:
            evidence.append(f"Calculator interactions recorded: {int(quotes)}.")
        if clicks is not None:
            evidence.append(f"Outbound Product 1 clicks recorded: {int(clicks)}.")
        if conversion is not None:
            evidence.append(f"Observed click/page-view conversion: {conversion:.2f}%.")

        if clicks == 0:
            recommendations.append("Improve the free-tool-to-Product-1 call-to-action before adding another acquisition channel.")
        elif conversion is not None and conversion < 2:
            recommendations.append("Prioritize CTA placement, offer clarity and product-detail presentation; current buyer intent is present but weak.")
        else:
            recommendations.append("Double down on the strongest measured traffic source and test one additional compliant acquisition angle.")

    if sources:
        top = sources[0]
        name = top.get("name", "unknown")
        views = int(top.get("views", 0) or 0)
        evidence.append(f"Top recorded source: {name} ({views} page views).")
        recommendations.insert(0, f"Prioritize the {name} source because it currently produces the most measured traffic.")

    if events is not None and events == 0:
        recommendations.append("Verify the telemetry storage binding if public pages are live but no events are appearing.")

    return {
        "analyst": "Leverage Acquisition Analyst",
        "mode": "deterministic",
        "confidence": confidence,
        "evidence": evidence,
        "recommendations": recommendations[:3],
        "financial_action": "none",
        "external_action": "none",
        "owner_approval_required": False,
        "metrics": metrics,
    }


def llm_analysis(metrics: dict[str, Any]) -> dict[str, Any] | None:
    endpoint = os.getenv("LEVERAGE_LLM_ENDPOINT", "").strip()
    if not endpoint:
        return None
    model = os.getenv("LEVERAGE_LLM_MODEL", "gpt-4.1-mini").strip()
    api_key = os.getenv("LEVERAGE_LLM_API_KEY", "").strip()
    prompt = {
        "role": "You are Leverage's acquisition analyst. Use only supplied verified metrics. Never invent numbers. Recommend at most 3 actions. Do not recommend paid acquisition or unsupervised external outreach. Return JSON.",
        "metrics": metrics,
    }
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": prompt["role"]},
            {"role": "user", "content": json.dumps(prompt["metrics"], sort_keys=True)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
        parsed = json.loads(content) if isinstance(content, str) else content
        return {
            "analyst": "Leverage Acquisition Analyst",
            "mode": "llm",
            "confidence": parsed.get("confidence", "medium"),
            "evidence": parsed.get("evidence", []),
            "recommendations": parsed.get("recommendations", [])[:3],
            "financial_action": "none",
            "external_action": "none",
            "owner_approval_required": False,
            "metrics": metrics,
        }
    except Exception:
        return None


def analyze(metrics: dict[str, Any]) -> dict[str, Any]:
    return llm_analysis(metrics) or deterministic_analysis(metrics)


def self_test() -> dict[str, Any]:
    report = analyze({
        "events": 20,
        "page_views": 10,
        "unique_visitors": 7,
        "calculated_quotes": 4,
        "pro_clicks": 1,
        "conversion_rate": 10.0,
        "traffic_sources": [{"name": "google", "views": 8}],
        "last_event": "2026-08-26T15:00:00Z",
    })
    assert report["recommendations"]
    assert report["financial_action"] == "none"
    assert report["external_action"] == "none"
    return {"worker": "acquisition-intelligence-worker", "role": ROLE, "status": "healthy", "report": report}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
