"""Read-only release gate for the reusable Leverage Company OS."""
from __future__ import annotations

from pathlib import Path
import json
from .runtime_state import ensure_runtime_state, state_path
from .company_ops import DEFAULT_PROJECT_WORKFLOW

ROOT = Path(__file__).resolve().parent
WORKERS_FILE = ROOT / "workers.json"
POLICIES_FILE = ROOT / "policies.json"
LEDGER_FILE = state_path("financial_ledger.json")

REQUIRED_RUNTIME = (
    "projects.json", "tasks.json", "approvals.json", "audit_log.json",
    "financial_ledger.json", "gates.json", "resource_state.json",
)
REQUIRED_FILES = ("company.json", "workers.json", "policies.json", "resource_limits.json")
REQUIRED_TESTS = (
    "test_company_core.py", "test_finance_core.py", "test_dispatcher.py",
    "test_company_ops.py", "test_gates.py", "test_cli.py", "test_readiness.py",
    "test_project_admin.py", "test_local_sync.py", "../server/test_api.py",
)
EXPECTED_WORKERS = {
    "research-worker": "research", "data-worker": "validate", "code-worker": "build",
    "project-manager": "plan", "operations-worker": "verify", "customer-worker": "intake",
    "finance-worker": "reconcile",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "status": "pass" if passed else "fail", "detail": detail}


def company_os_readiness() -> dict:
    ensure_runtime_state()
    checks: list[dict] = []
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    checks.append(_check("core_files", not missing, "All core policy/registry files are present." if not missing else f"Missing: {', '.join(missing)}"))
    missing_runtime = [name for name in REQUIRED_RUNTIME if not state_path(name).is_file()]
    checks.append(_check("runtime_state", not missing_runtime, "All runtime state stores are available." if not missing_runtime else f"Missing: {', '.join(missing_runtime)}"))

    try:
        workers = _load(WORKERS_FILE).get("workers", []); by_id = {w.get("id"): w for w in workers}
        missing_workers = [wid for wid in EXPECTED_WORKERS if wid not in by_id]
        offline = [wid for wid, w in by_id.items() if wid in EXPECTED_WORKERS and w.get("status") != "online"]
        unverified = [wid for wid, w in by_id.items() if wid in EXPECTED_WORKERS and w.get("activation") != "verified"]
        bad_capabilities = [wid for wid, action in EXPECTED_WORKERS.items() if wid in by_id and action not in set(by_id[wid].get("capabilities", []))]
        worker_ok = not (missing_workers or offline or unverified or bad_capabilities)
        detail = "7/7 required workers online, verified, and capability-aligned."
        if not worker_ok:
            detail = f"Worker contract problems: {', '.join(sorted(set(missing_workers + offline + unverified + bad_capabilities)))}"
        checks.append(_check("worker_fleet", worker_ok, detail))
    except (OSError, json.JSONDecodeError, AttributeError):
        checks.append(_check("worker_fleet", False, "Worker registry could not be read."))

    try:
        workers = _load(WORKERS_FILE).get("workers", []); by_id = {w.get("id"): w for w in workers}
        workflow_ok = True; problems: list[str] = []; actions_seen: set[str] = set()
        for worker_id, action, _description, _dependencies in DEFAULT_PROJECT_WORKFLOW:
            if worker_id not in by_id: workflow_ok = False; problems.append(f"missing worker {worker_id}"); continue
            if action in actions_seen: workflow_ok = False; problems.append(f"duplicate workflow action {action}")
            actions_seen.add(action)
            if action not in set(by_id[worker_id].get("capabilities", [])): workflow_ok = False; problems.append(f"{worker_id} lacks {action}")
        workflow_ok = workflow_ok and actions_seen == {item[1] for item in DEFAULT_PROJECT_WORKFLOW}
        detail = "Default 8-step project workflow is unique, dependency-defined, and capability-aligned."
        if not workflow_ok: detail = f"Workflow contract problems: {', '.join(problems)}"
        checks.append(_check("workflow_contract", workflow_ok, detail))
    except (OSError, json.JSONDecodeError, AttributeError):
        checks.append(_check("workflow_contract", False, "Default project workflow could not be validated."))

    missing_tests = [name for name in REQUIRED_TESTS if not (ROOT / name).is_file()]
    checks.append(_check("test_surface", not missing_tests, "Core OS regression tests are present." if not missing_tests else f"Missing tests: {', '.join(missing_tests)}"))

    try:
        policy = _load(POLICIES_FILE).get("company_policy", {})
        policy_ok = (
            policy.get("default_mode") == "owner-controlled" and policy.get("spend_requires_approval") is True
            and policy.get("external_side_effects_require_approval") is True
            and policy.get("financial_actions_require_owner_approval") is True
            and policy.get("unknown_provider_state") == "safe_mode" and policy.get("unknown_balance_state") == "blocked"
            and policy.get("audit_every_state_change") is True
        )
        checks.append(_check("safety_policy", policy_ok, "Owner control, approval boundaries, safe mode, blocked unknown balances, and auditing are enabled." if policy_ok else "Safety policy is incomplete or weaker than the Company OS baseline."))
    except (OSError, json.JSONDecodeError, AttributeError):
        checks.append(_check("safety_policy", False, "Safety policy could not be read."))

    try:
        ledger = _load(LEDGER_FILE); money_policy = ledger.get("policy", {})
        money_ok = (
            money_policy.get("live_money_movement") is False and money_policy.get("worker_can_prepare_payout") is True
            and money_policy.get("worker_can_approve_payout") is False and money_policy.get("worker_can_execute_payout") is False
            and money_policy.get("owner_approval_required") is True and money_policy.get("never_assume_balance") is True
            and money_policy.get("never_mark_paid_without_external_confirmation") is True
        )
        checks.append(_check("financial_boundary", money_ok, "Live money movement is disabled and worker financial authority is limited to preparation." if money_ok else "Financial safety boundary is not locked to the Company OS baseline."))
    except (OSError, json.JSONDecodeError, AttributeError):
        checks.append(_check("financial_boundary", False, "Financial ledger could not be read."))

    try:
        resource_limits = _load(ROOT / "resource_limits.json"); resources = resource_limits.get("resources", [])
        unknown = [r.get("id", "unknown") for r in resources if not r.get("quota_verified", False) and r.get("status") != "unknown_quota_safe_mode"]
        gemini = next((r for r in resources if r.get("id") == "gemini"), None)
        quota_ok = bool(gemini and gemini.get("status") == "unknown_quota_safe_mode" and gemini.get("quota_verified") is False)
        checks.append(_check("resource_safety", quota_ok and not unknown, "Unknown provider quota remains explicitly in safe mode; no unlimited usage is assumed." if quota_ok and not unknown else "Resource policy does not consistently enforce unknown-quota safe mode."))
    except (OSError, json.JSONDecodeError, AttributeError):
        checks.append(_check("resource_safety", False, "Resource limits could not be read."))

    passed = all(item["status"] == "pass" for item in checks)
    return {"ready": passed, "status": "ready" if passed else "not_ready", "checks": checks,
            "release_gate": "Build next income project" if passed else "Strengthen Company OS before starting the next income project"}


if __name__ == "__main__":
    result = company_os_readiness(); print(json.dumps(result, indent=2)); raise SystemExit(0 if result["ready"] else 1)
