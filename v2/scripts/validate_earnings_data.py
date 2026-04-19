from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.earnings import (  # noqa: E402
    DEFAULT_END_DATE,
    DEFAULT_V1_OHLCV_PATH,
    EARNINGS_EVENTS_PATH,
    MARKET_CLOSE,
    load_kospi_universe,
    validate_earnings_point_in_time,
)


REPORT_PATH = Path("v2/reports/earnings_data_quality.md")


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(empty)"
    rendered = frame.copy()
    for column in rendered.columns:
        if pd.api.types.is_float_dtype(rendered[column]):
            rendered[column] = rendered[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    lines = ["| " + " | ".join(rendered.columns) + " |"]
    lines.append("| " + " | ".join(["---"] * len(rendered.columns)) + " |")
    for _, row in rendered.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in rendered.columns) + " |")
    return "\n".join(lines)


def _missing_by_year(events: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    frame = events.copy()
    frame["year"] = pd.to_datetime(frame["rcept_dt"]).dt.year
    rows: list[dict[str, object]] = []
    for year, group in frame.groupby("year", sort=True):
        row: dict[str, object] = {"year": int(year), "records": int(len(group))}
        for column in columns:
            row[f"{column}_missing_rate"] = float(group[column].isna().mean()) if column in group else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _annual_counts(events: pd.DataFrame) -> pd.DataFrame:
    frame = events.copy()
    frame["year"] = pd.to_datetime(frame["rcept_dt"]).dt.year
    counts = frame.groupby(["stock_code", "year"], sort=False).size().reset_index(name="filings")
    summary = counts.groupby("year")["filings"].agg(["count", "mean", "median", "min", "max"]).reset_index()
    return summary.rename(columns={"count": "covered_symbols"})


def _receipt_time_distribution(events: pd.DataFrame) -> pd.DataFrame:
    raw_times = pd.to_datetime(events["rcept_time"], format="%H:%M", errors="coerce")
    times = raw_times.fillna(pd.Timestamp(f"2000-01-01 {MARKET_CLOSE}"))
    after_close = times.dt.time >= pd.Timestamp(f"2000-01-01 {MARKET_CLOSE}").time()
    return pd.DataFrame(
        [
            {"bucket": "before_15_30", "records": int((~after_close).sum()), "share": float((~after_close).mean())},
            {"bucket": "after_or_at_15_30", "records": int(after_close.sum()), "share": float(after_close.mean())},
            {"bucket": "missing_time", "records": int(raw_times.isna().sum()), "share": float(raw_times.isna().mean())},
        ]
    )


def _coverage(events: pd.DataFrame, ohlcv_path: Path) -> pd.DataFrame:
    kospi = load_kospi_universe(ohlcv_path=ohlcv_path, reference_date=DEFAULT_END_DATE)
    events_2026 = events.loc[pd.to_datetime(events["rcept_dt"]).dt.year.eq(2026)]
    covered = events_2026["stock_code"].dropna().astype(str).str.zfill(6).nunique()
    expected = kospi["stock_code"].nunique()
    return pd.DataFrame(
        [
            {
                "reference_year": 2026,
                "kospi_symbols_expected": int(expected),
                "covered_symbols": int(covered),
                "coverage": float(covered / expected) if expected else math.nan,
                "passes_70pct_gate": bool(covered / expected >= 0.70) if expected else False,
            }
        ]
    )


def build_quality_report(events: pd.DataFrame, *, ohlcv_path: Path) -> str:
    required_value_columns = ["revenue", "operating_income", "net_income", "total_assets", "total_equity"]
    annual_counts = _annual_counts(events)
    missing = _missing_by_year(events, required_value_columns)
    time_dist = _receipt_time_distribution(events)
    coverage = _coverage(events, ohlcv_path)
    violations = validate_earnings_point_in_time(events)

    violation_rows = pd.DataFrame(
        [
            {"violation_type": kind, "count": len(values), "examples": ", ".join(values[:5])}
            for kind, values in violations.items()
        ]
    )
    lines = [
        "# Earnings Data Quality",
        "",
        f"Records: {len(events)}",
        f"Date range: {pd.to_datetime(events['rcept_dt']).min().date()} to {pd.to_datetime(events['rcept_dt']).max().date()}",
        "",
        "## KOSPI Coverage",
        _markdown_table(coverage),
        "",
        "## Annual Filing Counts",
        _markdown_table(annual_counts),
        "",
        "## Missing Rates By Receipt Year",
        _markdown_table(missing),
        "",
        "## Receipt Time Distribution",
        _markdown_table(time_dist),
        "",
        "## Leakage Precheck",
        _markdown_table(violation_rows),
    ]
    return "\n".join(lines) + "\n"


def validate_dataset(
    *,
    earnings_path: Path = EARNINGS_EVENTS_PATH,
    output_path: Path = REPORT_PATH,
    ohlcv_path: Path = DEFAULT_V1_OHLCV_PATH,
) -> str:
    if not earnings_path.exists():
        raise FileNotFoundError(earnings_path)
    events = pd.read_parquet(earnings_path)
    report = build_quality_report(events, ohlcv_path=ohlcv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return report


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate MoneyGetter v2 earnings event data.")
    parser.add_argument("--earnings-path", default=str(EARNINGS_EVENTS_PATH))
    parser.add_argument("--ohlcv-path", default=str(DEFAULT_V1_OHLCV_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    report = validate_dataset(
        earnings_path=Path(args.earnings_path),
        ohlcv_path=Path(args.ohlcv_path),
        output_path=Path(args.output),
    )
    print(report)


if __name__ == "__main__":
    main()
