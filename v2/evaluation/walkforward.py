from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Mapping, Sequence

import pandas as pd


STAGE6_START = date(2020, 3, 27)
STAGE6_END = date(2026, 4, 17)
STAGE6_GATE_PF = 1.2


@dataclass(frozen=True)
class Fold:
    fold_id: str
    train_start: date
    train_end: date
    test_start: date
    test_end: date

    def as_strings(self) -> dict[str, str]:
        return {
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
        }


@dataclass(frozen=True)
class CostScenario:
    name: str
    transaction_cost_bps: float
    slippage_bps: float

    @property
    def round_trip_bps(self) -> float:
        return 2 * (self.transaction_cost_bps + self.slippage_bps)


COST_SCENARIOS: tuple[CostScenario, ...] = (
    CostScenario("round_trip_0bps", 0.0, 0.0),
    CostScenario("round_trip_50bps", 15.0, 10.0),
    CostScenario("round_trip_70bps", 20.0, 15.0),
)


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def build_stage6_folds(
    *,
    start: date = STAGE6_START,
    end: date = STAGE6_END,
    train_years: int = 3,
    test_years: int = 1,
) -> list[Fold]:
    """Build full 3-year train / 1-year test rolling folds."""

    folds: list[Fold] = []
    fold_start = start
    fold_number = 1
    while True:
        train_start = fold_start
        train_end = _add_years(train_start, train_years) - timedelta(days=1)
        test_start = train_end + timedelta(days=1)
        test_end = _add_years(test_start, test_years) - timedelta(days=1)
        if test_end > end:
            break
        folds.append(
            Fold(
                fold_id=f"fold_{fold_number}",
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
        fold_start = _add_years(fold_start, 1)
        fold_number += 1
    return folds


STAGE6_FOLDS: tuple[Fold, ...] = tuple(build_stage6_folds())


def _metric(result: Mapping[str, object], *names: str, default: float = math.nan) -> float:
    for name in names:
        if name in result:
            return float(result[name])
    return default


def _trade_count(result: Mapping[str, object]) -> int:
    if "trades" not in result:
        return int(result.get("trade_count", 0))
    trades = result["trades"]
    if isinstance(trades, int | float):
        return int(trades)
    try:
        return len(trades)  # type: ignore[arg-type]
    except TypeError:
        return int(trades)  # type: ignore[arg-type]


def summarize_fold_results(fold_results: pd.DataFrame) -> pd.DataFrame:
    if fold_results.empty:
        return pd.DataFrame(
            columns=[
                "scenario",
                "test_folds",
                "test_trades_total",
                "pf_median",
                "pf_mean",
                "pf_min",
                "pf_max",
                "passes_stage6_gate",
            ]
        )

    test = fold_results.loc[fold_results["phase"].eq("test")].copy()
    group_columns = ["scenario"]
    if "strategy" in test.columns:
        group_columns.insert(0, "strategy")

    rows: list[dict[str, object]] = []
    for keys, group in test.groupby(group_columns, sort=False, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_columns, keys, strict=False))
        pf = pd.to_numeric(group["PF"], errors="coerce").dropna()
        pf_median = float(pf.median()) if len(pf) else math.nan
        row.update(
            {
                "test_folds": int(len(group)),
                "test_trades_total": int(pd.to_numeric(group["trades"], errors="coerce").fillna(0).sum()),
                "pf_median": pf_median,
                "pf_mean": float(pf.mean()) if len(pf) else math.nan,
                "pf_min": float(pf.min()) if len(pf) else math.nan,
                "pf_max": float(pf.max()) if len(pf) else math.nan,
                "passes_stage6_gate": bool(pf_median >= STAGE6_GATE_PF) if not math.isnan(pf_median) else False,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def run_walkforward(
    run_phase: Callable[..., Mapping[str, object]],
    *,
    folds: Sequence[Fold] = STAGE6_FOLDS,
    cost_scenarios: Sequence[CostScenario] = COST_SCENARIOS,
    initial_cash: float = 100_000_000.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Execute isolated train/test phases through a supplied backtest runner.

    The runner is called once per fold, phase, and cost scenario with
    reset_positions=True. That keeps this module strategy-free while enforcing
    the Stage 6 restart contract.
    """

    rows: list[dict[str, object]] = []
    for scenario in cost_scenarios:
        for fold in folds:
            for phase in ("train", "test"):
                result = run_phase(
                    fold=fold,
                    phase=phase,
                    cost_scenario=scenario,
                    initial_cash=initial_cash,
                    reset_positions=True,
                )
                start = fold.train_start if phase == "train" else fold.test_start
                end = fold.train_end if phase == "train" else fold.test_end
                row: dict[str, object] = {
                    "scenario": scenario.name,
                    "round_trip_bps": scenario.round_trip_bps,
                    "transaction_cost_bps": scenario.transaction_cost_bps,
                    "slippage_bps": scenario.slippage_bps,
                    "fold_id": fold.fold_id,
                    "phase": phase,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "trades": _trade_count(result),
                    "total_return": _metric(result, "total_return"),
                    "PF": _metric(result, "PF", "profit_factor", "pf"),
                }
                if "strategy" in result:
                    row["strategy"] = result["strategy"]
                rows.append(row)

    fold_results = pd.DataFrame(rows)
    return fold_results, summarize_fold_results(fold_results)

