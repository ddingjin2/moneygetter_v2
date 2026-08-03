from __future__ import annotations

import pandas as pd

from v2.scripts.us_residual_reversal_experiment import (
    residual_reversal_signal,
    weekly_metrics,
    weights_from_scores,
)


def test_weights_from_scores_selects_top_decile_names() -> None:
    scores = pd.Series(range(100), index=[f"S{i:03d}" for i in range(100)], dtype="float64")

    weights = weights_from_scores(scores, quantile=0.1)

    assert weights.gt(0).sum() == 10
    assert weights.loc["S099"] == 0.1
    assert weights.loc["S000"] == 0.0


def test_residual_reversal_signal_prefers_negative_residual_losers() -> None:
    stock_returns = pd.DataFrame(
        {
            "A": [0.00, -0.02, -0.02, -0.02, -0.02, -0.02],
            "B": [0.00, 0.02, 0.02, 0.02, 0.02, 0.02],
        },
        index=pd.date_range("2024-01-01", periods=6),
    )
    market_returns = pd.Series([0.0] * 6, index=stock_returns.index)

    signal = residual_reversal_signal(stock_returns, market_returns, lookback=5, beta_window=3)

    assert signal.loc[stock_returns.index[-1], "A"] > signal.loc[stock_returns.index[-1], "B"]


def test_weekly_metrics_counts_win_rate_and_losing_streaks() -> None:
    returns = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=15, freq="B"),
            "net_return": [0.01, 0.0, 0.0, 0.0, 0.0, -0.02, 0.0, 0.0, 0.0, 0.0, -0.01, 0.0, 0.0, 0.0, 0.0],
        }
    )

    metrics = weekly_metrics(returns)

    assert metrics["n_weeks"] == 3
    assert metrics["weekly_win_rate"] == 1 / 3
    assert metrics["max_consecutive_losing_weeks"] == 2
