"""Leverage AgentJob income worker.

AgentJob is used as a zero-cost-first marketplace adapter. Public discovery
needs no API key; authenticated operation uses AGENTJOB_API_KEY. The worker
never spends money, executes work on the Owner PC, or performs irreversible
external actions without the existing Leverage approval boundary.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://agent-job.ai"
MCP_URL = f"{BASE}/api/mcp"
CONFIG = Path("control_plane/agentjob_income_config.json")
STATE = Path("control_plane/agentjob_income_state.json")


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def config() -> dict:
    return load_json(CONFIG, {
        "version": 1,
        "platform": "AgentJob",
        "quota": {"public_poll_seconds": 60, "authenticated_poll_seconds": 45, "max_task_wait_seconds": 60},
        "policy": {"rm0": True, "no_spend": True, "no_paid_ads": True, "no_impersonation": True, "respect_platform_rules": True, "owner_approval_for_binding_external_action": True, "owner_approval_for_money_movement": True},
        "execution": {"local_pc_execution": False, "allowed_runners": ["github-actions", "cloudflare"]},
    })


def mcp_request(tool: str, arguments: dict | None = None, api_key: str | None = None) -> dict:
    """Call a public/authenticated AgentJob MCP tool.

    The platform documents MCP Streamable HTTP at /api/mcp. This helper keeps
    discovery and execution provider-specific while preserving Leverage's
    policy boundary.
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "Leverage-AgentJob/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments or {}},
    }
    req = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def record(state: dict, status: str, detail: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    state.setdefault("runs", []).append({"timestamp": now, "status": status, **detail})
    state["runs"] = state["runs"][-50:]
    state["last_scan_at"] = now
    save_json(STATE, state)
    return state


def discover_public() -> dict:
    cfg = config()
    state = load_json(STATE, {"version": 1, "platform": "AgentJob", "runs": [], "active_candidates": []})
    try:
        result = mcp_request("list_posts", {"sort": "recent", "page": 1, "limit": 20})
        state["source"] = "public_mcp"
        state["operating_state"] = "identifying_buyer"
        state["active_candidates"] = [{"source": "AgentJob", "data": result, "status": "candidate", "owner_approval_required_for_external_action": True}]
        state["controls"] = {
            "rm0": bool(cfg["policy"]["rm0"]),
            "local_pc_execution": False,
            "public_poll_seconds": int(cfg["quota"]["public_poll_seconds"]),
            "authenticated_poll_seconds": int(cfg["quota"]["authenticated_poll_seconds"]),
            "max_task_wait_seconds": int(cfg["quota"]["max_task_wait_seconds"]),
        }
        return record(state, "success", {"source": "public_mcp", "candidate_count": 1})
    except Exception as exc:
        state["operating_state"] = "scanning_for_buyer"
        return record(state, "error", {"source": "public_mcp", "error": str(exc), "candidate_count": 0})


def authenticated_status() -> dict:
    """Check agent status and available work when the API key is authorized."""
    api_key = os.environ.get("AGENTJOB_API_KEY")
    state = load_json(STATE, {"version": 1, "platform": "AgentJob", "runs": [], "active_candidates": []})
    if not api_key:
        state["operating_state"] = "awaiting_agent_credential"
        return record(state, "blocked", {"reason": "AGENTJOB_API_KEY not configured"})
    try:
        profile = mcp_request("get_my_profile", {}, api_key)
        state["agent_profile"] = profile
        state["operating_state"] = "ready_for_paid_work"
        return record(state, "success", {"source": "authenticated_mcp", "profile_checked": True})
    except Exception as exc:
        return record(state, "error", {"source": "authenticated_mcp", "error": str(exc)})


def self_test() -> dict:
    cfg = config()
    return {
        "worker": "agentjob-income-worker",
        "status": "healthy",
        "platform": "AgentJob",
        "rm0": bool(cfg["policy"]["rm0"]),
        "local_pc_execution": False,
        "public_discovery_no_key": True,
        "authenticated_env": bool(os.environ.get("AGENTJOB_API_KEY")),
        "poll_seconds": int(cfg["quota"]["public_poll_seconds"]),
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
    print(json.dumps(discover_public(), indent=2))
    if os.environ.get("AGENTJOB_API_KEY"):
        print(json.dumps(authenticated_status(), indent=2))
