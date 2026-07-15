from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable

from supabase import Client, create_client

from .models import Observation


class SupabaseRepository:
    def __init__(self, url: str, service_role_key: str):
        self.client: Client = create_client(url, service_role_key)

    def start_run(self, trigger_type: str) -> str:
        response = (
            self.client.table("ingestion_runs")
            .insert({"status": "running", "trigger_type": trigger_type})
            .execute()
        )
        return str(response.data[0]["id"])

    def finish_run(
        self,
        run_id: str,
        status: str,
        records_received: int,
        error_message: str | None = None,
    ) -> None:
        (
            self.client.table("ingestion_runs")
            .update(
                {
                    "status": status,
                    "records_received": records_received,
                    "error_message": error_message,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", run_id)
            .execute()
        )

    def upsert_observations(self, observations: Iterable[Observation]) -> int:
        records = [item.to_record() for item in observations]
        if not records:
            return 0
        (
            self.client.table("observations")
            .upsert(
                records,
                on_conflict="indicator_code,period,source,data_type",
            )
            .execute()
        )
        return len(records)

    def get_observations(
        self,
        indicator_codes: list[str] | None = None,
        since: date | None = None,
        limit: int = 10_000,
    ) -> list[dict[str, object]]:
        query = self.client.table("observations").select("*")
        if indicator_codes:
            query = query.in_("indicator_code", indicator_codes)
        if since:
            query = query.gte("period", since.isoformat())
        response = query.order("period").limit(limit).execute()
        return list(response.data)

    def get_recent_runs(self, limit: int = 10) -> list[dict[str, object]]:
        response = (
            self.client.table("ingestion_runs")
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data)
