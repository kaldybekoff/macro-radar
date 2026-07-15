from datetime import date
from unittest.mock import Mock

import requests

from macro_radar.sources.bns import parse_inflation_release
from macro_radar.sources.nbk import NbkPolicyConnector, parse_policy_snapshot, parse_usd_rate


def test_parse_usd_rate():
    xml = b"""<rates><item><title>EUR</title><description>560.0</description></item>
    <item><title>USD</title><description>468.88</description></item></rates>"""
    assert parse_usd_rate(xml) == 468.88


def test_parse_policy_snapshot():
    payload = {
        "date": "2026-07-15",
        "baseRate": 17.0,
        "tonia": 16.79,
    }
    assert parse_policy_snapshot(payload) == (date(2026, 7, 15), 17.0, 16.79)


def test_policy_connector_prefers_api_over_manual_values(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "date": "2026-07-15",
        "baseRate": 17.0,
        "tonia": 16.79,
    }
    monkeypatch.setattr("macro_radar.sources.nbk.requests.get", lambda *a, **k: response)

    observations = NbkPolicyConnector(
        manual_base_rate=99.0,
        manual_tonia_rate=98.0,
    ).fetch()

    assert [item.value for item in observations] == [17.0, 16.79]
    assert all(item.period == date(2026, 7, 15) for item in observations)


def test_policy_connector_uses_manual_values_only_when_api_fails(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.ConnectionError("NBK unavailable")

    monkeypatch.setattr("macro_radar.sources.nbk.requests.get", fail)
    observations = NbkPolicyConnector(
        manual_base_rate=17.0,
        manual_tonia_rate=17.11,
    ).fetch()

    assert [item.value for item in observations] == [17.0, 17.11]


def test_parse_inflation_release():
    text = (
        "Инфляция в Республике Казахстан в мае 2026 года составила 10,4% "
        "(в апреле – 10,6%), за месяц – 0,7%. "
        "Цены на продовольственные товары за год выросли на 10,7%, "
        "непродовольственные товары выросли на 11,7%, "
        "платные услуги выросли на 8,7%."
    )
    period, values = parse_inflation_release(text)
    assert period == date(2026, 5, 1)
    assert values == {
        "CPI_YOY": 10.4,
        "CPI_MOM": 0.7,
        "CPI_FOOD_YOY": 10.7,
        "CPI_NON_FOOD_YOY": 11.7,
        "CPI_SERVICES_YOY": 8.7,
    }
