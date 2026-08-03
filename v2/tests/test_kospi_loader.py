from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

import pandas as pd
import pytest

from v2.data.kospi_loader import KOSPI_COLUMNS, load_or_fetch_kospi_daily, update_kospi_benchmark


def _output_dir() -> Path:
    path = Path("v2/data/cache/test_kospi_loader") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cleanup(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _fake_kospi_fetcher(start: str, end: str, ticker: str) -> pd.DataFrame:
    assert start == "20200327"
    assert end == "20260417"
    assert ticker == "1001"
    return pd.DataFrame(
        {
            "날짜": pd.to_datetime(["2020-03-27", "2026-04-17"]),
            "시가": [1700.0, 3800.0],
            "고가": [1710.0, 3810.0],
            "저가": [1690.0, 3790.0],
            "종가": [1700.0, 3800.0],
            "거래량": [1000, 2000],
        }
    )


def test_load_or_fetch_kospi_daily_creates_file_and_schema() -> None:
    output_dir = _output_dir()
    try:
        cache_path = output_dir / "kospi_daily.parquet"

        data = load_or_fetch_kospi_daily(
            cache_path=cache_path,
            start="20200327",
            end="20260417",
            fetcher=_fake_kospi_fetcher,
        )

        assert cache_path.exists()
        assert list(data.columns) == KOSPI_COLUMNS
        assert data["date"].min() <= pd.Timestamp("2020-03-27")
        assert data["date"].max() >= pd.Timestamp("2026-04-17")
    finally:
        _cleanup(output_dir)


def test_update_kospi_benchmark_merges_cache_and_writes_backtest_schema() -> None:
    output_dir = _output_dir()
    try:
        cache_path = output_dir / "kospi_daily.parquet"
        benchmark_path = output_dir / "benchmarks" / "kospi_daily_returns.parquet"
        pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-07-17"]),
                "open": [3000.0],
                "high": [3010.0],
                "low": [2990.0],
                "close": [3000.0],
                "volume": [1000],
                "returns": [pd.NA],
            }
        ).to_parquet(cache_path, index=False)

        def fetcher(start: str, end: str, ticker: str) -> pd.DataFrame:
            assert start == "20260718"
            assert end == "20260720"
            assert ticker == "1001"
            return pd.DataFrame(
                {
                    "날짜": pd.to_datetime(["2026-07-20"]),
                    "시가": [3005.0],
                    "고가": [3040.0],
                    "저가": [3000.0],
                    "종가": [3030.0],
                    "거래량": [1200],
                }
            )

        data, benchmark = update_kospi_benchmark(
            cache_path=cache_path,
            benchmark_path=benchmark_path,
            expected_latest="2026-07-20",
            fetcher=fetcher,
        )

        assert data["date"].max() == pd.Timestamp("2026-07-20")
        assert benchmark_path.exists()
        assert list(benchmark.columns) == ["date", "close", "daily_return"]
        assert benchmark["date"].max() == pd.Timestamp("2026-07-20")
        assert round(float(benchmark.iloc[-1]["daily_return"]), 6) == 0.01
    finally:
        _cleanup(output_dir)


def test_update_kospi_benchmark_rejects_stale_fetch() -> None:
    output_dir = _output_dir()
    try:
        with pytest.raises(RuntimeError, match="KOSPI benchmark is stale"):
            update_kospi_benchmark(
                cache_path=output_dir / "kospi_daily.parquet",
                benchmark_path=output_dir / "benchmarks" / "kospi_daily_returns.parquet",
                expected_latest="2026-07-20",
                start="20260720",
                fetcher=lambda start, end, ticker: pd.DataFrame(),
            )
    finally:
        _cleanup(output_dir)


def test_load_or_fetch_kospi_daily_uses_existing_cache() -> None:
    output_dir = _output_dir()
    try:
        cache_path = output_dir / "kospi_daily.parquet"
        expected = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-03-27", "2026-04-17"]),
                "open": [1.0, 2.0],
                "high": [1.0, 2.0],
                "low": [1.0, 2.0],
                "close": [1.0, 2.0],
                "volume": [10, 20],
                "returns": [pd.NA, 1.0],
            }
        )
        expected.to_parquet(cache_path, index=False)

        data = load_or_fetch_kospi_daily(cache_path=cache_path, fetcher=_fake_kospi_fetcher)

        assert len(data) == 2
        assert float(data.iloc[-1]["close"]) == 2.0
    finally:
        _cleanup(output_dir)
