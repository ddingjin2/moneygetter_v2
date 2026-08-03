from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import argparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.us_market_dataset import US_OHLCV_PATH, US_UNIVERSE_PATH  # noqa: E402
from v2.data.us_research_paths import us_research_paths  # noqa: E402
from v2.scripts.us_prepare_backtest_inputs import BENCHMARK_PATH, PRICE_DIR, RETURNS_PATH, STATUS_PATH  # noqa: E402

V2_ROOT = Path(__file__).resolve().parents[1]
SIGNALS_DIR = V2_ROOT / "data/cache/us/signals_batch"
IC_SUMMARY = V2_ROOT / "data/cache/us/ic/ic_batch_summary.parquet"
BACKTEST_METRICS = V2_ROOT / "data/cache/us/backtest_batch/all_metrics.parquet"
REPORT_PATH = V2_ROOT / "reports/us/us_research_audit.md"
JSON_PATH = V2_ROOT / "data/cache/us/us_research_audit.json"


def check(ok: bool, severity: str, code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ok": bool(ok), "severity": severity, "code": code, "message": message, "details": details or {}}


def max_date(path: Path) -> str | None:
    if not path.exists():
        return None
    frame = pd.read_parquet(path, columns=["date"])
    if frame.empty:
        return None
    return str(pd.to_datetime(frame["date"]).max().date())


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit US research data caches.")
    parser.add_argument("--universe-key", default="sp500")
    args = parser.parse_args()
    paths = us_research_paths(args.universe_key)
    checks = []
    checks.append(check(paths.ohlcv_path.exists(), "error", "processed_exists", "US processed OHLCV exists", {"path": str(paths.ohlcv_path)}))
    checks.append(check(paths.universe_path.exists(), "error", "universe_exists", "US universe exists", {"path": str(paths.universe_path)}))
    processed_date = max_date(paths.ohlcv_path)
    returns_date = max_date(paths.returns_path)
    status_date = max_date(paths.status_path)
    benchmark_date = max_date(paths.benchmark_path)
    price_files = sorted(path for path in paths.price_dir.glob("*.parquet") if not path.name.startswith("_"))
    checks.append(check(bool(price_files), "error", "price_cache_exists", "US per-symbol price cache exists", {"file_count": len(price_files)}))
    checks.append(check(processed_date == returns_date == status_date, "error", "input_dates_match", "processed, returns, and status latest dates match", {"processed": processed_date, "returns": returns_date, "status": status_date}))
    checks.append(check(benchmark_date == processed_date, "warning", "benchmark_date_matches", "benchmark latest date matches processed latest date", {"benchmark": benchmark_date, "processed": processed_date}))
    checks.append(check(any(paths.signals_dir.glob("*_cs_zscore.parquet")), "error", "signals_exist", "US signal z-score files exist"))
    checks.append(check(paths.ic_summary_path.exists(), "error", "ic_exists", "US IC summary exists", {"path": str(paths.ic_summary_path)}))
    checks.append(check(paths.metrics_path.exists(), "error", "backtest_exists", "US backtest metrics exist", {"path": str(paths.metrics_path)}))
    universe = pd.read_parquet(paths.universe_path) if paths.universe_path.exists() else pd.DataFrame()
    checks.append(check(False, "warning", "survivorship_bias", f"Current {paths.universe_key} universe is survivorship-biased and is not production-grade point-in-time membership", {"symbols": int(len(universe))}))
    ohlcv = pd.read_parquet(paths.ohlcv_path, columns=["adjustment_quality"]) if paths.ohlcv_path.exists() else pd.DataFrame()
    raw_only = int(ohlcv["adjustment_quality"].eq("raw_open_only").sum()) if not ohlcv.empty else 0
    checks.append(check(raw_only == 0, "warning", "adjusted_open_available", "Adjusted open is available for all rows", {"raw_open_only_rows": raw_only}))
    errors = sum(1 for item in checks if not item["ok"] and item["severity"] == "error")
    warnings = sum(1 for item in checks if not item["ok"] and item["severity"] == "warning")
    status = "error" if errors else "warning" if warnings else "ok"
    summary = {
        "universe_key": paths.universe_key,
        "errors": errors,
        "warnings": warnings,
        "processed_max_date": processed_date,
        "returns_max_date": returns_date,
        "benchmark_max_date": benchmark_date,
        "price_files": len(price_files),
        "universe_symbols": int(len(universe)),
    }
    payload = {"status": status, "summary": summary, "checks": checks}
    paths.audit_json_path.parent.mkdir(parents=True, exist_ok=True)
    paths.audit_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths.audit_report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# US Research Data Audit",
        "",
        f"- Status: `{status}`",
        f"- Summary: `{summary}`",
        "",
        "## Checks",
        pd.DataFrame(checks).to_markdown(index=False),
        "",
    ]
    paths.audit_report_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
