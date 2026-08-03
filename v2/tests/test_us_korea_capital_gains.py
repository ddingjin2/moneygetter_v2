from __future__ import annotations

import pandas as pd

from v2.tax.us_korea_capital_gains import (
    KoreanUsStockTaxConfig,
    realized_sales_from_trades,
    summarize_korean_us_stock_tax,
)


def test_realized_sales_use_trade_date_fx_and_fifo_cost_basis() -> None:
    trades = pd.DataFrame(
        [
            {"date": "2026-01-02", "symbol": "QLD", "side": "BUY", "quantity": 10, "price_usd": 100.0, "fx_krw_per_usd": 1300.0, "fees_krw": 1000.0},
            {"date": "2026-03-02", "symbol": "QLD", "side": "SELL", "quantity": 4, "price_usd": 120.0, "fx_krw_per_usd": 1400.0, "fees_krw": 800.0},
        ]
    )

    realized = realized_sales_from_trades(trades)

    assert len(realized) == 1
    assert float(realized.loc[0, "proceeds_krw"]) == 672000.0
    assert float(realized.loc[0, "cost_basis_krw"]) == 520400.0
    assert float(realized.loc[0, "gain_krw"]) == 150800.0


def test_tax_summary_applies_annual_deduction_then_twenty_two_percent_tax() -> None:
    realized = pd.DataFrame(
        [
            {"sell_date": "2026-02-01", "symbol": "QLD", "gain_krw": 3_000_000.0},
        ]
    )

    summary = summarize_korean_us_stock_tax(realized)

    assert float(summary.loc[0, "net_realized_gain_krw"]) == 3_000_000.0
    assert float(summary.loc[0, "deduction_used_krw"]) == 2_500_000.0
    assert float(summary.loc[0, "taxable_gain_krw"]) == 500_000.0
    assert float(summary.loc[0, "tax_due_krw"]) == 110_000.0


def test_losses_offset_same_year_but_do_not_carry_forward() -> None:
    realized = pd.DataFrame(
        [
            {"sell_date": "2026-02-01", "symbol": "QLD", "gain_krw": 3_000_000.0},
            {"sell_date": "2026-04-01", "symbol": "QLD", "gain_krw": -1_000_000.0},
            {"sell_date": "2027-02-01", "symbol": "QLD", "gain_krw": 3_000_000.0},
        ]
    )

    summary = summarize_korean_us_stock_tax(realized, KoreanUsStockTaxConfig(annual_deduction_krw=2_500_000.0, tax_rate=0.22))

    by_year = summary.set_index("tax_year")
    assert float(by_year.loc[2026, "tax_due_krw"]) == 0.0
    assert float(by_year.loc[2027, "tax_due_krw"]) == 110_000.0
