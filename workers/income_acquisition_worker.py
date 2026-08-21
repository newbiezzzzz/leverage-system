"""Leverage Income Acquisition Worker.

Discovery-first autonomous income worker for agent job marketplaces.

Rules:
- RM0-first: no paid bids or external spend without Owner approval.
- No local-PC workload: execution must use approved remote runners.
- Quota-aware: never consume more than the configured free bid/request budget.
- Discovery is autonomous; binding bids and money movement remain gated.

The worker uses a public MoltJobs jobs page for discovery when no API key is
configured, and the authenticated API when MOLTJOBS_API_KEY is available.
"""
from __future__ import annotations

import html
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

BASE_URL = "https://moltjobs.io"
OPEN_JOBS_URL = f"{BASE_URL}/open-jobs"
API_URL = "https://api.moltjobs.io/v1/jobs"
DEFAULT_CONFIG = Path("control_plane/income_acquisition_config.json")
DEFAULT_STATE = Path("control_plane/income_acquisition_state.json")

KEYWORDS = {
    "research": 18,
    "data": 18,
    "extract": 16,
    "analysis": 14,
    "analyze": 14,
    "python": 14,
    "api": 12,
    "automation": 15,
    "json": 10,
    "csv": 10,
    "documentation": 8,
    "content": 7,
    "web": 8,
    "spreadsheet": 10,
    "classification": 12,
    "lead": 8,
}

@dataclass(frozen=True)
class Job:
    job_id: str
    title: str
    url: str
    budget_usdc: float | None
    poster: str | None
    raw_text: str


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    return _load_json(path, {
        "version": 1,
        "platform": "moltjobs",
        "discovery": {"enabled": True, "max_jobs": 25, "minimum_score": 45},
        "quota": {"free_bids_per_month": 10, "free_requests_per_minute": 120, "max_bids_per_cycle": 1},
        "economics": {"min_budget_usdc": 5.0, "execution_cost_rm": 0.0, "min_expected_net_rm": 1.0},
        "policy": {"no_paid_bids": True, "no_pc_execution": True, "no_spam": True, "owner_approval_for_binding_bid": True, "owner_approval_for_money_movement": True},
    })


def _fetch(url: str, api_key: str | None = None, timeout: int = 20) -> str:
    headers = {"User-Agent": "Leverage-Income-Acquisition/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["x-api-key"] = api_key
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _budget(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*USDC", text, flags=re.I)
    return float(match.group(1)) if match else None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _parse_public_jobs(raw_html: str, max_jobs: int = 25) -> list[Job]:
    # Server-rendered job links are enough for discovery; details are fetched later.
    jobs: list[Job] = []
    seen: set[str] = set()
    pattern = re.compile(r'href=["\'](/(?:jobs|job)/[^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    for match in pattern.finditer(raw_html):
        path, inner = match.groups()
        url = urljoin(BASE_URL, path)
        if url in seen:
            continue
        seen.add(url)
        surrounding = raw_html[max(0, match.start() - 1800): min(len(raw_html), match.end() + 1800)]
        title = _clean_text(inner)
        text = _clean_text(surrounding)
        if not title or title.lower() in {"view details", "details"}:
            continue
        budget = _budget(text)
        poster_match = re.search(r"By\s+([A-Za-z0-9_.-]{2,64})", text, flags=re.I)
        poster = poster_match.group(1) if poster_match else None
        job_id = path.rstrip("/").split("/")[-1]
        jobs.append(Job(job_id, title, url, budget, poster, text))
        if len(jobs) >= max_jobs:
            break
    return jobs


def _parse_api_jobs(raw_json: str, max_jobs: int = 25) -> list[Job]:
    payload = json.loads(raw_json)
    items = payload.get("data", payload if isinstance(payload, list) else [])
    jobs: list[Job] = []
    for item in items[:max_jobs]:
        jobs.append(Job(
            job_id=str(item.get("id", "")),
            title=str(item.get("title") or item.get("name") or item.get("prompt") or "Untitled job"),
            url=str(item.get("url") or f"{BASE_URL}/jobs/{item.get('id', '')}"),
            budget_usdc=float(item["budgetUsdc"]) if item.get("budgetUsdc") not in (None, "") else None,
            poster=str(item.get("poster") or item.get("posterHandle") or "") or None,
            raw_text=json.dumps(item, ensure_ascii=False),
        ))
    return jobs


def score_job(job: Job, config: dict) -> tuple[float, list[str]]:
    minimum_budget = float(config["economics"].get("min_budget_usdc", 5.0))
    score = 0.0
    reasons: list[str] = []
    text = f"{job.title} {job.raw_text}".lower()
    for keyword, weight in KEYWORDS.items():
        if keyword in text:
            score += weight
            reasons.append(keyword)
    if job.budget_usdc is not None:
        if job.budget_usdc >= minimum_budget:
            score += min(25.0, job.budget_usdc / 4.0)
            reasons.append("budget>=minimum")
        else:
            score -= 30
    else:
        score -= 5
        reasons.append("budget-unknown")
    if any(word in text for word in ("captcha", "password", "credential", "private key", "impersonate")):
        score -= 60
        reasons.append("unsafe-content-risk")
    return max(0.0, min(100.0, score)), reasons


def discover_jobs(config_path: Path = DEFAULT_CONFIG, state_path: Path = DEFAULT_STATE) -> dict:
    config = load_config(config_path)
    if not config.get("discovery", {}).get("enabled", True):
        return {"status": "disabled", "jobs": []}

    api_key = __import__("os").environ.get("MOLTJOBS_API_KEY")
    max_jobs = int(config["discovery"].get("max_jobs", 25))
    source = "authenticated_api" if api_key else "public_open_jobs_page"
    try:
        raw = _fetch(f"{API_URL}?status=OPEN&limit={max_jobs}", api_key) if api_key else _fetch(OPEN_JOBS_URL)
        jobs = _parse_api_jobs(raw, max_jobs) if api_key else _parse_public_jobs(raw, max_jobs)
    except Exception as exc:  # discovery must fail safely
        state = _load_json(state_path, {"version": 1, "runs": []})
        result = {"status": "error", "source": source, "error": str(exc), "jobs": []}
        state.setdefault("runs", []).append({"timestamp": datetime.now(timezone.utc).isoformat(), **result})
        _save_json(state_path, state)
        return result

    ranked = []
    minimum_score = float(config["discovery"].get("minimum_score", 45))
    for job in jobs:
        score, reasons = score_job(job, config)
        if score >= minimum_score:
            ranked.append({
                "job_id": job.job_id,
                "title": job.title,
                "url": job.url,
                "poster": job.poster,
                "budget_usdc": job.budget_usdc,
                "score": round(score, 2),
                "reasons": reasons,
                "status": "candidate",
                "buyer_identified": bool(job.poster) or bool(job.job_id),
                "bid_status": "not_submitted",
                "owner_approval_required": True,
            })
    ranked.sort(key=lambda item: (item["score"], item["budget_usdc"] or 0), reverse=True)

    now = datetime.now(timezone.utc).isoformat()
    state = _load_json(state_path, {"version": 1, "runs": [], "active_candidates": []})
    state["last_scan_at"] = now
    state["source"] = source
    state["platform"] = "MoltJobs"
    state["active_candidates"] = ranked
    state.setdefault("runs", []).append({"timestamp": now, "status": "success", "source": source, "candidate_count": len(ranked)})
    state["runs"] = state["runs"][-50:]
    state["operating_state"] = "identifying_buyer" if ranked else "scanning_for_buyer"
    state["controls"] = {
        "rm0": bool(config["policy"].get("no_paid_bids", True)),
        "no_pc_execution": bool(config["policy"].get("no_pc_execution", True)),
        "free_bids_per_month": int(config["quota"].get("free_bids_per_month", 10)),
        "max_bids_per_cycle": int(config["quota"].get("max_bids_per_cycle", 1)),
        "binding_bid_owner_approval": bool(config["policy"].get("owner_approval_for_binding_bid", True)),
        "money_movement_owner_approval": bool(config["policy"].get("owner_approval_for_money_movement", True)),
    }
    _save_json(state_path, state)
    return {"status": "success", "source": source, "operating_state": state["operating_state"], "jobs": ranked, "scanned": len(jobs), "candidates": len(ranked)}


def self_test() -> dict:
    config = load_config()
    demo = Job("demo-1", "Extract CSV data and research API automation", "https://moltjobs.io/jobs/demo-1", 10.0, "demo-poster", "data extraction python api")
    score, reasons = score_job(demo, config)
    return {
        "worker": "income-acquisition-worker",
        "status": "healthy",
        "platform": "MoltJobs",
        "mode": "discover_then_owner_gate_bid",
        "rm0": True,
        "no_pc_execution": True,
        "free_bid_limit": int(config["quota"]["free_bids_per_month"]),
        "demo_score": score,
        "demo_reasons": reasons,
    }

if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
    print(json.dumps(discover_jobs(), indent=2))
