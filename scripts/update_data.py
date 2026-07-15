from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from macro_radar.config import load_settings
from macro_radar.ingestion import run_ingestion
from macro_radar.repository import SupabaseRepository


def main() -> int:
    settings = load_settings()
    if not settings.supabase_configured:
        print("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        return 2
    repository = SupabaseRepository(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
    result = run_ingestion(repository, settings, trigger_type="schedule")
    print(
        f"status={result.status} records={result.records_received} "
        f"errors={len(result.errors)}"
    )
    for error in result.errors:
        print(error)
    return 0 if result.status in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
