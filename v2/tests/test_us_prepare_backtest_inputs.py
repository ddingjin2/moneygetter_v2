from __future__ import annotations

import pandas as pd

from v2.scripts.us_prepare_backtest_inputs import build_benchmark_returns, build_forward_returns


def test_build_forward_returns_uses_adjusted_open() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAPL", "AAPL", "AAPL"],
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "adj_open": [100.0, 110.0, 121.0],
            "open": [10.0, 11.0, 12.0],
            "volume": [1000, 1000, 1000],
        }
    )

    out = build_forward_returns(frame, horizons=[1])

    assert round(float(out.loc[0, "forward_return_1d"]), 6) == 0.1
    assert bool(out.loc[0, "ret_valid_1d"]) is True
    assert bool(out.loc[2, "ret_valid_1d"]) is False


def test_build_benchmark_returns_aligns_to_forward_open_returns() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "adj_open": [100.0, 110.0, 121.0],
            "open": [10.0, 11.0, 12.0],
            "adj_close": [99.0, 111.0, 120.0],
            "close": [9.0, 11.0, 12.0],
        }
    )

    out = build_benchmark_returns(frame)

    assert round(float(out.loc[0, "daily_return"]), 6) == 0.1
    assert round(float(out.loc[1, "daily_return"]), 6) == 0.1
    assert pd.isna(out.loc[2, "daily_return"])
