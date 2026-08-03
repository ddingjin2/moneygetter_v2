from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.ohlcv import load_ohlcv  # noqa: E402
from v2.data.universe import load_kospi_universe  # noqa: E402


REQUEST_START = pd.Timestamp("2020-03-27")
REQUEST_END = pd.Timestamp("2026-12-31")
UNIVERSE_PATH = ROOT / "v2/data/cache/universe/kospi_universe.parquet"
KOSPI_CALENDAR_PATH = ROOT / "v2/data/cache/kospi_daily.parquet"
MINI_PRICE_DIR = ROOT / "v2/data/cache/prices_mini_pilot"
OUTPUT_DIR = ROOT / "v2/data/cache/price_market_cap_full"
QUALITY_LOG_PATH = OUTPUT_DIR / "_quality_log.parquet"
META_PATH = OUTPUT_DIR / "_prepare_meta.json"
REPORT_PATH = ROOT / "v2/reports/pr7_a_2_a_step3_price_market_cap.md"

OUTPUT_COLUMNS = [
    "date",
    "symbol",
    "name",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trading_value",
    "turnover",
    "market_cap",
    "shares_outstanding",
    "source",
]

LOG_COLUMNS = [
    "code",
    "name",
    "start_date",
    "end_date",
    "rows_collected",
    "expected_trading_days",
    "price_coverage_ratio",
    "positive_market_cap_rows",
    "market_cap_coverage_ratio",
    "status",
]


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


def load_universe() -> pd.DataFrame:
    frame = load_kospi_universe(UNIVERSE_PATH)
    frame["listed_date"] = pd.to_datetime(frame["listed_date"], errors="coerce").dt.normalize()
    frame["delisted_date"] = pd.to_datetime(frame["delisted_date"], errors="coerce").dt.normalize()
    frame["sector"] = frame["sector"].fillna("unknown")
    return frame.sort_values("code").reset_index(drop=True)


def load_trading_calendar() -> pd.DatetimeIndex:
    frame = pd.read_parquet(KOSPI_CALENDAR_PATH, columns=["date"])
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna().dt.normalize()
    dates = dates.loc[dates.between(REQUEST_START, REQUEST_END)].drop_duplicates().sort_values()
    return pd.DatetimeIndex(dates)


def normalize_ohlcv() -> pd.DataFrame:
    frame = load_ohlcv().copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
    if "name" not in frame.columns:
        frame["name"] = frame["symbol"]
    for column in OUTPUT_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame.loc[frame["market"].eq("KOSPI") & frame["date"].between(REQUEST_START, REQUEST_END)].copy()
    return frame[OUTPUT_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)


def window_for_row(row: Any) -> tuple[pd.Timestamp, pd.Timestamp]:
    listed = pd.Timestamp(row.listed_date).normalize()
    delisted = None if pd.isna(row.delisted_date) else pd.Timestamp(row.delisted_date).normalize()
    start = max(REQUEST_START, listed)
    end = min(REQUEST_END, delisted) if delisted is not None else REQUEST_END
    return start, end


def expected_days(calendar: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp) -> int:
    return int(calendar[(calendar >= start) & (calendar <= end)].nunique())


def classify_status(rows: int, expected: int, positive_market_cap_rows: int) -> str:
    if rows <= 0:
        return "failed"
    price_ratio = rows / expected if expected else math.nan
    if math.isnan(price_ratio) or price_ratio < 0.95:
        return "partial_price"
    if positive_market_cap_rows <= 0:
        return "ok_price_no_market_cap"
    return "ok"


def prepare_full_cache() -> dict[str, Any]:
    started = pd.Timestamp.now(tz="Asia/Seoul")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    universe = load_universe()
    calendar = load_trading_calendar()
    ohlcv = normalize_ohlcv()
    data_end = pd.to_datetime(ohlcv["date"], errors="coerce").max().normalize()
    effective_end = min(REQUEST_END, pd.Timestamp(data_end)) if not pd.isna(data_end) else REQUEST_END
    grouped = {code: frame.copy() for code, frame in ohlcv.groupby("symbol", sort=False)}

    log_rows: list[dict[str, Any]] = []
    for row in universe.itertuples(index=False):
        code = str(row.code).zfill(6)
        start, end = window_for_row(row)
        end = min(end, effective_end)
        expected = expected_days(calendar, start, end)
        frame = grouped.get(code, pd.DataFrame(columns=OUTPUT_COLUMNS)).copy()
        frame = frame.loc[frame["date"].between(start, end)].sort_values("date").reset_index(drop=True)
        positive_market_cap_rows = int(pd.to_numeric(frame["market_cap"], errors="coerce").gt(0).sum())
        rows = int(len(frame))
        price_ratio = rows / expected if expected else math.nan
        market_cap_ratio = positive_market_cap_rows / expected if expected else math.nan
        status = classify_status(rows, expected, positive_market_cap_rows)
        if rows > 0:
            atomic_write_parquet(frame, OUTPUT_DIR / f"{code}.parquet")
        log_rows.append(
            {
                "code": code,
                "name": str(row.name),
                "start_date": start.date().isoformat(),
                "end_date": end.date().isoformat(),
                "rows_collected": rows,
                "expected_trading_days": expected,
                "price_coverage_ratio": price_ratio,
                "positive_market_cap_rows": positive_market_cap_rows,
                "market_cap_coverage_ratio": market_cap_ratio,
                "status": status,
            }
        )

    log = pd.DataFrame(log_rows, columns=LOG_COLUMNS)
    atomic_write_parquet(log, QUALITY_LOG_PATH)
    finished = pd.Timestamp.now(tz="Asia/Seoul")
    meta = {
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "elapsed_seconds": float((finished - started).total_seconds()),
        "effective_end": effective_end.date().isoformat(),
        "source": "v2/data/processed/market_ohlcv.parquet via v2.data.ohlcv.load_ohlcv",
        "pykrx_market_cap_probe": probe_pykrx_market_cap(),
    }
    atomic_write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", META_PATH)
    write_report(meta=meta)
    return meta


def probe_pykrx_market_cap() -> dict[str, Any]:
    try:
        from pykrx import stock

        data = stock.get_market_cap_by_ticker("20260417", market="KOSPI")
        return {
            "attempted": True,
            "available": True,
            "rows": int(len(data)),
            "columns": [str(column) for column in data.columns],
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic report should preserve the failure
        return {
            "attempted": True,
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "note": "pykrx market-cap endpoint did not return the expected schema in this environment.",
        }


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.1f}%"


def compare_mini_prices() -> tuple[list[dict[str, object]], int, int]:
    rows: list[dict[str, object]] = []
    matched = 0
    matched_rows = 0
    value_columns = ["symbol", "name", "close", "volume"]
    for mini_path in sorted(MINI_PRICE_DIR.glob("*.parquet")):
        code = mini_path.stem.zfill(6)
        full_path = OUTPUT_DIR / f"{code}.parquet"
        mini = pd.read_parquet(mini_path)
        full = pd.read_parquet(full_path) if full_path.exists() else pd.DataFrame()
        mini["date"] = pd.to_datetime(mini["date"]).dt.normalize()
        if not full.empty:
            full["date"] = pd.to_datetime(full["date"]).dt.normalize()
        mini_dates = set(mini["date"]) if not mini.empty else set()
        full_dates = set(full["date"]) if not full.empty else set()
        dates_in_full = mini_dates.issubset(full_dates)
        same_values = False
        compared_rows = 0
        if dates_in_full and not full.empty:
            common_columns = ["date"] + [column for column in value_columns if column in mini.columns and column in full.columns]
            mini_cmp = mini[common_columns].sort_values("date").reset_index(drop=True)
            full_cmp = (
                full.loc[full["date"].isin(mini_dates), common_columns]
                .sort_values("date")
                .reset_index(drop=True)
            )
            compared_rows = int(len(mini_cmp))
            same_values = True
            for column in common_columns:
                if pd.api.types.is_numeric_dtype(mini_cmp[column]) or pd.api.types.is_numeric_dtype(full_cmp[column]):
                    left = pd.to_numeric(mini_cmp[column], errors="coerce")
                    right = pd.to_numeric(full_cmp[column], errors="coerce")
                    same_values = same_values and bool(left.fillna(-999999999999.0).eq(right.fillna(-999999999999.0)).all())
                else:
                    same_values = same_values and bool(mini_cmp[column].fillna("").astype(str).eq(full_cmp[column].fillna("").astype(str)).all())
        is_match = bool(dates_in_full and same_values)
        matched += int(is_match)
        matched_rows += compared_rows if is_match else 0
        rows.append(
            {
                "code": code,
                "mini_rows": int(len(mini)),
                "full_rows": int(len(full)),
                "mini_dates_in_full": dates_in_full,
                "value_match": same_values,
                "compared_rows": compared_rows,
            }
        )
    return rows, matched, matched_rows


def sample_rows_for_report(universe: pd.DataFrame) -> list[dict[str, object]]:
    selected = pd.concat([universe.head(2), universe.iloc[len(universe) // 2 : len(universe) // 2 + 2], universe.tail(2)])
    rows: list[dict[str, object]] = []
    for item in selected.itertuples(index=False):
        path = OUTPUT_DIR / f"{item.code}.parquet"
        if not path.exists():
            continue
        data = pd.read_parquet(path).sort_values("date")
        preview = pd.concat([data.head(3), data.tail(3)]).drop_duplicates("date")
        for row in preview.itertuples(index=False):
            rows.append(
                {
                    "code": item.code,
                    "name": item.name,
                    "date": pd.Timestamp(row.date).date().isoformat(),
                    "close": row.close,
                    "volume": row.volume,
                    "market_cap": row.market_cap,
                }
            )
    return rows


def read_meta(meta: dict[str, Any] | None = None) -> dict[str, Any]:
    if meta is not None:
        return meta
    if META_PATH.exists():
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    return {}


def write_report(meta: dict[str, Any] | None = None) -> None:
    meta = read_meta(meta)
    universe = load_universe()
    log = pd.read_parquet(QUALITY_LOG_PATH) if QUALITY_LOG_PATH.exists() else pd.DataFrame(columns=LOG_COLUMNS)
    status_counts = log["status"].value_counts().to_dict() if not log.empty else {}
    total_rows = int(pd.to_numeric(log["rows_collected"], errors="coerce").fillna(0).sum())
    price_95 = int(pd.to_numeric(log["price_coverage_ratio"], errors="coerce").ge(0.95).sum()) if not log.empty else 0
    cap_positive_codes = int(log["positive_market_cap_rows"].gt(0).sum()) if not log.empty else 0
    mini_rows, mini_matched, mini_matched_rows = compare_mini_prices()
    sample_rows = sample_rows_for_report(universe)
    delisted = universe.loc[universe["delisted_date"].notna(), ["code", "name", "delisted_date"]].merge(
        log[["code", "status", "rows_collected", "price_coverage_ratio", "positive_market_cap_rows"]],
        on="code",
        how="left",
    )
    pykrx_probe = meta.get("pykrx_market_cap_probe", {})
    elapsed = float(meta.get("elapsed_seconds", 0.0) or 0.0)

    lines = [
        "# PR-7.A.2.a Step 3 Price + Market-cap Data Readiness",
        "",
        "## Summary",
        f"- Universe stocks: `{len(universe)}`",
        f"- Price files: `{len(list(OUTPUT_DIR.glob('[0-9][0-9][0-9][0-9][0-9][0-9].parquet')))}`",
        f"- Price rows: `{total_rows}`",
        f"- Price coverage 95%+: `{price_95}`",
        f"- Status counts: `{status_counts}`",
        f"- Codes with positive market_cap rows: `{cap_positive_codes}`",
        f"- Elapsed: `{int(elapsed // 60)}m {int(elapsed % 60)}s`",
        "",
        "## Source",
        f"- Local OHLCV: `{meta.get('source', 'NA')}`",
        f"- Date window: `{REQUEST_START.date().isoformat()} ~ {meta.get('effective_end', REQUEST_END.date().isoformat())}`, intersected with each stock's universe active window.",
        "",
        "## Market-cap Availability",
        "- Local OHLCV `market_cap` is present but all values are zero for this universe window.",
        "- `shares_outstanding` is also unavailable in the local OHLCV source.",
        "- pykrx market-cap probe result:",
        "```json",
        json.dumps(pykrx_probe, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Delisted Stocks",
        markdown_table(
            delisted.to_dict("records"),
            ["code", "name", "delisted_date", "status", "rows_collected", "price_coverage_ratio", "positive_market_cap_rows"],
        ),
        "",
        "## Mini-pilot Price Cache Comparison",
        f"- Exact overlap match: `{mini_matched}/30`",
        f"- Matched rows: `{mini_matched_rows}`",
        markdown_table(
            mini_rows,
            ["code", "mini_rows", "full_rows", "mini_dates_in_full", "value_match", "compared_rows"],
        ),
        "",
        "## Sample Validation",
        markdown_table(sample_rows, ["code", "name", "date", "close", "volume", "market_cap"]),
        "",
        "## Artifacts",
        f"- Price/market-cap parquet directory: `{OUTPUT_DIR.relative_to(ROOT)}`",
        f"- Quality log: `{QUALITY_LOG_PATH.relative_to(ROOT)}`",
        f"- Report: `{REPORT_PATH.relative_to(ROOT)}`",
        "",
        "## Gate",
        "Step 3 prepared price data, but market-cap data is not usable from current local/pykrx sources. Do not run IC/backtest until the user accepts a no-market-cap path or provides/approves another market-cap source.",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text("\n".join(lines) + "\n", REPORT_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare full-universe price and market-cap readiness cache.")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.report_only:
        write_report()
    else:
        prepare_full_cache()
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
