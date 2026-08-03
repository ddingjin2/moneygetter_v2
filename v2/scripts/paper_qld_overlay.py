"""QLD 전술 오버레이 페이퍼 트레이딩.

룰 (qld_mdd_reduction_strategies.md 검증 룰 그대로):
  전일 QQQ 종가 > 175일 SMA 이면 risk-on, 아니면 현금.
  risk-on 시 QLD 비중 = min(1, 45% / QLD 20일 실현변동성).
  신호 t 종가 -> t+1 시가 체결 (pending order 방식). 현금은 ^IRX 일할 이자.

비용: 토스증권 보수 가정 20bp/체결. 정수 주수만.

사용:
  python scripts/paper_qld_overlay.py init [--capital 10000]
  python scripts/paper_qld_overlay.py run     # 데이터 갱신 + 대기주문 체결 + 마크 + 신호 갱신
  python scripts/paper_qld_overlay.py status
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/cache/paper_trading/qld_overlay"
PRICES_PATH = DIR / "prices.parquet"
STATE_PATH = DIR / "state.json"
EQUITY_PATH = DIR / "equity_curve.csv"
TRADES_PATH = DIR / "trades.csv"

FEE = 0.002  # 토스 가정 20bp per trade
MA_WINDOW = 175
VOL_WINDOW = 20
VOL_TARGET = 0.45
MIN_TRADE_FRAC = 0.01  # equity 대비 1% 미만 조정은 스킵


def atomic_write(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    atomic_write(json.dumps(state, indent=2), STATE_PATH)


def update_prices() -> pd.DataFrame:
    raw = yf.download(["QLD", "QQQ", "^IRX"], start="2019-01-01", auto_adjust=True, progress=False)
    df = pd.DataFrame(
        {
            "qld_open": raw["Open"]["QLD"],
            "qld_close": raw["Close"]["QLD"],
            "qqq_close": raw["Close"]["QQQ"],
            "irx": raw["Close"]["^IRX"] / 100.0,
        }
    ).dropna(subset=["qld_close", "qqq_close"])
    df.index.name = "date"
    if len(df) < MA_WINDOW + 1:
        raise SystemExit(f"price history too short: {len(df)} rows")
    DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PRICES_PATH)
    return df


def target_weight(df: pd.DataFrame) -> tuple[float, dict]:
    last = df.iloc[-1]
    ma = df["qqq_close"].rolling(MA_WINDOW).mean().iloc[-1]
    vol = df["qld_close"].pct_change().tail(VOL_WINDOW).std(ddof=0) * math.sqrt(252)
    risk_on = bool(last["qqq_close"] > ma)
    weight = min(1.0, VOL_TARGET / vol) if risk_on and vol > 0 else 0.0
    detail = {"qqq_close": float(last["qqq_close"]), "ma175": float(ma), "risk_on": risk_on, "vol20_ann": float(vol)}
    return (0.0 if not risk_on else float(weight)), detail


def append_csv(row: dict, path: Path) -> None:
    old = pd.read_csv(path) if path.exists() else pd.DataFrame()
    out = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.tmp{path.suffix}")
    out.to_csv(tmp, index=False)
    os.replace(tmp, path)


def cmd_init(capital: float) -> None:
    if STATE_PATH.exists():
        raise SystemExit(f"already initialized: {STATE_PATH}")
    save_state(
        {
            "strategy": "QLD_MA175_vol20_target45_toss20bp",
            "initial_capital_usd": capital,
            "cash": capital,
            "shares": 0,
            "pending": None,
            "created_at": pd.Timestamp.now().isoformat(),
        }
    )
    print(json.dumps(load_state(), indent=2))


def cmd_run() -> None:
    state = load_state()
    df = update_prices()
    today = df.index[-1]
    out: dict = {"date": str(today.date())}
    if EQUITY_PATH.exists():
        last_marked = pd.read_csv(EQUITY_PATH)["date"].iloc[-1]
        if last_marked == str(today.date()):
            print(json.dumps({**out, "skipped": "already_ran_for_latest_price_date"}))
            return

    # 1) 대기 주문 체결: 신호일 이후 첫 거래일 시가 (paused면 신호만 기록, 체결 안 함)
    pending = None if state.get("paused") else state.get("pending")
    if state.get("paused"):
        state["pending"] = None
        out["paused"] = True
    if pending and pd.Timestamp(pending["signal_date"]) < today:
        px = float(df.iloc[-1]["qld_open"])
        equity = state["cash"] + state["shares"] * px
        target_shares = int(equity * pending["target_weight"] / px)
        delta = target_shares - state["shares"]
        if abs(delta) * px >= equity * MIN_TRADE_FRAC:
            fee = abs(delta) * px * FEE
            state["cash"] -= delta * px + fee
            state["shares"] = target_shares
            append_csv(
                {"date": str(today.date()), "side": "BUY" if delta > 0 else "SELL", "shares": delta,
                 "price": px, "fee": round(fee, 4), "target_weight": pending["target_weight"]},
                TRADES_PATH,
            )
            out["filled"] = {"delta_shares": delta, "price": px, "fee": round(fee, 2)}
        else:
            out["filled"] = "skipped_below_min_trade"
        state["pending"] = None

    # 2) 현금 이자 (전일 ^IRX 일할)
    irx = float(df["irx"].ffill().iloc[-2]) if len(df) > 1 else 0.0
    state["cash"] *= 1.0 + irx / 252.0

    # 3) 마크 + 신호 갱신
    close = float(df.iloc[-1]["qld_close"])
    equity = state["cash"] + state["shares"] * close
    weight, detail = target_weight(df)
    if not state.get("paused"):
        state["pending"] = {"signal_date": str(today.date()), "target_weight": round(weight, 4)}
    save_state(state)
    append_csv(
        {"date": str(today.date()), "cash": round(state["cash"], 2), "shares": state["shares"],
         "qld_close": close, "equity": round(equity, 2),
         "cum_return": round(equity / state["initial_capital_usd"] - 1.0, 6),
         "target_weight": round(weight, 4), "risk_on": detail["risk_on"]},
        EQUITY_PATH,
    )
    out.update(
        {"equity": round(equity, 2), "cash": round(state["cash"], 2), "shares": state["shares"],
         "cum_return_pct": round((equity / state["initial_capital_usd"] - 1.0) * 100, 3),
         "signal": detail, "next_target_weight": round(weight, 4)}
    )
    print(json.dumps(out, indent=2))


def cmd_status() -> None:
    state = load_state()
    print(json.dumps(state, indent=2))
    if EQUITY_PATH.exists():
        print(pd.read_csv(EQUITY_PATH).tail(5).to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--capital", type=float, default=10_000.0)
    sub.add_parser("run")
    sub.add_parser("status")
    sub.add_parser("pause")
    sub.add_parser("resume")
    args = parser.parse_args()
    if args.cmd == "init":
        cmd_init(args.capital)
    elif args.cmd == "run":
        cmd_run()
    elif args.cmd in ("pause", "resume"):
        state = load_state()
        state["paused"] = args.cmd == "pause"
        if state["paused"]:
            state["pending"] = None
        save_state(state)
        print(json.dumps({"paused": state["paused"]}))
    else:
        cmd_status()


if __name__ == "__main__":
    main()
