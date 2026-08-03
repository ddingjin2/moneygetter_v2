from __future__ import annotations

import pandas as pd

from v2.scripts.us_quality_strategy_experiment import (
    apply_market_hedge_overlay,
    combine_signal_matrices,
    experiment_rebalance_days,
    monthly_metrics,
    quality_matrix_from_fundamentals,
    stock_leverage_grid,
    stop_loss_grid,
    stopped_forward_returns,
)


def test_quality_matrix_from_fundamentals_aligns_and_pivots_scores() -> None:
    fundamentals = pd.DataFrame(
        {
            "symbol": ["HIGH", "LOW"],
            "fiscal_period_end": ["2023-12-31", "2023-12-31"],
            "filing_date": ["2024-02-15", "2024-02-15"],
            "gross_profit": [30.0, 10.0],
            "net_income": [12.0, 2.0],
            "total_assets": [100.0, 100.0],
            "total_liabilities": [20.0, 80.0],
        }
    )
    dates = pd.DatetimeIndex(["2024-02-14", "2024-02-16"])

    matrix = quality_matrix_from_fundamentals(fundamentals, dates, ["HIGH", "LOW"])

    assert pd.isna(matrix.loc[pd.Timestamp("2024-02-14"), "HIGH"])
    assert matrix.loc[pd.Timestamp("2024-02-16"), "HIGH"] > matrix.loc[pd.Timestamp("2024-02-16"), "LOW"]


def test_combine_signal_matrices_uses_cross_sectional_ranks_without_lookahead() -> None:
    dates = pd.date_range("2024-01-01", periods=2)
    price = pd.DataFrame({"AAA": [1.0, 1.0], "BBB": [0.0, 0.0], "CCC": [-1.0, -1.0]}, index=dates)
    quality = pd.DataFrame({"AAA": [-1.0, -1.0], "BBB": [0.0, 0.0], "CCC": [1.0, 1.0]}, index=dates)

    combined = combine_signal_matrices(price, quality, quality_weight=1.0)

    assert combined.loc[dates[0], "AAA"] == combined.loc[dates[0], "CCC"]
    assert combined.loc[dates[0], "BBB"] == 0.0


def test_experiment_rebalance_days_include_higher_frequency_candidates() -> None:
    assert experiment_rebalance_days() == [2, 5, 10, 20]


def test_stock_leverage_grid_includes_two_times_individual_stock_leverage() -> None:
    assert stock_leverage_grid() == [1.0, 1.25, 1.5, 1.75, 2.0]


def test_stop_loss_grid_includes_practical_daily_stock_stops() -> None:
    assert stop_loss_grid() == [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]


def test_stopped_forward_returns_caps_loss_when_low_touches_stop() -> None:
    dates = pd.date_range("2024-01-01", periods=3)
    open_px = pd.DataFrame({"AAA": [100.0, 110.0, 120.0], "BBB": [100.0, 90.0, 95.0]}, index=dates)
    low_px = pd.DataFrame({"AAA": [94.0, 108.0, 119.0], "BBB": [99.0, 89.0, 94.0]}, index=dates)

    returns = stopped_forward_returns(open_px, low_px, stop_loss=0.05, stop_slippage_bps=0.0)

    assert returns.loc[dates[0], "AAA"] == -0.05
    assert round(returns.loc[dates[0], "BBB"], 2) == -0.10


def test_apply_market_hedge_overlay_shorts_market_only_when_riskoff() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=4),
            "net_return": [0.10, 0.10, 0.10, 0.10],
        }
    )
    market_returns = pd.Series([0.01, -0.02, 0.03, -0.04], index=pd.to_datetime(frame["date"]))
    riskoff = pd.Series([False, True, False, True], index=market_returns.index)

    out = apply_market_hedge_overlay(
        frame,
        market_returns,
        riskoff,
        stock_leverage=1.0,
        hedge_ratio=0.5,
        financing_rate=0.0,
        hedge_rebalance_cost_bps=0.0,
    )

    assert out.loc[0, "net_return"] == 0.10
    assert out.loc[1, "net_return"] == 0.10 - (-0.02 * 0.5)
    assert out.loc[2, "net_return"] == 0.10
    assert out.loc[3, "net_return"] == 0.10 - (-0.04 * 0.5)
    assert out.loc[1, "hedge_exposure"] == -0.5


def test_monthly_metrics_counts_win_rate_and_worst_month() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-31", "2024-02-02", "2024-02-29"]),
            "net_return": [0.10, -0.05, -0.10, -0.10],
        }
    )

    metrics = monthly_metrics(frame)

    assert metrics["n_months"] == 2
    assert metrics["monthly_win_rate"] == 0.5
    assert metrics["max_consecutive_losing_months"] == 1
    assert round(metrics["worst_monthly_return"], 2) == -0.19
