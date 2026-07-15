from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from macro_radar.config import load_settings
from macro_radar.models import Observation
from macro_radar.repository import SupabaseRepository
from macro_radar.validation import validate_observation


HISTORY = ROOT / "storage" / "macro_history.csv"
DATABASE = ROOT / "storage" / "macro_database.xlsx"


def from_history() -> list[Observation]:
    if not HISTORY.exists():
        return []
    frame = pd.read_csv(HISTORY)
    mappings = {
        "fx_usd_kzt": ("USD_KZT", "KZT", "daily"),
        "cpi": ("CPI_YOY", "%", "monthly"),
        "base_rate": ("NBK_BASE_RATE", "%", "daily"),
        "repo_rate": ("TONIA", "%", "daily"),
        "oil": ("BRENT_USD", "USD/bbl", "daily"),
    }
    output: list[Observation] = []
    for _, row in frame.iterrows():
        timestamp = pd.to_datetime(row["date"], errors="coerce")
        if pd.isna(timestamp):
            continue
        for column, (code, unit, frequency) in mappings.items():
            if column not in row or pd.isna(row[column]):
                continue
            observation = Observation(
                indicator_code=code,
                period=timestamp.date(),
                value=float(row[column]),
                unit=unit,
                source="Legacy snapshot",
                source_url="",
                frequency=frequency,
                fetched_at=timestamp.to_pydatetime().replace(tzinfo=timezone.utc),
                quality_status="warning",
            )
            output.append(validate_observation(observation))
    return output


def from_excel() -> list[Observation]:
    if not DATABASE.exists():
        return []
    output: list[Observation] = []
    specs = {
        "FX": {"fx_usd_kzt": ("USD_KZT", "KZT", "daily")},
        "Inflation": {
            "annual_inflation": ("CPI_YOY", "%", "monthly"),
            "monthly_inflation": ("CPI_MOM", "%", "monthly"),
            "food": ("CPI_FOOD_YOY", "%", "monthly"),
            "non_food": ("CPI_NON_FOOD_YOY", "%", "monthly"),
            "services": ("CPI_SERVICES_YOY", "%", "monthly"),
        },
        "Oil_Daily": {"brent": ("BRENT_USD", "USD/bbl", "daily")},
    }
    fetched_at = datetime.now(timezone.utc)
    for sheet, columns in specs.items():
        try:
            frame = pd.read_excel(DATABASE, sheet_name=sheet)
        except ValueError:
            continue
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce", dayfirst=True)
        for _, row in frame.dropna(subset=["date"]).iterrows():
            for column, (code, unit, frequency) in columns.items():
                if column not in row or pd.isna(row[column]):
                    continue
                try:
                    output.append(
                        validate_observation(
                            Observation(
                                indicator_code=code,
                                period=row["date"].date(),
                                value=float(row[column]),
                                unit=unit,
                                source="Legacy Excel",
                                source_url="",
                                frequency=frequency,
                                fetched_at=fetched_at,
                                quality_status="warning",
                            )
                        )
                    )
                except (TypeError, ValueError):
                    continue
    return output


def main() -> int:
    settings = load_settings()
    if not settings.supabase_configured:
        print("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        return 2
    repository = SupabaseRepository(settings.supabase_url, settings.supabase_service_role_key)
    run_id = repository.start_run("migration")
    try:
        observations = from_excel() + from_history()
        # Prefer the latest fetched copy of an identical legacy observation.
        deduplicated: dict[tuple[str, object, str], Observation] = {}
        for item in observations:
            key = (item.indicator_code, item.period, item.data_type)
            current = deduplicated.get(key)
            if current is None or (item.fetched_at or datetime.min.replace(tzinfo=timezone.utc)) > (
                current.fetched_at or datetime.min.replace(tzinfo=timezone.utc)
            ):
                deduplicated[key] = item
        observations = list(deduplicated.values())
        count = repository.upsert_observations(observations)
        repository.finish_run(run_id, "success", count)
        print(f"Migrated {count} observations")
        return 0
    except Exception as exc:
        repository.finish_run(run_id, "failed", 0, str(exc))
        raise


if __name__ == "__main__":
    raise SystemExit(main())
