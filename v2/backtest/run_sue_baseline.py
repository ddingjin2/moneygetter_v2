from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.backtest.fill_model import CostModel, long_entry_cash_price, long_exit_cash_price  # noqa: E402
from v2.backtest.ledger_writer import run_timestamp, write_trade_ledger  # noqa: E402
from v2.data.earnings import EARNINGS_EVENTS_PATH, load_earnings_events, validate_earnings_point_in_time  # noqa: E402
from v2.data.ohlcv import load_ohlcv  # noqa: E402
from v2.evaluation.common_trade_pf import compute_common_trade_pf  # noqa: E402
from v2.evaluation.leakage_check import check_leakage  # noqa: E402
from v2.evaluation.walkforward import COST_SCENARIOS, CostScenario, Fold, run_walkforward  # noqa: E402
from v2.signals.sue_baseline import default_nonmicrocap_filter, generate_signals  # noqa: E402


TRAIN_START = pd.Timestamp("2020-03-27")
TRAIN_END = pd.Timestamp("2023-12-31")
TEST_START = pd.Timestamp("2024-01-01")
TEST_END = pd.Timestamp("2026-04-17")
REPORT_PATH = Path("v2/reports/pr3_sue_baseline_report.md")
POSITIONS_MAX = 20
HOLD_DAYS = 20
LEDGER_COLUMNS = [
    "symbol",
    "entry_date",
    "exit_date",
    "entry_price",
    "exit_price",
    "quantity",
    "pnl",
    "return_pct",
    "signal_score",
    "holding_trading_days",
    "exit_reason",
    "data_source_timestamp",
    "rcept_dt",
    "rcept_time",
    "next_trade_date",
]


@dataclass
class OpenPosition:
    symbol: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    quantity: float
    signal_score: float
    data_source_timestamp: pd.Timestamp | None
    rcept_dt: pd.Timestamp | None
    rcept_time: str | None


def _scenario_cost_model(scenario: CostScenario) -> CostModel:
    return CostModel(
        transaction_cost_bps=scenario.transaction_cost_bps,
        slippage_bps=scenario.slippage_bps,
    )


def _profit_factor(pnl: pd.Series) -> float:
    if pnl.empty:
        return 0.0
    gross_profit = float(pnl.loc[pnl > 0].sum())
    gross_loss = abs(float(pnl.loc[pnl < 0].sum()))
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _metrics(ledger: pd.DataFrame, equity_curve: pd.DataFrame, initial_cash: float) -> dict[str, float]:
    if ledger.empty:
        return {
            "PF": 0.0,
            "win_rate": 0.0,
            "total_return": 0.0,
            "MDD": 0.0,
            "trades": 0,
        }
    pnl = pd.to_numeric(ledger["pnl"], errors="coerce").fillna(0.0)
    equity = pd.to_numeric(equity_curve["equity"], errors="coerce").fillna(initial_cash)
    running_peak = equity.cummax()
    drawdown = (equity - running_peak) / running_peak
    return {
        "PF": _profit_factor(pnl),
        "win_rate": float((pnl > 0).mean()),
        "total_return": float(equity.iloc[-1] / initial_cash - 1) if initial_cash else 0.0,
        "MDD": float(drawdown.min()) if not drawdown.empty else 0.0,
        "trades": int(len(ledger)),
    }


def _prepare_price_maps(ohlcv: pd.DataFrame) -> tuple[pd.DataFrame, dict[tuple[str, pd.Timestamp], pd.Series], dict[str, list[pd.Timestamp]]]:
    required = {"date", "symbol", "open", "close"}
    missing = required - set(ohlcv.columns)
    if missing:
        raise KeyError(f"ohlcv is missing required columns: {sorted(missing)}")

    prices = ohlcv.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()
    prices["symbol"] = prices["symbol"].astype(str).str.zfill(6)
    prices = prices.sort_values(["symbol", "date"]).reset_index(drop=True)
    row_map = {
        (str(row.symbol), pd.Timestamp(row.date)): row
        for row in prices.itertuples(index=False)
    }
    calendar_by_symbol = {
        symbol: list(group["date"])
        for symbol, group in prices.groupby("symbol", sort=False)
    }
    return prices, row_map, calendar_by_symbol


def _filter_ohlcv_for_backtest(
    ohlcv: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    start: pd.Timestamp = TRAIN_START,
    end: pd.Timestamp = TEST_END,
) -> pd.DataFrame:
    if signals.empty:
        return ohlcv.iloc[0:0].copy()
    symbols = set(signals["symbol"].astype(str).str.zfill(6))
    frame = ohlcv.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
    return frame.loc[
        frame["symbol"].isin(symbols) & frame["date"].between(start.normalize(), end.normalize())
    ].copy()


def _exit_date_for(symbol: str, entry_date: pd.Timestamp, calendar_by_symbol: dict[str, list[pd.Timestamp]], hold_days: int) -> pd.Timestamp | None:
    calendar = calendar_by_symbol.get(symbol, [])
    try:
        entry_index = calendar.index(entry_date)
    except ValueError:
        return None
    exit_index = entry_index + hold_days - 1
    if exit_index >= len(calendar):
        return None
    return pd.Timestamp(calendar[exit_index])


def _signal_with_metadata(signals: pd.DataFrame, earnings_events: pd.DataFrame) -> pd.DataFrame:
    metadata_columns = [
        "stock_code",
        "tradable_entry_date",
        "data_source_timestamp",
        "rcept_dt",
        "rcept_time",
        "fiscal_quarter",
    ]
    available = [column for column in metadata_columns if column in earnings_events.columns]
    metadata = earnings_events[available].copy()
    metadata["symbol"] = metadata["stock_code"].astype(str).str.zfill(6)
    metadata["entry_date"] = pd.to_datetime(metadata["tradable_entry_date"]).dt.normalize()
    metadata = metadata.drop(columns=[column for column in ("stock_code", "tradable_entry_date") if column in metadata.columns])
    metadata = metadata.drop_duplicates(["entry_date", "symbol"], keep="first")
    return signals.merge(metadata, on=["entry_date", "symbol"], how="left")


def backtest_sue_baseline(
    *,
    signals: pd.DataFrame,
    earnings_events: pd.DataFrame,
    ohlcv: pd.DataFrame,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    cost_model: CostModel,
    initial_cash: float = 100_000_000.0,
    positions_max: int = POSITIONS_MAX,
    hold_days: int = HOLD_DAYS,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    signals = signals.copy()
    if signals.empty:
        empty_ledger = pd.DataFrame(columns=LEDGER_COLUMNS)
        equity_curve = pd.DataFrame({"date": [start_ts, end_ts], "equity": [initial_cash, initial_cash]})
        return empty_ledger, equity_curve, _metrics(empty_ledger, equity_curve, initial_cash)

    signals["entry_date"] = pd.to_datetime(signals["entry_date"]).dt.normalize()
    signals["symbol"] = signals["symbol"].astype(str).str.zfill(6)
    signals = signals.loc[signals["entry_date"].between(start_ts, end_ts)].copy()
    signals = _signal_with_metadata(signals, earnings_events)
    signals = signals.sort_values(["entry_date", "signal_score"], ascending=[True, False])

    prices, row_map, calendar_by_symbol = _prepare_price_maps(ohlcv)
    trading_days = sorted(prices.loc[prices["date"].between(start_ts, end_ts), "date"].drop_duplicates())
    signal_groups = {pd.Timestamp(day): group for day, group in signals.groupby("entry_date", sort=False)}

    cash = float(initial_cash)
    open_positions: list[OpenPosition] = []
    ledger_rows: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []

    for day in trading_days:
        day = pd.Timestamp(day).normalize()
        remaining_positions: list[OpenPosition] = []
        for position in open_positions:
            if position.exit_date == day:
                price_row = row_map.get((position.symbol, day))
                if price_row is None:
                    remaining_positions.append(position)
                    continue
                exit_price = float(price_row.close)
                cash_exit_price = long_exit_cash_price(exit_price, cost_model)
                proceeds = cash_exit_price * position.quantity
                cash += proceeds
                pnl = proceeds - long_entry_cash_price(position.entry_price, cost_model) * position.quantity
                ledger_rows.append(
                    {
                        "symbol": position.symbol,
                        "entry_date": position.entry_date,
                        "exit_date": day,
                        "entry_price": position.entry_price,
                        "exit_price": exit_price,
                        "quantity": position.quantity,
                        "pnl": pnl,
                        "return_pct": pnl / (long_entry_cash_price(position.entry_price, cost_model) * position.quantity),
                        "signal_score": position.signal_score,
                        "holding_trading_days": hold_days,
                        "exit_reason": "fixed_20d",
                        "data_source_timestamp": position.data_source_timestamp,
                        "rcept_dt": position.rcept_dt,
                        "rcept_time": position.rcept_time,
                        "next_trade_date": position.entry_date,
                    }
                )
            else:
                remaining_positions.append(position)
        open_positions = remaining_positions

        open_symbols = {position.symbol for position in open_positions}
        available_slots = positions_max - len(open_positions)
        if available_slots > 0 and day in signal_groups:
            equity_before_entry = _liquidation_equity(cash, open_positions, row_map, day, cost_model)
            allocation = equity_before_entry / positions_max if positions_max else 0.0
            for signal in signal_groups[day].itertuples(index=False):
                if available_slots <= 0:
                    break
                symbol = str(signal.symbol)
                if symbol in open_symbols:
                    continue
                price_row = row_map.get((symbol, day))
                if price_row is None:
                    continue
                entry_price = float(price_row.open)
                cash_entry_price = long_entry_cash_price(entry_price, cost_model)
                if cash_entry_price <= 0:
                    continue
                spend = min(allocation, cash)
                quantity = spend / cash_entry_price
                if quantity <= 0:
                    continue
                exit_date = _exit_date_for(symbol, day, calendar_by_symbol, hold_days)
                if exit_date is None or exit_date > end_ts:
                    continue
                cash -= quantity * cash_entry_price
                open_positions.append(
                    OpenPosition(
                        symbol=symbol,
                        entry_date=day,
                        exit_date=exit_date,
                        entry_price=entry_price,
                        quantity=quantity,
                        signal_score=float(signal.signal_score),
                        data_source_timestamp=pd.Timestamp(signal.data_source_timestamp)
                        if hasattr(signal, "data_source_timestamp") and not pd.isna(signal.data_source_timestamp)
                        else None,
                        rcept_dt=pd.Timestamp(signal.rcept_dt)
                        if hasattr(signal, "rcept_dt") and not pd.isna(signal.rcept_dt)
                        else None,
                        rcept_time=str(signal.rcept_time)
                        if hasattr(signal, "rcept_time") and not pd.isna(signal.rcept_time)
                        else None,
                    )
                )
                open_symbols.add(symbol)
                available_slots -= 1

        equity_rows.append({"date": day, "equity": _liquidation_equity(cash, open_positions, row_map, day, cost_model)})

    ledger = pd.DataFrame(ledger_rows, columns=LEDGER_COLUMNS)
    equity_curve = pd.DataFrame(equity_rows)
    metrics = _metrics(ledger, equity_curve, initial_cash)
    return ledger, equity_curve, metrics


def _liquidation_equity(
    cash: float,
    open_positions: Sequence[OpenPosition],
    row_map: dict[tuple[str, pd.Timestamp], pd.Series],
    day: pd.Timestamp,
    cost_model: CostModel,
) -> float:
    equity = float(cash)
    for position in open_positions:
        price_row = row_map.get((position.symbol, day))
        if price_row is None:
            continue
        equity += long_exit_cash_price(float(price_row.close), cost_model) * position.quantity
    return equity


def _ledger_for_leakage(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return pd.DataFrame(columns=["symbol", "entry_date"])
    announcement_time = ledger["rcept_time"].fillna("15:30")
    return pd.DataFrame(
        {
            "symbol": ledger["symbol"],
            "entry_date": ledger["entry_date"],
            "feature_available_at": ledger["data_source_timestamp"],
            "earnings_announcement_at": pd.to_datetime(
                pd.to_datetime(ledger["rcept_dt"]).dt.strftime("%Y-%m-%d") + " " + announcement_time
            ),
            "next_trade_date": ledger["next_trade_date"],
        }
    )


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(empty)"
    rendered = frame.copy()
    for column in rendered.columns:
        if pd.api.types.is_float_dtype(rendered[column]):
            rendered[column] = rendered[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    lines = ["| " + " | ".join(rendered.columns) + " |"]
    lines.append("| " + " | ".join(["---"] * len(rendered.columns)) + " |")
    for _, row in rendered.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in rendered.columns) + " |")
    return "\n".join(lines)


def _measurement_rows(results: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(results)[
        ["period", "scenario", "trades", "PF", "win_rate", "total_return", "MDD"]
    ]


def run_pr3(
    *,
    earnings_path: Path = EARNINGS_EVENTS_PATH,
    report_path: Path = REPORT_PATH,
    initial_cash: float = 100_000_000.0,
) -> tuple[str, dict[str, Any]]:
    if not earnings_path.exists():
        raise FileNotFoundError(
            f"{earnings_path} does not exist. Run v2/scripts/build_earnings_dataset.py first."
        )

    earnings_events = load_earnings_events(earnings_path)
    ohlcv = load_ohlcv()
    signals = generate_signals(
        earnings_events=earnings_events,
        ohlcv=ohlcv,
        universe_filter=default_nonmicrocap_filter,
    )
    backtest_ohlcv = _filter_ohlcv_for_backtest(ohlcv, signals)
    signal_symbols = set(signals["symbol"].astype(str).str.zfill(6)) if not signals.empty else set()
    if signal_symbols:
        earnings_events_for_signals = earnings_events.loc[
            earnings_events["stock_code"].astype(str).str.zfill(6).isin(signal_symbols)
        ].copy()
    else:
        earnings_events_for_signals = earnings_events.iloc[0:0].copy()

    measurement_1_rows: list[dict[str, Any]] = []
    stage1_test_ledger_70 = pd.DataFrame()
    for scenario in COST_SCENARIOS:
        cost_model = _scenario_cost_model(scenario)
        for period, start, end in (
            ("train", TRAIN_START, TRAIN_END),
            ("test", TEST_START, TEST_END),
        ):
            ledger, _, metrics = backtest_sue_baseline(
                signals=signals,
                earnings_events=earnings_events_for_signals,
                ohlcv=backtest_ohlcv,
                start=start,
                end=end,
                cost_model=cost_model,
                initial_cash=initial_cash,
            )
            row = {"period": period, "scenario": scenario.name, **metrics}
            measurement_1_rows.append(row)
            if period == "test" and scenario.name == "round_trip_70bps":
                stage1_test_ledger_70 = ledger

    wf_ledgers: list[pd.DataFrame] = []

    def wf_runner(*, fold: Fold, phase: str, cost_scenario: CostScenario, initial_cash: float, reset_positions: bool) -> dict[str, Any]:
        start = fold.train_start if phase == "train" else fold.test_start
        end = fold.train_end if phase == "train" else fold.test_end
        ledger, _, metrics = backtest_sue_baseline(
            signals=signals,
            earnings_events=earnings_events_for_signals,
            ohlcv=backtest_ohlcv,
            start=start,
            end=end,
            cost_model=_scenario_cost_model(cost_scenario),
            initial_cash=initial_cash,
        )
        if phase == "test" and cost_scenario.name == "round_trip_70bps":
            ledger = ledger.copy()
            ledger["fold_id"] = fold.fold_id
            ledger["phase"] = phase
            wf_ledgers.append(ledger)
        return metrics

    wf_folds, wf_summary = run_walkforward(wf_runner, initial_cash=initial_cash)
    wf_70 = wf_summary.loc[wf_summary["scenario"].eq("round_trip_70bps")]
    wf_pf_median = float(wf_70.iloc[0]["pf_median"]) if not wf_70.empty else math.nan
    wf_ledger_70 = pd.concat(wf_ledgers, ignore_index=True) if wf_ledgers else pd.DataFrame()
    ledger_run_ts = run_timestamp()
    ledger_inputs: list[tuple[int, pd.DataFrame]] = [(0, stage1_test_ledger_70)]
    if not wf_ledger_70.empty and "fold_id" in wf_ledger_70.columns:
        for fold_id, fold_ledger in wf_ledger_70.groupby("fold_id", sort=True):
            fold_number = int(str(fold_id).split("_")[-1])
            ledger_inputs.append((fold_number, fold_ledger.drop(columns=["fold_id", "phase"], errors="ignore")))
    ledger_write = write_trade_ledger(
        ledger_inputs,
        pr_tag="pr3",
        variant="a_sue_only",
        run_ts=ledger_run_ts,
        initial_cash=initial_cash,
        signals=signals,
    )

    common = compute_common_trade_pf(
        stage1_test_ledger_70,
        wf_ledger_70,
        (TEST_START.date(), pd.Timestamp("2026-03-26").date()),
    )

    leakage_ledger = _ledger_for_leakage(stage1_test_ledger_70)
    leakage_result = check_leakage(leakage_ledger, ["earnings_yoy_sue"])
    point_in_time_result = validate_earnings_point_in_time(earnings_events)
    leakage_count = sum(len(values) for values in leakage_result.values()) + sum(
        len(values) for values in point_in_time_result.values()
    )

    if leakage_count > 0:
        verdict = "BUG: point-in-time leakage detected. Fix and rerun."
    elif wf_pf_median < 1.0:
        verdict = "FAIL: SUE 단독으로는 엣지 부족. 옵션 B 재검토 또는 PR-4 조건화 레이어 추가 불가피."
    elif float(common["common_trade_pf"]) < 0.8:
        verdict = "FAIL: 공통 trade PF 낮음. v1 과 같은 경로 의존 위험."
    else:
        verdict = "PASS: baseline 엣지 확인. PR-4 진행 권고."

    measurement_1 = _measurement_rows(measurement_1_rows)
    wf_test_70 = wf_folds.loc[
        wf_folds["phase"].eq("test") & wf_folds["scenario"].eq("round_trip_70bps"),
        ["fold_id", "start", "end", "trades", "PF", "total_return"],
    ].copy()
    common_table = pd.DataFrame([common])
    leakage_table = pd.DataFrame(
        [
            {"source": "trade_ledger", "violation_type": kind, "count": len(values), "examples": ", ".join(values[:5])}
            for kind, values in leakage_result.items()
        ]
        + [
            {"source": "earnings_dataset", "violation_type": kind, "count": len(values), "examples": ", ".join(values[:5])}
            for kind, values in point_in_time_result.items()
        ]
    )

    lines = [
        "# PR-3 SUE Baseline Report",
        "",
        "Strategy: top-quintile SUE events, next trading-day open entry, fixed 20-trading-day close exit, equal-weight capacity of 20 positions.",
        "",
        "## Measurement 1. Train/Test",
        _markdown_table(measurement_1),
        "",
        "## Measurement 2. Walk-forward",
        _markdown_table(wf_test_70),
        "",
        _markdown_table(wf_summary.loc[wf_summary["scenario"].eq("round_trip_70bps")]),
        "",
        "## Measurement 3. Common Trade PF",
        _markdown_table(common_table),
        "",
        "## Measurement 4. Leakage",
        _markdown_table(leakage_table),
        "",
        "## Verdict",
        verdict,
        "",
        "## Interpretation",
        _interpret(verdict, wf_pf_median, float(common["common_trade_pf"])),
        "",
        "## Next Step",
        _next_step(verdict),
    ]
    report = "\n".join(lines) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report, {
        "signals": signals,
        "measurement_1": measurement_1,
        "wf_folds": wf_folds,
        "wf_summary": wf_summary,
        "common": common,
        "leakage_count": leakage_count,
        "verdict": verdict,
        "ledger_write": ledger_write,
    }


def _interpret(verdict: str, wf_pf_median: float, common_pf: float) -> str:
    if verdict.startswith("PASS"):
        return f"SUE 단독 신호가 비용 적용 후 WF median PF {wf_pf_median:.4f}, common PF {common_pf:.4f}를 통과했다."
    if "SUE 단독" in verdict:
        return f"SUE 단독 신호의 WF median PF는 {wf_pf_median:.4f}로 1.0 미만이다. 단독 알파는 약하며 조건화 없이는 baseline으로 부족하다."
    if "공통 trade" in verdict:
        return f"WF median PF는 버텼지만 common PF {common_pf:.4f}가 낮아 trade-set 경로 의존 위험이 크다."
    return "Point-in-time 위반이 있어 성과 해석을 중단해야 한다."


def _next_step(verdict: str) -> str:
    if verdict.startswith("PASS"):
        return "PR-4의 52-week high proximity 조건화를 진행한다."
    if "SUE 단독" in verdict:
        return "PR-4 진행 전 사용자와 상의한다. 가격 위치와 attention 조건화로 해결 가능한지 확인해야 한다."
    if "공통 trade" in verdict:
        return "옵션 B 신호 설계를 재검토한다. 공통 trade가 약하면 v1과 같은 경로 의존 실패가 반복될 수 있다."
    return "누수 원인을 수정한 뒤 PR-3을 재실행한다."


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PR-3 SUE baseline evaluation.")
    parser.add_argument("--earnings-path", default=str(EARNINGS_EVENTS_PATH))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--initial-cash", type=float, default=100_000_000.0)
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    report, _ = run_pr3(
        earnings_path=Path(args.earnings_path),
        report_path=Path(args.report_path),
        initial_cash=args.initial_cash,
    )
    print(report)


if __name__ == "__main__":
    main()
