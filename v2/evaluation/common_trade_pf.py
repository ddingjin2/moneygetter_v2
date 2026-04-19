from __future__ import annotations

import math
from datetime import date
from typing import Tuple

import pandas as pd


REQUIRED_LEDGER_COLUMNS = {"symbol", "entry_date", "pnl"}


def _profit_factor(frame: pd.DataFrame, pnl_column: str = "pnl") -> float:
    if frame.empty:
        return 0.0
    pnl = pd.to_numeric(frame[pnl_column], errors="coerce").fillna(0.0)
    gross_profit = float(pnl.loc[pnl > 0].sum())
    gross_loss = abs(float(pnl.loc[pnl < 0].sum()))
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _validate_ledger(frame: pd.DataFrame, name: str) -> None:
    missing = REQUIRED_LEDGER_COLUMNS - set(frame.columns)
    if missing:
        raise KeyError(f"{name} ledger is missing required columns: {sorted(missing)}")


def _prepare_ledger(
    ledger: pd.DataFrame,
    *,
    name: str,
    overlap_period: Tuple[date, date],
) -> pd.DataFrame:
    _validate_ledger(ledger, name)
    start, end = (pd.Timestamp(value).normalize() for value in overlap_period)
    frame = ledger.copy()
    if "phase" in frame.columns:
        frame = frame.loc[frame["phase"].astype(str).str.lower().eq("test")].copy()
    frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.normalize()
    frame = frame.loc[frame["entry_date"].between(start, end)].copy()
    frame["match_key"] = frame["symbol"].astype(str) + "|" + frame["entry_date"].dt.strftime("%Y-%m-%d")
    return frame


def _wf_median_pf(wf_ledger: pd.DataFrame) -> float:
    if wf_ledger.empty:
        return 0.0
    if "fold_id" not in wf_ledger.columns:
        return _profit_factor(wf_ledger)

    fold_pfs = [
        _profit_factor(group)
        for _, group in wf_ledger.groupby("fold_id", sort=True)
        if not group.empty
    ]
    if not fold_pfs:
        return 0.0
    return float(pd.Series(fold_pfs, dtype="float64").median())


def _verdict(common_trade_pf: float) -> str:
    if common_trade_pf >= 1.2:
        return "edge_confirmed"
    if common_trade_pf >= 0.8:
        return "legacy_effect_suspected"
    return "no_edge"


def compute_common_trade_pf(
    stage1_ledger: pd.DataFrame,
    wf_ledger: pd.DataFrame,
    overlap_period: Tuple[date, date],
) -> dict:
    """Compare Stage 1 and walk-forward ledgers on shared trade keys.

    A common trade is a (symbol, entry_date) key present in both ledgers. The
    common-trade PF is computed from the Stage 1 PnL of that shared trade set,
    matching the Stage 6.5 diagnostic that exposed v1 path dependence.
    """

    stage1 = _prepare_ledger(stage1_ledger, name="stage1", overlap_period=overlap_period)
    wf = _prepare_ledger(wf_ledger, name="walk-forward", overlap_period=overlap_period)

    stage1_keys = set(stage1["match_key"])
    wf_keys = set(wf["match_key"])
    common_keys = stage1_keys & wf_keys

    common = stage1.loc[stage1["match_key"].isin(common_keys)].copy()
    stage1_only = stage1.loc[~stage1["match_key"].isin(common_keys)].copy()

    stage1_profit = pd.to_numeric(stage1["pnl"], errors="coerce").fillna(0.0)
    stage1_only_profit = pd.to_numeric(stage1_only["pnl"], errors="coerce").fillna(0.0)
    gross_profit = float(stage1_profit.loc[stage1_profit > 0].sum())
    stage1_only_gross_profit = float(stage1_only_profit.loc[stage1_only_profit > 0].sum())
    stage1_only_pnl_share = stage1_only_gross_profit / gross_profit if gross_profit else 0.0

    common_pf = _profit_factor(common)
    return {
        "stage1_test_pf": _profit_factor(stage1),
        "wf_median_pf": _wf_median_pf(wf),
        "common_trade_count": len(common_keys),
        "common_trade_pf": common_pf,
        "stage1_only_pnl_share": stage1_only_pnl_share,
        "verdict": _verdict(common_pf),
    }

