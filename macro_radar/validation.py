from __future__ import annotations

from .models import Observation


RANGES = {
    "USD_KZT": (100.0, 1_500.0),
    "CPI_YOY": (-10.0, 100.0),
    "CPI_MOM": (-20.0, 30.0),
    "CPI_FOOD_YOY": (-20.0, 150.0),
    "CPI_NON_FOOD_YOY": (-20.0, 150.0),
    "CPI_SERVICES_YOY": (-20.0, 150.0),
    "BRENT_USD": (5.0, 300.0),
    "NBK_BASE_RATE": (0.0, 50.0),
    "TONIA": (0.0, 100.0),
}


class DataValidationError(ValueError):
    pass


def validate_observation(observation: Observation) -> Observation:
    if observation.indicator_code not in RANGES:
        raise DataValidationError(
            f"Unknown indicator: {observation.indicator_code}"
        )
    lower, upper = RANGES[observation.indicator_code]
    if not lower <= float(observation.value) <= upper:
        raise DataValidationError(
            f"{observation.indicator_code}={observation.value} is outside "
            f"the allowed range [{lower}, {upper}]"
        )
    return observation
