from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXECUTABLE = sys.executable
ACCOUNT_DIR = ROOT / "data/cache/paper_trading/a4_20d_top10"
PRICE_DIR = ROOT / "data/cache/price_market_cap_full"
STATE_PATH = ACCOUNT_DIR / "rebalance_state.json"
LOG_PATH = ACCOUNT_DIR / "after_close_log.csv"
DEFAULT_INTERVAL = 20


def build_data_update_commands() -> list[list[str]]:
    return [
        [PYTHON_EXECUTABLE, "scripts/update_market_dataset_v2.py"],
        [PYTHON_EXECUTABLE, "scripts/update_kospi_benchmark.py"],
        [PYTHON_EXECUTABLE, "scripts/prepare_price_market_cap_full.py"],
    ]


def atomic_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def atomic_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def read_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def latest_price_date() -> pd.Timestamp:
    latest = None
    for path in PRICE_DIR.glob("[0-9][0-9][0-9][0-9][0-9][0-9].parquet"):
        try:
            col = pd.read_parquet(path, columns=["date"])
        except Exception:
            continue
        if col.empty:
            continue
        d = pd.to_datetime(col["date"]).max().normalize()
        latest = d if latest is None else max(latest, d)
    if latest is None:
        raise SystemExit(f"No price data under {PRICE_DIR}")
    return pd.Timestamp(latest)


def trading_dates() -> pd.DatetimeIndex:
    dates = []
    for path in PRICE_DIR.glob("[0-9][0-9][0-9][0-9][0-9][0-9].parquet"):
        try:
            col = pd.read_parquet(path, columns=["date"])
        except Exception:
            continue
        if not col.empty:
            dates.append(pd.to_datetime(col["date"]).dt.normalize())
    if not dates:
        return pd.DatetimeIndex([])
    return pd.DatetimeIndex(pd.concat(dates).drop_duplicates().sort_values())


def run(cmd: list[str], execute: bool, cwd: Path = ROOT) -> dict:
    if not execute:
        return {"cmd": " ".join(cmd), "cwd": str(cwd), "skipped": True, "returncode": 0}
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(cmd)}\nCWD: {cwd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return {"cmd": " ".join(cmd), "cwd": str(cwd), "returncode": proc.returncode, "stdout_tail": proc.stdout[-1000:]}


def ensure_state(interval: int, latest_date: pd.Timestamp) -> dict:
    account = read_json(ACCOUNT_DIR / "account.json", {})
    state = read_json(STATE_PATH, {})
    if not state:
        last = account.get("last_fill_date") or latest_date.strftime("%Y-%m-%d")
        state = {
            "strategy": "A4_60_20d_top10",
            "rebalance_interval_trading_days": interval,
            "last_rebalance_date": last,
            "next_rebalance_due_after_days": interval,
            "created_at": pd.Timestamp.now().isoformat(),
        }
        atomic_json(state, STATE_PATH)
    return state


def days_since(last_date: str, dates: pd.DatetimeIndex, latest_date: pd.Timestamp) -> int:
    last = pd.Timestamp(last_date).normalize()
    return int(((dates > last) & (dates <= latest_date)).sum())


def append_log(row: dict) -> None:
    old = pd.read_csv(LOG_PATH) if LOG_PATH.exists() else pd.DataFrame()
    out = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
    atomic_csv(out, LOG_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(description="After-close operation runner for A4 paper trading.")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Rebalance interval in trading days.")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would happen.")
    parser.add_argument("--skip-data-update", action="store_true", help="Do not run the v2 dataset update or v2 cache prepare step.")
    parser.add_argument("--force-rebalance", action="store_true")
    parser.add_argument("--no-fill", action="store_true", help="Generate rebalance orders but do not paper-fill them.")
    parser.add_argument("--skip-audit", action="store_true", help="Do not run the daily A4 audit harness at the end.")
    args = parser.parse_args()

    execute = not args.dry_run
    steps = []
    if not args.skip_data_update:
        for command in build_data_update_commands():
            steps.append(run(command, execute, cwd=ROOT))

    latest = latest_price_date()
    dates = trading_dates()
    state = ensure_state(args.interval, latest)
    elapsed = days_since(state["last_rebalance_date"], dates, latest)
    due = bool(args.force_rebalance or elapsed >= int(state.get("rebalance_interval_trading_days", args.interval)))

    steps.append(run([PYTHON_EXECUTABLE, "scripts/paper_account_a4.py", "process-delistings", "--asof", latest.strftime("%Y-%m-%d")], execute))
    steps.append(run([PYTHON_EXECUTABLE, "scripts/paper_account_a4.py", "mark"], execute))
    if due:
        steps.append(run([PYTHON_EXECUTABLE, "scripts/paper_quality_gate_a4.py", "--strict"], execute))
        steps.append(run([PYTHON_EXECUTABLE, "scripts/paper_account_a4.py", "rebalance", "--asof", latest.strftime("%Y-%m-%d")], execute))
        if not args.no_fill:
            steps.append(run([PYTHON_EXECUTABLE, "scripts/paper_account_a4.py", "fill", "--asof", latest.strftime("%Y-%m-%d")], execute))
            if execute:
                state["last_rebalance_date"] = latest.strftime("%Y-%m-%d")
                state["last_rebalance_elapsed_trading_days"] = elapsed
                state["updated_at"] = pd.Timestamp.now().isoformat()
                atomic_json(state, STATE_PATH)

    if not args.skip_audit:
        steps.append(run([PYTHON_EXECUTABLE, "scripts/audit_daily_a4.py"], execute))

    summary = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "latest_price_date": latest.strftime("%Y-%m-%d"),
        "last_rebalance_date": state.get("last_rebalance_date"),
        "elapsed_trading_days": elapsed,
        "interval": args.interval,
        "due": due,
        "dry_run": args.dry_run,
        "filled": bool(due and not args.no_fill and execute),
        "steps": steps,
    }
    if execute:
        append_log({k: v for k, v in summary.items() if k != "steps"})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
