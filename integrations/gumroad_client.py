"""Read-only Gumroad commerce adapter for Leverage.

Uses GUMROAD_ACCESS_TOKEN from the local environment. The token is never
stored in source control, runtime state, or logs.

Current scope is deliberately read-only: health check, products, and sales.
Product creation/upload and money movement are not performed by this module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json

BASE_URL = "https://api.gumroad.com/v2"


class GumroadError(RuntimeError):
    pass


@dataclass(frozen=True)
class GumroadClient:
    token: str

    @classmethod
    def from_env(cls) -> "GumroadClient":
        token = os.environ.get("GUMROAD_ACCESS_TOKEN", "").strip()
        if not token:
            raise GumroadError("GUMROAD_ACCESS_TOKEN is not set")
        return cls(token=token)

    def _get(self, path: str) -> Any:
        req = Request(
            BASE_URL + path,
            method="GET",
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
        )
        try:
            with urlopen(req, timeout=20) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise GumroadError(f"Gumroad API HTTP {exc.code}: {body[:300]}") from exc
        except URLError as exc:
            raise GumroadError(f"Gumroad API connection failed: {exc.reason}") from exc
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise GumroadError("Gumroad API returned invalid JSON") from exc

    def products(self) -> dict[str, Any]:
        return self._get("/products")

    def sales(self) -> dict[str, Any]:
        return self._get("/sales")

    def health(self) -> dict[str, Any]:
        data = self.products()
        return {
            "provider": "Gumroad",
            "status": "connected" if data.get("success") else "error",
            "product_count": len(data.get("products", [])),
            "read_only": True,
        }


def self_test() -> dict[str, Any]:
    configured = bool(os.environ.get("GUMROAD_ACCESS_TOKEN", "").strip())
    return {
        "integration": "gumroad",
        "status": "configured" if configured else "missing_secret",
        "secret_source": "environment:GUMROAD_ACCESS_TOKEN",
        "secret_persisted_in_repo": False,
        "read_only": True,
    }


if __name__ == "__main__":
    result = self_test()
    print(json.dumps(result, indent=2))
