from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.us_market_dataset import latest_us_ohlcv_date, load_us_ohlcv, load_us_universe, merge_us_ohlcv, save_us_ohlcv, us_ohlcv_path  # noqa: E402
from v2.data.us_providers import provider_from_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally update US OHLCV dataset.")
    parser.add_argument("--config", default="config/us_market_data.example.json")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--limit-symbols", type=int, default=None)
    parser.add_argument("--universe-key", default=None)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    universe_key = args.universe_key or config.get("universe_key", "sp500")
    ohlcv_path = us_ohlcv_path(universe_key)
    latest = latest_us_ohlcv_date(universe_key=universe_key)
    start = args.start or ((latest + pd.Timedelta(days=1)).date().isoformat() if latest is not None else config["start"])
    provider = provider_from_config(config)
    universe = load_us_universe(universe_key=universe_key)
    symbols = universe["symbol"].astype(str).tolist()
    benchmark = config.get("benchmark", {}).get("symbol", "SPY").upper()
    if benchmark not in symbols:
        symbols.append(benchmark)
    if args.limit_symbols:
        symbols = symbols[: args.limit_symbols]
        if benchmark not in symbols:
            symbols.append(benchmark)
    existing = load_us_ohlcv(universe_key=universe_key) if ohlcv_path.exists() else pd.DataFrame()
    existing_symbols = set(existing["symbol"].astype(str).unique()) if not existing.empty else set()
    missing_symbols = [symbol for symbol in symbols if symbol not in existing_symbols]
    current_symbols = [symbol for symbol in symbols if symbol in existing_symbols]
    frames = []
    if current_symbols:
        frames.append(provider.fetch_daily_bars(current_symbols, start, args.end))
    if missing_symbols:
        frames.append(provider.fetch_daily_bars(missing_symbols, config["start"], args.end))
    incoming = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True) if frames else pd.DataFrame()
    merged = merge_us_ohlcv(existing, incoming)
    path = save_us_ohlcv(merged, universe_key=universe_key)
    print(
        json.dumps(
            {
                "path": str(path),
                "universe_key": universe_key,
                "start": start,
                "end": args.end,
                "symbols_requested": len(symbols),
                "symbols_backfilled": len(missing_symbols),
                "rows_new": int(len(incoming)),
                "rows_total": int(len(merged)),
                "max_date": str(pd.to_datetime(merged["date"]).max().date()) if not merged.empty else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
