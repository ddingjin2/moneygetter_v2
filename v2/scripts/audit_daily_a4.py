from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_OHLCV_PATH = ROOT / "data/processed/market_ohlcv.parquet"
PRICE_DIR = ROOT / "data/cache/price_market_cap_full"
ACCOUNT_DIR = ROOT / "data/cache/paper_trading/a4_20d_top10"
AUDIT_JSON_PATH = ACCOUNT_DIR / "daily_audit.json"
AUDIT_REPORT_PATH = ROOT / "reports/daily_a4_audit.md"
CRON_LOG_PATH = ACCOUNT_DIR / "cron_after_close_latest.log"


def atomic_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition: bool, severity: str, code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": bool(condition),
        "severity": severity,
        "code": code,
        "message": message,
        "details": details or {},
    }


def max_date_from_parquet(path: Path, date_column: str = "date") -> tuple[int, str | None]:
    if not path.exists():
        return 0, None
    frame = pd.read_parquet(path, columns=[date_column])
    if frame.empty:
        return 0, None
    dates = pd.to_datetime(frame[date_column], errors="coerce").dropna()
    return int(len(frame)), dates.max().date().isoformat() if not dates.empty else None


def inspect_v2_price_cache() -> dict[str, Any]:
    files = sorted(path for path in PRICE_DIR.glob("[0-9][0-9][0-9][0-9][0-9][0-9].parquet"))
    latest: pd.Timestamp | None = None
    dates: list[pd.Series] = []
    total_rows = 0
    failed_files: list[str] = []
    for path in files:
        try:
            frame = pd.read_parquet(path, columns=["date"])
        except Exception as exc:  # noqa: BLE001 - audit must report corrupt files
            failed_files.append(f"{path.name}: {type(exc).__name__}: {exc}")
            continue
        total_rows += int(len(frame))
        if frame.empty:
            continue
        normalized = pd.to_datetime(frame["date"], errors="coerce").dropna().dt.normalize()
        if normalized.empty:
            continue
        dates.append(normalized)
        max_date = normalized.max()
        latest = max_date if latest is None else max(latest, max_date)
    trading_dates = pd.DatetimeIndex(pd.concat(dates).drop_duplicates().sort_values()) if dates else pd.DatetimeIndex([])
    return {
        "file_count": len(files),
        "total_rows": total_rows,
        "latest_date": latest.date().isoformat() if latest is not None else None,
        "trading_date_count": int(len(trading_dates)),
        "failed_files": failed_files[:20],
    }


def load_latest_price_map(asof: pd.Timestamp | None = None) -> tuple[str | None, pd.DataFrame]:
    frames = []
    for path in PRICE_DIR.glob("[0-9][0-9][0-9][0-9][0-9][0-9].parquet"):
        try:
            frame = pd.read_parquet(path, columns=["date", "symbol", "name", "close", "volume"])
        except Exception:
            continue
        frame["code"] = path.stem
        frames.append(frame)
    if not frames:
        return None, pd.DataFrame(columns=["code", "name", "close", "volume"])
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.normalize()
    panel["close"] = pd.to_numeric(panel["close"], errors="coerce")
    panel["volume"] = pd.to_numeric(panel["volume"], errors="coerce")
    panel = panel.dropna(subset=["date"])
    if asof is not None:
        panel = panel.loc[panel["date"].le(asof)]
    if panel.empty:
        return None, pd.DataFrame(columns=["code", "name", "close", "volume"])
    actual = panel["date"].max()
    latest = panel.loc[panel["date"].eq(actual)].drop_duplicates("code").set_index("code")
    return pd.Timestamp(actual).date().isoformat(), latest[["name", "close", "volume"]]


def inspect_account(latest_prices: pd.DataFrame, latest_price_date: str | None) -> dict[str, Any]:
    account = read_json(ACCOUNT_DIR / "account.json")
    state = read_json(ACCOUNT_DIR / "rebalance_state.json")
    positions_path = ACCOUNT_DIR / "positions.csv"
    trades_path = ACCOUNT_DIR / "trades.csv"
    equity_path = ACCOUNT_DIR / "equity_curve.csv"
    positions = pd.read_csv(positions_path, dtype={"code": str}) if positions_path.exists() else pd.DataFrame()
    trades = pd.read_csv(trades_path, dtype={"code": str}) if trades_path.exists() else pd.DataFrame()
    equity = pd.read_csv(equity_path) if equity_path.exists() else pd.DataFrame()

    if not positions.empty:
        positions["code"] = positions["code"].astype(str).str.zfill(6)
        positions["shares"] = pd.to_numeric(positions["shares"], errors="coerce").fillna(0).astype(int)
        positions["avg_cost"] = pd.to_numeric(positions["avg_cost"], errors="coerce")
    if not trades.empty:
        trades["code"] = trades["code"].astype(str).str.zfill(6)
        for column in ["shares", "price", "gross", "fee", "cash_flow"]:
            trades[column] = pd.to_numeric(trades[column], errors="coerce")

    cash = float(account.get("cash", math.nan))
    initial_capital = float(account.get("initial_capital", math.nan))
    market_value = 0.0
    missing_price_codes: list[str] = []
    if not positions.empty and not latest_prices.empty:
        merged = positions.merge(latest_prices.reset_index()[["code", "close"]], on="code", how="left")
        missing_price_codes = sorted(merged.loc[merged["close"].isna(), "code"].astype(str).tolist())
        merged["close"] = pd.to_numeric(merged["close"], errors="coerce").fillna(0.0)
        market_value = float((merged["shares"] * merged["close"]).sum())
    equity_recomputed = cash + market_value

    latest_equity = equity.tail(1).iloc[0].to_dict() if not equity.empty else {}
    latest_equity_value = float(latest_equity.get("equity", math.nan)) if latest_equity else math.nan
    equity_diff = equity_recomputed - latest_equity_value if not math.isnan(latest_equity_value) else math.nan

    trade_cash_flow = float(trades["cash_flow"].sum()) if not trades.empty and "cash_flow" in trades.columns else 0.0
    expected_cash = initial_capital + trade_cash_flow if not math.isnan(initial_capital) else math.nan
    cash_diff = cash - expected_cash if not math.isnan(expected_cash) else math.nan

    return {
        "account": account,
        "rebalance_state": state,
        "positions_count": int(len(positions)),
        "trades_count": int(len(trades)),
        "latest_equity_row": latest_equity,
        "latest_price_date": latest_price_date,
        "cash": cash,
        "initial_capital": initial_capital,
        "market_value_recomputed": market_value,
        "equity_recomputed": equity_recomputed,
        "equity_diff_vs_curve": equity_diff,
        "expected_cash_from_trades": expected_cash,
        "cash_diff_vs_trades": cash_diff,
        "missing_price_codes": missing_price_codes[:50],
    }


def infer_rebalance_due(state: dict[str, Any], latest_price_date: str | None) -> dict[str, Any]:
    if not latest_price_date or not state.get("last_rebalance_date"):
        return {"elapsed_trading_days": None, "due": None}
    dates = []
    for path in PRICE_DIR.glob("[0-9][0-9][0-9][0-9][0-9][0-9].parquet"):
        try:
            col = pd.read_parquet(path, columns=["date"])
        except Exception:
            continue
        if not col.empty:
            dates.append(pd.to_datetime(col["date"], errors="coerce").dropna().dt.normalize())
    if not dates:
        return {"elapsed_trading_days": None, "due": None}
    calendar = pd.DatetimeIndex(pd.concat(dates).drop_duplicates().sort_values())
    last = pd.Timestamp(state["last_rebalance_date"]).normalize()
    latest = pd.Timestamp(latest_price_date).normalize()
    elapsed = int(((calendar > last) & (calendar <= latest)).sum())
    interval = int(state.get("rebalance_interval_trading_days", 20))
    return {"elapsed_trading_days": elapsed, "interval": interval, "due": bool(elapsed >= interval)}


def inspect_cron_log() -> dict[str, Any]:
    if not CRON_LOG_PATH.exists():
        return {"exists": False, "has_error_words": False, "tail": ""}
    text = CRON_LOG_PATH.read_text(encoding="utf-8", errors="replace")
    tail = text[-4000:]
    lowered = tail.lower()
    error_words = [word for word in ["traceback", "error", "failed", "exception", "command failed"] if word in lowered]
    return {"exists": True, "has_error_words": bool(error_words), "error_words": error_words, "tail": tail[-1200:]}


def build_audit(asof: str | None = None) -> dict[str, Any]:
    generated_at = pd.Timestamp.now(tz="Asia/Seoul").isoformat()
    checks: list[dict[str, Any]] = []

    processed_rows, processed_max_date = max_date_from_parquet(PROCESSED_OHLCV_PATH)
    v2_cache = inspect_v2_price_cache()
    asof_ts = pd.Timestamp(asof).normalize() if asof else None
    latest_price_date, latest_prices = load_latest_price_map(asof_ts)
    account = inspect_account(latest_prices, latest_price_date)
    rebalance = infer_rebalance_due(account["rebalance_state"], latest_price_date)
    cron_log = inspect_cron_log()

    checks.append(check(PROCESSED_OHLCV_PATH.exists(), "error", "processed_ohlcv_exists", "v2 processed market_ohlcv parquet exists", {"path": str(PROCESSED_OHLCV_PATH)}))
    checks.append(check(processed_rows > 0, "error", "processed_ohlcv_nonempty", "v2 processed market_ohlcv has rows", {"rows": processed_rows}))
    checks.append(check(v2_cache["file_count"] >= 700, "error", "v2_cache_file_count", "v2 per-symbol price cache has expected file count", {"file_count": v2_cache["file_count"]}))
    checks.append(check(not v2_cache["failed_files"], "error", "v2_cache_readable", "v2 price cache files are readable", {"failed_files": v2_cache["failed_files"]}))
    checks.append(check(processed_max_date == latest_price_date, "warning", "processed_cache_latest_date_match", "v2 processed and per-symbol cache latest dates match", {"processed_max_date": processed_max_date, "v2_latest_date": latest_price_date}))
    checks.append(check(account["positions_count"] > 0, "error", "positions_nonempty", "paper account has open positions", {"positions_count": account["positions_count"]}))
    checks.append(check(abs(float(account["cash_diff_vs_trades"])) < 0.01, "error", "cash_reconciles", "account cash reconciles with trade cash flows", {"cash_diff": account["cash_diff_vs_trades"]}))
    checks.append(check(abs(float(account["equity_diff_vs_curve"])) < 1.0, "warning", "equity_curve_reconciles", "latest equity curve row reconciles with current prices", {"equity_diff": account["equity_diff_vs_curve"]}))
    checks.append(check(not account["missing_price_codes"], "error", "all_positions_priced", "all open positions have latest prices", {"missing_price_codes": account["missing_price_codes"]}))
    checks.append(check(cron_log["exists"], "warning", "cron_log_exists", "latest after-close cron log exists", {"path": str(CRON_LOG_PATH)}))
    checks.append(check(not cron_log.get("has_error_words", False), "warning", "cron_log_clean", "latest cron log tail has no obvious error words", {"error_words": cron_log.get("error_words", [])}))

    failed_errors = [c for c in checks if not c["ok"] and c["severity"] == "error"]
    failed_warnings = [c for c in checks if not c["ok"] and c["severity"] == "warning"]
    status = "pass" if not failed_errors and not failed_warnings else "warning" if not failed_errors else "fail"

    return {
        "generated_at": generated_at,
        "status": status,
        "summary": {
            "errors": len(failed_errors),
            "warnings": len(failed_warnings),
            "checks": len(checks),
            "processed_max_date": processed_max_date,
            "v2_latest_date": latest_price_date,
            "positions": account["positions_count"],
            "equity_recomputed": account["equity_recomputed"],
            "rebalance_due": rebalance.get("due"),
            "elapsed_trading_days": rebalance.get("elapsed_trading_days"),
        },
        "checks": checks,
        "processed_ohlcv": {"path": str(PROCESSED_OHLCV_PATH), "rows": processed_rows, "max_date": processed_max_date},
        "v2_cache": v2_cache,
        "account": account,
        "rebalance": rebalance,
        "cron_log": cron_log,
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Daily A4 audit",
        "",
        f"- generated_at: {audit['generated_at']}",
        f"- status: **{audit['status']}**",
        f"- processed_max_date: {audit['summary']['processed_max_date']}",
        f"- v2_latest_date: {audit['summary']['v2_latest_date']}",
        f"- positions: {audit['summary']['positions']}",
        f"- equity_recomputed: {audit['summary']['equity_recomputed']:.3f}",
        f"- rebalance_due: {audit['summary']['rebalance_due']}",
        f"- elapsed_trading_days: {audit['summary']['elapsed_trading_days']}",
        "",
        "## Checks",
        "",
        "| status | severity | code | message |",
        "| --- | --- | --- | --- |",
    ]
    for item in audit["checks"]:
        mark = "OK" if item["ok"] else "FAIL"
        lines.append(f"| {mark} | {item['severity']} | `{item['code']}` | {item['message']} |")
    lines.extend([
        "",
        "## Key reconciliation",
        "",
        f"- cash: {audit['account']['cash']:.3f}",
        f"- expected_cash_from_trades: {audit['account']['expected_cash_from_trades']:.3f}",
        f"- cash_diff_vs_trades: {audit['account']['cash_diff_vs_trades']:.6f}",
        f"- market_value_recomputed: {audit['account']['market_value_recomputed']:.3f}",
        f"- equity_diff_vs_curve: {audit['account']['equity_diff_vs_curve']:.6f}",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily audit harness for A4 paper trading.")
    parser.add_argument("--asof", default=None, help="Optional price as-of date, e.g. 2026-04-17.")
    parser.add_argument("--json", default=str(AUDIT_JSON_PATH), help="Output JSON path.")
    parser.add_argument("--report", default=str(AUDIT_REPORT_PATH), help="Output markdown report path.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings as well as errors.")
    args = parser.parse_args()

    audit = build_audit(args.asof)
    atomic_text(json.dumps(audit, ensure_ascii=False, indent=2, default=str) + "\n", Path(args.json))
    atomic_text(render_markdown(audit) + "\n", Path(args.report))
    print(json.dumps({"status": audit["status"], "summary": audit["summary"], "json": args.json, "report": args.report}, ensure_ascii=False, indent=2))

    if audit["status"] == "fail" or (args.strict and audit["status"] != "pass"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
