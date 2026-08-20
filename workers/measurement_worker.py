"""Provider-agnostic measurement worker.

Prepares measurement configuration and verifies imported evidence.
Provider credentials and external writes are intentionally out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MeasurementResult:
    provider: str
    status: str
    evidence: dict[str, Any]


def prepare(provider: str, site_code: str | None = None) -> MeasurementResult:
    if provider == "goatcounter" and not site_code:
        return MeasurementResult(
            provider=provider,
            status="needs_configuration",
            evidence={"required": ["site_code"]},
        )
    return MeasurementResult(
        provider=provider,
        status="ready",
        evidence={"configured": bool(site_code)},
    )


def verify_import(
    provider: str,
    date_range: str,
    metrics: dict[str, Any],
    source_reference: str,
) -> MeasurementResult:
    if not provider or not date_range or not source_reference:
        return MeasurementResult(
            provider=provider,
            status="rejected",
            evidence={"reason": "provider, date_range and source_reference are required"},
        )
    return MeasurementResult(
        provider=provider,
        status="verified",
        evidence={
            "date_range": date_range,
            "metrics": metrics,
            "source_reference": source_reference,
        },
    )
