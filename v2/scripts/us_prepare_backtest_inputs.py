from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.us_market_dataset import load_us_ohlcv  # noqa: E402
from v2.data.us_research_paths import us_research_paths  # noqa: E402

V2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = us_research_paths("sp500")
US_CACHE = DEFAULT_PATHS.cache_dir
PRICE_DIR = DEFAULT_PATHS.price_dir
RETURNS_PATH = DEFAULT_PATHS.returns_path
STATUS_PATH = PRICE_DIR / "_trading_status.parquet"
BUCKETS_PATH = PRICE_DIR / "_liquidity_buckets.parquet"
BENCHMARK_PATH = DEFAULT_PATHS.benchmark_path
META_PATH = DEFAULT_PATHS.prepare_meta_path


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def build_forward_returns(frame: pd.DataFrame, horizons: list[int] | None = None) -> pd.DataFrame:
    horizons = horizons or [1, 5, 20]
    data = frame.copy().sort_values(["symbol", "date"]).reset_index(drop=True)
    raw_open = pd.to_numeric(data["open"], errors="coerce")
    adj_open = pd.to_numeric(data.get("adj_open", pd.Series(pd.NA, index=data.index)), errors="coerce")
    data["price_for_return"] = adj_open.fillna(raw_open)
    out = data[["symbol", "date"]].copy()
    for horizon in horizons:
        future = data.groupby("symbol")["price_for_return"].shift(-horizon)
        current = data["price_for_return"]
        ret = future / current - 1.0
        valid = current.gt(0) & future.gt(0) & ret.notna()
        out[f"forward_return_{horizon}d"] = ret.where(valid)
        out[f"ret_valid_{horizon}d"] = valid.astype(bool)
    return out


def build_benchmark_returns(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy().sort_values("date").reset_index(drop=True)
    raw_open = pd.to_numeric(data["open"], errors="coerce")
    adj_open = pd.to_numeric(data.get("adj_open", pd.Series(pd.NA, index=data.index)), errors="coerce")
    open_price = adj_open.fillna(raw_open)
    raw_close = pd.to_numeric(data["close"], errors="coerce")
    adj_close = pd.to_numeric(data.get("adj_close", pd.Series(pd.NA, index=data.index)), errors="coerce")
    out = data[["date"]].copy()
    out["close"] = adj_close.fillna(raw_close)
    future = open_price.shift(-1)
    ret = future / open_price - 1.0
    out["daily_return"] = ret.where(open_price.gt(0) & future.gt(0))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare US backtest input caches.")
    parser.add_argument("--benchmark-symbol", default="SPY")
    parser.add_argument("--universe-key", default="sp500")
    args = parser.parse_args()
    paths = us_research_paths(args.universe_key)
    ohlcv = load_us_ohlcv(universe_key=args.universe_key)
    ohlcv["date"] = pd.to_datetime(ohlcv["date"]).dt.normalize()
    for symbol, frame in ohlcv.groupby("symbol", sort=True):
        atomic_write_parquet(frame.sort_values("date"), paths.price_dir / f"{symbol}.parquet")
    returns = build_forward_returns(ohlcv)
    atomic_write_parquet(returns, paths.returns_path)
    status = ohlcv[["symbol", "date", "open", "adj_open", "close", "adj_close", "volume", "dollar_volume", "adjustment_quality"]].copy()
    status["trading_halt"] = pd.to_numeric(status["volume"], errors="coerce").fillna(0).eq(0)
    atomic_write_parquet(status, paths.status_path)
    buckets = (
        ohlcv.assign(dollar_volume=pd.to_numeric(ohlcv["dollar_volume"], errors="coerce"))
        .groupby("symbol", as_index=False)
        .agg(avg_dollar_volume=("dollar_volume", "mean"), nonhalt_days=("volume", lambda s: int(pd.to_numeric(s, errors="coerce").gt(0).sum())))
        .sort_values("avg_dollar_volume", ascending=False)
        .reset_index(drop=True)
    )
    buckets["liquidity_rank"] = range(1, len(buckets) + 1)
    if len(buckets) >= 3:
        buckets["liquidity_bucket"] = pd.qcut(buckets["liquidity_rank"], q=[0, 1 / 3, 2 / 3, 1], labels=["large_liquid", "mid", "small_illiquid"]).astype(str)
    else:
        buckets["liquidity_bucket"] = "all"
    atomic_write_parquet(buckets, paths.buckets_path)
    benchmark_symbol = args.benchmark_symbol.upper()
    benchmark = ohlcv.loc[ohlcv["symbol"].eq(benchmark_symbol)].sort_values("date")
    if not benchmark.empty:
        atomic_write_parquet(build_benchmark_returns(benchmark), paths.benchmark_path)
    meta = {
        "universe_key": paths.universe_key,
        "symbols": int(ohlcv["symbol"].nunique()),
        "rows": int(len(ohlcv)),
        "max_date": str(ohlcv["date"].max().date()),
        "benchmark_symbol": benchmark_symbol,
        "benchmark_rows": int(len(benchmark)),
        "data_warning": "survivorship_biased_current_universe",
    }
    atomic_write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", paths.prepare_meta_path)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
