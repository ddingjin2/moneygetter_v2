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

from v2.data.market_dataset import (  # noqa: E402
    DEFAULT_OHLCV_PATH,
    atomic_write_text,
    latest_ohlcv_date,
    load_ohlcv,
    merge_ohlcv,
    save_ohlcv,
)
from v2.data.delistings import DEFAULT_DELISTING_REGISTRY_PATH  # noqa: E402
from v2.data.ohlcv_cleaner import clean_ohlcv  # noqa: E402
from v2.data.pykrx_collector import PykrxCollector, TickerRecord  # noqa: E402
from v2.data.universe import load_kospi_universe  # noqa: E402

REPORT_PATH = ROOT / "v2/reports/v2_market_dataset_update.md"
META_PATH = ROOT / "v2/data/processed/market_ohlcv_update_meta.json"
UNIVERSE_PATH = ROOT / "v2/data/cache/universe/kospi_universe.parquet"


def ymd(value: str | pd.Timestamp) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def infer_range(start: str | None, end: str | None, path: Path) -> tuple[pd.Timestamp, pd.Timestamp]:
    end_ts = pd.Timestamp(end).normalize() if end else pd.Timestamp.now(tz="Asia/Seoul").tz_localize(None).normalize()
    if start:
        start_ts = pd.Timestamp(start).normalize()
    else:
        latest = latest_ohlcv_date(path)
        start_ts = (latest + pd.Timedelta(days=1)).normalize() if latest is not None else end_ts
    return start_ts, end_ts


def load_universe_records(
    limit: int | None = None,
    *,
    start: pd.Timestamp | None = None,
    universe_path: Path = UNIVERSE_PATH,
    registry_path: Path = DEFAULT_DELISTING_REGISTRY_PATH,
) -> list[TickerRecord]:
    frame = load_kospi_universe(universe_path, registry_path=registry_path)
    if start is not None:
        start_date = pd.Timestamp(start).normalize()
        frame = frame.loc[frame["delisted_date"].isna() | frame["delisted_date"].ge(start_date)]
    records = [
        TickerRecord(ticker=str(row.code).zfill(6), market="KOSPI", name=str(row.name) if not pd.isna(row.name) else None, source="v2_universe_cache")
        for row in frame.sort_values("code").itertuples(index=False)
    ]
    return records[:limit] if limit is not None else records


def collect_incremental(
    records: list[TickerRecord],
    start: pd.Timestamp,
    end: pd.Timestamp,
    adjusted: bool,
    progress: int,
    include_market_cap: bool = False,
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    collector = PykrxCollector()
    frames: list[pd.DataFrame] = []
    failures: list[dict[str, str]] = []
    for index, record in enumerate(records, start=1):
        try:
            raw = collector.fetch_ohlcv_with_market_cap(
                record.ticker,
                ymd(start),
                ymd(end),
                adjusted=adjusted,
                include_market_cap=include_market_cap,
            )
            if raw.empty:
                failures.append({"ticker": record.ticker, "error": "empty"})
                continue
            frames.append(clean_ohlcv(raw, ticker=record.ticker, market=record.market, name=record.name))
        except Exception as exc:  # noqa: BLE001
            failures.append({"ticker": record.ticker, "error": f"{type(exc).__name__}: {exc}"})
        if progress and (index == len(records) or index % progress == 0):
            print(json.dumps({"done": index, "total": len(records), "failures": len(failures)}, ensure_ascii=False))
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), failures


def render_report(meta: dict[str, Any]) -> str:
    return "\n".join(["# v2 market dataset update", "", "```json", json.dumps(meta, ensure_ascii=False, indent=2), "```", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally update v2 standalone market_ohlcv parquet from pykrx.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--adjusted", action="store_true", default=True)
    parser.add_argument("--unadjusted", dest="adjusted", action="store_false")
    parser.add_argument("--limit-symbols", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--progress", type=int, default=50)
    parser.add_argument("--include-market-cap", action="store_true", help="Also try pykrx market-cap endpoint. Default off because this endpoint is unreliable without KRX credentials in this environment.")
    parser.add_argument("--output", default=str(DEFAULT_OHLCV_PATH))
    args = parser.parse_args()

    output = Path(args.output)
    start_ts, end_ts = infer_range(args.start, args.end, output)
    records = load_universe_records(args.limit_symbols, start=start_ts)
    meta: dict[str, Any] = {
        "start": start_ts.date().isoformat(),
        "end": end_ts.date().isoformat(),
        "symbols_requested": len(records),
        "dry_run": bool(args.dry_run),
        "output": str(output),
    }
    if start_ts > end_ts:
        meta.update({"rows_new": 0, "symbols_with_rows": 0, "skipped": "already_up_to_date"})
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return
    if args.dry_run:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    incoming, failures = collect_incremental(records, start_ts, end_ts, args.adjusted, args.progress, args.include_market_cap)
    meta["failure_count"] = len(failures)
    meta["failures"] = failures[:100]
    meta["rows_new"] = int(len(incoming))
    meta["symbols_with_rows"] = int(incoming["symbol"].nunique()) if not incoming.empty else 0
    if incoming.empty:
        atomic_write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", META_PATH)
        atomic_write_text(render_report(meta), REPORT_PATH)
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    existing = load_ohlcv(output) if output.exists() else pd.DataFrame()
    merged = merge_ohlcv(existing, incoming)
    save_ohlcv(merged, output)
    meta["rows_total"] = int(len(merged))
    meta["max_date"] = pd.to_datetime(merged["date"]).max().date().isoformat()
    atomic_write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", META_PATH)
    atomic_write_text(render_report(meta), REPORT_PATH)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
