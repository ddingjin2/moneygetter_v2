from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

import pandas as pd

from v2.data.kospi_loader import KOSPI_COLUMNS, load_or_fetch_kospi_daily


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
