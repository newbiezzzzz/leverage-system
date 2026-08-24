"""Creative Director worker for Leverage Product Factory v2.

Deterministic preflight scoring and revision routing. It does not publish or spend money.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreativeReview:
    score: int
    decision: str
    reasons: tuple[str, ...]


REQUIRED = (
    "hierarchy", "typography", "spacing", "color", "imagery",
    "responsive", "accessibility", "brand", "originality", "conversion",
)


def review_asset(signals: dict[str, float], minimum: int = 85) -> CreativeReview:
    missing = [name for name in REQUIRED if name not in signals]
    if missing:
        return CreativeReview(0, "redesign", (f"missing design signals: {', '.join(missing)}",))
    values = [max(0.0, min(100.0, float(signals[name]))) for name in REQUIRED]
    score = round(sum(values) / len(values))
    reasons: list[str] = []
    for name in REQUIRED:
        if float(signals[name]) < minimum:
            reasons.append(f"{name} below {minimum}")
    decision = "publish" if score >= minimum and not reasons else "redesign"
    return CreativeReview(score, decision, tuple(reasons) or ("passes creative gate",))


def design_brief(product_name: str, audience: str, format_name: str) -> dict:
    return {
        "product": product_name,
        "audience": audience,
        "format": format_name,
        "requirements": list(REQUIRED),
        "instruction": "Prioritize clarity, visual hierarchy, intentional composition, responsive behavior, and conversion without using deceptive design.",
    }


if __name__ == "__main__":
    sample = {key: 90 for key in REQUIRED}
    print(review_asset(sample))
