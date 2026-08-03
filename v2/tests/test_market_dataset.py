from __future__ import annotations

from pathlib import Path

import pandas as pd

from v2.data.market_dataset import load_ohlcv, merge_ohlcv, save_ohlcv
from v2.data.ohlcv_cleaner import clean_ohlcv


def test_market_dataset_loads_v2_parquet_and_adds_symbol_alias(tmp_path: Path) -> None:
    path = tmp_path / "market_ohlcv.parquet"
    pd.DataFrame(
        {
            "date": ["2026-04-17"],
            "ticker": ["20"],
            "open": [1],
            "high": [2],
            "low": [1],
            "close": [2],
            "volume": [10],
        }
    ).to_parquet(path, index=False)

    frame = load_ohlcv(path)

    assert frame.loc[0, "symbol"] == "000020"
    assert frame.loc[0, "ticker"] == "000020"
    assert frame.loc[0, "date"] == pd.Timestamp("2026-04-17")


def test_market_dataset_merge_deduplicates_latest_row() -> None:
    old = pd.DataFrame(
        {
            "date": ["2026-04-17"],
            "symbol": ["000020"],
            "open": [1],
            "high": [2],
            "low": [1],
            "close": [2],
            "volume": [10],
        }
    )
    new = old.assign(close=[3])

    merged = merge_ohlcv(old, new)

    assert len(merged) == 1
    assert float(merged.loc[0, "close"]) == 3.0


def test_save_ohlcv_writes_normalized_parquet(tmp_path: Path) -> None:
    path = tmp_path / "market_ohlcv.parquet"
    save_ohlcv(
        pd.DataFrame(
            {
                "date": ["2026-04-17"],
                "symbol": ["000020"],
                "open": [1],
                "high": [2],
                "low": [1],
                "close": [2],
                "volume": [10],
            }
        ),
        path,
    )

    assert path.exists()
    assert len(load_ohlcv(path)) == 1


def test_clean_ohlcv_normalizes_pykrx_columns_and_halted_prices() -> None:
    raw = pd.DataFrame(
        {
            "날짜": ["2026-04-17"],
            "시가": [0],
            "고가": [0],
            "저가": [0],
            "종가": [1000],
            "거래량": [0],
            "거래대금": [0],
            "시가총액": [1000000],
            "상장주식수": [1000],
        }
    )

    cleaned = clean_ohlcv(raw, ticker="20", market="KOSPI", name="동화약품")

    assert cleaned.loc[0, "symbol"] == "000020"
    assert cleaned.loc[0, "market"] == "KOSPI"
    assert float(cleaned.loc[0, "open"]) == 1000.0
    assert float(cleaned.loc[0, "high"]) == 1000.0
    assert float(cleaned.loc[0, "low"]) == 1000.0
    assert float(cleaned.loc[0, "trading_value"]) == 0.0
