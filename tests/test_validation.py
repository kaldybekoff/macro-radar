from datetime import date

import pytest

from macro_radar.models import Observation
from macro_radar.validation import DataValidationError, validate_observation


def observation(value: float) -> Observation:
    return Observation(
        indicator_code="USD_KZT",
        period=date(2026, 7, 15),
        value=value,
        unit="KZT",
        source="test",
        source_url="",
        frequency="daily",
    )


def test_accepts_reasonable_fx():
    assert validate_observation(observation(468.88)).value == 468.88


def test_rejects_impossible_fx():
    with pytest.raises(DataValidationError):
        validate_observation(observation(0))
