from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRICE_DIR = ROOT / "v2/data/cache/price_market_cap_full"
SIGNAL_PATH = ROOT / "v2/data/cache/signals_batch/A4_cs_zscore.parquet"
OUTPUT_DIR = ROOT / "v2/data/cache/a4_risk_overlay"
REPORT_PATH = ROOT / "v2/reports/a4_risk_overlay.md"


@dataclass(frozen=True)
class RiskOverlayConfig:
    position_kind: str | None = None
    position_threshold: float | None = None
    portfolio_mdd: float | None = None
    portfolio_action: str | None = None

    def __post_init__(self) -> None:
        if self.position_kind not in {None, "fixed", "trailing"}:
            raise ValueError(f"Unknown position stop: {self.position_kind}")
        if self.position_kind is not None and self.position_threshold is None:
            raise ValueError("Position stop requires position_threshold")
        if self.portfolio_action not in {None, "cash", "half"}:
            raise ValueError(f"Unknown portfolio action: {self.portfolio_action}")
        if self.portfolio_action is not None and self.portfolio_mdd is None:
            raise ValueError("Portfolio action requires portfolio_mdd")


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def _atomic_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _top_codes(values: pd.Series, top_q: float, min_universe: int) -> list[str]:
    valid = values.dropna().sort_values()
    if len(valid) < min_universe:
        return []
    count = max(int(math.floor(len(valid) * top_q)), 1)
    return [str(code) for code in valid.tail(count).index]


def simulate_risk_overlay(
    open_px: pd.DataFrame,
    close_px: pd.DataFrame,
    signal: pd.DataFrame,
    config: RiskOverlayConfig,
    *,
    rebalance_days: int = 20,
    top_q: float = 0.10,
    min_universe: int = 30,
    cost_bps: int = 30,
    initial_capital: float = 1.0,
    exclude: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate A4 long-only portfolio with close trigger and next-open execution."""

    dates = open_px.index.intersection(close_px.index).intersection(signal.index).sort_values()
    codes = open_px.columns.intersection(close_px.columns).intersection(signal.columns)
    open_px = open_px.reindex(index=dates, columns=codes).apply(pd.to_numeric, errors="coerce")
    close_px = close_px.reindex(index=dates, columns=codes).apply(pd.to_numeric, errors="coerce")
    signal = signal.reindex(index=dates, columns=codes).apply(pd.to_numeric, errors="coerce")
    if exclude is not None:
        exclude = exclude.reindex(index=dates, columns=codes).fillna(False).astype(bool)
    rate = float(cost_bps) / 10000.0

    shares = pd.Series(0.0, index=codes)
    avg_cost = pd.Series(np.nan, index=codes)
    peak_close = pd.Series(np.nan, index=codes)
    last_price = pd.Series(np.nan, index=codes)
    cash = float(initial_capital)
    previous_equity = float(initial_capital)
    cycle_peak: float | None = None
    pending_stops: set[str] = set()
    pending_guard: str | None = None
    guard_active = False
    rows: list[dict[str, object]] = []
    events: list[dict[str, object]] = []

    def trade_to_targets(target_shares: pd.Series, prices: pd.Series, date: pd.Timestamp) -> tuple[float, float]:
        nonlocal cash, shares, avg_cost, peak_close
        traded = 0.0
        fees = 0.0
        deltas = target_shares - shares
        for code in deltas[deltas.lt(-1e-12)].index:
            if not prices.get(code, np.nan) > 0:
                continue
            quantity = min(float(-deltas[code]), float(shares[code]))
            gross = quantity * float(prices[code])
            fee = gross * rate
            cash += gross - fee
            shares[code] -= quantity
            traded += gross
            fees += fee
            if shares[code] <= 1e-12:
                shares[code] = 0.0
                avg_cost[code] = np.nan
                peak_close[code] = np.nan
        for code in deltas[deltas.gt(1e-12)].index:
            if not prices.get(code, np.nan) > 0:
                continue
            quantity = float(deltas[code])
            gross = quantity * float(prices[code])
            fee = gross * rate
            old_shares = float(shares[code])
            old_basis = float(avg_cost[code]) if pd.notna(avg_cost[code]) else 0.0
            new_shares = old_shares + quantity
            avg_cost[code] = (old_shares * old_basis + gross + fee) / new_shares
            if old_shares <= 1e-12:
                peak_close[code] = float(prices[code])
            shares[code] = new_shares
            cash -= gross + fee
            traded += gross
            fees += fee
        if traded > 0:
            events.append({"date": date, "event": "trade", "code": None, "trigger_return": np.nan, "gross": traded, "fee": fees})
        return traded, fees

    for index, date_value in enumerate(dates):
        date = pd.Timestamp(date_value)
        raw_open = open_px.loc[date]
        valid_open = raw_open.where(raw_open.gt(0))
        last_price = valid_open.combine_first(last_price)
        valuation_open = valid_open.combine_first(last_price)
        equity_pre = cash + float((shares * valuation_open.fillna(0.0)).sum())
        traded = 0.0
        fees = 0.0
        scheduled = index > 0 and ((index - 1) % rebalance_days) == 0

        if scheduled:
            pending_stops.clear()
            pending_guard = None
            guard_active = False
            selected = _top_codes(signal.iloc[index - 1], top_q, min_universe)
            if exclude is not None:
                dropped = exclude.iloc[index - 1]
                selected = [code for code in selected if not dropped.get(code, False)]
            selected = [code for code in selected if valid_open.get(code, np.nan) > 0]
            targets = pd.Series(0.0, index=codes)
            if selected:
                investable = max(equity_pre, 0.0) / (1.0 + rate)
                for code in selected:
                    targets[code] = (investable / len(selected)) / float(valid_open[code])
            traded, fees = trade_to_targets(targets, valid_open, date)
            events.append({"date": date, "event": "rebalance", "code": None, "trigger_return": np.nan, "gross": traded, "fee": fees})
            cycle_peak = None
        else:
            for code in sorted(pending_stops):
                price = valid_open.get(code, np.nan)
                if not price > 0 or shares.get(code, 0.0) <= 0:
                    continue
                quantity = float(shares[code])
                target = shares.copy()
                target[code] = 0.0
                gross, fee = trade_to_targets(target, valid_open, date)
                traded += gross
                fees += fee
                events.append({"date": date, "event": "position_stop_fill", "code": code, "trigger_return": np.nan, "gross": quantity * float(price), "fee": quantity * float(price) * rate})
            pending_stops = {code for code in pending_stops if shares.get(code, 0.0) > 1e-12}

            if pending_guard is not None:
                targets = shares.copy()
                if pending_guard == "cash":
                    targets[:] = 0.0
                elif pending_guard == "half":
                    targets *= 0.5
                gross, fee = trade_to_targets(targets, valid_open, date)
                traded += gross
                fees += fee
                events.append({"date": date, "event": "portfolio_guard_fill", "code": None, "trigger_return": np.nan, "gross": gross, "fee": fee})
                pending_guard = None

        market_value = float((shares * valuation_open.fillna(0.0)).sum())
        equity_post = cash + market_value
        net_return = equity_post / previous_equity - 1.0 if previous_equity else 0.0
        gross_exposure = market_value / equity_post if equity_post > 0 else 0.0

        raw_close = close_px.loc[date]
        valuation_close = raw_close.where(raw_close.gt(0)).combine_first(valuation_open).fillna(0.0)
        held = shares.gt(1e-12)
        peak_close.loc[held] = pd.concat([peak_close.loc[held], valuation_close.loc[held]], axis=1).max(axis=1)
        peak_close.loc[~held] = np.nan
        equity_close = cash + float((shares * valuation_close).sum())

        if config.position_kind is not None and config.position_threshold is not None:
            reference = avg_cost if config.position_kind == "fixed" else peak_close
            trigger_return = valuation_close / reference - 1.0
            triggered = held & trigger_return.le(config.position_threshold)
            for code in trigger_return.index[triggered.fillna(False)]:
                if code not in pending_stops:
                    pending_stops.add(str(code))
                    events.append(
                        {
                            "date": date,
                            "event": "position_stop_trigger",
                            "code": str(code),
                            "trigger_return": float(trigger_return[code]),
                            "gross": 0.0,
                            "fee": 0.0,
                        }
                    )

        if scheduled or cycle_peak is None:
            cycle_peak = equity_close
        else:
            cycle_peak = max(cycle_peak, equity_close)
        portfolio_drawdown = equity_close / cycle_peak - 1.0 if cycle_peak else 0.0
        if (
            config.portfolio_mdd is not None
            and config.portfolio_action is not None
            and not guard_active
            and portfolio_drawdown <= config.portfolio_mdd
        ):
            pending_guard = config.portfolio_action
            guard_active = True
            events.append(
                {
                    "date": date,
                    "event": "portfolio_guard_trigger",
                    "code": None,
                    "trigger_return": float(portfolio_drawdown),
                    "gross": 0.0,
                    "fee": 0.0,
                }
            )

        rows.append(
            {
                "date": date,
                "equity": equity_post,
                "net_return": net_return,
                "cash": cash,
                "market_value": market_value,
                "position_count": int(held.sum()),
                "gross_exposure": gross_exposure,
                "turnover_notional": traded,
                "fees": fees,
                "portfolio_drawdown_close": portfolio_drawdown,
            }
        )
        previous_equity = equity_post

    event_columns = ["date", "event", "code", "trigger_return", "gross", "fee"]
    return pd.DataFrame(rows), pd.DataFrame(events, columns=event_columns)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames = []
    for path in sorted(PRICE_DIR.glob("[0-9][0-9][0-9][0-9][0-9][0-9].parquet")):
        frame = pd.read_parquet(path, columns=["date", "open", "close"])
        frame["code"] = path.stem
        frames.append(frame)
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    open_px = panel.pivot(index="date", columns="code", values="open").sort_index()
    close_px = panel.pivot(index="date", columns="code", values="close").reindex_like(open_px)
    raw_signal = pd.read_parquet(SIGNAL_PATH)
    raw_signal["date"] = pd.to_datetime(raw_signal["date"]).dt.normalize()
    signal = raw_signal.pivot(index="date", columns="code", values="signal_cs_z").reindex(index=open_px.index, columns=open_px.columns)
    return open_px, close_px, signal


def metrics(daily: pd.DataFrame) -> dict[str, float]:
    returns = daily["net_return"].astype("float64")
    annual_return = float(returns.mean() * 252)
    annual_volatility = float(returns.std(ddof=1) * math.sqrt(252))
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    max_dd = float((equity / equity.cummax() - 1.0).min())
    return {
        "sharpe": annual_return / annual_volatility if annual_volatility else math.nan,
        "ann_return": annual_return,
        "ann_vol": annual_volatility,
        "max_dd": max_dd,
        "final_equity": float(daily["equity"].iloc[-1]),
        "avg_exposure": float(daily["gross_exposure"].mean()),
    }


def candidate_configs() -> dict[str, RiskOverlayConfig]:
    configs = {"baseline": RiskOverlayConfig()}
    position_rules = {
        "fixed_10": ("fixed", -0.10),
        "fixed_15": ("fixed", -0.15),
        "fixed_20": ("fixed", -0.20),
        "trailing_15": ("trailing", -0.15),
    }
    for position_name, (kind, threshold) in position_rules.items():
        for action in ["cash", "half"]:
            configs[f"{position_name}_mdd10_{action}"] = RiskOverlayConfig(
                position_kind=kind,
                position_threshold=threshold,
                portfolio_mdd=-0.10,
                portfolio_action=action,
            )
    return configs


def markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in frame.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("NA" if math.isnan(value) else f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def run_experiment() -> dict[str, object]:
    open_px, close_px, signal = load_inputs()
    configs = candidate_configs()
    result_rows = []
    daily_frames = []
    event_frames = []
    for cost_bps in [10, 30]:
        for name, config in configs.items():
            daily, events = simulate_risk_overlay(
                open_px,
                close_px,
                signal,
                config,
                rebalance_days=20,
                top_q=0.10,
                min_universe=30,
                cost_bps=cost_bps,
                initial_capital=100_000_000.0,
            )
            summary = metrics(daily)
            summary.update(
                {
                    "variant": name,
                    "cost_bps": cost_bps,
                    "position_stop_triggers": int(events["event"].eq("position_stop_trigger").sum()),
                    "portfolio_guard_triggers": int(events["event"].eq("portfolio_guard_trigger").sum()),
                }
            )
            result_rows.append(summary)
            daily.insert(0, "cost_bps", cost_bps)
            daily.insert(0, "variant", name)
            events.insert(0, "cost_bps", cost_bps)
            events.insert(0, "variant", name)
            daily_frames.append(daily)
            event_frames.append(events)

    results = pd.DataFrame(result_rows)
    for cost_bps in [10, 30]:
        baseline = results.loc[results["cost_bps"].eq(cost_bps) & results["variant"].eq("baseline")].iloc[0]
        mask = results["cost_bps"].eq(cost_bps)
        results.loc[mask, "sharpe_vs_baseline"] = results.loc[mask, "sharpe"] - float(baseline["sharpe"])
        results.loc[mask, "ann_return_vs_baseline"] = results.loc[mask, "ann_return"] - float(baseline["ann_return"])
        results.loc[mask, "max_dd_improvement"] = results.loc[mask, "max_dd"] - float(baseline["max_dd"])
        results.loc[mask, "balanced_pass"] = (
            results.loc[mask, "sharpe"].ge(float(baseline["sharpe"]))
            & results.loc[mask, "max_dd_improvement"].ge(0.03)
            & results.loc[mask, "ann_return_vs_baseline"].ge(-0.03)
            & results.loc[mask, "variant"].ne("baseline")
        )

    daily_all = pd.concat(daily_frames, ignore_index=True)
    events_all = pd.concat(event_frames, ignore_index=True)
    _atomic_parquet(results, OUTPUT_DIR / "metrics.parquet")
    _atomic_parquet(daily_all, OUTPUT_DIR / "daily.parquet")
    _atomic_parquet(events_all, OUTPUT_DIR / "events.parquet")

    view = results[
        [
            "variant",
            "cost_bps",
            "sharpe",
            "ann_return",
            "max_dd",
            "max_dd_improvement",
            "ann_return_vs_baseline",
            "avg_exposure",
            "position_stop_triggers",
            "portfolio_guard_triggers",
            "balanced_pass",
        ]
    ].sort_values(["cost_bps", "balanced_pass", "sharpe"], ascending=[True, False, False])
    text = f"""# A4 risk overlay backtest

## Rules

- A4 60-day average traded-value signal, bottom traded-value decile, 20-trading-day rebalance.
- Stop observed at close and executed at next available open.
- Position candidates: fixed -10%/-15%/-20% from average cost and trailing -15% from highest close.
- Portfolio guard: cycle MDD -10%, then all cash or 50% exposure until next scheduled rebalance.
- Re-entry only at next scheduled rebalance.
- Costs: 10bp and conservative 30bp one-way.
- Balanced pass at 30bp: Sharpe no lower than baseline, MDD improves at least 3%p, annual return falls no more than 3%p.

## Results

{markdown_table(view)}

## Decision

- 30bp pass count: {int(results.loc[results['cost_bps'].eq(30), 'balanced_pass'].sum())}
"""
    _atomic_text(text, REPORT_PATH)
    pass_rows = results.loc[results["cost_bps"].eq(30) & results["balanced_pass"]]
    return {
        "variants": len(configs),
        "rows": len(results),
        "latest_date": pd.to_datetime(daily_all["date"]).max().date().isoformat(),
        "pass_count_30bp": int(len(pass_rows)),
        "passing_variants_30bp": pass_rows["variant"].tolist(),
        "report": str(REPORT_PATH),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest A4 position stops and portfolio drawdown guards.")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({name: config.__dict__ for name, config in candidate_configs().items()}, ensure_ascii=False, indent=2))
        return
    print(json.dumps(run_experiment(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
