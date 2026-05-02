from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.scripts.explore_naver_investor_flow import _read_naver_page  # noqa: E402


REQUEST_START = pd.Timestamp("2020-03-27")
REQUEST_END = pd.Timestamp("2026-04-17")
UNIVERSE_PATH = ROOT / "v2/data/cache/universe/kospi_universe.parquet"
KOSPI_CALENDAR_PATH = ROOT / "v2/data/cache/kospi_daily.parquet"
MINI_PILOT_DIR = ROOT / "v2/data/cache/investor_flow_mini_pilot"
OUTPUT_DIR = ROOT / "v2/data/cache/investor_flow_full"
LOG_PATH = OUTPUT_DIR / "_collection_log.parquet"
META_PATH = OUTPUT_DIR / "_collection_meta.json"
REPORT_PATH = ROOT / "v2/reports/pr7_a_2_a_step2_collection.md"
FRESH_OK_HOURS = 24

LOG_COLUMNS = [
    "code",
    "name",
    "start_date",
    "end_date",
    "rows_collected",
    "expected_trading_days",
    "coverage_ratio",
    "failed_pages",
    "last_attempt_ts",
    "status",
]


@dataclass(frozen=True)
class StockWindow:
    code: str
    name: str
    sector: str
    listed_date: pd.Timestamp
    delisted_date: pd.Timestamp | None
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    expected_trading_days: int


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
    frame = pd.read_parquet(UNIVERSE_PATH)
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    frame["listed_date"] = pd.to_datetime(frame["listed_date"], errors="coerce").dt.normalize()
    frame["delisted_date"] = pd.to_datetime(frame["delisted_date"], errors="coerce").dt.normalize()
    frame["sector"] = frame["sector"].fillna("unknown")
    return frame.sort_values("code").reset_index(drop=True)


def load_trading_calendar() -> pd.DatetimeIndex:
    frame = pd.read_parquet(KOSPI_CALENDAR_PATH, columns=["date"])
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna().dt.normalize()
    dates = dates.loc[dates.between(REQUEST_START, REQUEST_END)].drop_duplicates().sort_values()
    return pd.DatetimeIndex(dates)


def build_stock_windows(universe: pd.DataFrame, calendar: pd.DatetimeIndex) -> list[StockWindow]:
    windows: list[StockWindow] = []
    for row in universe.itertuples(index=False):
        listed_date = pd.Timestamp(row.listed_date).normalize()
        delisted_date = None if pd.isna(row.delisted_date) else pd.Timestamp(row.delisted_date).normalize()
        start_date = max(REQUEST_START, listed_date)
        end_date = min(REQUEST_END, delisted_date) if delisted_date is not None else REQUEST_END
        expected = int(calendar[(calendar >= start_date) & (calendar <= end_date)].nunique())
        windows.append(
            StockWindow(
                code=str(row.code).zfill(6),
                name=str(row.name),
                sector=str(row.sector),
                listed_date=listed_date,
                delisted_date=delisted_date,
                start_date=start_date,
                end_date=end_date,
                expected_trading_days=expected,
            )
        )
    return windows


def empty_log() -> pd.DataFrame:
    return pd.DataFrame(columns=LOG_COLUMNS)


def load_log() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return empty_log()
    log = pd.read_parquet(LOG_PATH)
    for column in LOG_COLUMNS:
        if column not in log.columns:
            log[column] = pd.NA
    log["code"] = log["code"].astype(str).str.zfill(6)
    return log[LOG_COLUMNS].drop_duplicates("code", keep="last").reset_index(drop=True)


def save_log(log: pd.DataFrame) -> None:
    clean = log[LOG_COLUMNS].drop_duplicates("code", keep="last").sort_values("code").reset_index(drop=True)
    atomic_write_parquet(clean, LOG_PATH)


def update_log(row: dict[str, Any]) -> None:
    log = load_log()
    code = str(row["code"]).zfill(6)
    log = log.loc[log["code"].astype(str).str.zfill(6) != code].copy()
    log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    save_log(log)


def should_skip(window: StockWindow, log: pd.DataFrame, *, retry_only: bool, refresh_stale_ok: bool) -> bool:
    path = OUTPUT_DIR / f"{window.code}.parquet"
    row = log.loc[log["code"].astype(str).str.zfill(6).eq(window.code)]
    if row.empty:
        return retry_only
    status = str(row.iloc[-1]["status"])
    if retry_only and status not in {"partial", "failed"}:
        return True
    if status != "ok" or not path.exists():
        return False
    if not refresh_stale_ok:
        return True
    last_attempt = pd.to_datetime(row.iloc[-1]["last_attempt_ts"], errors="coerce", utc=True)
    if pd.isna(last_attempt):
        return False
    age_hours = (pd.Timestamp.now(tz="UTC") - last_attempt).total_seconds() / 3600
    return age_hours <= FRESH_OK_HOURS


def sleep_random(low: float, high: float) -> None:
    time.sleep(random.uniform(low, high))


def read_page_with_backoff(stock_code: str, page: int) -> tuple[pd.DataFrame, str | None]:
    last_error: str | None = None
    for attempt in range(1, 4):
        try:
            return _read_naver_page(stock_code, page), None
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            last_error = f"page={page} attempt={attempt}: HTTPError status={status_code}: {exc}"
            if status_code not in {429, 500, 502, 503, 504}:
                break
        except Exception as exc:  # noqa: BLE001 - each failure is logged and surfaced to stderr
            last_error = f"page={page} attempt={attempt}: {type(exc).__name__}: {exc}"
        if attempt < 3:
            time.sleep(min(8.0, 0.8 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.4))
    return pd.DataFrame(), last_error


def fetch_stock(window: StockWindow, *, max_pages: int) -> tuple[pd.DataFrame, list[str]]:
    frames: list[pd.DataFrame] = []
    failed_pages: list[str] = []
    for page in range(1, max_pages + 1):
        frame, error = read_page_with_backoff(window.code, page)
        if error is not None:
            print(f"[{window.code}] {error}", file=sys.stderr, flush=True)
            failed_pages.append(error)
            break
        if frame.empty:
            break
        frames.append(frame)
        if frame["date"].min() <= window.start_date:
            break
        sleep_random(0.2, 0.5)

    if not frames:
        return pd.DataFrame(), failed_pages
    data = pd.concat(frames, ignore_index=True)
    data = data.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    data = data.loc[data["date"].between(window.start_date, window.end_date)].copy().reset_index(drop=True)
    data["symbol"] = window.code
    data["name"] = window.name
    return data, failed_pages


def classify_status(rows: int, expected_days: int, failed_pages: list[str]) -> str:
    if rows <= 0:
        return "failed"
    coverage = rows / expected_days if expected_days else math.nan
    if failed_pages or math.isnan(coverage) or coverage < 0.95:
        return "partial"
    return "ok"


def collect_all(*, restart_failed: bool, max_pages: int, refresh_stale_ok: bool) -> None:
    started = pd.Timestamp.now(tz="Asia/Seoul")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    universe = load_universe()
    calendar = load_trading_calendar()
    windows = build_stock_windows(universe, calendar)
    log = load_log()
    attempted = 0

    for index, window in enumerate(windows, start=1):
        if should_skip(window, log, retry_only=restart_failed, refresh_stale_ok=refresh_stale_ok):
            continue

        attempted += 1
        print(f"[{index}/{len(windows)}] collect {window.code} {window.name}", flush=True)
        frame, failed_pages = fetch_stock(window, max_pages=max_pages)
        rows = int(len(frame))
        coverage = rows / window.expected_trading_days if window.expected_trading_days else math.nan
        status = classify_status(rows, window.expected_trading_days, failed_pages)
        if rows > 0:
            atomic_write_parquet(frame, OUTPUT_DIR / f"{window.code}.parquet")

        row = {
            "code": window.code,
            "name": window.name,
            "start_date": window.start_date.date().isoformat(),
            "end_date": window.end_date.date().isoformat(),
            "rows_collected": rows,
            "expected_trading_days": window.expected_trading_days,
            "coverage_ratio": coverage,
            "failed_pages": "; ".join(failed_pages),
            "last_attempt_ts": pd.Timestamp.now(tz="Asia/Seoul").isoformat(),
            "status": status,
        }
        update_log(row)
        log = load_log()
        print(
            f"[{window.code}] status={status} rows={rows} expected={window.expected_trading_days} "
            f"coverage={coverage:.3f}",
            flush=True,
        )
        if index < len(windows):
            sleep_random(0.5, 1.0)

    finished = pd.Timestamp.now(tz="Asia/Seoul")
    meta = {
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "elapsed_seconds": float((finished - started).total_seconds()),
        "attempted_this_run": attempted,
        "restart_failed": restart_failed,
        "refresh_stale_ok": refresh_stale_ok,
    }
    atomic_write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", META_PATH)
    write_report(meta)


def listing_bucket(value: object) -> str:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp) or timestamp <= REQUEST_START:
        return "listed_on_or_before_2020-03-27"
    if timestamp.year <= 2021:
        return "listed_2020-03-28_to_2021-12-31"
    return f"listed_{timestamp.year}"


def code_size_bucket(code: str) -> str:
    numeric = int(str(code).zfill(6))
    if numeric < 100_000:
        return "large_code_lt_100000"
    if numeric < 300_000:
        return "mid_code_100000_299999"
    return "small_code_ge_300000"


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def pct(value: float) -> str:
    if value is None or math.isnan(float(value)):
        return "NA"
    return f"{float(value) * 100:.1f}%"


def read_meta(meta: dict[str, Any] | None = None) -> dict[str, Any]:
    if meta is not None:
        return meta
    if META_PATH.exists():
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    return {}


def compare_mini_pilot() -> tuple[list[dict[str, object]], int, int]:
    rows: list[dict[str, object]] = []
    matched = 0
    matched_rows = 0
    value_columns = [
        "close",
        "volume",
        "institutional_net_buy_shares",
        "foreign_net_buy_shares",
        "foreign_holding_shares",
        "foreign_holding_ratio",
        "symbol",
        "name",
    ]
    for mini_path in sorted(MINI_PILOT_DIR.glob("*.parquet")):
        code = mini_path.stem.zfill(6)
        full_path = OUTPUT_DIR / f"{code}.parquet"
        mini = pd.read_parquet(mini_path)
        full = pd.read_parquet(full_path) if full_path.exists() else pd.DataFrame()
        mini["date"] = pd.to_datetime(mini["date"]).dt.normalize()
        if not full.empty:
            full["date"] = pd.to_datetime(full["date"]).dt.normalize()
        mini_dates = set(mini["date"]) if not mini.empty else set()
        full_dates = set(full["date"]) if not full.empty else set()
        mini_dates_in_full = mini_dates.issubset(full_dates)
        same_values = False
        compared_rows = 0
        if mini_dates_in_full and not full.empty:
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
                if column == "date":
                    same_values = same_values and bool(mini_cmp[column].equals(full_cmp[column]))
                elif pd.api.types.is_numeric_dtype(mini_cmp[column]) or pd.api.types.is_numeric_dtype(full_cmp[column]):
                    left = pd.to_numeric(mini_cmp[column], errors="coerce")
                    right = pd.to_numeric(full_cmp[column], errors="coerce")
                    if column == "foreign_holding_ratio":
                        direct_equal = left.fillna(-999999999999.0).eq(right.fillna(-999999999999.0))
                        scaled_equal = (left / 100.0).fillna(-999999999999.0).eq(right.fillna(-999999999999.0))
                        same_values = same_values and bool((direct_equal | scaled_equal).all())
                    else:
                        same_values = same_values and bool(left.fillna(-999999999999.0).eq(right.fillna(-999999999999.0)).all())
                else:
                    same_values = same_values and bool(mini_cmp[column].fillna("").astype(str).eq(full_cmp[column].fillna("").astype(str)).all())
        is_match = bool(mini_dates_in_full and same_values)
        matched += int(is_match)
        matched_rows += compared_rows if is_match else 0
        if len(full_dates) > len(mini_dates):
            pattern = "full_more_dates"
        elif len(full_dates) < len(mini_dates):
            pattern = "mini_more_dates"
        elif mini_dates_in_full and not same_values:
            pattern = "same_dates_value_diff"
        else:
            pattern = "match" if is_match else "date_diff"
        rows.append(
            {
                "code": code,
                "mini_rows": int(len(mini)),
                "full_rows": int(len(full)),
                "mini_dates_in_full": mini_dates_in_full,
                "value_match": same_values,
                "compared_rows": compared_rows,
                "pattern": pattern,
            }
        )
    return rows, matched, matched_rows


def coverage_histogram(log: pd.DataFrame) -> list[dict[str, object]]:
    ratios = pd.to_numeric(log["coverage_ratio"], errors="coerce").fillna(0.0).clip(lower=0.0, upper=1.0)
    buckets: Counter[str] = Counter()
    for value in ratios:
        low = int((value * 100) // 10) * 10
        if low >= 100:
            label = "100%"
        else:
            label = f"{low:02d}-{low + 10:02d}%"
        buckets[label] += 1
    labels = [f"{low:02d}-{low + 10:02d}%" for low in range(0, 100, 10)] + ["100%"]
    return [{"bucket": label, "count": buckets.get(label, 0)} for label in labels]


def year_coverage_rows(log: pd.DataFrame, universe: pd.DataFrame, calendar: pd.DatetimeIndex) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    merged = universe.merge(log[["code", "status"]], on="code", how="left")
    for year in range(2020, 2027):
        ratios: list[float] = []
        year_start = max(REQUEST_START, pd.Timestamp(f"{year}-01-01"))
        year_end = min(REQUEST_END, pd.Timestamp(f"{year}-12-31"))
        year_calendar = calendar[(calendar >= year_start) & (calendar <= year_end)]
        for row in merged.itertuples(index=False):
            path = OUTPUT_DIR / f"{row.code}.parquet"
            if not path.exists():
                continue
            listed = pd.Timestamp(row.listed_date).normalize()
            delisted = None if pd.isna(row.delisted_date) else pd.Timestamp(row.delisted_date).normalize()
            start = max(year_start, listed)
            end = min(year_end, delisted) if delisted is not None else year_end
            expected = int(year_calendar[(year_calendar >= start) & (year_calendar <= end)].nunique())
            if expected <= 0:
                continue
            frame = pd.read_parquet(path, columns=["date"])
            dates = pd.to_datetime(frame["date"]).dt.normalize()
            observed = int(dates.loc[dates.between(start, end)].nunique())
            ratios.append(observed / expected)
        rows.append(
            {
                "year": year,
                "stock_count": len(ratios),
                "avg_coverage_ratio": pct(float(sum(ratios) / len(ratios))) if ratios else "NA",
            }
        )
    return rows


def sample_rows_for_report(universe: pd.DataFrame) -> list[dict[str, object]]:
    samples = []
    by_bucket = {
        "large": universe.loc[universe["code"].map(code_size_bucket).eq("large_code_lt_100000")].head(1),
        "mid": universe.loc[universe["code"].map(code_size_bucket).eq("mid_code_100000_299999")].head(2),
        "small": universe.loc[universe["code"].map(code_size_bucket).eq("small_code_ge_300000")].head(2),
    }
    for bucket, frame in by_bucket.items():
        for row in frame.itertuples(index=False):
            path = OUTPUT_DIR / f"{row.code}.parquet"
            if not path.exists():
                continue
            data = pd.read_parquet(path).sort_values("date")
            preview = pd.concat([data.head(5), data.tail(5)]).drop_duplicates("date")
            for item in preview.itertuples(index=False):
                samples.append(
                    {
                        "bucket": bucket,
                        "code": row.code,
                        "name": row.name,
                        "date": pd.Timestamp(item.date).date().isoformat(),
                        "foreign_net_buy_shares": getattr(item, "foreign_net_buy_shares", ""),
                        "institutional_net_buy_shares": getattr(item, "institutional_net_buy_shares", ""),
                    }
                )
    return samples


def suspicious_quiet_rows(log: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in log.itertuples(index=False):
        path = OUTPUT_DIR / f"{row.code}.parquet"
        if not path.exists():
            continue
        data = pd.read_parquet(path)
        if data.empty:
            continue
        columns = ["foreign_net_buy_shares", "institutional_net_buy_shares"]
        if all(column in data.columns for column in columns):
            zeros = data[columns].fillna(0).eq(0).all(axis=1)
            if bool(zeros.all()):
                rows.append({"code": row.code, "name": row.name, "rows": int(len(data))})
    return rows


def pattern_rows(log: pd.DataFrame, universe: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    merged = universe.merge(log, on=["code", "name"], how="left")
    target = merged.loc[merged["status"].isin(["partial", "failed"])].copy()
    if target.empty:
        return [], [], []
    target["size_bucket"] = target["code"].map(code_size_bucket)
    target["listing_bucket"] = target["listed_date"].map(listing_bucket)
    size_rows = target.groupby("size_bucket", as_index=False).agg(count=("code", "count")).to_dict("records")
    listing_rows = target.groupby("listing_bucket", as_index=False).agg(count=("code", "count")).to_dict("records")
    sector_rows = (
        target.assign(sector=target["sector"].fillna("unknown"))
        .groupby("sector", as_index=False)
        .agg(count=("code", "count"))
        .sort_values(["count", "sector"], ascending=[False, True])
        .head(5)
        .to_dict("records")
    )
    return size_rows, listing_rows, sector_rows


def write_report(meta: dict[str, Any] | None = None) -> None:
    meta = read_meta(meta)
    universe = load_universe()
    calendar = load_trading_calendar()
    log = load_log()
    total_rows = int(pd.to_numeric(log["rows_collected"], errors="coerce").fillna(0).sum()) if not log.empty else 0
    status_counts = log["status"].value_counts().to_dict() if not log.empty else {}
    coverage = pd.to_numeric(log["coverage_ratio"], errors="coerce")
    coverage_95 = int(coverage.ge(0.95).sum())
    coverage_80_95 = int(coverage.ge(0.80).mul(coverage.lt(0.95)).sum())
    coverage_50_80 = int(coverage.ge(0.50).mul(coverage.lt(0.80)).sum())
    coverage_lt_50 = int(coverage.lt(0.50).sum())
    elapsed_seconds = float(meta.get("elapsed_seconds", 0.0) or 0.0)
    elapsed = f"{int(elapsed_seconds // 3600)}h {int((elapsed_seconds % 3600) // 60)}m"
    year_rows = year_coverage_rows(log, universe, calendar)
    mini_rows, mini_matched, mini_matched_rows = compare_mini_pilot()
    size_rows, listing_rows, sector_rows = pattern_rows(log, universe)
    delisted = universe.loc[universe["delisted_date"].notna(), ["code", "name", "delisted_date"]].merge(
        log[["code", "status", "rows_collected", "coverage_ratio"]],
        on="code",
        how="left",
    )
    sample_rows = sample_rows_for_report(universe)
    quiet_rows = suspicious_quiet_rows(log)

    lines = [
        "# PR-7.A.2.a Step 2 Investor Flow Collection",
        "",
        "## Summary",
        f"- Attempted stocks in log: `{len(log)}` / universe `{len(universe)}`",
        f"- Success: `{status_counts.get('ok', 0)}`",
        f"- Partial: `{status_counts.get('partial', 0)}`",
        f"- Failed: `{status_counts.get('failed', 0)}`",
        f"- Total rows: `{total_rows}`",
        f"- Last run elapsed: `{elapsed}`",
        f"- Last run attempted: `{meta.get('attempted_this_run', 'NA')}`",
        "",
        "## Coverage Distribution",
        markdown_table(coverage_histogram(log), ["bucket", "count"]),
        "",
        "## Coverage Threshold Counts",
        markdown_table(
            [
                {"range": "95%+", "count": coverage_95},
                {"range": "80-95%", "count": coverage_80_95},
                {"range": "50-80%", "count": coverage_50_80},
                {"range": "<50%", "count": coverage_lt_50},
            ],
            ["range", "count"],
        ),
        "",
        "## Yearly Availability",
        markdown_table(year_rows, ["year", "stock_count", "avg_coverage_ratio"]),
        "",
        "## Failed / Partial Pattern Analysis",
        "### Code-size bucket fallback",
        markdown_table(size_rows, ["size_bucket", "count"]) if size_rows else "(none)",
        "",
        "### Listing bucket",
        markdown_table(listing_rows, ["listing_bucket", "count"]) if listing_rows else "(none)",
        "",
        "### Sector top 5",
        markdown_table(sector_rows, ["sector", "count"]) if sector_rows else "(none)",
        "",
        "### Delisted stocks",
        markdown_table(delisted.to_dict("records"), ["code", "name", "delisted_date", "status", "rows_collected", "coverage_ratio"]),
        "",
        "## Mini-pilot 30-stock Recollection Comparison",
        f"- Exact date/value match: `{mini_matched}/30`",
        f"- Matched rows: `{mini_matched_rows}`",
        markdown_table(
            mini_rows,
            ["code", "mini_rows", "full_rows", "mini_dates_in_full", "value_match", "compared_rows", "pattern"],
        ),
        "",
        "## Sample Validation",
        markdown_table(
            sample_rows,
            ["bucket", "code", "name", "date", "foreign_net_buy_shares", "institutional_net_buy_shares"],
        )
        if sample_rows
        else "(no collected sample files available)",
        "",
        "## Suspicious Quiet Stocks",
        markdown_table(quiet_rows, ["code", "name", "rows"]) if quiet_rows else "(none found)",
        "",
        "## Artifacts",
        f"- Parquet directory: `{OUTPUT_DIR.relative_to(ROOT)}`",
        f"- Collection log: `{LOG_PATH.relative_to(ROOT)}`",
        f"- Report: `{REPORT_PATH.relative_to(ROOT)}`",
        "",
        "## Gate",
        "Step 2 collection and validation only. Signal calculation, IC measurement, backtest, and Step 3 are not included.",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text("\n".join(lines) + "\n", REPORT_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect full-universe Naver investor flow parquet files.")
    parser.add_argument("--restart-failed", action="store_true", help="Retry only partial/failed codes in the log.")
    parser.add_argument(
        "--refresh-stale-ok",
        action="store_true",
        help="Re-fetch ok codes whose last_attempt_ts is older than the 24-hour freshness window.",
    )
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--report-only", action="store_true", help="Regenerate the completeness report from existing files.")
    args = parser.parse_args()
    if args.report_only:
        write_report()
        print(REPORT_PATH)
        return
    collect_all(restart_failed=args.restart_failed, max_pages=args.max_pages, refresh_stale_ok=args.refresh_stale_ok)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
