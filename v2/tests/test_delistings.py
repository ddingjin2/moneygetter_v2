from __future__ import annotations

import sys
import threading
from pathlib import Path

import pandas as pd
import pytest

from v2.data.delistings import apply_delisting_registry, settle_delisted_positions
from v2.data.universe import get_active_universe
from v2.scripts.paper_account_a4 import DEFAULT_CAPITAL as ACCOUNT_DEFAULT_CAPITAL
from v2.scripts.paper_account_a4 import build_paper_trade_command, calculate_account_equity
from v2.scripts.paper_trade_a4 import DEFAULT_CAPITAL as TRADE_DEFAULT_CAPITAL
from v2.scripts.paper_trade_a4 import build_a4_rank
from v2.scripts.run_after_close_a4 import (
    PYTHON_EXECUTABLE,
    build_data_update_commands,
    build_financial_update_commands,
    build_shadow_command,
    run_parallel_update_lanes,
)
from v2.scripts.update_market_dataset_v2 import load_universe_records


def _registry() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": ["008500"],
            "name": ["일정실업"],
            "last_trading_date": ["2026-06-29"],
            "delisted_date": ["2026-06-30"],
            "reason": ["시가총액 미달"],
            "source_url": ["https://example.com/disclosure"],
        }
    )


def test_registry_sets_universe_last_active_date() -> None:
    universe = pd.DataFrame(
        {
            "code": ["008500", "005930"],
            "name": ["일정실업", "삼성전자"],
            "listed_date": ["2020-01-02", "2020-01-02"],
            "delisted_date": [pd.NaT, pd.NaT],
        }
    )

    updated = apply_delisting_registry(universe, _registry())

    event = updated.loc[updated["code"].eq("008500")].iloc[0]
    assert event["delisted_date"] == pd.Timestamp("2026-06-29")
    assert pd.isna(updated.loc[updated["code"].eq("005930"), "delisted_date"].iloc[0])
    assert "008500" not in get_active_universe("2026-07-14", universe=updated)
    assert "005930" in get_active_universe("2026-07-14", universe=updated)


def test_market_update_excludes_symbols_delisted_before_incremental_start(tmp_path) -> None:
    universe_path = tmp_path / "universe.parquet"
    registry_path = tmp_path / "delistings.csv"
    pd.DataFrame(
        {
            "code": ["008500", "005930"],
            "name": ["일정실업", "삼성전자"],
            "listed_date": ["2020-01-02", "2020-01-02"],
            "delisted_date": [pd.NaT, pd.NaT],
        }
    ).to_parquet(universe_path, index=False)
    _registry().to_csv(registry_path, index=False)

    records = load_universe_records(
        start=pd.Timestamp("2026-07-11"),
        universe_path=universe_path,
        registry_path=registry_path,
    )

    assert [record.ticker for record in records] == ["005930"]


def test_paper_account_default_capital_is_100m_krw() -> None:
    assert ACCOUNT_DEFAULT_CAPITAL == 100_000_000.0
    assert TRADE_DEFAULT_CAPITAL == 100_000_000


def test_after_close_runner_uses_current_python_interpreter() -> None:
    assert PYTHON_EXECUTABLE == sys.executable


def test_after_close_runner_updates_kospi_benchmark_with_market_data() -> None:
    commands = build_data_update_commands()

    assert commands == [
        [PYTHON_EXECUTABLE, "scripts/update_market_dataset_v2.py"],
        [PYTHON_EXECUTABLE, "scripts/update_kospi_benchmark.py"],
        [PYTHON_EXECUTABLE, "scripts/prepare_price_market_cap_full.py"],
        [PYTHON_EXECUTABLE, "scripts/refresh_a4_signal.py"],
    ]


def test_after_close_runner_builds_financial_update_and_shadow_commands() -> None:
    commands = build_financial_update_commands("2026-08-30")

    assert commands == [
        [
            PYTHON_EXECUTABLE,
            "scripts/build_earnings_dataset.py",
            "--start-date",
            "2019-01-01",
            "--end-date",
            "2026-08-30",
            "--ohlcv-path",
            "data/processed/market_ohlcv.parquet",
            "--output",
            "data/cache/earnings_events.parquet",
            "--checkpoint",
            "data/cache/earnings_events_partial.parquet",
            "--checkpoint-every",
            "100",
            "--max-workers",
            "4",
        ],
        [
            PYTHON_EXECUTABLE,
            "scripts/validate_earnings_data.py",
            "--earnings-path",
            "data/cache/earnings_events.parquet",
            "--ohlcv-path",
            "data/processed/market_ohlcv.parquet",
            "--output",
            "reports/earnings_data_quality.md",
        ],
    ]
    assert build_shadow_command() == [
        PYTHON_EXECUTABLE,
        "spikes/a4_financial_multifactor.py",
        "--run",
    ]


def test_after_close_update_lanes_start_in_parallel() -> None:
    barrier = threading.Barrier(2)
    started: list[str] = []

    def fake_run(command: list[str], execute: bool, cwd: Path) -> dict:
        started.append(command[0])
        barrier.wait(timeout=1.0)
        return {"cmd": command[0], "returncode": 0}

    result = run_parallel_update_lanes(
        {"market": [["market"]], "financial": [["financial"]]},
        execute=True,
        cwd=Path("."),
        runner=fake_run,
    )

    assert sorted(started) == ["financial", "market"]
    assert result["market"]["status"] == "pass"
    assert result["financial"]["status"] == "pass"


def test_financial_lane_failure_is_reported_without_hiding_market_success() -> None:
    def fake_run(command: list[str], execute: bool, cwd: Path) -> dict:
        if command[0] == "financial":
            raise SystemExit("dart unavailable")
        return {"cmd": command[0], "returncode": 0}

    result = run_parallel_update_lanes(
        {"market": [["market"]], "financial": [["financial"]]},
        execute=True,
        cwd=Path("."),
        runner=fake_run,
    )

    assert result["market"]["status"] == "pass"
    assert result["financial"]["status"] == "fail"
    assert "dart unavailable" in result["financial"]["error"]


def test_rebalance_notional_uses_current_account_equity() -> None:
    account = {"cash": 1_000_000.0, "initial_capital": 100_000_000.0}
    positions = pd.DataFrame({"code": ["005930"], "shares": [10]})
    prices = pd.DataFrame({"close": [2_000_000.0]}, index=pd.Index(["005930"], name="code"))

    assert calculate_account_equity(account, positions, prices) == 21_000_000.0


def test_paper_trade_subprocess_uses_current_python_interpreter(tmp_path) -> None:
    command = build_paper_trade_command(
        capital=10_000_000.0,
        buy_fee=0.001,
        sell_fee=0.001,
        positions_path=tmp_path / "positions.csv",
        asof="2026-07-14",
    )

    assert command[0] == sys.executable


def test_a4_rank_excludes_codes_outside_active_universe() -> None:
    dates = pd.bdate_range("2026-04-22", periods=60)
    panel = pd.concat(
        [
            pd.DataFrame(
                {
                    "date": dates,
                    "code": code,
                    "name": name,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": volume,
                    "trading_value": close * volume,
                    "dvol": close * volume,
                }
            )
            for code, name, close, volume in [
                ("008500", "일정실업", 624.0, 1000.0),
                ("005930", "삼성전자", 100.0, 10000.0),
            ]
        ],
        ignore_index=True,
    )

    rank = build_a4_rank(
        panel,
        dates[-1],
        lookback=60,
        top_q=0.10,
        active_codes={"005930"},
    )

    assert rank["code"].tolist() == ["005930"]


def test_settlement_sells_all_shares_at_last_trading_close() -> None:
    account = {"cash": 1000.0, "sell_fee": 0.001}
    positions = pd.DataFrame(
        {"code": ["008500"], "name": ["일정실업"], "shares": [2], "avg_cost": [3000.0]}
    )
    prices = pd.DataFrame(
        {
            "code": ["008500", "008500"],
            "date": ["2026-06-26", "2026-06-29"],
            "name": ["일정실업", "일정실업"],
            "close": [620.0, 624.0],
        }
    )

    updated_account, updated_positions, trades = settle_delisted_positions(
        account,
        positions,
        _registry(),
        prices,
        asof=pd.Timestamp("2026-07-14"),
    )

    assert updated_positions.empty
    assert updated_account["cash"] == pytest.approx(2246.752)
    assert len(trades) == 1
    assert trades.loc[0, "date"] == pd.Timestamp("2026-06-29")
    assert trades.loc[0, "side"] == "SELL"
    assert trades.loc[0, "event"] == "DELISTING"
    assert trades.loc[0, "price"] == 624.0
    assert trades.loc[0, "cash_flow"] == pytest.approx(1246.752)


def test_settlement_blocks_when_final_trading_price_is_missing() -> None:
    account = {"cash": 1000.0, "sell_fee": 0.001}
    positions = pd.DataFrame(
        {"code": ["008500"], "name": ["일정실업"], "shares": [2], "avg_cost": [3000.0]}
    )
    prices = pd.DataFrame(
        {"code": ["008500"], "date": ["2026-06-26"], "name": ["일정실업"], "close": [620.0]}
    )

    with pytest.raises(ValueError, match="008500.*2026-06-29"):
        settle_delisted_positions(
            account,
            positions,
            _registry(),
            prices,
            asof=pd.Timestamp("2026-07-14"),
        )
