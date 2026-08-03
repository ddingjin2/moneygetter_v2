from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_DELISTING_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config/delistings.csv"
REGISTRY_COLUMNS = ["code", "name", "last_trading_date", "delisted_date", "reason", "source_url"]
TRADE_COLUMNS = [
    "date",
    "code",
    "name",
    "side",
    "shares",
    "price",
    "gross",
    "fee",
    "cash_flow",
    "event",
    "reason",
    "source_url",
]


def normalize_delisting_registry(frame: pd.DataFrame) -> pd.DataFrame:
    registry = frame.copy()
    for column in REGISTRY_COLUMNS:
        if column not in registry.columns:
            registry[column] = pd.NA
    registry["code"] = registry["code"].astype(str).str.zfill(6)
    registry["last_trading_date"] = pd.to_datetime(registry["last_trading_date"], errors="coerce").dt.normalize()
    registry["delisted_date"] = pd.to_datetime(registry["delisted_date"], errors="coerce").dt.normalize()
    if registry["code"].duplicated().any():
        duplicates = sorted(registry.loc[registry["code"].duplicated(keep=False), "code"].unique().tolist())
        raise ValueError(f"Duplicate delisting registry codes: {duplicates}")
    invalid = registry["last_trading_date"].isna() | registry["delisted_date"].isna()
    if invalid.any():
        codes = sorted(registry.loc[invalid, "code"].tolist())
        raise ValueError(f"Delisting registry requires both dates: {codes}")
    return registry[REGISTRY_COLUMNS].sort_values("code").reset_index(drop=True)


def load_delisting_registry(path: str | Path = DEFAULT_DELISTING_REGISTRY_PATH) -> pd.DataFrame:
    registry_path = Path(path)
    if not registry_path.exists():
        return pd.DataFrame(columns=REGISTRY_COLUMNS)
    return normalize_delisting_registry(pd.read_csv(registry_path, dtype={"code": str}))


def apply_delisting_registry(universe: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    updated = universe.copy()
    updated["code"] = updated["code"].astype(str).str.zfill(6)
    if "delisted_date" not in updated.columns:
        updated["delisted_date"] = pd.NaT
    updated["delisted_date"] = pd.to_datetime(updated["delisted_date"], errors="coerce").dt.normalize()
    events = normalize_delisting_registry(registry) if not registry.empty else registry
    if events.empty:
        return updated
    last_active_by_code = events.set_index("code")["last_trading_date"]
    override = updated["code"].map(last_active_by_code)
    updated.loc[override.notna(), "delisted_date"] = override.loc[override.notna()]
    return updated


def settle_delisted_positions(
    account: dict[str, Any],
    positions: pd.DataFrame,
    registry: pd.DataFrame,
    prices: pd.DataFrame,
    *,
    asof: pd.Timestamp,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    updated_account = dict(account)
    updated_positions = positions.copy()
    if updated_positions.empty:
        return updated_account, updated_positions, pd.DataFrame(columns=TRADE_COLUMNS)

    updated_positions["code"] = updated_positions["code"].astype(str).str.zfill(6)
    updated_positions["shares"] = pd.to_numeric(updated_positions["shares"], errors="coerce").fillna(0).astype(int)
    events = normalize_delisting_registry(registry)
    cutoff = pd.Timestamp(asof).normalize()
    due = events.loc[events["delisted_date"].le(cutoff)].copy()
    held_codes = set(updated_positions.loc[updated_positions["shares"].gt(0), "code"])
    due = due.loc[due["code"].isin(held_codes)].sort_values(["last_trading_date", "code"])
    if due.empty:
        return updated_account, updated_positions, pd.DataFrame(columns=TRADE_COLUMNS)

    price_frame = prices.copy()
    price_frame["code"] = price_frame["code"].astype(str).str.zfill(6)
    price_frame["date"] = pd.to_datetime(price_frame["date"], errors="coerce").dt.normalize()
    price_frame["close"] = pd.to_numeric(price_frame["close"], errors="coerce")
    sell_fee = float(updated_account.get("sell_fee", 0.001))
    cash = float(updated_account.get("cash", 0.0))
    trade_rows: list[dict[str, Any]] = []

    for event in due.itertuples(index=False):
        code = str(event.code).zfill(6)
        final_date = pd.Timestamp(event.last_trading_date).normalize()
        final_price = price_frame.loc[
            price_frame["code"].eq(code)
            & price_frame["date"].eq(final_date)
            & price_frame["close"].gt(0)
        ].sort_values("date")
        if final_price.empty:
            raise ValueError(f"Missing final trading price for {code} on {final_date.date()}")
        price_row = final_price.iloc[-1]
        held = updated_positions.loc[updated_positions["code"].eq(code)]
        shares = int(held["shares"].sum())
        if shares <= 0:
            continue
        price = float(price_row["close"])
        gross = shares * price
        fee = gross * sell_fee
        cash_flow = gross - fee
        cash += cash_flow
        held_name = str(held.iloc[0].get("name", ""))
        event_name = "" if pd.isna(event.name) else str(event.name)
        price_name = "" if "name" not in price_row or pd.isna(price_row.get("name")) else str(price_row.get("name"))
        name = event_name or price_name or held_name or code
        trade_rows.append(
            {
                "date": final_date,
                "code": code,
                "name": name,
                "side": "SELL",
                "shares": shares,
                "price": price,
                "gross": gross,
                "fee": fee,
                "cash_flow": cash_flow,
                "event": "DELISTING",
                "reason": "" if pd.isna(event.reason) else str(event.reason),
                "source_url": "" if pd.isna(event.source_url) else str(event.source_url),
            }
        )
        updated_positions = updated_positions.loc[~updated_positions["code"].eq(code)].copy()

    updated_account["cash"] = cash
    if trade_rows:
        updated_account["last_corporate_action_date"] = max(row["date"] for row in trade_rows).date().isoformat()
    trades = pd.DataFrame(trade_rows, columns=TRADE_COLUMNS)
    return updated_account, updated_positions.reset_index(drop=True), trades
