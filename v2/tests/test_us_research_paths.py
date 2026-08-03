from __future__ import annotations

from v2.data.us_research_paths import us_research_paths


def test_research_paths_keep_sp500_legacy_locations() -> None:
    paths = us_research_paths("sp500")

    assert paths.cache_dir.as_posix().endswith("data/cache/us")
    assert paths.report_dir.as_posix().endswith("reports/us")
    assert paths.ohlcv_path.as_posix().endswith("data/processed/us_market_ohlcv.parquet")
    assert paths.benchmark_path.as_posix().endswith("data/cache/us/benchmarks/us_benchmark_daily_returns.parquet")


def test_research_paths_isolate_secondary_universes() -> None:
    paths = us_research_paths("nasdaq100")

    assert paths.cache_dir.as_posix().endswith("data/cache/us/nasdaq100")
    assert paths.report_dir.as_posix().endswith("reports/us/nasdaq100")
    assert paths.ohlcv_path.as_posix().endswith("data/processed/us_nasdaq100_ohlcv.parquet")
    assert paths.benchmark_path.as_posix().endswith("data/cache/us/nasdaq100/benchmarks/us_benchmark_daily_returns.parquet")
