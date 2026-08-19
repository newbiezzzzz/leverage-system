"""Safe Gumroad commerce adapter for Leverage.

Reads GUMROAD_ACCESS_TOKEN only from the local environment. Never persists the
secret, prints it, or sends it to source control. This adapter is intentionally
read-only: it can verify the account and retrieve products/sales for finance
and dashboard use, but it cannot create products or move money.
"""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = "https://api.gumroad.com/v2"
TOKEN_ENV = "GUMROAD_ACCESS_TOKEN"


def _token() -> str:
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise RuntimeError(f"{TOKEN_ENV} is not set")
    return token


def _get(path: str, params: dict[str, str] | None = None) -> dict:
    token = _token()
    url = f"{BASE_URL}/{path.lstrip('/')}"
    if params:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Gumroad API HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Gumroad API network error: {exc.reason}") from exc


def health_check() -> dict:
    """Verify token/account access and return only non-secret health data."""
    data = _get("user")
    user = data.get("user", data)
    return {
        "status": "healthy",
        "provider": "gumroad",
        "account_id_present": bool(user.get("id")),
        "email_present": bool(user.get("email")),
        "token_present": True,
        "read_only": True,
        "money_movement": False,
    }


def list_products() -> list[dict]:
    """Return available products from the connected Gumroad account."""
    data = _get("products")
    return data.get("products", [])


def list_sales(after: str | None = None) -> list[dict]:
    """Return sales records for revenue reconciliation."""
    params = {"after": after} if after else None
    data = _get("sales", params)
    return data.get("sales", [])


if __name__ == "__main__":
    print(json.dumps(health_check(), indent=2))
