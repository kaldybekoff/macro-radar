from __future__ import annotations

from datetime import timedelta

import pandas as pd

from .models import INDICATORS


def prepare_frame(records: list[dict[str, object]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(records)
    frame["period"] = pd.to_datetime(frame["period"], errors="coerce")
    frame["fetched_at"] = pd.to_datetime(frame["fetched_at"], errors="coerce", utc=True)
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame["source_priority"] = (~frame["source"].astype(str).str.startswith("Legacy")).astype(int)
    return frame.dropna(subset=["period", "value"]).sort_values("period")


def canonical_series(frame: pd.DataFrame, code: str) -> pd.DataFrame:
    series = frame.loc[frame["indicator_code"] == code].copy()
    if series.empty:
        return series
    if "source_priority" not in series.columns:
        series["source_priority"] = (
            ~series["source"].astype(str).str.startswith("Legacy")
        ).astype(int)
    return (
        series.sort_values(["period", "source_priority", "fetched_at"])
        .groupby("period", as_index=False)
        .tail(1)
        .sort_values("period")
    )


def latest_per_indicator(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    return (
        pd.concat(
            [canonical_series(frame, code).tail(1) for code in frame["indicator_code"].unique()],
            ignore_index=True,
        )
        .set_index("indicator_code")
    )


def comparison(frame: pd.DataFrame, code: str, days: int) -> float | None:
    series = canonical_series(frame, code)
    if len(series) < 2:
        return None
    latest = series.iloc[-1]
    target = latest["period"] - timedelta(days=days)
    previous = series.loc[series["period"] <= target]
    if previous.empty:
        previous = series.iloc[:-1]
    if previous.empty:
        return None
    return round(float(latest["value"] - previous.iloc[-1]["value"]), 2)


def previous_change(frame: pd.DataFrame, code: str) -> float | None:
    series = canonical_series(frame, code)
    if len(series) < 2:
        return None
    return round(float(series.iloc[-1]["value"] - series.iloc[-2]["value"]), 2)


def signal_for_change(code: str, change: float | None) -> str:
    if change is None or change == 0:
        return "NEUTRAL"
    positive_when_up = INDICATORS.get(code, {}).get("positive_when_up", False)
    positive = change > 0 if positive_when_up else change < 0
    return "POSITIVE" if positive else "NEGATIVE"


def build_summary(frame: pd.DataFrame) -> list[str]:
    if frame.empty:
        return ["Нет данных для аналитического вывода."]
    latest = latest_per_indicator(frame)
    summary: list[str] = []

    for code in ("CPI_YOY", "USD_KZT", "BRENT_USD"):
        if code not in latest.index:
            continue
        value = float(latest.loc[code, "value"])
        change = previous_change(frame, code)
        label = INDICATORS[code]["label"]
        direction = "без изменения"
        if change is not None and change > 0:
            direction = f"вырос на {abs(change):.2f}"
        elif change is not None and change < 0:
            direction = f"снизился на {abs(change):.2f}"
        summary.append(f"{label}: {value:.2f}; {direction} к предыдущему наблюдению.")

    if "NBK_BASE_RATE" in latest.index and "CPI_YOY" in latest.index:
        real_rate = float(latest.loc["NBK_BASE_RATE", "value"]) - float(
            latest.loc["CPI_YOY", "value"]
        )
        summary.append(f"Условная реальная базовая ставка: {real_rate:.2f} п.п.")
    return summary


def freshness_status(frame: pd.DataFrame) -> dict[str, dict[str, object]]:
    if frame.empty:
        return {}
    latest = latest_per_indicator(frame)
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    result: dict[str, dict[str, object]] = {}
    for code, row in latest.iterrows():
        period = pd.Timestamp(row["period"]).tz_localize(None)
        age_days = max((today - period.normalize()).days, 0)
        frequency = str(row.get("frequency", "daily"))
        allowed = 45 if frequency == "monthly" else 5
        result[code] = {
            "age_days": age_days,
            "is_stale": age_days > allowed,
            "period": period.date(),
        }
    return result
