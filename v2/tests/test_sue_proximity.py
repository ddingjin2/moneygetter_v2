from __future__ import annotations

import math

import pandas as pd

from v2.signals.sue_proximity import generate_signals


def _earnings(sue_values: list[float | None] | None = None) -> pd.DataFrame:
    symbols = [f"00000{i}" for i in range(1, 6)]
    data = {
        "stock_code": symbols,
        "tradable_entry_date": ["2024-01-04"] * 5,
    }
    if sue_values is not None:
        data["sue"] = sue_values
    return pd.DataFrame(data)


def _ohlcv(prior_closes: list[float], prior_highs: list[float] | None = None) -> pd.DataFrame:
    symbols = [f"00000{i}" for i in range(1, 6)]
    highs = prior_highs or [1000] * len(symbols)
    rows = []
    for index, symbol in enumerate(symbols):
        close = prior_closes[index]
        high = highs[index]
        rows.extend(
            [
                {"date": "2024-01-01", "symbol": symbol, "open": 1000, "high": 1000, "close": 900, "market_cap": 1},
                {"date": "2024-01-02", "symbol": symbol, "open": 1000, "high": 1000, "close": 900, "market_cap": 1},
                {"date": "2024-01-03", "symbol": symbol, "open": 1000, "high": high, "close": close, "market_cap": 1},
                {"date": "2024-01-04", "symbol": symbol, "open": 1000, "high": 1010, "close": 1005, "market_cap": 1},
            ]
        )
    return pd.DataFrame(rows)


def test_sue_near_high_keeps_top_quintile_candidate() -> None:
    signals = generate_signals(
        _earnings([5.0, 4.0, 3.0, 2.0, 1.0]),
        _ohlcv([960, 500, 500, 500, 500]),
        lambda frame: frame,
        proximity_threshold=0.95,
        lookback_days=2,
    )

    assert list(signals["symbol"]) == ["000001"]
    assert math.isclose(float(signals.iloc[0]["sue_score"]), 5.0)
    assert math.isclose(float(signals.iloc[0]["proximity"]), 0.96)
    assert signals.iloc[0]["proximity_as_of_date"] == pd.Timestamp("2024-01-03")


def test_sue_filter_runs_before_proximity_filter() -> None:
    signals = generate_signals(
        _earnings([5.0, 4.0, 3.0, 2.0, 1.0]),
        _ohlcv([1100, 990, 990, 990, 990], [2200, 1000, 1000, 1000, 1000]),
        lambda frame: frame,
        proximity_threshold=0.95,
        lookback_days=2,
    )

    assert signals.empty


def test_far_from_high_variant_keeps_low_proximity_top_sue() -> None:
    signals = generate_signals(
        _earnings([5.0, 4.0, 3.0, 2.0, 1.0]),
        _ohlcv([1100, 990, 990, 990, 990], [2000, 1000, 1000, 1000, 1000]),
        lambda frame: frame,
        proximity_threshold=0.60,
        proximity_direction="far",
        lookback_days=2,
    )

    assert list(signals["symbol"]) == ["000001"]
    assert math.isclose(float(signals.iloc[0]["proximity"]), 0.55)


def test_proximity_only_does_not_require_sue_values() -> None:
    signals = generate_signals(
        _earnings(None),
        _ohlcv([960, 990, 970, 500, 500]),
        lambda frame: frame,
        proximity_threshold=0.95,
        sue_top_quintile=False,
        lookback_days=2,
    )

    assert list(signals["symbol"]) == ["000002", "000003", "000001"]
    assert list(signals["signal_score"]) == sorted(signals["signal_score"], reverse=True)


def test_invalid_proximity_direction_raises() -> None:
    try:
        generate_signals(
            _earnings([5.0, 4.0, 3.0, 2.0, 1.0]),
            _ohlcv([960, 990, 970, 500, 500]),
            lambda frame: frame,
            proximity_direction="middle",
            lookback_days=2,
        )
    except ValueError as exc:
        assert "proximity_direction" in str(exc)
    else:
        raise AssertionError("expected ValueError")
