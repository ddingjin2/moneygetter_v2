from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from v2.data.us_market_dataset import US_CACHE_ROOT, US_OHLCV_PATH, normalize_universe_key, us_ohlcv_path, us_universe_path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class UsResearchPaths:
    universe_key: str
    cache_dir: Path
    report_dir: Path
    ohlcv_path: Path
    universe_path: Path
    price_dir: Path
    returns_path: Path
    status_path: Path
    buckets_path: Path
    benchmark_path: Path
    prepare_meta_path: Path
    signals_dir: Path
    signal_report_path: Path
    ic_dir: Path
    ic_full_path: Path
    ic_summary_path: Path
    ic_report_path: Path
    backtest_dir: Path
    metrics_path: Path
    verdicts_path: Path
    backtest_report_path: Path
    audit_report_path: Path
    audit_json_path: Path


def us_research_paths(universe_key: str | None = None) -> UsResearchPaths:
    key = normalize_universe_key(universe_key)
    cache_dir = US_CACHE_ROOT if key == "sp500" else US_CACHE_ROOT / key
    report_dir = ROOT / "reports/us" if key == "sp500" else ROOT / "reports/us" / key
    ohlcv = US_OHLCV_PATH if key == "sp500" else us_ohlcv_path(key)
    universe = us_universe_path(key)
    price_dir = cache_dir / "price_full"
    returns_path = cache_dir / "returns/forward_returns.parquet"
    status_path = price_dir / "_trading_status.parquet"
    buckets_path = price_dir / "_liquidity_buckets.parquet"
    benchmark_path = cache_dir / "benchmarks/us_benchmark_daily_returns.parquet"
    signals_dir = cache_dir / "signals_batch"
    ic_dir = cache_dir / "ic"
    backtest_dir = cache_dir / "backtest_batch"
    return UsResearchPaths(
        universe_key=key,
        cache_dir=cache_dir,
        report_dir=report_dir,
        ohlcv_path=ohlcv,
        universe_path=universe,
        price_dir=price_dir,
        returns_path=returns_path,
        status_path=status_path,
        buckets_path=buckets_path,
        benchmark_path=benchmark_path,
        prepare_meta_path=cache_dir / "prepare_meta.json",
        signals_dir=signals_dir,
        signal_report_path=report_dir / "us_signal_catalog.md",
        ic_dir=ic_dir,
        ic_full_path=ic_dir / "ic_batch_full.parquet",
        ic_summary_path=ic_dir / "ic_batch_summary.parquet",
        ic_report_path=report_dir / "us_ic_batch.md",
        backtest_dir=backtest_dir,
        metrics_path=backtest_dir / "all_metrics.parquet",
        verdicts_path=backtest_dir / "verdicts.parquet",
        backtest_report_path=report_dir / "us_backtest_batch.md",
        audit_report_path=report_dir / "us_research_audit.md",
        audit_json_path=cache_dir / "us_research_audit.json",
    )
