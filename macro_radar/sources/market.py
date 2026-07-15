from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from macro_radar.models import Observation


class BrentConnector:
    name = "Yahoo Finance"

    def fetch(self) -> list[Observation]:
        history = yf.Ticker("BZ=F").history(period="10d")
        if history.empty:
            raise ValueError("No Brent data received")
        series = history["Close"].dropna()
        if series.empty:
            raise ValueError("Brent history contains no closing prices")
        timestamp = pd.Timestamp(series.index[-1])
        return [
            Observation(
                indicator_code="BRENT_USD",
                period=timestamp.date(),
                value=round(float(series.iloc[-1]), 2),
                unit="USD/bbl",
                source="Yahoo Finance",
                source_url="https://finance.yahoo.com/quote/BZ=F/",
                frequency="daily",
                fetched_at=datetime.now(timezone.utc),
            )
        ]
