from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.us_research_paths import us_research_paths  # noqa: E402

V2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = us_research_paths("sp500")
PRICE_DIR = DEFAULT_PATHS.price_dir
BENCHMARK_PATH = DEFAULT_PATHS.benchmark_path
OUTPUT_DIR = DEFAULT_PATHS.signals_dir
REPORT_PATH = DEFAULT_PATHS.signal_report_path

SignalFunc = Callable[[pd.DataFrame, pd.DataFrame | None], pd.Series]


@dataclass(frozen=True)
class SignalSpec:
    signal_id: str
    name: str
    formula: str
    func: SignalFunc
    requires_benchmark: bool = False


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


def adjusted_close(frame: pd.DataFrame) -> pd.Series:
    adjusted = pd.to_numeric(frame["adj_close"], errors="coerce") if "adj_close" in frame.columns else pd.Series(pd.NA, index=frame.index)
    raw = pd.to_numeric(frame["close"], errors="coerce") if "close" in frame.columns else pd.Series(pd.NA, index=frame.index)
    return adjusted.fillna(raw).astype("float64")


def adjusted_open(frame: pd.DataFrame) -> pd.Series:
    adjusted = pd.to_numeric(frame["adj_open"], errors="coerce") if "adj_open" in frame.columns else pd.Series(pd.NA, index=frame.index)
    raw = pd.to_numeric(frame["open"], errors="coerce") if "open" in frame.columns else pd.Series(pd.NA, index=frame.index)
    return adjusted.fillna(raw).astype("float64")


def signal_12_1_momentum(frame: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.Series:
    close = adjusted_close(frame)
    return close.shift(21) / close.shift(252) - 1.0


def signal_1m_reversal(frame: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.Series:
    close = adjusted_close(frame)
    return -(close / close.shift(21) - 1.0)


def signal_low_volatility(frame: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.Series:
    return -adjusted_close(frame).pct_change().rolling(60, min_periods=60).std(ddof=0)


def signal_liquidity_size(frame: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.Series:
    dvol = pd.to_numeric(frame["dollar_volume"], errors="coerce").replace(0.0, np.nan)
    return -np.log(dvol.rolling(60, min_periods=60).mean())


def signal_illiquidity(frame: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.Series:
    close = adjusted_close(frame)
    dvol = pd.to_numeric(frame["dollar_volume"], errors="coerce").replace(0.0, np.nan)
    return -(close.pct_change().abs() / dvol).replace([np.inf, -np.inf], np.nan)


def signal_volume_shock(frame: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.Series:
    volume = pd.to_numeric(frame["volume"], errors="coerce")
    recent = volume.rolling(5, min_periods=5).mean()
    base = volume.shift(5).rolling(60, min_periods=60).mean()
    return recent / base - 1.0


def signal_near_high(frame: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.Series:
    close = adjusted_close(frame)
    return close / close.rolling(252, min_periods=252).max()


def signal_overnight_gap_reversal(frame: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.Series:
    open_ = adjusted_open(frame)
    close = adjusted_close(frame)
    return -(open_ / close.shift(1) - 1.0)


def signal_beta_residual(frame: pd.DataFrame, benchmark: pd.DataFrame | None) -> pd.Series:
    if benchmark is None or benchmark.empty:
        return pd.Series(np.nan, index=frame.index)
    data = frame[["date"]].copy()
    data["stock_ret"] = adjusted_close(frame).pct_change()
    bench = benchmark[["date", "daily_return"]].copy()
    bench["date"] = pd.to_datetime(bench["date"]).dt.normalize()
    data = data.merge(bench, on="date", how="left")
    stock = data["stock_ret"].astype("float64")
    market = data["daily_return"].astype("float64")
    beta = stock.rolling(60, min_periods=60).cov(market) / market.rolling(60, min_periods=60).var(ddof=0)
    residual = stock - beta * market
    return -residual.rolling(21, min_periods=21).sum()


SIGNALS = [
    SignalSpec("US_A1_12_1_momentum", "12-1 momentum", "adj_close.shift(21) / adj_close.shift(252) - 1", signal_12_1_momentum),
    SignalSpec("US_A2_1m_reversal", "1m reversal", "-1m return", signal_1m_reversal),
    SignalSpec("US_A3_low_volatility", "low volatility", "-rolling_std(ret_1d, 60)", signal_low_volatility),
    SignalSpec("US_A4_liquidity_size", "liquidity size", "-log(avg dollar volume 60d)", signal_liquidity_size),
    SignalSpec("US_A5_illiquidity", "Amihud illiquidity", "-abs(ret)/dollar_volume", signal_illiquidity),
    SignalSpec("US_A6_volume_shock", "volume shock", "avg volume 5d / prior avg volume 60d - 1", signal_volume_shock),
    SignalSpec("US_A7_near_high", "near 252d high", "adj_close / rolling_252d_high", signal_near_high),
    SignalSpec("US_A8_gap_reversal", "overnight gap reversal", "-overnight gap", signal_overnight_gap_reversal),
    SignalSpec("US_A9_beta_residual", "beta residual reversal", "-21d beta residual", signal_beta_residual, True),
]


def cs_zscore(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    grouped = out.groupby("date")["signal_value"]
    mean = grouped.transform("mean")
    std = grouped.transform(lambda values: values.std(ddof=0))
    out["signal_cs_z"] = ((out["signal_value"] - mean) / std.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)
    return out[["symbol", "date", "signal_cs_z"]]


def stock_symbols(price_dir: Path = PRICE_DIR) -> list[str]:
    return sorted(path.stem for path in price_dir.glob("*.parquet") if not path.name.startswith("_"))


def compute_signal(spec: SignalSpec, benchmark: pd.DataFrame | None, price_dir: Path = PRICE_DIR) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    frames: list[pd.DataFrame] = []
    for symbol in stock_symbols(price_dir):
        frame = pd.read_parquet(price_dir / f"{symbol}.parquet")
        frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
        frame = frame.sort_values("date").reset_index(drop=True)
        raw = spec.func(frame, benchmark if spec.requires_benchmark else None)
        frames.append(pd.DataFrame({"symbol": symbol, "date": frame["date"], "signal_value": raw.astype("float64")}))
    raw_out = pd.concat(frames, ignore_index=True)
    z_out = cs_zscore(raw_out)
    stats = {
        "signal_id": spec.signal_id,
        "rows": int(len(raw_out)),
        "non_nan_ratio": float(raw_out["signal_value"].notna().mean()) if len(raw_out) else math.nan,
        "z_non_nan_ratio": float(z_out["signal_cs_z"].notna().mean()) if len(z_out) else math.nan,
    }
    return raw_out, z_out, stats


def write_report(stats: pd.DataFrame, report_path: Path = REPORT_PATH) -> None:
    lines = [
        "# US Signal Catalog",
        "",
        "- Universe mode: `survivorship_biased_current_universe`.",
        "- Data source mode: `free_yfinance_research_data` unless config says otherwise.",
        "- Signals are OHLCV-only Phase 1 candidates; no strategy is promoted from this report alone.",
        "",
        "## Signals",
        "| signal_id | name | formula |",
        "| --- | --- | --- |",
    ]
    for spec in SIGNALS:
        lines.append(f"| {spec.signal_id} | {spec.name} | {spec.formula} |")
    lines.extend(["", "## Sanity", stats.to_markdown(index=False), ""])
    atomic_write_text("\n".join(lines), report_path)


def run(universe_key: str = "sp500") -> dict[str, object]:
    paths = us_research_paths(universe_key)
    paths.signals_dir.mkdir(parents=True, exist_ok=True)
    benchmark = pd.read_parquet(paths.benchmark_path) if paths.benchmark_path.exists() else pd.DataFrame()
    rows = []
    for spec in SIGNALS:
        raw, z, stats = compute_signal(spec, benchmark, paths.price_dir)
        atomic_write_parquet(raw, paths.signals_dir / f"{spec.signal_id}.parquet")
        atomic_write_parquet(z, paths.signals_dir / f"{spec.signal_id}_cs_zscore.parquet")
        rows.append(stats)
    stats = pd.DataFrame(rows)
    atomic_write_parquet(stats, paths.signals_dir / "_sanity_check.parquet")
    write_report(stats, paths.signal_report_path)
    return {"universe_key": paths.universe_key, "signals": len(SIGNALS), "symbols": len(stock_symbols(paths.price_dir)), "rows_per_signal": int(stats["rows"].iloc[0]) if len(stats) else 0}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute US batch factor signals.")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--universe-key", default="sp500")
    args = parser.parse_args()
    if not args.run:
        print(f"signals={len(SIGNALS)}")
        return
    print(json.dumps(run(args.universe_key), indent=2))


if __name__ == "__main__":
    main()
