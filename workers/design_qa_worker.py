"""Design/UX QA worker.

Provides a deterministic gate that can be fed by screenshot/visual inspection tooling.
It never publishes by itself.
"""
from __future__ import annotations

CATEGORIES = (
    "layout", "mobile", "readability", "interaction", "consistency",
    "accessibility", "performance", "visual_polish", "content_density", "cta_clarity",
)


def evaluate(scores: dict[str, float], minimum: int = 85) -> dict:
    missing = [key for key in CATEGORIES if key not in scores]
    if missing:
        return {"status": "fail", "score": 0, "missing": missing, "action": "redesign"}
    normalized = {k: max(0.0, min(100.0, float(scores[k]))) for k in CATEGORIES}
    score = round(sum(normalized.values()) / len(normalized))
    weak = [k for k, v in normalized.items() if v < minimum]
    return {
        "status": "pass" if score >= minimum and not weak else "fail",
        "score": score,
        "weak_categories": weak,
        "action": "publish" if score >= minimum and not weak else "redesign",
    }


def mobile_check(viewports: list[dict]) -> dict:
    failures = [v for v in viewports if not v.get("pass")]
    return {"status": "pass" if not failures else "fail", "failures": failures}
