from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class KoreanUsStockTaxConfig:
    annual_deduction_krw: float = 2_500_000.0
    tax_rate: float = 0.22


REALIZED_COLUMNS = [
    "sell_date",
    "tax_year",
    "symbol",
    "quantity",
    "proceeds_krw",
    "cost_basis_krw",
    "sell_fees_krw",
    "gain_krw",
]

TAX_SUMMARY_COLUMNS = [
    "tax_year",
    "net_realized_gain_krw",
    "deduction_used_krw",
    "taxable_gain_krw",
    "tax_due_krw",
]


def _normalized_trades(trades: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "symbol", "side", "quantity", "price_usd", "fx_krw_per_usd"}
    missing = sorted(required.difference(trades.columns))
    if missing:
        raise ValueError(f"trades are missing required columns: {missing}")
    out = trades.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    out["side"] = out["side"].astype(str).str.strip().str.upper()
    for column in ["quantity", "price_usd", "fx_krw_per_usd"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    if "fees_krw" not in out.columns:
        out["fees_krw"] = 0.0
    out["fees_krw"] = pd.to_numeric(out["fees_krw"], errors="coerce").fillna(0.0)
    out = out.dropna(subset=["date", "symbol", "side", "quantity", "price_usd", "fx_krw_per_usd"])
    out = out.loc[out["quantity"].gt(0)]
    return out.sort_values(["date", "symbol"]).reset_index(drop=True)


def realized_sales_from_trades(trades: pd.DataFrame) -> pd.DataFrame:
    data = _normalized_trades(trades)
    lots: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []

    for trade in data.itertuples(index=False):
        symbol = str(trade.symbol)
        quantity = float(trade.quantity)
        trade_value_krw = float(trade.quantity) * float(trade.price_usd) * float(trade.fx_krw_per_usd)
        fees_krw = float(trade.fees_krw)

        if trade.side == "BUY":
            lots.setdefault(symbol, []).append({"quantity": quantity, "cost_krw": trade_value_krw + fees_krw})
            continue

        if trade.side != "SELL":
            raise ValueError(f"unsupported trade side: {trade.side}")

        remaining = quantity
        cost_basis_krw = 0.0
        symbol_lots = lots.setdefault(symbol, [])
        while remaining > 1e-12:
            if not symbol_lots:
                raise ValueError(f"sell quantity exceeds available lots for {symbol}")
            lot = symbol_lots[0]
            take = min(remaining, float(lot["quantity"]))
            lot_cost_per_share = float(lot["cost_krw"]) / float(lot["quantity"])
            cost_basis_krw += take * lot_cost_per_share
            lot["quantity"] = float(lot["quantity"]) - take
            lot["cost_krw"] = float(lot["cost_krw"]) - take * lot_cost_per_share
            remaining -= take
            if float(lot["quantity"]) <= 1e-12:
                symbol_lots.pop(0)

        proceeds_krw = trade_value_krw
        gain_krw = proceeds_krw - cost_basis_krw - fees_krw
        sell_date = pd.Timestamp(trade.date)
        rows.append(
            {
                "sell_date": sell_date,
                "tax_year": int(sell_date.year),
                "symbol": symbol,
                "quantity": quantity,
                "proceeds_krw": proceeds_krw,
                "cost_basis_krw": cost_basis_krw,
                "sell_fees_krw": fees_krw,
                "gain_krw": gain_krw,
            }
        )

    return pd.DataFrame(rows, columns=REALIZED_COLUMNS)


def summarize_korean_us_stock_tax(
    realized_sales: pd.DataFrame,
    config: KoreanUsStockTaxConfig | None = None,
) -> pd.DataFrame:
    cfg = config or KoreanUsStockTaxConfig()
    if realized_sales.empty:
        return pd.DataFrame(columns=TAX_SUMMARY_COLUMNS)
    data = realized_sales.copy()
    if "tax_year" not in data.columns:
        data["tax_year"] = pd.to_datetime(data["sell_date"]).dt.year
    data["gain_krw"] = pd.to_numeric(data["gain_krw"], errors="coerce").fillna(0.0)

    rows = []
    for tax_year, group in data.groupby("tax_year", sort=True):
        net_gain = float(group["gain_krw"].sum())
        deduction = min(max(net_gain, 0.0), cfg.annual_deduction_krw)
        taxable = max(net_gain - deduction, 0.0)
        rows.append(
            {
                "tax_year": int(tax_year),
                "net_realized_gain_krw": net_gain,
                "deduction_used_krw": deduction,
                "taxable_gain_krw": taxable,
                "tax_due_krw": taxable * cfg.tax_rate,
            }
        )
    return pd.DataFrame(rows, columns=TAX_SUMMARY_COLUMNS)
