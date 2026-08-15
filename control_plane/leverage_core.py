"""Provider-independent Leverage Core and Resource Manager."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import json

@dataclass
class ResourceState:
    provider: str
    metric: str
    status: str = "unknown"
    used: Optional[float] = None
    limit: Optional[float] = None
    remaining: Optional[float] = None
    reset_at: Optional[str] = None
    quota_verified: bool = False
    source: str = "worker"
    checked_at: str = ""

class ResourceManager:
    WARNING = 0.80
    CRITICAL = 0.95

    def __init__(self, state_path="control_plane/resource_state.json"):
        self.state_path = Path(state_path)
        self.states = {}
        self.load()

    def register(self, state: ResourceState):
        state.checked_at = state.checked_at or datetime.now(timezone.utc).isoformat()
        if state.remaining is None and state.used is not None and state.limit is not None:
            state.remaining = max(0, state.limit - state.used)
        if state.limit and state.used is not None:
            ratio = state.used / state.limit
            state.status = "critical" if ratio >= self.CRITICAL else "warning" if ratio >= self.WARNING else "safe"
        elif not state.quota_verified:
            state.status = "unknown_quota_safe_mode"
        self.states[f"{state.provider}:{state.metric}"] = state
        self.save()

    def can_run(self, provider, metric):
        state = self.states.get(f"{provider}:{metric}")
        if not state:
            return True, "no_cached_observation"
        if state.status == "critical":
            return False, "provider_near_limit"
        if state.status == "warning":
            return True, "reduced_request_mode"
        return True, "safe" if state.status == "safe" else "safe_mode_unknown_quota"

    def snapshot(self):
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "resources": [asdict(s) for s in self.states.values()],
            "policy": {
                "warning_threshold": self.WARNING,
                "critical_threshold": self.CRITICAL,
                "unknown_quota_policy": "safe_mode",
                "no_unbounded_retry": True,
                "zero_cost_core": True
            }
        }

    def save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")

    def load(self):
        if not self.state_path.exists():
            return
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        for item in data.get("resources", []):
            s = ResourceState(**{k:v for k,v in item.items() if k in ResourceState.__dataclass_fields__})
            self.states[f"{s.provider}:{s.metric}"] = s

if __name__ == "__main__":
    print(json.dumps(ResourceManager().snapshot(), indent=2))
