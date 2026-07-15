from __future__ import annotations

import re
from datetime import date, datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from macro_radar.models import Observation


BNS_PRICES_PAGE = "https://stat.gov.kz/ru/industries/economy/prices/"
MONTHS = {
    "январе": 1,
    "феврале": 2,
    "марте": 3,
    "апреле": 4,
    "мае": 5,
    "июне": 6,
    "июле": 7,
    "августе": 8,
    "сентябре": 9,
    "октябре": 10,
    "ноябре": 11,
    "декабре": 12,
}


def _number(value: str) -> float:
    return float(value.replace(",", ".").replace("%", "").strip())


def parse_inflation_release(text: str) -> tuple[date, dict[str, float]]:
    normalized = " ".join(text.split()).replace("¬", "")
    period_match = re.search(
        r"в\s+(январе|феврале|марте|апреле|мае|июне|июле|августе|"
        r"сентябре|октябре|ноябре|декабре)\s+(20\d{2})\s+года",
        normalized,
        re.IGNORECASE,
    )
    annual = re.search(
        r"инфляци[яи].{0,80}?составил[а]?\s+(\d+(?:[,.]\d+)?)\s*%",
        normalized,
        re.IGNORECASE,
    )
    monthly = re.search(
        r"за\s+месяц\s*[–—-]?\s*(\d+(?:[,.]\d+)?)\s*%",
        normalized,
        re.IGNORECASE,
    )
    food = re.search(
        r"продовольственн(?:ые|ых)\s+товар(?:ы|ов).{0,45}?"
        r"(?:выросли|повысились|на)\s*(?:на\s*)?(\d+(?:[,.]\d+)?)\s*%",
        normalized,
        re.IGNORECASE,
    )
    non_food = re.search(
        r"непродовольственн(?:ые|ых)\s+товар(?:ы|ов).{0,45}?"
        r"(?:выросли|повысились|на)\s*(?:на\s*)?(\d+(?:[,.]\d+)?)\s*%",
        normalized,
        re.IGNORECASE,
    )
    services = re.search(
        r"(?:платн(?:ые|ых)\s+услуг(?:и|)|услуг(?:и|)).{0,45}?"
        r"(?:выросли|повысились|на)\s*(?:на\s*)?(\d+(?:[,.]\d+)?)\s*%",
        normalized,
        re.IGNORECASE,
    )

    if not period_match or not annual:
        raise ValueError("Release period or annual inflation not found")

    period = date(int(period_match.group(2)), MONTHS[period_match.group(1).lower()], 1)
    values = {"CPI_YOY": _number(annual.group(1))}
    optional = {
        "CPI_MOM": monthly,
        "CPI_FOOD_YOY": food,
        "CPI_NON_FOOD_YOY": non_food,
        "CPI_SERVICES_YOY": services,
    }
    for code, match in optional.items():
        if match:
            values[code] = _number(match.group(1))
    return period, values


class BnsInflationConnector:
    name = "BNS"

    def __init__(self, timeout: int = 25):
        self.timeout = timeout

    def _latest_release_url(self) -> str:
        response = requests.get(BNS_PRICES_PAGE, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        candidates: list[str] = []
        for link in soup.find_all("a", href=True):
            title = link.get_text(" ", strip=True).lower()
            if "инфляция в республике казахстан" in title:
                candidates.append(urljoin(BNS_PRICES_PAGE, link["href"]))
        if not candidates:
            raise ValueError("Latest BNS inflation release link not found")
        publication_links = [url for url in candidates if "/publications/" in url]
        return (publication_links or candidates)[0]

    def fetch(self) -> list[Observation]:
        release_url = self._latest_release_url()
        response = requests.get(release_url, timeout=self.timeout)
        response.raise_for_status()
        text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
        period, values = parse_inflation_release(text)
        fetched_at = datetime.now(timezone.utc)
        units = {code: "%" for code in values}
        return [
            Observation(
                indicator_code=code,
                period=period,
                value=value,
                unit=units[code],
                source="BNS",
                source_url=release_url,
                frequency="monthly",
                fetched_at=fetched_at,
            )
            for code, value in values.items()
        ]
