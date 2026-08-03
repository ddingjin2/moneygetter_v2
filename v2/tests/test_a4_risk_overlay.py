from __future__ import annotations

import pandas as pd
import pytest

from v2.scripts.a4_risk_overlay import RiskOverlayConfig, simulate_risk_overlay


def _frame(values: dict[str, list[float]]) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=len(next(iter(values.values()))), freq="D")
    return pd.DataFrame(values, index=dates, dtype="float64")


def _signal_like(prices: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({column: range(1, len(prices) + 1) for column in prices.columns}, index=prices.index, dtype="float64")


def test_fixed_stop_sells_next_open_and_waits_for_rebalance() -> None:
    open_px = _frame({"A": [100, 100, 85, 85, 85]})
    close_px = _frame({"A": [100, 89, 85, 85, 85]})

    daily, events = simulate_risk_overlay(
        open_px,
        close_px,
        _signal_like(open_px),
        RiskOverlayConfig(position_kind="fixed", position_threshold=-0.10),
        rebalance_days=10,
        top_q=1.0,
        min_universe=1,
        cost_bps=0,
    )

    assert events.loc[events["event"].eq("position_stop_trigger"), "date"].tolist() == [pd.Timestamp("2026-01-02")]
    assert events.loc[events["event"].eq("position_stop_fill"), "date"].tolist() == [pd.Timestamp("2026-01-03")]
    assert daily.set_index("date").loc[pd.Timestamp("2026-01-03"), "position_count"] == 0
    assert daily.iloc[-1]["position_count"] == 0


def test_trailing_stop_uses_highest_close_since_entry() -> None:
    open_px = _frame({"A": [100, 100, 120, 100, 100]})
    close_px = _frame({"A": [100, 120, 101, 100, 100]})

    daily, events = simulate_risk_overlay(
        open_px,
        close_px,
        _signal_like(open_px),
        RiskOverlayConfig(position_kind="trailing", position_threshold=-0.15),
        rebalance_days=10,
        top_q=1.0,
        min_universe=1,
        cost_bps=0,
    )

    trigger = events.loc[events["event"].eq("position_stop_trigger")].iloc[0]
    assert trigger["date"] == pd.Timestamp("2026-01-03")
    assert trigger["trigger_return"] == pytest.approx(101 / 120 - 1)
    assert events.loc[events["event"].eq("position_stop_fill"), "date"].tolist() == [pd.Timestamp("2026-01-04")]


def test_exclude_mask_drops_code_from_rebalance_selection() -> None:
    open_px = _frame({"A": [100, 100, 100], "B": [100, 100, 100]})
    close_px = open_px.copy()
    exclude = pd.DataFrame(False, index=open_px.index, columns=open_px.columns)
    exclude["B"] = True

    daily, _ = simulate_risk_overlay(
        open_px,
        close_px,
        _signal_like(open_px),
        RiskOverlayConfig(),
        rebalance_days=10,
        top_q=1.0,
        min_universe=1,
        cost_bps=0,
        exclude=exclude,
    )

    assert daily.iloc[-1]["position_count"] == 1
    assert daily.iloc[-1]["gross_exposure"] == pytest.approx(1.0, abs=0.01)


@pytest.mark.parametrize(
    ("action", "expected_positions", "expected_exposure"),
    [("cash", 0, 0.0), ("half", 2, 0.5)],
)
def test_portfolio_drawdown_defense_executes_next_open(
    action: str,
    expected_positions: int,
    expected_exposure: float,
) -> None:
    open_px = _frame({"A": [100, 100, 100, 90, 90], "B": [100, 100, 100, 90, 90]})
    close_px = _frame({"A": [100, 100, 89, 90, 90], "B": [100, 100, 89, 90, 90]})

    daily, events = simulate_risk_overlay(
        open_px,
        close_px,
        _signal_like(open_px),
        RiskOverlayConfig(portfolio_mdd=-0.10, portfolio_action=action),
        rebalance_days=10,
        top_q=1.0,
        min_universe=1,
        cost_bps=0,
    )

    assert events.loc[events["event"].eq("portfolio_guard_trigger"), "date"].tolist() == [pd.Timestamp("2026-01-03")]
    assert events.loc[events["event"].eq("portfolio_guard_fill"), "date"].tolist() == [pd.Timestamp("2026-01-04")]
    row = daily.set_index("date").loc[pd.Timestamp("2026-01-04")]
    assert row["position_count"] == expected_positions
    assert row["gross_exposure"] == pytest.approx(expected_exposure, abs=0.01)
