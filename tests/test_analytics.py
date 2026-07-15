from macro_radar.analytics import comparison, latest_per_indicator, prepare_frame, signal_for_change


def records():
    return [
        {
            "indicator_code": "USD_KZT",
            "period": "2026-07-01",
            "value": 470,
            "unit": "KZT",
            "source": "NBK",
            "frequency": "daily",
            "fetched_at": "2026-07-01T08:00:00+00:00",
        },
        {
            "indicator_code": "USD_KZT",
            "period": "2026-07-08",
            "value": 465,
            "unit": "KZT",
            "source": "NBK",
            "frequency": "daily",
            "fetched_at": "2026-07-08T08:00:00+00:00",
        },
    ]


def test_latest_and_comparison():
    frame = prepare_frame(records())
    latest = latest_per_indicator(frame)
    assert latest.loc["USD_KZT", "value"] == 465
    assert comparison(frame, "USD_KZT", 7) == -5


def test_tenge_strengthening_is_positive():
    assert signal_for_change("USD_KZT", -5) == "POSITIVE"


def test_live_source_wins_over_later_legacy_import():
    rows = records() + [
        {
            "indicator_code": "USD_KZT",
            "period": "2026-07-08",
            "value": 999,
            "unit": "KZT",
            "source": "Legacy snapshot",
            "frequency": "daily",
            "fetched_at": "2026-07-08T23:00:00+00:00",
        }
    ]
    latest = latest_per_indicator(prepare_frame(rows))
    assert latest.loc["USD_KZT", "value"] == 465
