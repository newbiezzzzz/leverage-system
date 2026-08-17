"""Guarded finance operations for Leverage."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
from .runtime_state import state_path

ROOT = Path(__file__).resolve().parent
LEDGER_FILE = state_path("financial_ledger.json")
APPROVALS_FILE = state_path("approvals.json")

@dataclass
class PayoutRequest:
    id: str
    amount: float
    currency: str
    source_account: str
    destination: str
    purpose: str
    status: str = "prepared"
    approval_required: bool = True
    owner_approval_id: str | None = None
    external_reference: str | None = None
    created_at: str = ""

def now() -> str: return datetime.now(timezone.utc).isoformat()
def load(path: Path) -> dict: return json.loads(path.read_text(encoding="utf-8"))
def save(path: Path, value: dict) -> None: path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

def prepare_owner_payout(amount: float, destination: str, purpose: str, currency: str = "MYR") -> PayoutRequest:
    if amount <= 0: raise ValueError("payout amount must be positive")
    if not destination.strip(): raise ValueError("destination is required")
    request = PayoutRequest(id=f"payout-{uuid.uuid4().hex[:10]}", amount=round(amount, 2), currency=currency, source_account="company", destination=destination, purpose=purpose.strip() or "owner payout", created_at=now())
    ledger = load(LEDGER_FILE); ledger.setdefault("payout_queue", []).append(asdict(request)); ledger["last_modified_at"] = now(); save(LEDGER_FILE, ledger); return request

def can_execute_payout(request_id: str) -> tuple[bool, str]:
    ledger = load(LEDGER_FILE)
    for request in ledger.get("payout_queue", []):
        if request.get("id") == request_id:
            if request.get("status") != "approved": return False, "owner approval is required"
            if not request.get("owner_approval_id"): return False, "approval reference is missing"
            if not ledger.get("policy", {}).get("live_money_movement", False): return False, "live money movement is disabled"
            return False, "payment provider execution is not implemented"
    return False, "payout request not found"

def reconcile_entry(description: str, amount: float, direction: str, verified_external_reference: str | None = None) -> dict:
    if direction not in {"income", "expense", "transfer"}: raise ValueError("direction must be income, expense or transfer")
    entry = {"id": f"entry-{uuid.uuid4().hex[:10]}", "description": description.strip(), "amount": round(float(amount), 2), "currency": "MYR", "direction": direction, "verified": bool(verified_external_reference), "external_reference": verified_external_reference, "created_at": now()}
    ledger = load(LEDGER_FILE); ledger.setdefault("entries", []).append(entry); ledger["last_modified_at"] = now(); save(LEDGER_FILE, ledger); return entry
