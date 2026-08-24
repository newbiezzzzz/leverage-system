"""Content and marketing asset planner for Product Factory v2.

Creates a structured content plan; actual publishing remains guarded by channel adapters.
"""
from __future__ import annotations


def build_content_plan(product: dict) -> dict:
    name = product.get("name", "Product")
    problem = product.get("problem", "a specific customer problem")
    return {
        "product": name,
        "core_message": f"Solve {problem} with a practical, easy-to-use tool.",
        "assets": [
            {"type": "landing_page", "purpose": "conversion"},
            {"type": "educational_article", "purpose": "search_discovery"},
            {"type": "short_social_post", "purpose": "awareness"},
            {"type": "square_visual", "purpose": "visual_discovery"},
            {"type": "comparison_visual", "purpose": "decision_support"},
            {"type": "faq", "purpose": "objection_handling"},
        ],
        "rules": [
            "useful before promotional",
            "no spam or deceptive claims",
            "platform-specific presentation",
            "creative review required before publication",
        ],
    }
