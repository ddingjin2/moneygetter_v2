from __future__ import annotations

import pandas as pd
import pytest

from v2.data.us_schema import normalize_us_ohlcv, normalize_us_universe


def test_normalize_us_universe_standardizes_symbols_and_dates() -> None:
    frame = pd.DataFrame(
        {
            "symbol": [" aapl ", "brk.b"],
            "name": ["Apple Inc.", "Berkshire Hathaway Inc."],
            "exchange": ["nasdaq", "nyse"],
            "security_type": ["common_stock", "common_stock"],
            "active_start_date": ["2020-01-01", "2020-01-02"],
            "active_end_date": [None, ""],
        }
    )

    out = normalize_us_universe(frame)

    assert out["symbol"].tolist() == ["AAPL", "BRK-B"]
    assert out["exchange"].tolist() == ["NASDAQ", "NYSE"]
    assert str(out["active_start_date"].min().date()) == "2020-01-01"
    assert out["active_end_date"].isna().all()


def test_normalize_us_ohlcv_marks_adjusted_open_quality_and_dollar_volume() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2024-01-02"],
            "symbol": ["aapl"],
            "open": [100],
            "high": [110],
            "low": [99],
            "close": [105],
            "adj_open": [98],
            "adj_close": [103],
            "volume": [1000],
        }
    )

    out = normalize_us_ohlcv(frame)

    assert out.loc[0, "symbol"] == "AAPL"
    assert float(out.loc[0, "dollar_volume"]) == 105000.0
    assert out.loc[0, "adjustment_quality"] == "adjusted_open_available"


def test_normalize_us_ohlcv_rejects_missing_required_columns() -> None:
    with pytest.raises(ValueError, match="missing required"):
        normalize_us_ohlcv(pd.DataFrame({"symbol": ["AAPL"]}))
