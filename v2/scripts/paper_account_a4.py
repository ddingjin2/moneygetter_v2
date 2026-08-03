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
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from v2.data.delistings import load_delisting_registry, settle_delisted_positions  # noqa: E402

ACCOUNT_DIR = ROOT / "data/cache/paper_trading/a4_20d_top10"
PRICE_DIR = ROOT / "data/cache/price_market_cap_full"
DEFAULT_CAPITAL = 100_000_000.0
DEFAULT_BUY_FEE = 0.001
DEFAULT_SELL_FEE = 0.001


def atomic_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def atomic_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_latest_price_map(asof: pd.Timestamp | None = None) -> tuple[pd.Timestamp, pd.DataFrame]:
    frames = []
    for path in PRICE_DIR.glob("*.parquet"):
        if not (path.stem.isdigit() and len(path.stem) == 6):
            continue
        f = pd.read_parquet(path, columns=["date", "symbol", "name", "close", "volume"])
        f["code"] = path.stem
        frames.append(f)
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel["close"] = pd.to_numeric(panel["close"], errors="coerce").astype("float64")
    panel["volume"] = pd.to_numeric(panel["volume"], errors="coerce").astype("float64")
    if asof is not None:
        panel = panel[panel["date"].le(asof)]
    actual = panel["date"].max()
    latest = panel[panel["date"].eq(actual)].drop_duplicates("code").set_index("code")
    return pd.Timestamp(actual), latest[["name", "close", "volume"]]


def load_price_history(codes: set[str]) -> pd.DataFrame:
    frames = []
    for code in sorted(codes):
        path = PRICE_DIR / f"{code}.parquet"
        if not path.exists():
            continue
        frame = pd.read_parquet(path, columns=["date", "name", "close"])
        frame["code"] = code
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["code", "date", "name", "close"])
    return pd.concat(frames, ignore_index=True)


def init_account(capital: float, buy_fee: float, sell_fee: float, force: bool) -> None:
    ACCOUNT_DIR.mkdir(parents=True, exist_ok=True)
    account_path = ACCOUNT_DIR / "account.json"
    if account_path.exists() and not force:
        raise SystemExit(f"Account already exists: {account_path}. Use --force to overwrite.")
    account = {
        "strategy": "A4_60_20d_top10",
        "initial_capital": capital,
        "cash": capital,
        "buy_fee": buy_fee,
        "sell_fee": sell_fee,
        "created_at": pd.Timestamp.now().isoformat(),
        "note": "Paper account. No broker orders are sent.",
    }
    atomic_json(account, account_path)
    atomic_csv(pd.DataFrame(columns=["code", "name", "shares", "avg_cost"]), ACCOUNT_DIR / "positions.csv")
    atomic_csv(pd.DataFrame(columns=["date", "code", "name", "side", "shares", "price", "gross", "fee", "cash_flow"]), ACCOUNT_DIR / "trades.csv")
    mark_to_market(None)
    print(json.dumps({"initialized": str(account_path), "capital": capital}, ensure_ascii=False, indent=2))


def load_account() -> dict:
    path = ACCOUNT_DIR / "account.json"
    if not path.exists():
        raise SystemExit(f"No paper account. Run: {sys.executable} scripts/paper_account_a4.py init --capital 100000000")
    return read_json(path)


def load_positions() -> pd.DataFrame:
    path = ACCOUNT_DIR / "positions.csv"
    if not path.exists():
        return pd.DataFrame(columns=["code", "name", "shares", "avg_cost"])
    pos = pd.read_csv(path, dtype={"code": str})
    if pos.empty:
        return pd.DataFrame(columns=["code", "name", "shares", "avg_cost"])
    pos["code"] = pos["code"].str.zfill(6)
    pos["shares"] = pd.to_numeric(pos["shares"], errors="coerce").fillna(0).astype(int)
    pos["avg_cost"] = pd.to_numeric(pos["avg_cost"], errors="coerce").fillna(0.0)
    return pos[pos["shares"].gt(0)].copy()


def save_account(account: dict) -> None:
    atomic_json(account, ACCOUNT_DIR / "account.json")


def save_positions(pos: pd.DataFrame) -> None:
    cols = ["code", "name", "shares", "avg_cost"]
    atomic_csv(pos[cols].sort_values("code"), ACCOUNT_DIR / "positions.csv")


def append_trades(trades: pd.DataFrame) -> None:
    path = ACCOUNT_DIR / "trades.csv"
    old = pd.read_csv(path, dtype={"code": str}) if path.exists() else pd.DataFrame()
    out = pd.concat([old, trades], ignore_index=True) if not old.empty else trades
    atomic_csv(out, path)


def current_positions_arg() -> Path:
    pos = load_positions()
    path = ACCOUNT_DIR / ".current_positions_for_orders.csv"
    atomic_csv(pos[["code", "shares"]] if not pos.empty else pd.DataFrame(columns=["code", "shares"]), path)
    return path


def calculate_account_equity(account: dict, positions: pd.DataFrame, price_map: pd.DataFrame) -> float:
    cash = float(account.get("cash", 0.0))
    if positions.empty:
        return cash
    held = positions[["code", "shares"]].copy()
    held["code"] = held["code"].astype(str).str.zfill(6)
    held["shares"] = pd.to_numeric(held["shares"], errors="coerce").fillna(0).astype(int)
    valued = held.merge(price_map.reset_index()[["code", "close"]], on="code", how="left")
    missing = sorted(valued.loc[valued["close"].isna(), "code"].tolist())
    if missing:
        raise ValueError(f"Cannot rebalance with unpriced positions: {missing}")
    return cash + float((valued["shares"] * pd.to_numeric(valued["close"], errors="coerce")).sum())


def build_paper_trade_command(
    *,
    capital: float,
    buy_fee: float,
    sell_fee: float,
    positions_path: Path,
    asof: str | None,
) -> list[str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/paper_trade_a4.py"),
        "--capital",
        str(capital),
        "--buy-fee",
        str(buy_fee),
        "--sell-fee",
        str(sell_fee),
        "--positions",
        str(positions_path),
    ]
    if asof:
        cmd += ["--asof", asof]
    return cmd


def generate_orders(capital: float | None, asof: str | None) -> dict:
    account = load_account()
    positions = load_positions()
    positions_path = current_positions_arg()
    if capital is None:
        asof_ts = pd.Timestamp(asof).normalize() if asof else None
        _, price_map = load_latest_price_map(asof_ts)
        cap = calculate_account_equity(account, positions, price_map)
    else:
        cap = float(capital)
    cmd = build_paper_trade_command(
        capital=cap,
        buy_fee=float(account.get("buy_fee", DEFAULT_BUY_FEE)),
        sell_fee=float(account.get("sell_fee", DEFAULT_SELL_FEE)),
        positions_path=positions_path,
        asof=asof,
    )
    subprocess.run(cmd, cwd=ROOT, check=True)
    return read_json(ACCOUNT_DIR / "latest_state.json")


def fill_orders(asof: str | None, max_cash: bool) -> None:
    account = load_account()
    state = read_json(ACCOUNT_DIR / "latest_state.json")
    orders_path = Path(state["orders_path"])
    if not orders_path.exists():
        raise SystemExit("No orders found. Run `rebalance` first.")
    orders = pd.read_csv(orders_path, dtype={"code": str})
    if orders.empty:
        print("No orders to fill.")
        return
    fill_date, price_map = load_latest_price_map(pd.Timestamp(asof).normalize() if asof else None)
    pos = load_positions().set_index("code")
    trades = []
    cash = float(account["cash"])
    buy_fee = float(account.get("buy_fee", DEFAULT_BUY_FEE))
    sell_fee = float(account.get("sell_fee", DEFAULT_SELL_FEE))
    # Sells first, then buys.
    side_order = {"SELL": 0, "BUY": 1}
    orders = orders.sort_values(by="side", key=lambda s: s.map(side_order)).reset_index(drop=True)
    for row in orders.itertuples(index=False):
        code = str(row.code).zfill(6)
        if code not in price_map.index:
            continue
        price = float(price_map.loc[code, "close"])
        name = str(price_map.loc[code, "name"])
        shares = int(row.order_shares)
        if shares <= 0 or price <= 0:
            continue
        if row.side == "SELL":
            held = int(pos.loc[code, "shares"]) if code in pos.index else 0
            fill_shares = min(shares, held)
            if fill_shares <= 0:
                continue
            gross = fill_shares * price
            fee = gross * sell_fee
            cash += gross - fee
            old_shares = held
            new_shares = old_shares - fill_shares
            if new_shares > 0:
                pos.loc[code, "shares"] = new_shares
            elif code in pos.index:
                pos = pos.drop(index=code)
            trades.append({"date": fill_date, "code": code, "name": name, "side": "SELL", "shares": fill_shares, "price": price, "gross": gross, "fee": fee, "cash_flow": gross - fee})
        elif row.side == "BUY":
            affordable = int(cash // (price * (1.0 + buy_fee))) if max_cash else shares
            fill_shares = min(shares, affordable)
            if fill_shares <= 0:
                continue
            gross = fill_shares * price
            fee = gross * buy_fee
            cash -= gross + fee
            if code in pos.index:
                old_shares = int(pos.loc[code, "shares"])
                old_cost = float(pos.loc[code, "avg_cost"])
                new_shares = old_shares + fill_shares
                pos.loc[code, "shares"] = new_shares
                pos.loc[code, "avg_cost"] = ((old_shares * old_cost) + gross + fee) / new_shares
                pos.loc[code, "name"] = name
            else:
                pos.loc[code, ["name", "shares", "avg_cost"]] = [name, fill_shares, (gross + fee) / fill_shares]
            trades.append({"date": fill_date, "code": code, "name": name, "side": "BUY", "shares": fill_shares, "price": price, "gross": gross, "fee": fee, "cash_flow": -(gross + fee)})
    account["cash"] = cash
    account["last_fill_date"] = fill_date.strftime("%Y-%m-%d")
    pos = pos.reset_index()
    save_positions(pos if not pos.empty else pd.DataFrame(columns=["code", "name", "shares", "avg_cost"]))
    save_account(account)
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        append_trades(trades_df)
    mark_to_market(fill_date)
    print(json.dumps({"fill_date": fill_date.strftime("%Y-%m-%d"), "filled_orders": len(trades), "cash": cash}, ensure_ascii=False, indent=2))


def process_delistings(asof: str | None) -> None:
    account = load_account()
    positions = load_positions()
    registry = load_delisting_registry()
    if registry.empty or positions.empty:
        print(json.dumps({"processed": 0, "reason": "no_due_delisted_positions"}, ensure_ascii=False, indent=2))
        return
    if asof:
        cutoff = pd.Timestamp(asof).normalize()
    else:
        cutoff, _ = load_latest_price_map(None)
    due_codes = set(
        registry.loc[
            registry["delisted_date"].le(cutoff) & registry["code"].isin(set(positions["code"])),
            "code",
        ]
    )
    if not due_codes:
        print(json.dumps({"processed": 0, "asof": cutoff.date().isoformat(), "reason": "no_due_delisted_positions"}, ensure_ascii=False, indent=2))
        return
    prices = load_price_history(due_codes)
    updated_account, updated_positions, trades = settle_delisted_positions(
        account,
        positions,
        registry,
        prices,
        asof=cutoff,
    )
    if trades.empty:
        print(json.dumps({"processed": 0, "asof": cutoff.date().isoformat()}, ensure_ascii=False, indent=2))
        return
    save_account(updated_account)
    save_positions(updated_positions if not updated_positions.empty else pd.DataFrame(columns=["code", "name", "shares", "avg_cost"]))
    append_trades(trades)
    for event_date in sorted(pd.to_datetime(trades["date"]).dt.normalize().unique()):
        mark_to_market(pd.Timestamp(event_date))
    mark_to_market(cutoff)
    print(
        json.dumps(
            {
                "processed": int(len(trades)),
                "asof": cutoff.date().isoformat(),
                "codes": trades["code"].tolist(),
                "cash_flow": float(trades["cash_flow"].sum()),
                "cash": float(updated_account["cash"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def mark_to_market(asof: pd.Timestamp | None) -> None:
    account_path = ACCOUNT_DIR / "account.json"
    if not account_path.exists():
        return
    account = read_json(account_path)
    pos = load_positions()
    actual_date, price_map = load_latest_price_map(asof)
    if pos.empty:
        equity = float(account["cash"])
        row = {"date": actual_date, "cash": equity, "market_value": 0.0, "equity": equity, "positions": 0, "cum_return": equity / float(account["initial_capital"]) - 1.0}
    else:
        m = pos.merge(price_map.reset_index()[["code", "close"]], on="code", how="left")
        m["last_price"] = pd.to_numeric(m["close"], errors="coerce").fillna(0.0)
        m["market_value"] = m["shares"] * m["last_price"]
        m["unrealized_pnl"] = m["market_value"] - m["shares"] * m["avg_cost"]
        atomic_csv(m.drop(columns=["close"]), ACCOUNT_DIR / "positions_mtm.csv")
        market_value = float(m["market_value"].sum())
        equity = float(account["cash"]) + market_value
        row = {"date": actual_date, "cash": float(account["cash"]), "market_value": market_value, "equity": equity, "positions": int(len(pos)), "cum_return": equity / float(account["initial_capital"]) - 1.0}
    path = ACCOUNT_DIR / "equity_curve.csv"
    old = pd.read_csv(path) if path.exists() else pd.DataFrame()
    out = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out = out.drop_duplicates("date", keep="last").sort_values("date")
    atomic_csv(out, path)


def status() -> None:
    account = load_account()
    mark_to_market(None)
    eq = pd.read_csv(ACCOUNT_DIR / "equity_curve.csv")
    pos = load_positions()
    latest = eq.tail(1).iloc[0].to_dict() if not eq.empty else {}
    summary = {
        "account": str(ACCOUNT_DIR / "account.json"),
        "cash": account.get("cash"),
        "latest_equity": latest,
        "positions": int(len(pos)),
        "positions_path": str(ACCOUNT_DIR / "positions.csv"),
        "equity_curve_path": str(ACCOUNT_DIR / "equity_curve.csv"),
        "trades_path": str(ACCOUNT_DIR / "trades.csv"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Paper account ledger for A4 20d top10.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--capital", type=float, default=DEFAULT_CAPITAL)
    p.add_argument("--buy-fee", type=float, default=DEFAULT_BUY_FEE)
    p.add_argument("--sell-fee", type=float, default=DEFAULT_SELL_FEE)
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("rebalance")
    p.add_argument("--capital", type=float, default=None, help="Target notional. Default: initial capital.")
    p.add_argument("--asof", default=None)
    p = sub.add_parser("fill")
    p.add_argument("--asof", default=None)
    p.add_argument("--no-cash-limit", action="store_true", help="Do not reduce buys if cash is insufficient.")
    p = sub.add_parser("process-delistings")
    p.add_argument("--asof", default=None)
    sub.add_parser("mark")
    sub.add_parser("status")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.cmd == "init":
        init_account(args.capital, args.buy_fee, args.sell_fee, args.force)
    elif args.cmd == "rebalance":
        state = generate_orders(args.capital, args.asof)
        print(json.dumps(state, ensure_ascii=False, indent=2))
    elif args.cmd == "fill":
        fill_orders(args.asof, max_cash=not args.no_cash_limit)
    elif args.cmd == "process-delistings":
        process_delistings(args.asof)
    elif args.cmd == "mark":
        mark_to_market(None)
        status()
    elif args.cmd == "status":
        status()


if __name__ == "__main__":
    main()
