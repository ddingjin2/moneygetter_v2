from __future__ import annotations

from datetime import date

import pandas as pd

from v2.evaluation.common_trade_pf import compute_common_trade_pf
from v2.evaluation.leakage_check import check_leakage
from v2.evaluation.walkforward import COST_SCENARIOS, STAGE6_FOLDS, build_stage6_folds, run_walkforward


def _ledger(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_common_trade_pf_edge_confirmed() -> None:
    stage1 = _ledger(
        [
            {"symbol": "AAA", "entry_date": "2024-01-02", "pnl": 15.0, "phase": "test"},
            {"symbol": "BBB", "entry_date": "2024-01-03", "pnl": -10.0, "phase": "test"},
            {"symbol": "CCC", "entry_date": "2024-01-04", "pnl": 5.0, "phase": "test"},
        ]
    )
    wf = _ledger(
        [
            {"symbol": "AAA", "entry_date": "2024-01-02", "pnl": 1.0, "fold_id": "fold_1", "phase": "test"},
            {"symbol": "BBB", "entry_date": "2024-01-03", "pnl": -1.0, "fold_id": "fold_1", "phase": "test"},
        ]
    )

    result = compute_common_trade_pf(stage1, wf, (date(2024, 1, 1), date(2024, 12, 31)))

    assert result["common_trade_count"] == 2
    assert result["common_trade_pf"] == 1.5
    assert result["verdict"] == "edge_confirmed"


def test_common_trade_pf_legacy_effect_suspected() -> None:
    stage1 = _ledger(
        [
            {"symbol": "AAA", "entry_date": "2024-01-02", "pnl": 10.0},
            {"symbol": "BBB", "entry_date": "2024-01-03", "pnl": -10.0},
            {"symbol": "CCC", "entry_date": "2024-01-04", "pnl": 20.0},
        ]
    )
    wf = _ledger(
        [
            {"symbol": "AAA", "entry_date": "2024-01-02", "pnl": 10.0, "fold_id": "fold_1"},
            {"symbol": "BBB", "entry_date": "2024-01-03", "pnl": -10.0, "fold_id": "fold_1"},
        ]
    )

    result = compute_common_trade_pf(stage1, wf, (date(2024, 1, 1), date(2024, 12, 31)))

    assert result["common_trade_pf"] == 1.0
    assert result["verdict"] == "legacy_effect_suspected"


def test_common_trade_pf_no_edge() -> None:
    stage1 = _ledger(
        [
            {"symbol": "AAA", "entry_date": "2024-01-02", "pnl": 5.0},
            {"symbol": "BBB", "entry_date": "2024-01-03", "pnl": -10.0},
            {"symbol": "CCC", "entry_date": "2024-01-04", "pnl": 100.0},
        ]
    )
    wf = _ledger(
        [
            {"symbol": "AAA", "entry_date": "2024-01-02", "pnl": 5.0, "fold_id": "fold_1"},
            {"symbol": "BBB", "entry_date": "2024-01-03", "pnl": -10.0, "fold_id": "fold_1"},
        ]
    )

    result = compute_common_trade_pf(stage1, wf, (date(2024, 1, 1), date(2024, 12, 31)))

    assert result["common_trade_pf"] == 0.5
    assert result["stage1_only_pnl_share"] == 100.0 / 105.0
    assert result["verdict"] == "no_edge"


def test_walkforward_folds_match_stage6_boundaries() -> None:
    folds = build_stage6_folds()

    assert [(fold.fold_id, fold.train_start.isoformat(), fold.train_end.isoformat(), fold.test_start.isoformat(), fold.test_end.isoformat()) for fold in folds] == [
        ("fold_1", "2020-03-27", "2023-03-26", "2023-03-27", "2024-03-26"),
        ("fold_2", "2021-03-27", "2024-03-26", "2024-03-27", "2025-03-26"),
        ("fold_3", "2022-03-27", "2025-03-26", "2025-03-27", "2026-03-26"),
    ]
    assert tuple(folds) == STAGE6_FOLDS


def test_walkforward_runner_outputs_fold_rows_and_summary() -> None:
    calls: list[tuple[str, str, str, bool]] = []

    def fake_runner(*, fold, phase, cost_scenario, initial_cash, reset_positions):
        calls.append((fold.fold_id, phase, cost_scenario.name, reset_positions))
        return {
            "trades": 10,
            "total_return": 0.01,
            "PF": 1.3 if phase == "test" and cost_scenario.round_trip_bps == 70 else 1.0,
        }

    fold_results, summary = run_walkforward(fake_runner, folds=STAGE6_FOLDS[:1], cost_scenarios=COST_SCENARIOS)

    assert len(fold_results) == 6
    assert all(call[3] for call in calls)
    scenario70 = summary.loc[summary["scenario"].eq("round_trip_70bps")].iloc[0]
    assert scenario70["pf_median"] == 1.3
    assert bool(scenario70["passes_stage6_gate"]) is True


def test_leakage_check_detects_future_price_window() -> None:
    ledger = _ledger(
        [
            {
                "symbol": "AAA",
                "entry_date": "2024-06-03",
                "high_52w_window_end": "2024-06-04",
            }
        ]
    )

    result = check_leakage(ledger, ["52w_high"])

    assert result["future_price"] == ["AAA|2024-06-03"]
    assert result["point_in_time"] == []


def test_leakage_check_detects_after_close_earnings_same_day_entry() -> None:
    ledger = _ledger(
        [
            {
                "symbol": "AAA",
                "entry_date": "2024-05-10",
                "earnings_announcement_at": "2024-05-10 16:10:00",
            }
        ]
    )

    result = check_leakage(ledger, ["earnings_surprise"])

    assert result["earnings_after_close"] == ["AAA|2024-05-10"]

