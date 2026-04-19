from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.backtest.run_sue_baseline import (  # noqa: E402
    TEST_END,
    TEST_START,
    TRAIN_END,
    TRAIN_START,
    _filter_ohlcv_for_backtest,
    _ledger_for_leakage,
    _markdown_table,
    _scenario_cost_model,
    backtest_sue_baseline,
)
from v2.backtest.ledger_writer import run_timestamp, write_trade_ledger  # noqa: E402
from v2.data.earnings import EARNINGS_EVENTS_PATH, load_earnings_events, validate_earnings_point_in_time  # noqa: E402
from v2.data.ohlcv import load_ohlcv  # noqa: E402
from v2.evaluation.common_trade_pf import compute_common_trade_pf  # noqa: E402
from v2.evaluation.leakage_check import check_leakage  # noqa: E402
from v2.evaluation.walkforward import COST_SCENARIOS, CostScenario, Fold, run_walkforward  # noqa: E402
from v2.signals.proximity import compute_daily_proximity  # noqa: E402
from v2.signals.sue_baseline import default_nonmicrocap_filter, generate_signals as generate_sue_signals  # noqa: E402
from v2.signals.sue_proximity import generate_signals as generate_sue_proximity_signals  # noqa: E402


REPORT_PATH = Path("v2/reports/pr4_proximity_report.md")
PROXIMITY_THRESHOLD = 0.95
FAR_THRESHOLD = 0.60
ROUND_TRIP_70 = next(scenario for scenario in COST_SCENARIOS if scenario.name == "round_trip_70bps")
VARIANT_SLUGS = {
    "A": "a_sue_only",
    "B": "b_sue_near_high",
    "C": "c_sue_far_from_high",
    "D": "d_proximity_only",
}


@dataclass(frozen=True)
class Variant:
    variant_id: str
    name: str
    signal_factory: Callable[[pd.DataFrame, pd.DataFrame, pd.DataFrame], pd.DataFrame]


def _profit_factor(pnl: pd.Series) -> float:
    if pnl.empty:
        return 0.0
    values = pd.to_numeric(pnl, errors="coerce").fillna(0.0)
    gross_profit = float(values.loc[values > 0].sum())
    gross_loss = abs(float(values.loc[values < 0].sum()))
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _variant_definitions() -> list[Variant]:
    return [
        Variant(
            "A",
            "SUE Only",
            lambda earnings, ohlcv, proximity: generate_sue_signals(
                earnings_events=earnings,
                ohlcv=ohlcv,
                universe_filter=default_nonmicrocap_filter,
            ),
        ),
        Variant(
            "B",
            "SUE + Near High",
            lambda earnings, ohlcv, proximity: generate_sue_proximity_signals(
                earnings_events=earnings,
                ohlcv=ohlcv,
                universe_filter=default_nonmicrocap_filter,
                proximity_threshold=PROXIMITY_THRESHOLD,
                sue_top_quintile=True,
                proximity_direction="near",
                precomputed_proximity=proximity,
            ),
        ),
        Variant(
            "C",
            "SUE + Far from High",
            lambda earnings, ohlcv, proximity: generate_sue_proximity_signals(
                earnings_events=earnings,
                ohlcv=ohlcv,
                universe_filter=default_nonmicrocap_filter,
                proximity_threshold=FAR_THRESHOLD,
                sue_top_quintile=True,
                proximity_direction="far",
                precomputed_proximity=proximity,
            ),
        ),
        Variant(
            "D",
            "Proximity Only",
            lambda earnings, ohlcv, proximity: generate_sue_proximity_signals(
                earnings_events=earnings,
                ohlcv=ohlcv,
                universe_filter=default_nonmicrocap_filter,
                proximity_threshold=PROXIMITY_THRESHOLD,
                sue_top_quintile=False,
                proximity_direction="near",
                precomputed_proximity=proximity,
            ),
        ),
    ]


def _earnings_for_signal_symbols(earnings_events: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    if signals.empty:
        return earnings_events.iloc[0:0].copy()
    symbols = set(signals["symbol"].astype(str).str.zfill(6))
    return earnings_events.loc[earnings_events["stock_code"].astype(str).str.zfill(6).isin(symbols)].copy()


def _signals_for_leakage(signals: pd.DataFrame, ledger: pd.DataFrame) -> pd.DataFrame:
    if signals.empty or ledger.empty or "proximity_as_of_date" not in signals.columns:
        return ledger.copy()
    keyed = signals[["symbol", "entry_date", "proximity_as_of_date"]].copy()
    keyed["symbol"] = keyed["symbol"].astype(str).str.zfill(6)
    keyed["entry_date"] = pd.to_datetime(keyed["entry_date"]).dt.normalize()
    keyed = keyed.drop_duplicates(["symbol", "entry_date"], keep="first")

    enriched = ledger.copy()
    enriched["symbol"] = enriched["symbol"].astype(str).str.zfill(6)
    enriched["entry_date"] = pd.to_datetime(enriched["entry_date"]).dt.normalize()
    enriched = enriched.merge(keyed, on=["symbol", "entry_date"], how="left")
    enriched["lookback_end_date"] = enriched["proximity_as_of_date"]
    return enriched


def _run_variant(
    *,
    variant: Variant,
    earnings_events: pd.DataFrame,
    ohlcv: pd.DataFrame,
    proximity: pd.DataFrame,
    initial_cash: float,
) -> dict[str, Any]:
    signals = variant.signal_factory(earnings_events, ohlcv, proximity)
    backtest_ohlcv = _filter_ohlcv_for_backtest(ohlcv, signals)
    earnings_for_signals = _earnings_for_signal_symbols(earnings_events, signals)

    measurement_rows: list[dict[str, Any]] = []
    stage1_test_ledger_70 = pd.DataFrame()
    stage1_test_equity_70 = pd.DataFrame()
    for scenario in COST_SCENARIOS:
        for period, start, end in (
            ("train", TRAIN_START, TRAIN_END),
            ("test", TEST_START, TEST_END),
        ):
            ledger, equity, metrics = backtest_sue_baseline(
                signals=signals,
                earnings_events=earnings_for_signals,
                ohlcv=backtest_ohlcv,
                start=start,
                end=end,
                cost_model=_scenario_cost_model(scenario),
                initial_cash=initial_cash,
            )
            measurement_rows.append(
                {
                    "variant": variant.variant_id,
                    "name": variant.name,
                    "period": period,
                    "scenario": scenario.name,
                    **metrics,
                }
            )
            if period == "test" and scenario.name == ROUND_TRIP_70.name:
                stage1_test_ledger_70 = ledger
                stage1_test_equity_70 = equity

    wf_ledgers: list[pd.DataFrame] = []

    def wf_runner(*, fold: Fold, phase: str, cost_scenario: CostScenario, initial_cash: float, reset_positions: bool) -> dict[str, Any]:
        start = fold.train_start if phase == "train" else fold.test_start
        end = fold.train_end if phase == "train" else fold.test_end
        ledger, _, metrics = backtest_sue_baseline(
            signals=signals,
            earnings_events=earnings_for_signals,
            ohlcv=backtest_ohlcv,
            start=start,
            end=end,
            cost_model=_scenario_cost_model(cost_scenario),
            initial_cash=initial_cash,
        )
        if phase == "test":
            ledger = ledger.copy()
            ledger["fold_id"] = fold.fold_id
            ledger["phase"] = phase
            wf_ledgers.append(ledger)
        return metrics

    wf_folds, wf_summary = run_walkforward(
        wf_runner,
        initial_cash=initial_cash,
        cost_scenarios=(ROUND_TRIP_70,),
    )
    wf_ledger_70 = pd.concat(wf_ledgers, ignore_index=True) if wf_ledgers else pd.DataFrame()
    common = compute_common_trade_pf(
        stage1_test_ledger_70,
        wf_ledger_70,
        (TEST_START.date(), pd.Timestamp("2026-03-26").date()),
    )

    leakage_ledger = _ledger_for_leakage(stage1_test_ledger_70)
    leakage_ledger = _signals_for_leakage(signals, leakage_ledger)
    leakage = check_leakage(leakage_ledger, ["earnings_yoy_sue", "52_week_high_proximity"])
    leakage_count = sum(len(values) for values in leakage.values())

    return {
        "variant": variant,
        "signals": signals,
        "measurement": pd.DataFrame(measurement_rows),
        "stage1_test_ledger_70": stage1_test_ledger_70,
        "stage1_test_equity_70": stage1_test_equity_70,
        "wf_folds": wf_folds,
        "wf_summary": wf_summary,
        "wf_ledger_70": wf_ledger_70,
        "common": common,
        "leakage": leakage,
        "leakage_count": leakage_count,
    }


def _kospi_proxy_index(ohlcv: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "symbol", "close"}
    missing = required - set(ohlcv.columns)
    if missing:
        raise KeyError(f"ohlcv is missing required columns: {sorted(missing)}")

    frame = ohlcv.copy()
    if "market" in frame.columns:
        frame = frame.loc[frame["market"].astype(str).eq("KOSPI")].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.loc[frame["close"].gt(0)].sort_values(["symbol", "date"]).copy()
    frame["ret"] = frame.groupby("symbol", sort=False)["close"].pct_change()
    daily = frame.groupby("date", sort=True)["ret"].mean().fillna(0.0).reset_index(name="daily_return")
    daily["index"] = (1.0 + daily["daily_return"]).cumprod()
    return daily


def _max_drawdown(index_values: pd.Series) -> float:
    if index_values.empty:
        return math.nan
    running_peak = index_values.cummax()
    drawdown = (index_values - running_peak) / running_peak
    return float(drawdown.min())


def _fold_regime_context(results: dict[str, dict[str, Any]], ohlcv: pd.DataFrame) -> pd.DataFrame:
    kospi = _kospi_proxy_index(ohlcv)
    rows: list[dict[str, object]] = []
    for result in results.values():
        variant = result["variant"]
        folds = result["wf_folds"]
        test = folds.loc[folds["phase"].eq("test") & folds["scenario"].eq(ROUND_TRIP_70.name)]
        for row in test.itertuples(index=False):
            start = pd.Timestamp(row.start).normalize()
            end = pd.Timestamp(row.end).normalize()
            period = kospi.loc[kospi["date"].between(start, end)].copy()
            if period.empty:
                kospi_return = math.nan
                kospi_mdd = math.nan
                kospi_volatility = math.nan
            else:
                kospi_return = float(period["index"].iloc[-1] / period["index"].iloc[0] - 1.0)
                kospi_mdd = _max_drawdown(period["index"] / period["index"].iloc[0])
                kospi_volatility = float(period["daily_return"].std() * math.sqrt(252))
            rows.append(
                {
                    "variant": f"{variant.variant_id}. {variant.name}",
                    "fold_id": row.fold_id,
                    "test_period": f"{row.start} ~ {row.end}",
                    "kospi_proxy_return": kospi_return,
                    "kospi_proxy_mdd": kospi_mdd,
                    "kospi_proxy_volatility": kospi_volatility,
                    "strategy_pf": float(row.PF),
                    "strategy_trades": int(row.trades),
                    "strategy_total_return": float(row.total_return),
                }
            )
    return pd.DataFrame(rows)


def _pnl_concentration(ledger: pd.DataFrame, freq: str) -> tuple[pd.DataFrame, dict[str, float]]:
    if ledger.empty:
        empty = pd.DataFrame(columns=["period", "pnl"])
        return empty, {
            "top_3_periods_share": math.nan,
            "top_period_share": math.nan,
            "positive_periods_ratio": math.nan,
            "period_pnl_std": math.nan,
        }

    frame = ledger.copy()
    frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.normalize()
    frame["period"] = frame["entry_date"].dt.to_period(freq).astype(str)
    pnl = frame.groupby("period", sort=True)["pnl"].sum().reset_index()
    total = float(pnl["pnl"].sum())
    ranked = pnl.sort_values("pnl", ascending=False)
    top3 = float(ranked.head(3)["pnl"].sum())
    top1 = float(ranked.head(1)["pnl"].sum()) if len(ranked) else math.nan
    stats = {
        "top_3_periods_share": top3 / total if total != 0 else math.nan,
        "top_period_share": top1 / total if total != 0 else math.nan,
        "positive_periods_ratio": float((pnl["pnl"] > 0).mean()) if len(pnl) else math.nan,
        "period_pnl_std": float(pnl["pnl"].std()) if len(pnl) else math.nan,
    }
    return pnl, stats


def _summary_matrix(results: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for result in results.values():
        variant = result["variant"]
        measurement = result["measurement"]
        train = measurement.loc[measurement["period"].eq("train") & measurement["scenario"].eq(ROUND_TRIP_70.name)].iloc[0]
        test = measurement.loc[measurement["period"].eq("test") & measurement["scenario"].eq(ROUND_TRIP_70.name)].iloc[0]
        wf = result["wf_summary"].loc[result["wf_summary"]["scenario"].eq(ROUND_TRIP_70.name)].iloc[0]
        rows.append(
            {
                "Variant": f"{variant.variant_id}. {variant.name}",
                "Train PF": float(train.PF),
                "Test PF": float(test.PF),
                "WF Median PF": float(wf.pf_median),
                "Common PF": float(result["common"]["common_trade_pf"]),
                "MDD": float(test.MDD),
                "Trades": int(test.trades),
                "WF Trades": int(wf.test_trades_total),
                "Common Trades": int(result["common"]["common_trade_count"]),
                "Leakage Violations": int(result["leakage_count"]),
            }
        )
    return pd.DataFrame(rows)


def _directionality_table(summary: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    values = {
        row["Variant"].split(".", 1)[0]: float(row["WF Median PF"])
        for _, row in summary.iterrows()
    }
    rows = []
    for relation, lhs, rhs in (
        ("B > A", "B", "A"),
        ("B > C", "B", "C"),
        ("B > D", "B", "D"),
    ):
        passed = values.get(lhs, math.nan) > values.get(rhs, math.nan)
        rows.append(
            {
                "Relation": relation,
                "Left WF Median PF": values.get(lhs, math.nan),
                "Right WF Median PF": values.get(rhs, math.nan),
                "Passes": bool(passed),
            }
        )
    table = pd.DataFrame(rows)
    return table, bool(table["Passes"].all()) if not table.empty else False


def _commercial_gate_table(summary: pd.DataFrame, results: dict[str, dict[str, Any]], concentration: dict[str, float]) -> tuple[pd.DataFrame, bool]:
    b_row = summary.loc[summary["Variant"].str.startswith("B.")].iloc[0]
    b_folds = results["B"]["wf_folds"]
    b_test_folds = b_folds.loc[b_folds["phase"].eq("test") & b_folds["scenario"].eq(ROUND_TRIP_70.name)]
    min_fold_pf = float(pd.to_numeric(b_test_folds["PF"], errors="coerce").min()) if len(b_test_folds) else math.nan
    rows = [
        {
            "Gate": "WF median PF >= 1.3",
            "Value": float(b_row["WF Median PF"]),
            "Threshold": ">= 1.3",
            "Passes": bool(float(b_row["WF Median PF"]) >= 1.3),
        },
        {
            "Gate": "Common trade PF >= 1.0",
            "Value": float(b_row["Common PF"]),
            "Threshold": ">= 1.0",
            "Passes": bool(float(b_row["Common PF"]) >= 1.0),
        },
        {
            "Gate": "MDD >= -20%",
            "Value": float(b_row["MDD"]),
            "Threshold": ">= -0.20",
            "Passes": bool(float(b_row["MDD"]) >= -0.20),
        },
        {
            "Gate": "Minimum fold PF >= 0.9",
            "Value": min_fold_pf,
            "Threshold": ">= 0.9",
            "Passes": bool(min_fold_pf >= 0.9),
        },
        {
            "Gate": "Top 3 months share < 150%",
            "Value": float(concentration["top_3_periods_share"]),
            "Threshold": "< 1.5",
            "Passes": bool(float(concentration["top_3_periods_share"]) < 1.5),
        },
    ]
    table = pd.DataFrame(rows)
    return table, bool(table["Passes"].all())


def _final_verdict(reproduction_passed: bool, commercial_passed: bool) -> str:
    if reproduction_passed and commercial_passed:
        return "PASS: Goh & Jeon directionality reproduced and commercial gates passed. Recommend PR-5."
    if reproduction_passed:
        return "PARTIAL: Directionality reproduced, but at least one commercial gate failed. Review PR-5 mitigations."
    return "FAIL: Goh & Jeon directionality was not reproduced. Re-evaluate Option B before PR-5."


def build_report(
    *,
    results: dict[str, dict[str, Any]],
    earnings_events: pd.DataFrame,
    ohlcv: pd.DataFrame,
) -> str:
    summary = _summary_matrix(results)
    directionality, reproduction_passed = _directionality_table(summary)
    regime = _fold_regime_context(results, ohlcv)
    monthly_pnl, monthly_concentration = _pnl_concentration(results["B"]["stage1_test_ledger_70"], "M")
    quarterly_pnl, quarterly_concentration = _pnl_concentration(results["B"]["stage1_test_ledger_70"], "Q")
    gates, commercial_passed = _commercial_gate_table(summary, results, monthly_concentration)
    point_in_time = validate_earnings_point_in_time(earnings_events)
    point_in_time_rows = pd.DataFrame(
        [
            {"violation_type": kind, "count": len(values), "examples": ", ".join(values[:5])}
            for kind, values in point_in_time.items()
        ]
    )

    verdict = _final_verdict(reproduction_passed, commercial_passed)
    b_folds = results["B"]["wf_folds"]
    b_fold_dist = b_folds.loc[
        b_folds["phase"].eq("test") & b_folds["scenario"].eq(ROUND_TRIP_70.name),
        ["fold_id", "start", "end", "trades", "PF", "total_return"],
    ]

    concentration_table = pd.DataFrame(
        [
            {"frequency": "monthly", **monthly_concentration},
            {"frequency": "quarterly", **quarterly_concentration},
        ]
    )

    lines = [
        "# PR-4 52-Week High Proximity Report",
        "",
        "Thresholds are fixed before evaluation: near-high proximity >= 0.95, far-from-high proximity <= 0.60.",
        "No OPENDART calls are made; this report reuses the existing earnings_events.parquet.",
        "",
        "## Section 1. Variant Comparison Matrix",
        _markdown_table(summary),
        "",
        "## Section 2. Goh & Jeon Directionality Test",
        _markdown_table(directionality),
        "",
        f"Directionality reproduced: {reproduction_passed}",
        "",
        "## Section 3. Fold Regime Analysis",
        "KOSPI context uses an equal-weight KOSPI-stock proxy from local OHLCV because the dataset has no official index row.",
        _markdown_table(regime),
        "",
        "Strategy B fold distribution:",
        _markdown_table(b_fold_dist),
        "",
        "## Section 4. PnL Concentration",
        "Strategy B uses the fixed Train/Test test ledger at 70bps.",
        _markdown_table(concentration_table),
        "",
        "Monthly PnL:",
        _markdown_table(monthly_pnl),
        "",
        "Quarterly PnL:",
        _markdown_table(quarterly_pnl),
        "",
        "## Section 5. Commercialization Gates",
        _markdown_table(gates),
        "",
        f"All commercial gates passed: {commercial_passed}",
        "",
        "Leakage checks by variant:",
        _markdown_table(
            pd.DataFrame(
                [
                    {
                        "Variant": f"{result['variant'].variant_id}. {result['variant'].name}",
                        "trade_ledger_violations": int(result["leakage_count"]),
                    }
                    for result in results.values()
                ]
            )
        ),
        "",
        "Earnings dataset point-in-time checks:",
        _markdown_table(point_in_time_rows),
        "",
        "## Section 6. Final Verdict",
        verdict,
        "",
        "## Section 7. Uncertainty And Constraints",
        "- Goh & Jeon reported long-short monthly returns on 2004-2015 data; this is a 2020-2026 long-only test after 70bps round-trip costs.",
        "- The local OHLCV file has all-zero market_cap and no official KOSPI index row, so regime context uses an equal-weight KOSPI-stock proxy.",
        "- The 2020-2026 period includes unusual Korean-market regimes, including the 2023-2024 short-sale ban period.",
        "- The proximity threshold is fixed at 0.95. No threshold sensitivity search was run in this PR.",
        "- Directionality, not numeric equality with the paper, is the reproduction target.",
        "",
    ]
    return "\n".join(lines)


def run_pr4(
    *,
    earnings_path: Path = EARNINGS_EVENTS_PATH,
    report_path: Path = REPORT_PATH,
    initial_cash: float = 100_000_000.0,
) -> tuple[str, dict[str, Any]]:
    if not earnings_path.exists():
        raise FileNotFoundError(earnings_path)

    earnings_events = load_earnings_events(earnings_path)
    ohlcv = load_ohlcv()
    proximity = compute_daily_proximity(ohlcv)

    results = {
        variant.variant_id: _run_variant(
            variant=variant,
            earnings_events=earnings_events,
            ohlcv=ohlcv,
            proximity=proximity,
            initial_cash=initial_cash,
        )
        for variant in _variant_definitions()
    }
    ledger_run_ts = run_timestamp()
    for variant_id, result in results.items():
        ledger_inputs: list[tuple[int, pd.DataFrame]] = [(0, result["stage1_test_ledger_70"])]
        wf_ledger = result["wf_ledger_70"]
        if not wf_ledger.empty and "fold_id" in wf_ledger.columns:
            for fold_id, fold_ledger in wf_ledger.groupby("fold_id", sort=True):
                fold_number = int(str(fold_id).split("_")[-1])
                ledger_inputs.append((fold_number, fold_ledger.drop(columns=["fold_id", "phase"], errors="ignore")))
        result["ledger_write"] = write_trade_ledger(
            ledger_inputs,
            pr_tag="pr4",
            variant=VARIANT_SLUGS[variant_id],
            run_ts=ledger_run_ts,
            initial_cash=initial_cash,
            signals=result["signals"],
        )

    report = build_report(results=results, earnings_events=earnings_events, ohlcv=ohlcv)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report, results


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PR-4 52-week high proximity ablation.")
    parser.add_argument("--earnings-path", default=str(EARNINGS_EVENTS_PATH))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--initial-cash", type=float, default=100_000_000.0)
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    report, _ = run_pr4(
        earnings_path=Path(args.earnings_path),
        report_path=Path(args.report_path),
        initial_cash=args.initial_cash,
    )
    print(report)


if __name__ == "__main__":
    main()
