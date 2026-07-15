from datetime import date

from macro_radar.config import Settings
from macro_radar.ingestion import run_ingestion
from macro_radar.models import Observation


class FakeConnector:
    name = "fake"

    def fetch(self):
        return [
            Observation(
                indicator_code="USD_KZT",
                period=date(2026, 7, 15),
                value=468.88,
                unit="KZT",
                source="test",
                source_url="",
                frequency="daily",
            )
        ]


class BrokenConnector:
    name = "broken"

    def fetch(self):
        raise RuntimeError("source unavailable")


class FakeRepository:
    def __init__(self):
        self.finished = None

    def start_run(self, trigger_type):
        return "run-1"

    def upsert_observations(self, observations):
        return len(list(observations))

    def finish_run(self, run_id, status, records_received, error_message=None):
        self.finished = (status, records_received, error_message)


def test_partial_run_keeps_successful_source():
    repository = FakeRepository()
    settings = Settings("url", "key")
    result = run_ingestion(
        repository,
        settings,
        connectors=[FakeConnector(), BrokenConnector()],
    )
    assert result.status == "partial"
    assert result.records_received == 1
    assert repository.finished[0] == "partial"
