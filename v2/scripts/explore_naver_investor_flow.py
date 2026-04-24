from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REPORT_PATH = Path("v2/reports/pr7_a_1_data_exploration.md")
PILOT_OUTPUT_PATH = Path("v2/data/cache/investor_flow_pilot/005930.parquet")
NAVER_URL = "https://finance.naver.com/item/frgn.naver"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass(frozen=True)
class FetchResult:
    data: pd.DataFrame
    pages_fetched: int
    source: str
    errors: list[str]


def _flatten_column(column: object) -> str:
    if isinstance(column, tuple):
        parts = [str(part).strip() for part in column if str(part).strip() and not str(part).startswith("Unnamed")]
        return "_".join(parts)
    return str(column).strip()


def _clean_number(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "nan", "None"}:
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


def _normalize_table(table: pd.DataFrame) -> pd.DataFrame:
    frame = table.copy()
    frame.columns = [_flatten_column(column) for column in frame.columns]
    column_map = {
        "날짜_날짜": "date",
        "날짜": "date",
        "종가_종가": "close",
        "종가": "close",
        "전일비_전일비": "price_change",
        "전일비": "price_change",
        "등락률_등락률": "change_rate",
        "등락률": "change_rate",
        "거래량_거래량": "volume",
        "거래량": "volume",
        "기관_순매매량": "institutional_net_buy_shares",
        "외국인_순매매량": "foreign_net_buy_shares",
        "외국인_보유주수": "foreign_holding_shares",
        "외국인_보유율": "foreign_holding_ratio",
    }
    frame = frame.rename(columns={column: column_map.get(column, column) for column in frame.columns})
    if "date" not in frame.columns:
        return pd.DataFrame()

    frame = frame.loc[frame["date"].notna()].copy()
    frame["date"] = pd.to_datetime(frame["date"], format="%Y.%m.%d", errors="coerce")
    frame = frame.loc[frame["date"].notna()].copy()
    if frame.empty:
        return frame

    numeric_columns = [
        "close",
        "volume",
        "institutional_net_buy_shares",
        "foreign_net_buy_shares",
        "foreign_holding_shares",
        "foreign_holding_ratio",
    ]
    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = frame[column].map(_clean_number)

    for column in ["close", "volume", "foreign_holding_shares"]:
        if column in frame.columns:
            frame[column] = frame[column].astype("Int64")
    for column in ["institutional_net_buy_shares", "foreign_net_buy_shares"]:
        if column in frame.columns:
            frame[column] = frame[column].astype("Int64")

    if "foreign_holding_ratio" in frame.columns:
        frame["foreign_holding_ratio"] = pd.to_numeric(frame["foreign_holding_ratio"], errors="coerce") / 100.0

    keep_columns = [
        "date",
        "close",
        "volume",
        "foreign_net_buy_shares",
        "institutional_net_buy_shares",
        "foreign_holding_shares",
        "foreign_holding_ratio",
    ]
    existing = [column for column in keep_columns if column in frame.columns]
    return frame[existing].sort_values("date").reset_index(drop=True)


def _read_naver_page(stock_code: str, page: int, timeout: int = 30) -> pd.DataFrame:
    response = requests.get(
        NAVER_URL,
        params={"code": stock_code, "page": page},
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    html = response.content.decode("euc-kr", errors="replace")
    tables = pd.read_html(StringIO(html), flavor="lxml")
    candidates = []
    for table in tables:
        flat_columns = [_flatten_column(column) for column in table.columns]
        if any(column in flat_columns for column in ["기관_순매매량", "외국인_순매매량"]):
            candidates.append(table)
    if not candidates:
        raise ValueError(f"No investor-flow table found on page {page}")
    return _normalize_table(candidates[0])


def fetch_naver_investor_flow(
    stock_code: str,
    *,
    start_date: str,
    end_date: str,
    request_delay_seconds: float = 1.0,
    max_pages: int = 500,
) -> FetchResult:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    pages_fetched = 0

    for page in range(1, max_pages + 1):
        try:
            frame = _read_naver_page(stock_code, page)
        except Exception as exc:  # noqa: BLE001 - report full pilot failure context
            errors.append(f"page={page}: {type(exc).__name__}: {exc}")
            break

        if frame.empty:
            break
        pages_fetched += 1
        frames.append(frame)
        oldest = frame["date"].min()
        if oldest < start:
            break
        time.sleep(request_delay_seconds)

    if not frames:
        return FetchResult(pd.DataFrame(), pages_fetched, "naver", errors)

    data = pd.concat(frames, ignore_index=True)
    data = data.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    data = data.loc[data["date"].between(start, end)].copy().reset_index(drop=True)
    return FetchResult(data, pages_fetched, "naver", errors)


def _finance_data_reader_fallback(stock_code: str, start_date: str, end_date: str) -> dict[str, Any]:
    try:
        import FinanceDataReader as fdr  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - diagnostic report should capture import failure
        return {
            "attempted": True,
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "note": "FinanceDataReader is not installed or not importable.",
        }

    try:
        data = fdr.DataReader(stock_code, start_date, end_date)
    except Exception as exc:  # noqa: BLE001 - diagnostic report should capture fetch failure
        return {
            "attempted": True,
            "available": True,
            "error": f"{type(exc).__name__}: {exc}",
            "note": "FinanceDataReader fetch failed.",
        }
    return {
        "attempted": True,
        "available": True,
        "rows": int(len(data)),
        "columns": list(data.columns),
        "note": "FinanceDataReader returned price data, not investor-flow net-buy columns.",
    }


def _coverage_summary(data: pd.DataFrame, start_date: str, end_date: str) -> dict[str, Any]:
    if data.empty:
        return {}
    business_days = pd.date_range(start_date, end_date, freq="B")
    row_dates = pd.DatetimeIndex(data["date"])
    return {
        "rows": int(len(data)),
        "date_min": data["date"].min().date().isoformat(),
        "date_max": data["date"].max().date().isoformat(),
        "business_day_count": int(len(business_days)),
        "business_day_row_ratio": float(len(data) / len(business_days)) if len(business_days) else math.nan,
        "missing_vs_business_days": int(len(set(business_days.date) - set(row_dates.date))),
    }


def _dtype_rows(data: pd.DataFrame) -> list[dict[str, str]]:
    return [{"column": column, "dtype": str(dtype)} for column, dtype in data.dtypes.items()]


def _markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def _write_report(
    *,
    result: FetchResult,
    fallback: dict[str, Any],
    start_date: str,
    end_date: str,
    output_path: Path,
) -> None:
    data = result.data
    required_columns = ["foreign_net_buy_shares", "institutional_net_buy_shares"]
    required_presence = {column: column in data.columns for column in required_columns}
    required_non_null = {
        column: float(data[column].notna().mean()) if column in data.columns and not data.empty else math.nan
        for column in required_columns
    }
    coverage = _coverage_summary(data, start_date, end_date)
    personal_possible = False
    personal_note = (
        "Naver frgn.naver exposes institutional and foreign net buy shares, but no direct total net buy "
        "or individual net buy column. Individual net buy cannot be derived from volume alone."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not data.empty:
        PILOT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(PILOT_OUTPUT_PATH, index=False)

    lines = [
        "# PR-7.A.1 Investor Flow Data Exploration",
        "",
        "## Step 0. Scope",
        "- Diagnostic/data-exploration only.",
        "- Stock: Samsung Electronics (`005930`).",
        f"- Requested period: `{start_date}` to `{end_date}`.",
        "- Source priority: Naver Finance first; FinanceDataReader fallback only if Naver fails.",
        "- pykrx was not retried.",
        "",
        "## Step 1. Naver Pilot Result",
        f"- Source used: `{result.source}`.",
        f"- Pages fetched: `{result.pages_fetched}`.",
        f"- Rows collected in requested period: `{len(data)}`.",
        f"- Pilot parquet: `{PILOT_OUTPUT_PATH}`.",
        f"- Date range: `{coverage.get('date_min', '')}` to `{coverage.get('date_max', '')}`.",
        f"- Business-day row ratio: `{coverage.get('business_day_row_ratio', '')}`.",
        f"- Missing vs simple Mon-Fri business days: `{coverage.get('missing_vs_business_days', '')}`.",
        "",
        "## Step 2. Schema",
        _markdown_table(_dtype_rows(data), ["column", "dtype"]) if not data.empty else "(empty)",
        "",
        "## Step 3. Required Column Completeness",
        _markdown_table(
            [
                {
                    "column": column,
                    "exists": required_presence[column],
                    "non_null_ratio": "" if math.isnan(required_non_null[column]) else f"{required_non_null[column]:.4f}",
                }
                for column in required_columns
            ],
            ["column", "exists", "non_null_ratio"],
        ),
        "",
        "## Step 4. Individual Net Buy Feasibility",
        f"- Individual net buy calculable: `{personal_possible}`.",
        f"- Note: {personal_note}",
        "",
        "## Step 5. Fallback Check",
        "```json",
        json.dumps(fallback, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Step 6. Errors",
        "```text",
        "\n".join(result.errors) if result.errors else "(none)",
        "```",
        "",
        "## Step 7. User Gate",
        "Step 1 pilot collection is complete. Do not proceed to full-universe collection until user approval.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore Naver investor-flow data for one pilot stock.")
    parser.add_argument("--stock-code", default="005930")
    parser.add_argument("--start-date", default="2020-01-01")
    parser.add_argument("--end-date", default="2026-04-17")
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--max-pages", type=int, default=500)
    args = parser.parse_args()

    result = fetch_naver_investor_flow(
        args.stock_code,
        start_date=args.start_date,
        end_date=args.end_date,
        request_delay_seconds=args.delay_seconds,
        max_pages=args.max_pages,
    )
    fallback = (
        {"attempted": False, "note": "Naver pilot succeeded."}
        if not result.data.empty and not result.errors
        else _finance_data_reader_fallback(args.stock_code, args.start_date, args.end_date)
    )
    _write_report(
        result=result,
        fallback=fallback,
        start_date=args.start_date,
        end_date=args.end_date,
        output_path=REPORT_PATH,
    )
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
