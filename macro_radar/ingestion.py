from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .repository import SupabaseRepository
from .sources import (
    BnsInflationConnector,
    BrentConnector,
    NbkFxConnector,
    NbkPolicyConnector,
)
from .sources.base import Connector
from .validation import validate_observation


@dataclass(frozen=True)
class IngestionResult:
    status: str
    records_received: int
    errors: list[str]


def default_connectors(settings: Settings) -> list[Connector]:
    return [
        NbkFxConnector(timeout=settings.request_timeout),
        NbkPolicyConnector(
            timeout=settings.request_timeout,
            manual_base_rate=settings.manual_base_rate,
            manual_tonia_rate=settings.manual_tonia_rate,
        ),
        BnsInflationConnector(timeout=settings.request_timeout),
        BrentConnector(),
    ]


def run_ingestion(
    repository: SupabaseRepository,
    settings: Settings,
    trigger_type: str = "manual",
    connectors: list[Connector] | None = None,
) -> IngestionResult:
    run_id = repository.start_run(trigger_type)
    errors: list[str] = []
    count = 0

    for connector in connectors or default_connectors(settings):
        try:
            observations = [validate_observation(item) for item in connector.fetch()]
            count += repository.upsert_observations(observations)
        except Exception as exc:
            errors.append(f"{connector.name}: {exc}")

    status = "success"
    if errors and count:
        status = "partial"
    elif errors:
        status = "failed"

    repository.finish_run(
        run_id=run_id,
        status=status,
        records_received=count,
        error_message="\n".join(errors) or None,
    )
    return IngestionResult(status=status, records_received=count, errors=errors)
