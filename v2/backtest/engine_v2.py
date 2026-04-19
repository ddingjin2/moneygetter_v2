from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v2.backtest.fill_model import DEFAULT_SLIPPAGE_BPS, DEFAULT_TRANSACTION_COST_BPS


DEFAULT_V1_ROOT = Path("C:/dev/moneygetter")


@dataclass(frozen=True)
class EngineV2Options:
    """Execution constraints shared by all future v2 strategy evaluations."""

    initial_cash: float = 100_000_000.0
    long_only: bool = True
    nonmicrocap_filter: bool = True
    block_limit_bars: bool = True
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS


def resolve_v1_root(v1_root: str | Path | None = None) -> Path:
    configured = v1_root or os.environ.get("MONEYGETTER_V1_ROOT")
    return Path(configured) if configured else DEFAULT_V1_ROOT


def _ensure_v1_on_path(v1_root: str | Path | None = None) -> Path:
    root = resolve_v1_root(v1_root)
    if not root.exists():
        raise FileNotFoundError(root)
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def load_v1_backtest_inputs(
    *,
    settings_path: str | Path,
    data_config_path: str | Path,
    start_date: str,
    end_date: str,
    v1_root: str | Path | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """Read v1 inputs without modifying v1 code or writing into v1 folders."""

    _ensure_v1_on_path(v1_root)
    app_backtest = importlib.import_module("app.backtest")
    return app_backtest.load_backtest_inputs(
        settings_path=Path(settings_path),
        data_config_path=Path(data_config_path),
        start_date=start_date,
        end_date=end_date,
    )


def build_v1_engine(settings: dict[str, Any], *, v1_root: str | Path | None = None) -> Any:
    _ensure_v1_on_path(v1_root)
    app_backtest = importlib.import_module("app.backtest")
    return app_backtest.build_backtest_engine(settings)


def apply_v2_cost_options(
    settings: dict[str, Any],
    options: EngineV2Options = EngineV2Options(),
) -> dict[str, Any]:
    updated = dict(settings)
    updated["transaction_cost_bps"] = options.transaction_cost_bps
    updated["slippage_bps"] = options.slippage_bps
    return updated


def validate_long_only(ledger: pd.DataFrame) -> None:
    """Reject explicit short trades in v2 evaluation ledgers."""

    if "side" in ledger.columns:
        short_side = ledger["side"].astype(str).str.lower().isin({"short", "sell_short"})
        if bool(short_side.any()):
            raise ValueError("v2 allows long-only ledgers only")
    if "position" in ledger.columns and bool((ledger["position"] < 0).any()):
        raise ValueError("v2 allows long-only ledgers only")

