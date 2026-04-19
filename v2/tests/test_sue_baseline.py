from __future__ import annotations

import math

import pandas as pd

from v2.backtest.fill_model import CostModel
from v2.backtest.run_sue_baseline import backtest_sue_baseline
from v2.signals.sue_baseline import generate_signals


def test_generate_signals_selects_daily_top_quintile_with_entry_price() -> None:
    symbols = [f"00000{i}" for i in range(1, 6)]
    earnings = pd.DataFrame(
        {
            "stock_code": symbols,
            "tradable_entry_date": ["2024-01-03"] * 5,
            "sue": [0.1, 1.0, 0.3, 2.5, -0.2],
        }
    )
    previous = pd.DataFrame(
        {
            "date": ["2024-01-02"] * 5,
            "symbol": symbols,
            "open": [1000] * 5,
            "high": [1000] * 5,
            "close": [2000] * 5,
            "market_cap": [100_000] * 5,
        }
    )
    entry = pd.DataFrame(
        {
            "date": ["2024-01-03"] * 5,
            "symbol": symbols,
            "open": [1100, 1200, 1300, 1400, 1500],
            "high": [1110, 1210, 1310, 1410, 1510],
            "close": [1105, 1205, 1305, 1405, 1505],
            "market_cap": [100_000] * 5,
        }
    )

    signals = generate_signals(earnings, pd.concat([previous, entry], ignore_index=True), lambda frame: frame)

    assert list(signals["symbol"]) == ["000004"]
    assert float(signals.iloc[0]["signal_score"]) == 2.5
    assert float(signals.iloc[0]["tradable_entry_price"]) == 1400.0


def test_generate_signals_filters_price_and_limit_up_entries() -> None:
    earnings = pd.DataFrame(
        {
            "stock_code": ["000001", "000002", "000003"],
            "tradable_entry_date": ["2024-01-03"] * 3,
            "sue": [3.0, 2.0, 1.0],
        }
    )
    ohlcv = pd.DataFrame(
        [
            {"date": "2024-01-02", "symbol": "000001", "open": 1000, "high": 1000, "close": 1000, "market_cap": 1},
            {"date": "2024-01-02", "symbol": "000002", "open": 1000, "high": 1000, "close": 1000, "market_cap": 1},
            {"date": "2024-01-02", "symbol": "000003", "open": 1000, "high": 1000, "close": 1000, "market_cap": 1},
            {"date": "2024-01-03", "symbol": "000001", "open": 900, "high": 950, "close": 930, "market_cap": 1},
            {"date": "2024-01-03", "symbol": "000002", "open": 1300, "high": 1300, "close": 1300, "market_cap": 1},
            {"date": "2024-01-03", "symbol": "000003", "open": 1100, "high": 1120, "close": 1110, "market_cap": 1},
        ]
    )

    signals = generate_signals(earnings, ohlcv, lambda frame: frame)

    assert list(signals["symbol"]) == ["000003"]


def test_backtest_sue_baseline_exits_after_fixed_holding_days() -> None:
    earnings = pd.DataFrame(
        {
            "stock_code": ["000001"],
            "tradable_entry_date": ["2024-01-02"],
            "data_source_timestamp": [pd.Timestamp("2024-01-01")],
            "rcept_dt": [pd.Timestamp("2024-01-01")],
            "rcept_time": ["16:00"],
            "fiscal_quarter": ["2023Q4"],
        }
    )
    signals = pd.DataFrame(
        {
            "entry_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001"],
            "signal_score": [2.0],
            "tradable_entry_price": [100.0],
        }
    )
    ohlcv = pd.DataFrame(
        [
            {"date": "2024-01-02", "symbol": "000001", "open": 100.0, "high": 101.0, "close": 105.0},
            {"date": "2024-01-03", "symbol": "000001", "open": 106.0, "high": 112.0, "close": 110.0},
        ]
    )

    ledger, equity, metrics = backtest_sue_baseline(
        signals=signals,
        earnings_events=earnings,
        ohlcv=ohlcv,
        start="2024-01-02",
        end="2024-01-03",
        cost_model=CostModel(0.0, 0.0),
        initial_cash=2000.0,
        positions_max=1,
        hold_days=2,
    )

    assert len(ledger) == 1
    assert ledger.iloc[0]["exit_date"] == pd.Timestamp("2024-01-03")
    assert math.isclose(float(ledger.iloc[0]["pnl"]), 200.0)
    assert math.isclose(float(equity.iloc[-1]["equity"]), 2200.0)
    assert metrics["PF"] == math.inf
    assert math.isclose(metrics["total_return"], 0.1)
