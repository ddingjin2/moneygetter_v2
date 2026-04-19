from __future__ import annotations

import filecmp
import shutil
from pathlib import Path
from uuid import uuid4

import pandas as pd

from v2.backtest.ledger_writer import LEDGER_COLUMNS, write_trade_ledger


def _output_dir() -> Path:
    path = Path("v2/data/cache/test_ledger_writer") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cleanup(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _ledger() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "005930",
                "entry_date": pd.Timestamp("2024-01-02"),
                "exit_date": pd.Timestamp("2024-01-29"),
                "entry_price": 100.0,
                "exit_price": 110.0,
                "quantity": 10.0,
                "pnl": 93.0,
                "return_pct": 0.093,
                "signal_score": 2.5,
                "holding_trading_days": 20,
                "exit_reason": "fixed_20d",
            }
        ]
    )


def _signals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "005930",
                "entry_date": pd.Timestamp("2024-01-02"),
                "sue_score": 2.5,
                "proximity": 0.97,
            }
        ]
    )


def test_write_trade_ledger_creates_timestamped_and_latest_files() -> None:
    output_dir = _output_dir()
    try:
        result = write_trade_ledger(
            [(0, _ledger())],
            pr_tag="prx",
            variant="a_sue_only",
            run_ts="20260419_213000",
            initial_cash=10_000.0,
            signals=_signals(),
            output_dir=output_dir,
        )

        assert result.timestamped_path.exists()
        assert result.latest_path.exists()
        assert filecmp.cmp(result.timestamped_path, result.latest_path, shallow=False)
    finally:
        _cleanup(output_dir)


def test_write_trade_ledger_schema_contains_required_columns() -> None:
    output_dir = _output_dir()
    try:
        result = write_trade_ledger(
            [(0, _ledger())],
            pr_tag="prx",
            variant="a_sue_only",
            run_ts="20260419_213000",
            initial_cash=10_000.0,
            signals=_signals(),
            output_dir=output_dir,
        )

        saved = pd.read_parquet(result.latest_path)

        assert list(saved.columns) == LEDGER_COLUMNS
        assert saved.iloc[0]["trade_id"]
        assert saved.iloc[0]["variant"] == "a_sue_only"
        assert float(saved.iloc[0]["sue_value"]) == 2.5
        assert float(saved.iloc[0]["proximity_value"]) == 0.97
    finally:
        _cleanup(output_dir)


def test_write_trade_ledger_accepts_empty_ledger() -> None:
    output_dir = _output_dir()
    try:
        result = write_trade_ledger(
            [(0, pd.DataFrame())],
            pr_tag="prx",
            variant="empty",
            run_ts="20260419_213000",
            initial_cash=10_000.0,
            output_dir=output_dir,
        )

        saved = pd.read_parquet(result.latest_path)

        assert result.rows == 0
        assert list(saved.columns) == LEDGER_COLUMNS
        assert saved.empty
    finally:
        _cleanup(output_dir)
