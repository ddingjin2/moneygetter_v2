from __future__ import annotations

import pandas as pd
import pytest

from v2.scripts.explore_intraday_flat_strategies import (
    backtest_flat,
    build_candidate_signals,
    performance_metrics,
    select_long_weights,
    backtest_index_gap_direction,
)


def test_select_long_weights_respects_eligibility_fraction_and_cap() -> None:
    signal = pd.Series({"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0})
    eligible = pd.Series({"A": True, "B": True, "C": True, "D": False})

    weights = select_long_weights(signal, eligible, top_fraction=0.75, max_positions=2, min_names=3)

    assert weights.to_dict() == {"A": 0.5, "B": 0.5, "C": 0.0, "D": 0.0}


def test_select_long_weights_keeps_unused_capital_in_cash_when_name_weight_is_capped() -> None:
    signal = pd.Series({"A": 2.0, "B": 1.0, "C": 0.0})
    eligible = pd.Series(True, index=signal.index)

    weights = select_long_weights(
        signal,
        eligible,
        top_fraction=1.0,
        max_positions=3,
        min_names=1,
        max_name_weight=0.2,
    )

    assert weights.sum() == pytest.approx(0.6)
    assert weights.max() == pytest.approx(0.2)


def test_backtest_uses_previous_day_signal_and_charges_round_trip_cost_daily() -> None:
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"])
    signal = pd.DataFrame({"A": [2.0, 0.0, 0.0], "B": [0.0, 2.0, 0.0]}, index=dates)
    eligible = pd.DataFrame(True, index=dates, columns=["A", "B"])
    open_px = pd.DataFrame({"A": [100.0, 100.0, 100.0], "B": [100.0, 100.0, 100.0]}, index=dates)
    close_px = pd.DataFrame({"A": [100.0, 110.0, 100.0], "B": [100.0, 100.0, 120.0]}, index=dates)
    execution_valid = pd.DataFrame(True, index=dates, columns=["A", "B"])

    pnl = backtest_flat(
        signal,
        eligible,
        open_px,
        close_px,
        execution_valid,
        top_fraction=0.5,
        max_positions=1,
        min_names=2,
        one_way_cost_bps=100,
    ).set_index("date")

    assert pnl.loc[dates[0], "n_long"] == 0
    assert pnl.loc[dates[1], "gross_return"] == pytest.approx(0.10)
    assert pnl.loc[dates[1], "cost"] == pytest.approx(0.02)
    assert pnl.loc[dates[1], "net_return"] == pytest.approx(0.08)
    assert pnl.loc[dates[2], "gross_return"] == pytest.approx(0.20)
    assert pnl.loc[dates[2], "cost"] == pytest.approx(0.02)
    assert pnl.loc[dates[2], "round_trip_notional"] == pytest.approx(2.0)


def test_backtest_reports_positions_that_may_not_flatten_at_limit_down() -> None:
    dates = pd.to_datetime(["2025-01-02", "2025-01-03"])
    signal = pd.DataFrame({"A": [2.0, 0.0], "B": [1.0, 0.0]}, index=dates)
    eligible = pd.DataFrame(True, index=dates, columns=["A", "B"])
    open_px = pd.DataFrame(100.0, index=dates, columns=["A", "B"])
    close_px = pd.DataFrame(90.0, index=dates, columns=["A", "B"])
    execution_valid = pd.DataFrame(True, index=dates, columns=["A", "B"])
    exit_blocked = pd.DataFrame({"A": [False, True], "B": [False, False]}, index=dates)

    pnl = backtest_flat(
        signal,
        eligible,
        open_px,
        close_px,
        execution_valid,
        top_fraction=1.0,
        max_positions=2,
        min_names=2,
        one_way_cost_bps=0,
        exit_blocked=exit_blocked,
    ).set_index("date")

    assert pnl.loc[dates[1], "blocked_exit_weight"] == pytest.approx(0.5)
    assert pnl.loc[dates[1], "has_blocked_exit"]


def test_candidate_signals_use_close_known_features_and_mask_event_nonlosers() -> None:
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"])
    open_px = pd.DataFrame({"A": [100.0, 90.0, 80.0], "B": [100.0, 101.0, 102.0]}, index=dates)
    high_px = open_px * 1.02
    low_px = open_px * 0.88
    close_px = pd.DataFrame({"A": [90.0, 80.0, 100.0], "B": [101.0, 102.0, 103.0]}, index=dates)
    volume = pd.DataFrame(1_000.0, index=dates, columns=["A", "B"])
    dvol = close_px * volume

    signals = build_candidate_signals(open_px, high_px, low_px, close_px, volume, dvol)

    assert signals["REV_OC_1"].loc[dates[0], "A"] == pytest.approx(0.10)
    assert signals["MOM_OC_1"].loc[dates[0], "A"] == pytest.approx(-0.10)
    assert signals["EVENT_CC_LOSER_3"].loc[dates[1], "A"] > 0
    assert pd.isna(signals["EVENT_CC_LOSER_3"].loc[dates[1], "B"])


def test_index_gap_direction_uses_open_gap_and_exits_at_same_close() -> None:
    index = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-03"]),
            "open": [100.0, 110.0],
            "close": [100.0, 121.0],
        }
    )

    pnl = backtest_index_gap_direction(index, one_way_cost_bps=10, gap_threshold=0.05)

    assert pnl.loc[1, "position"] == pytest.approx(1.0)
    assert pnl.loc[1, "gross_return"] == pytest.approx(0.10)
    assert pnl.loc[1, "cost"] == pytest.approx(0.002)
    assert pnl.loc[1, "net_return"] == pytest.approx(0.098)


def test_performance_metrics_reports_daily_flat_exposure_and_drawdown() -> None:
    pnl = pd.DataFrame(
        {
            "net_return": [0.10, -0.10, 0.0],
            "gross_return": [0.11, -0.09, 0.0],
            "deployed_weight": [1.0, 0.5, 0.0],
            "n_long": [2, 1, 0],
            "round_trip_notional": [2.0, 1.0, 0.0],
        }
    )

    result = performance_metrics(pnl)

    assert result["ann_return"] == pytest.approx(0.0)
    assert result["max_dd"] == pytest.approx(-0.10)
    assert result["trade_day_ratio"] == pytest.approx(2 / 3)
    assert result["avg_deployed"] == pytest.approx(0.5)


def test_unfilled_names_stay_cash_and_do_not_incur_cost() -> None:
    dates = pd.to_datetime(["2025-01-02", "2025-01-03"])
    signal = pd.DataFrame({"A": [2.0, 0.0], "B": [1.0, 0.0]}, index=dates)
    eligible = pd.DataFrame(True, index=dates, columns=["A", "B"])
    open_px = pd.DataFrame(100.0, index=dates, columns=["A", "B"])
    close_px = pd.DataFrame({"A": [100.0, 110.0], "B": [100.0, 110.0]}, index=dates)
    execution_valid = pd.DataFrame({"A": [True, False], "B": [True, True]}, index=dates)

    pnl = backtest_flat(
        signal,
        eligible,
        open_px,
        close_px,
        execution_valid,
        top_fraction=1.0,
        max_positions=2,
        min_names=2,
        one_way_cost_bps=50,
    ).set_index("date")

    assert pnl.loc[dates[1], "n_long"] == 1
    assert pnl.loc[dates[1], "gross_return"] == pytest.approx(0.05)
    assert pnl.loc[dates[1], "cost"] == pytest.approx(0.005)
    assert pnl.loc[dates[1], "cash_weight"] == pytest.approx(0.5)
