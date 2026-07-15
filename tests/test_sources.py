from datetime import date

from macro_radar.sources.bns import parse_inflation_release
from macro_radar.sources.nbk import parse_policy_rates, parse_usd_rate


def test_parse_usd_rate():
    xml = b"""<rates><item><title>EUR</title><description>560.0</description></item>
    <item><title>USD</title><description>468.88</description></item></rates>"""
    assert parse_usd_rate(xml) == 468.88


def test_parse_policy_rates():
    text = "Базовая ставка 17% TONIA 17,11%"
    assert parse_policy_rates(text) == (17.0, 17.11)


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
