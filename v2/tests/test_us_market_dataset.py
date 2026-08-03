from __future__ import annotations

import pandas as pd

from v2.data.us_market_dataset import US_OHLCV_PATH, US_UNIVERSE_PATH, merge_us_ohlcv, us_ohlcv_path, us_universe_path
from v2.data.us_providers import CsvLocalUsProvider, provider_from_config


def test_csv_local_provider_loads_universe_and_daily_bars(tmp_path) -> None:
    universe_csv = tmp_path / "universe.csv"
    bars_dir = tmp_path / "bars"
    bars_dir.mkdir()
    universe_csv.write_text(
        "symbol,name,exchange,security_type,active_start_date\nAAPL,Apple Inc.,NASDAQ,common_stock,2020-01-01\n",
        encoding="utf-8",
    )
    (bars_dir / "AAPL.csv").write_text(
        "date,symbol,open,high,low,close,adj_open,adj_close,volume\n2024-01-02,AAPL,100,101,99,100,98,98,1000\n",
        encoding="utf-8",
    )

    provider = CsvLocalUsProvider(raw_universe_csv=universe_csv, raw_ohlcv_dir=bars_dir)

    universe = provider.fetch_universe()
    bars = provider.fetch_daily_bars(["AAPL"], "2024-01-01", "2024-01-31")

    assert universe["symbol"].tolist() == ["AAPL"]
    assert bars.loc[0, "symbol"] == "AAPL"
    assert pd.Timestamp(bars.loc[0, "date"]).date().isoformat() == "2024-01-02"


def test_merge_us_ohlcv_keeps_latest_duplicate() -> None:
    old = pd.DataFrame(
        {
            "date": ["2024-01-02"],
            "symbol": ["AAPL"],
            "open": [100],
            "high": [101],
            "low": [99],
            "close": [100],
            "adj_open": [98],
            "adj_close": [98],
            "volume": [1000],
            "source": ["old"],
        }
    )
    new = old.copy()
    new["close"] = [101]
    new["source"] = ["new"]

    merged = merge_us_ohlcv(old, new)

    assert len(merged) == 1
    assert float(merged.loc[0, "close"]) == 101.0
    assert merged.loc[0, "source"] == "new"


def test_universe_key_uses_isolated_us_cache_paths() -> None:
    assert us_universe_path("sp500") == US_UNIVERSE_PATH
    assert us_ohlcv_path("sp500") == US_OHLCV_PATH

    assert us_universe_path("nasdaq100").as_posix().endswith("data/cache/us/nasdaq100/universe/us_universe.parquet")
    assert us_ohlcv_path("nasdaq100").as_posix().endswith("data/processed/us_nasdaq100_ohlcv.parquet")


def test_provider_from_config_supports_nasdaq100_yfinance() -> None:
    provider = provider_from_config(
        {
            "provider": "yfinance_nasdaq100",
            "provider_settings": {"batch_size": 7, "pause_seconds": 0},
        }
    )

    assert provider.batch_size == 7
    assert provider.pause_seconds == 0
