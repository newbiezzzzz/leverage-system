"""P-003 Game Idea Worker.

Deterministic scoring layer for AI-generated Roblox entertainment concepts.
It does not publish games, spend money, or make irreversible external changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


WEIGHTS = {
    "hook_and_first_minute": 20,
    "replayability_and_retention": 20,
    "social_and_co_play": 15,
    "content_and_shareability": 15,
    "novelty_and_differentiation": 10,
    "buildability_and_iteration_speed": 10,
    "monetization_fit": 5,
    "discovery_and_metadata_fit": 5,
}

HARD_REJECT_FIELDS = ("hard_rejects",)
BUILD_THRESHOLD = 70
PREFERRED_THRESHOLD = 80


@dataclass(frozen=True)
class IdeaEvaluation:
    idea_id: str
    score: int
    decision: str
    reasons: tuple[str, ...]


def _clamp_score(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def evaluate_idea(idea: dict[str, Any]) -> IdeaEvaluation:
    idea_id = str(idea.get("idea_id", "unknown"))
    rejects = [str(x) for x in idea.get("hard_rejects", []) if str(x).strip()]
    scores = idea.get("scores", {})
    reasons: list[str] = []

    if rejects:
        return IdeaEvaluation(idea_id, 0, "reject", tuple(f"hard reject: {x}" for x in rejects))

    missing = [name for name in WEIGHTS if name not in scores]
    if missing:
        return IdeaEvaluation(idea_id, 0, "reject", (f"missing scores: {', '.join(missing)}",))

    weighted_total = sum(_clamp_score(scores[name]) * weight for name, weight in WEIGHTS.items())
    score = round(weighted_total / 100.0)

    if score >= PREFERRED_THRESHOLD:
        decision = "build_candidate"
        reasons.append("passes preferred pre-build score")
    elif score >= BUILD_THRESHOLD:
        decision = "prototype_only"
        reasons.append("passes minimum build threshold but needs stronger evidence")
    else:
        decision = "reject"
        reasons.append("below minimum build threshold")

    for name in WEIGHTS:
        if _clamp_score(scores[name]) < 50:
            reasons.append(f"weak {name}")

    return IdeaEvaluation(idea_id, score, decision, tuple(reasons))


def rank_ideas(ideas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evaluations = [evaluate_idea(idea) for idea in ideas]
    ranked = []
    for evaluation in evaluations:
        ranked.append({
            "idea_id": evaluation.idea_id,
            "score": evaluation.score,
            "decision": evaluation.decision,
            "reasons": list(evaluation.reasons),
        })
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def self_test() -> dict[str, Any]:
    sample = {
        "idea_id": "sample-social-race",
        "scores": {name: 90 for name in WEIGHTS},
    }
    result = evaluate_idea(sample)
    return {
        "worker": "game-idea-worker",
        "status": "healthy" if result.score == 90 and result.decision == "build_candidate" else "unhealthy",
        "sample": {
            "score": result.score,
            "decision": result.decision,
        },
        "external_dependencies": [],
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    import json
    print(json.dumps(self_test(), indent=2))
