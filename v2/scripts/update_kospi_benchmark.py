from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.kospi_loader import (  # noqa: E402
    DEFAULT_BENCHMARK_PATH,
    DEFAULT_CACHE_PATH,
    update_kospi_benchmark,
)
from v2.data.market_dataset import latest_ohlcv_date  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Update KOSPI daily data and research benchmark returns.")
    parser.add_argument("--expected-latest", default=None, help="Required latest trading date. Defaults to canonical OHLCV latest date.")
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--benchmark-path", default=str(DEFAULT_BENCHMARK_PATH))
    args = parser.parse_args()

    expected = pd.Timestamp(args.expected_latest).normalize() if args.expected_latest else latest_ohlcv_date()
    if expected is None:
        raise SystemExit("Canonical OHLCV has no latest date; cannot update KOSPI benchmark.")

    data, benchmark = update_kospi_benchmark(
        cache_path=args.cache_path,
        benchmark_path=args.benchmark_path,
        expected_latest=expected,
    )
    result = {
        "status": "pass",
        "expected_latest": expected.date().isoformat(),
        "kospi_latest": pd.to_datetime(data["date"]).max().date().isoformat(),
        "benchmark_latest": pd.to_datetime(benchmark["date"]).max().date().isoformat(),
        "rows": int(len(benchmark)),
        "cache_path": str(Path(args.cache_path)),
        "benchmark_path": str(Path(args.benchmark_path)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
