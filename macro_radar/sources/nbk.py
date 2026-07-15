from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import requests

from macro_radar.models import Observation


FX_URL = "https://nationalbank.kz/rss/get_rates.cfm?fdate={date}"
NBK_DATA_URL = "https://data.nationalbank.kz/"
NBK_INDICATORS_URL = "https://data.nationalbank.kz/api/indicators/latest"


def parse_usd_rate(xml: bytes) -> float:
    root = ET.fromstring(xml)
    for item in root.findall("item"):
        title = item.findtext("title", default="").strip()
        if title == "USD":
            value = item.findtext("description", default="").strip()
            return float(value.replace(",", "."))
    raise ValueError("USD rate not found in NBK response")


def parse_policy_snapshot(payload: dict[str, object]) -> tuple[date, float, float]:
    """Parse the public NBK latest-indicators API response."""
    try:
        period = date.fromisoformat(str(payload["date"]))
        base_rate = float(payload["baseRate"])
        tonia_rate = float(payload["tonia"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid NBK indicators response") from exc
    return period, base_rate, tonia_rate


class NbkFxConnector:
    name = "NBK FX"

    def __init__(self, timeout: int = 25):
        self.timeout = timeout

    def fetch(self) -> list[Observation]:
        today = date.today()
        fetched_at = datetime.now(timezone.utc)
        fx_response = requests.get(
            FX_URL.format(date=today.strftime("%d.%m.%Y")),
            timeout=self.timeout,
        )
        fx_response.raise_for_status()
        usd_kzt = parse_usd_rate(fx_response.content)
        return [
            Observation(
                indicator_code="USD_KZT",
                period=today,
                value=usd_kzt,
                unit="KZT",
                source="NBK",
                source_url=FX_URL.format(date=today.strftime("%d.%m.%Y")),
                frequency="daily",
                fetched_at=fetched_at,
            ),
        ]


class NbkPolicyConnector:
    name = "NBK policy rates"

    def __init__(
        self,
        timeout: int = 25,
        manual_base_rate: float | None = None,
        manual_tonia_rate: float | None = None,
    ):
        self.timeout = timeout
        self.manual_base_rate = manual_base_rate
        self.manual_tonia_rate = manual_tonia_rate

    def fetch(self) -> list[Observation]:
        # Official API is always primary. Manual settings are only used when
        # the API is temporarily unavailable or returns an invalid payload.
        try:
            response = requests.get(NBK_INDICATORS_URL, timeout=self.timeout)
            response.raise_for_status()
            period, base_rate, tonia_rate = parse_policy_snapshot(response.json())
            source_url = NBK_INDICATORS_URL
        except (requests.RequestException, ValueError, TypeError):
            if self.manual_base_rate is None or self.manual_tonia_rate is None:
                raise
            period = date.today()
            base_rate = self.manual_base_rate
            tonia_rate = self.manual_tonia_rate
            source_url = NBK_DATA_URL

        fetched_at = datetime.now(timezone.utc)
        common = {
            "period": period,
            "source": "NBK",
            "source_url": source_url,
            "frequency": "daily",
            "fetched_at": fetched_at,
        }
        return [
            Observation(
                indicator_code="NBK_BASE_RATE",
                value=float(base_rate),
                unit="%",
                **common,
            ),
            Observation(
                indicator_code="TONIA",
                value=float(tonia_rate),
                unit="%",
                **common,
            ),
        ]
