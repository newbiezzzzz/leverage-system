"""Reusable customer delivery gateway for Leverage.

Provider-independent order/job/artifact state for digital services. It does not
perform payments, external messaging, or public file hosting; those are adapters
that can be added later without changing the core delivery lifecycle.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

from .runtime_state import state_path

ORDERS_FILE = state_path("customer_orders.json")

STATUSES = {
    "awaiting_payment",
    "paid",
    "processing",
    "ready",
    "delivered",
    "cancelled",
    "failed",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if not ORDERS_FILE.exists():
        return {"version": 1, "orders": []}
    return json.loads(ORDERS_FILE.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    ORDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ORDERS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def create_order(customer_ref: str, service: str, project_id: str, input_manifest: list[dict] | None = None) -> dict:
    customer_ref = customer_ref.strip()
    service = service.strip()
    project_id = project_id.strip()
    if not customer_ref or not service or not project_id:
        raise ValueError("customer_ref, service and project_id are required")
    order = {
        "id": f"order-{uuid.uuid4().hex[:10]}",
        "customer_ref": customer_ref,
        "service": service,
        "project_id": project_id,
        "status": "awaiting_payment",
        "payment": {"status": "unverified", "provider": None, "external_reference": None},
        "input_manifest": input_manifest or [],
        "output_manifest": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    data = _load()
    data.setdefault("orders", []).append(order)
    data["last_modified_at"] = order["updated_at"]
    _save(data)
    return order


def update_payment(order_id: str, provider: str, external_reference: str) -> dict:
    order = get_order(order_id)
    provider = provider.strip()
    external_reference = external_reference.strip()
    if not provider or not external_reference:
        raise ValueError("provider and external_reference are required")
    order["payment"] = {"status": "verified", "provider": provider, "external_reference": external_reference}
    order["status"] = "paid"
    return _save_order(order)


def start_processing(order_id: str) -> dict:
    order = get_order(order_id)
    if order["status"] != "paid":
        raise ValueError("order must be paid before processing")
    order["status"] = "processing"
    return _save_order(order)


def attach_output(order_id: str, artifact: dict) -> dict:
    order = get_order(order_id)
    if order["status"] not in {"processing", "ready"}:
        raise ValueError("order must be processing or ready before attaching output")
    required = {"name", "kind", "locator"}
    if not required.issubset(artifact):
        raise ValueError("artifact requires name, kind and locator")
    order.setdefault("output_manifest", []).append({
        "name": str(artifact["name"]),
        "kind": str(artifact["kind"]),
        "locator": str(artifact["locator"]),
        "created_at": _now(),
    })
    order["status"] = "ready"
    return _save_order(order)


def mark_delivered(order_id: str, delivery_reference: str) -> dict:
    order = get_order(order_id)
    if order["status"] != "ready":
        raise ValueError("order must be ready before delivery")
    delivery_reference = delivery_reference.strip()
    if not delivery_reference:
        raise ValueError("delivery_reference is required")
    order["delivery"] = {"status": "delivered", "reference": delivery_reference, "delivered_at": _now()}
    order["status"] = "delivered"
    return _save_order(order)


def get_order(order_id: str) -> dict:
    for order in _load().get("orders", []):
        if order.get("id") == order_id:
            return order
    raise KeyError(f"order not found: {order_id}")


def list_orders() -> list[dict]:
    return list(_load().get("orders", []))


def _save_order(order: dict) -> dict:
    data = _load()
    replaced = False
    for index, existing in enumerate(data.get("orders", [])):
        if existing.get("id") == order.get("id"):
            order["updated_at"] = _now()
            data["orders"][index] = order
            replaced = True
            break
    if not replaced:
        raise KeyError(f"order not found: {order.get('id')}")
    data["last_modified_at"] = order["updated_at"]
    _save(data)
    return order


if __name__ == "__main__":
    print(json.dumps({"orders": len(list_orders()), "provider_independent": True}, indent=2))
