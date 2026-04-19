from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from v2.signals.proximity import compute_daily_proximity, compute_proximity


def _frame(symbol: str, rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [row[0] for row in rows],
            "symbol": [symbol] * len(rows),
            "high": [row[1] for row in rows],
            "close": [row[2] for row in rows],
        }
    )


def test_compute_proximity_simple_case_below_high() -> None:
    ohlcv = _frame("000001", [("2024-01-01", 100, 90), ("2024-01-02", 100, 95), ("2024-01-03", 98, 95)])

    result = compute_proximity(ohlcv, pd.Timestamp("2024-01-03"), lookback_days=3)

    assert math.isclose(float(result.iloc[0]["proximity"]), 0.95)
    assert float(result.iloc[0]["past_high_value"]) == 100.0


def test_compute_proximity_is_one_at_current_high() -> None:
    ohlcv = _frame("000001", [("2024-01-01", 90, 90), ("2024-01-02", 95, 95), ("2024-01-03", 100, 100)])

    result = compute_proximity(ohlcv, pd.Timestamp("2024-01-03"), lookback_days=3)

    assert math.isclose(float(result.iloc[0]["proximity"]), 1.0)
    assert result.iloc[0]["past_high_date"] == pd.Timestamp("2024-01-03")


def test_compute_proximity_ignores_future_high() -> None:
    ohlcv = _frame(
        "000001",
        [
            ("2024-05-30", 100, 90),
            ("2024-05-31", 100, 95),
            ("2024-06-01", 100, 95),
            ("2024-06-02", 200, 100),
        ],
    )

    result = compute_proximity(ohlcv, pd.Timestamp("2024-06-01"), lookback_days=3)

    assert math.isclose(float(result.iloc[0]["proximity"]), 0.95)
    assert float(result.iloc[0]["past_high_value"]) == 100.0


def test_compute_proximity_requires_full_lookback() -> None:
    ohlcv = _frame("000001", [("2024-01-01", 100, 90), ("2024-01-02", 100, 95)])

    result = compute_proximity(ohlcv, pd.Timestamp("2024-01-02"), lookback_days=3)

    assert math.isnan(float(result.iloc[0]["proximity"]))


def test_compute_proximity_flat_prices_equal_one() -> None:
    ohlcv = _frame("000001", [("2024-01-01", 100, 100), ("2024-01-02", 100, 100), ("2024-01-03", 100, 100)])

    result = compute_proximity(ohlcv, pd.Timestamp("2024-01-03"), lookback_days=3)

    assert math.isclose(float(result.iloc[0]["proximity"]), 1.0)


def test_daily_proximity_matches_manual_rolling_high() -> None:
    ohlcv = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-01", "2024-01-02", "2024-01-03"],
            "symbol": ["000001", "000001", "000001", "000002", "000002", "000002"],
            "high": [100, 110, 105, 200, 190, 180],
            "close": [90, 100, 99, 180, 180, 180],
        }
    )

    result = compute_daily_proximity(ohlcv, lookback_days=2)
    value = result.loc[result["symbol"].eq("000001") & result["as_of_date"].eq(pd.Timestamp("2024-01-03")), "proximity"].iloc[0]

    assert math.isclose(float(value), 99 / 110)


def test_samsung_sample_matches_manual_52_week_high() -> None:
    path = Path("C:/dev/moneygetter/data/processed/market_ohlcv.parquet")
    if not path.exists():
        raise AssertionError(f"missing local OHLCV fixture: {path}")

    ohlcv = pd.read_parquet(path, columns=["date", "symbol", "high", "close"])
    samsung = ohlcv.loc[ohlcv["symbol"].astype(str).str.zfill(6).eq("005930")].copy()
    samsung["date"] = pd.to_datetime(samsung["date"]).dt.normalize()
    samsung = samsung.sort_values("date").reset_index(drop=True)
    sample_dates = samsung.loc[[300, 420, 540, 660, 780], "date"]

    for as_of_date in sample_dates:
        result = compute_proximity(samsung, as_of_date, lookback_days=252)
        history = samsung.loc[samsung["date"].le(as_of_date)].tail(252)
        expected = float(history.iloc[-1]["close"]) / float(history["high"].max())
        actual = float(result.iloc[0]["proximity"])
        assert math.isclose(actual, expected)
