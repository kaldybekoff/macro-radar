from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import requests
from bs4 import BeautifulSoup

from macro_radar.models import Observation


FX_URL = "https://nationalbank.kz/rss/get_rates.cfm?fdate={date}"
NBK_DATA_URL = "https://data.nationalbank.kz/"


def parse_usd_rate(xml: bytes) -> float:
    root = ET.fromstring(xml)
    for item in root.findall("item"):
        title = item.findtext("title", default="").strip()
        if title == "USD":
            value = item.findtext("description", default="").strip()
            return float(value.replace(",", "."))
    raise ValueError("USD rate not found in NBK response")


def parse_policy_rates(text: str) -> tuple[float, float]:
    normalized = " ".join(text.split()).replace(",", ".")
    base_match = re.search(
        r"Базовая\s+ставка\s*(?:[-–—:]\s*)?(\d+(?:\.\d+)?)\s*%",
        normalized,
        re.IGNORECASE,
    )
    tonia_match = re.search(
        r"TONIA\s*(?:[-–—:]\s*)?(\d+(?:\.\d+)?)\s*%",
        normalized,
        re.IGNORECASE,
    )
    if not base_match or not tonia_match:
        raise ValueError("Base rate or TONIA not found on NBK data page")
    return float(base_match.group(1)), float(tonia_match.group(1))


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
        base_rate = self.manual_base_rate
        tonia_rate = self.manual_tonia_rate
        if base_rate is None or tonia_rate is None:
            response = requests.get(NBK_DATA_URL, timeout=self.timeout)
            response.raise_for_status()
            page_text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
            parsed_base, parsed_tonia = parse_policy_rates(page_text)
            base_rate = base_rate if base_rate is not None else parsed_base
            tonia_rate = tonia_rate if tonia_rate is not None else parsed_tonia

        today = date.today()
        fetched_at = datetime.now(timezone.utc)
        common = {
            "period": today,
            "source": "NBK",
            "source_url": NBK_DATA_URL,
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
