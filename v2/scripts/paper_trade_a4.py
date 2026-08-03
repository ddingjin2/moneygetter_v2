from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from v2.data.universe import get_active_universe, load_kospi_universe  # noqa: E402

PRICE_DIR = ROOT / "data/cache/price_market_cap_full"
OUT_DIR = ROOT / "data/cache/paper_trading/a4_20d_top10"

DEFAULT_CAPITAL = 100_000_000
DEFAULT_BUY_FEE = 0.001
DEFAULT_SELL_FEE = 0.001
DEFAULT_TOP_Q = 0.10
DEFAULT_LOOKBACK = 60


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def atomic_write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def stock_codes() -> list[str]:
    return sorted(p.stem for p in PRICE_DIR.glob("*.parquet") if p.stem.isdigit() and len(p.stem) == 6)


def load_latest_panel() -> pd.DataFrame:
    frames = []
    cols = ["date", "symbol", "name", "open", "high", "low", "close", "volume", "trading_value"]
    for code in stock_codes():
        frame = pd.read_parquet(PRICE_DIR / f"{code}.parquet", columns=cols)
        frame["code"] = code
        frames.append(frame)
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    for col in ["open", "high", "low", "close", "volume", "trading_value"]:
        panel[col] = pd.to_numeric(panel[col], errors="coerce").astype("float64")
    panel["dvol"] = panel["close"] * panel["volume"]
    return panel.sort_values(["date", "code"])


def build_a4_rank(
    panel: pd.DataFrame,
    asof: pd.Timestamp,
    lookback: int,
    top_q: float,
    *,
    active_codes: set[str] | None = None,
) -> pd.DataFrame:
    eligible = panel[panel["date"].le(asof)].copy()
    if active_codes is not None:
        eligible = eligible.loc[eligible["code"].isin(active_codes)]
    if eligible.empty:
        raise SystemExit(f"No price data on/before {asof.date()}")
    last_date = eligible["date"].max()
    eligible = eligible[eligible["date"].le(last_date)]
    close = eligible.pivot(index="date", columns="code", values="close").sort_index()
    volume = eligible.pivot(index="date", columns="code", values="volume").sort_index()
    dvol = close * volume
    avg_dvol = dvol.rolling(lookback, min_periods=lookback).mean().loc[last_date]
    latest = eligible[eligible["date"].eq(last_date)].drop_duplicates("code").set_index("code")
    rank = pd.DataFrame({
        "code": avg_dvol.index,
        "a4_avg_dvol_krw": avg_dvol.values,
    }).dropna()
    rank = rank.merge(
        latest[["name", "open", "high", "low", "close", "volume", "trading_value"]],
        left_on="code", right_index=True, how="left"
    )
    rank = rank[rank["close"].gt(0) & rank["volume"].gt(0)].copy()
    rank["a4_score"] = -np.log(rank["a4_avg_dvol_krw"].replace(0, np.nan))
    rank = rank.dropna(subset=["a4_score"]).sort_values("a4_score", ascending=False).reset_index(drop=True)
    n = max(int(math.floor(len(rank) * top_q)), 1)
    rank["selected"] = False
    rank.loc[: n - 1, "selected"] = True
    rank["target_weight"] = np.where(rank["selected"], 1.0 / n, 0.0)
    rank["rank"] = np.arange(1, len(rank) + 1)
    rank.insert(0, "asof_date", last_date)
    return rank


def load_positions(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=["code", "shares"])
    pos = pd.read_csv(path, dtype={"code": str})
    if "shares" not in pos.columns:
        raise SystemExit("positions CSV must have columns: code, shares")
    pos["code"] = pos["code"].str.zfill(6)
    pos["shares"] = pd.to_numeric(pos["shares"], errors="coerce").fillna(0).astype(int)
    return pos[["code", "shares"]].groupby("code", as_index=False).sum()


def make_orders(rank: pd.DataFrame, positions: pd.DataFrame, capital: float, buy_fee: float, sell_fee: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected = rank[rank["selected"]].copy()
    selected["target_value_gross"] = capital * selected["target_weight"]
    selected["target_shares"] = np.floor(selected["target_value_gross"] / (selected["close"] * (1.0 + buy_fee))).astype(int)
    selected["target_value_est"] = selected["target_shares"] * selected["close"]
    # With small paper capital and many top-10% names, a few high-priced stocks can round to 0 shares.
    # Keep them in the rank file, but exclude them from the executable target portfolio/orders.
    selected = selected[selected["target_shares"].gt(0)].copy()
    current = positions.merge(rank[["code", "name", "close"]], on="code", how="left")
    current["close"] = current["close"].fillna(0.0)
    current["current_value_est"] = current["shares"] * current["close"]
    target = selected[["code", "name", "close", "target_weight", "target_shares", "target_value_est"]]
    orders = current[["code", "shares"]].rename(columns={"shares": "current_shares"}).merge(target, on="code", how="outer")
    orders["current_shares"] = orders["current_shares"].fillna(0).astype(int)
    orders["target_shares"] = orders["target_shares"].fillna(0).astype(int)
    orders["name"] = orders["name"].fillna(orders["code"])
    orders["close"] = orders["close"].fillna(0.0)
    orders["delta_shares"] = orders["target_shares"] - orders["current_shares"]
    orders["side"] = np.where(orders["delta_shares"].gt(0), "BUY", np.where(orders["delta_shares"].lt(0), "SELL", "HOLD"))
    orders["order_shares"] = orders["delta_shares"].abs().astype(int)
    orders["gross_amount_est"] = orders["order_shares"] * orders["close"]
    orders["fee_est"] = np.where(
        orders["side"].eq("BUY"), orders["gross_amount_est"] * buy_fee,
        np.where(orders["side"].eq("SELL"), orders["gross_amount_est"] * sell_fee, 0.0)
    )
    orders["cash_flow_est"] = np.where(
        orders["side"].eq("BUY"), -(orders["gross_amount_est"] + orders["fee_est"]),
        np.where(orders["side"].eq("SELL"), orders["gross_amount_est"] - orders["fee_est"], 0.0)
    )
    orders = orders[orders["side"].ne("HOLD")].sort_values(["side", "code"]).reset_index(drop=True)
    portfolio = selected.sort_values("rank").reset_index(drop=True)
    return portfolio, orders


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate A4 20d top10 paper-trading target portfolio and orders.")
    parser.add_argument("--asof", default=None, help="Signal date YYYY-MM-DD. Default: latest cached date.")
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL, help="Paper capital in KRW. Default: 10,000,000")
    parser.add_argument("--positions", type=Path, default=None, help="Current paper positions CSV with code,shares. Omit for initial buy list.")
    parser.add_argument("--buy-fee", type=float, default=DEFAULT_BUY_FEE, help="Buy fee/slippage rate. 0.001 = 0.1%%")
    parser.add_argument("--sell-fee", type=float, default=DEFAULT_SELL_FEE, help="Sell fee/slippage rate. 0.001 = 0.1%%")
    parser.add_argument("--top-q", type=float, default=DEFAULT_TOP_Q, help="Selected top fraction. Default: 0.10")
    parser.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK, help="A4 average traded-value lookback. Default: 60")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--max-order-dvol-pct", type=float, default=0.05, help="Warn if order amount exceeds this fraction of 60d average traded value.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel = load_latest_panel()
    asof = pd.Timestamp(args.asof).normalize() if args.asof else panel["date"].max()
    active_codes = set(get_active_universe(asof, universe=load_kospi_universe()))
    rank = build_a4_rank(panel, asof, args.lookback, args.top_q, active_codes=active_codes)
    actual_asof = pd.Timestamp(rank["asof_date"].iloc[0])
    positions = load_positions(args.positions)
    portfolio, orders = make_orders(rank, positions, args.capital, args.buy_fee, args.sell_fee)
    if not orders.empty:
        liq = rank[["code", "a4_avg_dvol_krw"]].copy()
        orders = orders.merge(liq, on="code", how="left")
        orders["order_to_avg_dvol"] = orders["gross_amount_est"] / orders["a4_avg_dvol_krw"].replace(0, pd.NA)
        orders["liquidity_warning"] = orders["order_to_avg_dvol"].gt(args.max_order_dvol_pct)
    date_tag = actual_asof.strftime("%Y%m%d")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rank_path = args.out_dir / f"rank_{date_tag}.csv"
    portfolio_path = args.out_dir / f"target_portfolio_{date_tag}.csv"
    orders_path = args.out_dir / f"orders_{date_tag}.csv"
    state_path = args.out_dir / "latest_state.json"
    atomic_write_csv(rank, rank_path)
    atomic_write_csv(portfolio, portfolio_path)
    atomic_write_csv(orders, orders_path)
    summary = {
        "strategy": "A4_60_20d_top10",
        "asof_date": actual_asof.strftime("%Y-%m-%d"),
        "capital_krw": args.capital,
        "buy_fee": args.buy_fee,
        "sell_fee": args.sell_fee,
        "lookback_days": args.lookback,
        "top_q": args.top_q,
        "universe_count": int(len(rank)),
        "selected_count": int(len(portfolio)),
        "target_gross_value_est": float(portfolio["target_value_est"].sum()),
        "buy_amount_est": float(orders.loc[orders["side"].eq("BUY"), "gross_amount_est"].sum()),
        "sell_amount_est": float(orders.loc[orders["side"].eq("SELL"), "gross_amount_est"].sum()),
        "fee_est": float(orders["fee_est"].sum()) if len(orders) else 0.0,
        "liquidity_warning_count": int(orders["liquidity_warning"].sum()) if "liquidity_warning" in orders.columns else 0,
        "max_order_to_avg_dvol": float(orders["order_to_avg_dvol"].max()) if "order_to_avg_dvol" in orders.columns and len(orders) else 0.0,
        "cash_flow_est": float(orders["cash_flow_est"].sum()) if len(orders) else 0.0,
        "rank_path": str(rank_path),
        "target_portfolio_path": str(portfolio_path),
        "orders_path": str(orders_path),
    }
    atomic_write_json(summary, state_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
