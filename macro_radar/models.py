from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone


@dataclass(frozen=True)
class Observation:
    indicator_code: str
    period: date
    value: float
    unit: str
    source: str
    source_url: str
    frequency: str
    data_type: str = "fact"
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    quality_status: str = "valid"

    def to_record(self) -> dict[str, object]:
        record = asdict(self)
        record["period"] = self.period.isoformat()
        record["published_at"] = (
            self.published_at.isoformat() if self.published_at else None
        )
        record["fetched_at"] = (
            self.fetched_at or datetime.now(timezone.utc)
        ).isoformat()
        return record


INDICATORS = {
    "USD_KZT": {"label": "USD/KZT", "unit": "KZT", "positive_when_up": False},
    "CPI_YOY": {"label": "Инфляция г/г", "unit": "%", "positive_when_up": False},
    "CPI_MOM": {"label": "Инфляция м/м", "unit": "%", "positive_when_up": False},
    "CPI_FOOD_YOY": {"label": "Продовольствие г/г", "unit": "%", "positive_when_up": False},
    "CPI_NON_FOOD_YOY": {"label": "Непродовольствие г/г", "unit": "%", "positive_when_up": False},
    "CPI_SERVICES_YOY": {"label": "Услуги г/г", "unit": "%", "positive_when_up": False},
    "BRENT_USD": {"label": "Brent", "unit": "USD/bbl", "positive_when_up": True},
    "NBK_BASE_RATE": {"label": "Базовая ставка", "unit": "%", "positive_when_up": False},
    "TONIA": {"label": "TONIA", "unit": "%", "positive_when_up": False},
}
