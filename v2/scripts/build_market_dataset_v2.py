from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.market_dataset import DEFAULT_OHLCV_PATH, atomic_write_text, save_ohlcv  # noqa: E402
from v2.data.ohlcv_cleaner import clean_ohlcv  # noqa: E402
from v2.data.pykrx_collector import CollectorError, PykrxCollector, TickerRecord  # noqa: E402

REPORT_PATH = ROOT / "v2/reports/v2_market_dataset_build.md"
META_PATH = ROOT / "v2/data/processed/market_ohlcv_meta.json"
UNIVERSE_PATH = ROOT / "v2/data/cache/universe/kospi_universe.parquet"


def ymd(value: str) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def load_universe_records(path: Path, market: str, limit: int | None = None) -> list[TickerRecord]:
    frame = pd.read_parquet(path)
    records = [
        TickerRecord(
            ticker=str(row.code).zfill(6),
            market=market,
            name=str(row.name) if not pd.isna(row.name) else None,
            source="v2_universe_cache",
        )
        for row in frame.sort_values("code").itertuples(index=False)
    ]
    return records[:limit] if limit is not None else records


def collect_records(args: argparse.Namespace, collector: PykrxCollector) -> tuple[pd.DataFrame, dict[str, Any]]:
    frames: list[pd.DataFrame] = []
    failures: list[dict[str, str]] = []
    markets = [item.strip().upper() for item in args.markets.split(",") if item.strip()]
    total_seen = 0

    for market in markets:
        if args.use_universe_cache and market == "KOSPI" and UNIVERSE_PATH.exists():
            records = load_universe_records(UNIVERSE_PATH, market, args.limit_symbols)
        else:
            records = collector.fetch_ticker_records(market, as_of_date=ymd(args.end))
            if args.limit_symbols is not None:
                records = records[: args.limit_symbols]
        total_seen += len(records)
        for index, record in enumerate(records, start=1):
            try:
                raw = collector.fetch_ohlcv_with_market_cap(
                    record.ticker,
                    ymd(args.start),
                    ymd(args.end),
                    adjusted=args.adjusted,
                    include_market_cap=args.include_market_cap,
                )
                if raw.empty:
                    failures.append({"ticker": record.ticker, "market": market, "error": "empty"})
                    continue
                frames.append(clean_ohlcv(raw, ticker=record.ticker, market=market, name=record.name))
            except Exception as exc:  # noqa: BLE001 - build report should preserve per-symbol failures
                failures.append({"ticker": record.ticker, "market": market, "error": f"{type(exc).__name__}: {exc}"})
            if args.progress and (index == len(records) or index % args.progress == 0):
                print(json.dumps({"market": market, "done": index, "total": len(records), "failures": len(failures)}, ensure_ascii=False))

    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    meta = {
        "start": args.start,
        "end": args.end,
        "markets": markets,
        "symbols_seen": total_seen,
        "symbols_with_rows": int(frame["symbol"].nunique()) if not frame.empty else 0,
        "rows": int(len(frame)),
        "failures": failures[:100],
        "failure_count": len(failures),
        "dry_run": bool(args.dry_run),
        "output": str(Path(args.output)),
    }
    return frame, meta


def render_report(meta: dict[str, Any]) -> str:
    return "\n".join(["# v2 market dataset build", "", "```json", json.dumps(meta, ensure_ascii=False, indent=2), "```", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build v2 standalone market_ohlcv parquet from pykrx.")
    parser.add_argument("--start", default="2020-03-27")
    parser.add_argument("--end", default=pd.Timestamp.now(tz="Asia/Seoul").date().isoformat())
    parser.add_argument("--markets", default="KOSPI")
    parser.add_argument("--adjusted", action="store_true", default=True)
    parser.add_argument("--unadjusted", dest="adjusted", action="store_false")
    parser.add_argument("--use-universe-cache", action="store_true", default=True)
    parser.add_argument("--no-universe-cache", dest="use_universe_cache", action="store_false")
    parser.add_argument("--limit-symbols", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--progress", type=int, default=50)
    parser.add_argument("--include-market-cap", action="store_true", help="Also try pykrx market-cap endpoint. Default off because this endpoint is unreliable without KRX credentials in this environment.")
    parser.add_argument("--output", default=str(DEFAULT_OHLCV_PATH))
    args = parser.parse_args()

    collector = PykrxCollector()
    frame, meta = collect_records(args, collector)
    if not frame.empty:
        meta["min_date"] = pd.to_datetime(frame["date"]).min().date().isoformat()
        meta["max_date"] = pd.to_datetime(frame["date"]).max().date().isoformat()
    if not args.dry_run:
        if frame.empty:
            raise SystemExit("No rows collected; refusing to overwrite market_ohlcv parquet")
        save_ohlcv(frame, args.output)
        atomic_write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", META_PATH)
        atomic_write_text(render_report(meta), REPORT_PATH)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
