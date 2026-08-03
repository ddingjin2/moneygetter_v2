from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.us_research_paths import us_research_paths  # noqa: E402

V2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = us_research_paths("sp500")
SIGNALS_DIR = DEFAULT_PATHS.signals_dir
RETURNS_PATH = DEFAULT_PATHS.returns_path
OUTPUT_DIR = DEFAULT_PATHS.ic_dir
FULL_PATH = DEFAULT_PATHS.ic_full_path
SUMMARY_PATH = DEFAULT_PATHS.ic_summary_path
REPORT_PATH = DEFAULT_PATHS.ic_report_path


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


def daily_ic(merged: pd.DataFrame, signal_col: str, return_col: str) -> pd.DataFrame:
    rows = []
    for date, group in merged.dropna(subset=[signal_col, return_col]).groupby("date"):
        if len(group) < 30:
            continue
        signal_rank = group[signal_col].rank(method="average")
        return_rank = group[return_col].rank(method="average")
        rows.append({"date": date, "ic": signal_rank.corr(return_rank), "n_valid": len(group)})
    return pd.DataFrame(rows)


def summarize(full: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (signal_id, horizon), group in full.groupby(["signal_id", "horizon"], sort=True):
        ic = group["ic"].astype("float64")
        mean = float(ic.mean()) if len(ic) else math.nan
        std = float(ic.std(ddof=1)) if len(ic) > 1 else math.nan
        rows.append(
            {
                "signal_id": signal_id,
                "horizon": horizon,
                "mean_ic": mean,
                "std_ic": std,
                "t_stat": mean / (std / math.sqrt(len(ic))) if std and not math.isnan(std) else math.nan,
                "positive_ratio": float((ic > 0).mean()) if len(ic) else math.nan,
                "n_days": int(len(ic)),
                "avg_n_valid": float(group["n_valid"].mean()) if len(group) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def run(universe_key: str = "sp500") -> dict[str, object]:
    paths = us_research_paths(universe_key)
    returns = pd.read_parquet(paths.returns_path)
    returns["symbol"] = returns["symbol"].astype(str)
    returns["date"] = pd.to_datetime(returns["date"]).dt.normalize()
    full_rows = []
    for path in sorted(paths.signals_dir.glob("*_cs_zscore.parquet")):
        signal_id = path.stem.replace("_cs_zscore", "")
        signal = pd.read_parquet(path)
        signal["symbol"] = signal["symbol"].astype(str)
        signal["date"] = pd.to_datetime(signal["date"]).dt.normalize()
        merged = signal.merge(returns, on=["symbol", "date"], how="inner")
        for horizon in [1, 5, 20]:
            col = f"forward_return_{horizon}d"
            valid_col = f"ret_valid_{horizon}d"
            sub = merged.loc[merged[valid_col].astype(bool), ["date", "signal_cs_z", col]].copy()
            ic = daily_ic(sub, "signal_cs_z", col)
            if ic.empty:
                continue
            ic.insert(0, "horizon", f"{horizon}d")
            ic.insert(0, "signal_id", signal_id)
            full_rows.append(ic)
    full = pd.concat(full_rows, ignore_index=True) if full_rows else pd.DataFrame(columns=["signal_id", "horizon", "date", "ic", "n_valid"])
    summary = summarize(full) if not full.empty else pd.DataFrame()
    atomic_write_parquet(full, paths.ic_full_path)
    atomic_write_parquet(summary, paths.ic_summary_path)
    lines = [
        "# US IC Batch",
        "",
        "- Universe mode: `survivorship_biased_current_universe`.",
        "- IC is diagnostic; promotion requires backtest gates too.",
        "",
        "## Summary",
        summary.to_markdown(index=False) if not summary.empty else "(no IC rows)",
        "",
    ]
    atomic_write_text("\n".join(lines), paths.ic_report_path)
    return {"universe_key": paths.universe_key, "signals": int(summary["signal_id"].nunique()) if not summary.empty else 0, "full_rows": int(len(full)), "summary_rows": int(len(summary))}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run US batch IC measurement.")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--universe-key", default="sp500")
    args = parser.parse_args()
    if not args.run:
        print("Use --run")
        return
    print(json.dumps(run(args.universe_key), indent=2))


if __name__ == "__main__":
    main()
