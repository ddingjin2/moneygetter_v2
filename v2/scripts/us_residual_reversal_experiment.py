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

V2_ROOT = Path(__file__).resolve().parents[1]
OHLCV_PATH = V2_ROOT / "data/processed/us_nasdaq100_pitlite_ohlcv.parquet"
OUT_DIR = V2_ROOT / "data/cache/us/nasdaq100_pitlite/strategy_compare/residual_reversal"
REPORT_PATH = V2_ROOT / "reports/us/residual_reversal_experiment.md"

SUBPERIODS = {
    "Full 2020-2026": ("2020-01-02", "2026-05-28"),
    "2020-2021": ("2020-01-02", "2021-12-31"),
    "2022": ("2022-01-01", "2022-12-31"),
    "2023-2024": ("2023-01-01", "2024-12-31"),
    "2025-2026 YTD": ("2025-01-01", "2026-05-28"),
}


@dataclass(frozen=True)
class StrategySpec:
    signal_id: str
    quantile: float
    rebalance_days: int
    risk_filter: str
    cost_bps: int = 40

    @property
    def strategy_id(self) -> str:
        q = "decile" if self.quantile == 0.1 else "quintile"
        return f"{self.signal_id}_LO_{q}_{self.rebalance_days}d_{self.risk_filter}_{self.cost_bps}bps"


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def weights_from_scores(scores: pd.Series, quantile: float) -> pd.Series:
    valid = scores.dropna().sort_values()
    weights = pd.Series(0.0, index=scores.index)
    if len(valid) < 30:
        return weights
    n = max(int(math.floor(len(valid) * quantile)), 1)
    names = valid.tail(n).index
    weights.loc[names] = 1.0 / n
    return weights


def residual_reversal_signal(
    stock_returns: pd.DataFrame,
    market_returns: pd.Series,
    lookback: int = 5,
    beta_window: int = 60,
) -> pd.DataFrame:
    market = market_returns.reindex(stock_returns.index).astype("float64")
    market_var = market.rolling(beta_window, min_periods=min(beta_window, 3)).var()
    beta = stock_returns.mul(market, axis=0).rolling(beta_window, min_periods=min(beta_window, 3)).mean().div(market_var.replace(0.0, np.nan), axis=0).fillna(0.0)
    residual = stock_returns.sub(beta.mul(market, axis=0), axis=0)
    return -residual.rolling(lookback, min_periods=lookback).sum()


def max_drawdown(returns: pd.Series) -> float:
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min()) if len(drawdown) else math.nan


def max_consecutive_losses(values: pd.Series) -> int:
    best = 0
    current = 0
    for value in values.fillna(0.0):
        if value < 0.0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def weekly_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["week"] = data["date"].dt.to_period("W-FRI")
    weekly = data.groupby("week")["net_return"].apply(lambda s: float((1.0 + s).prod() - 1.0))
    return {
        "n_weeks": int(len(weekly)),
        "weekly_win_rate": float((weekly > 0.0).mean()) if len(weekly) else math.nan,
        "weekly_loss_rate": float((weekly < 0.0).mean()) if len(weekly) else math.nan,
        "mean_weekly_return": float(weekly.mean()) if len(weekly) else math.nan,
        "median_weekly_return": float(weekly.median()) if len(weekly) else math.nan,
        "p05_weekly_return": float(weekly.quantile(0.05)) if len(weekly) else math.nan,
        "worst_weekly_return": float(weekly.min()) if len(weekly) else math.nan,
        "max_consecutive_losing_weeks": max_consecutive_losses(weekly),
    }


def performance_metrics(frame: pd.DataFrame, period: str) -> dict[str, float | int | str]:
    r = frame["net_return"].astype("float64").fillna(0.0)
    years = len(r) / 252.0
    total = float((1.0 + r).prod() - 1.0) if len(r) else math.nan
    cagr = float((1.0 + total) ** (1.0 / years) - 1.0) if years > 0 and total > -1.0 else math.nan
    ann_return = float(r.mean() * 252.0) if len(r) else math.nan
    ann_vol = float(r.std(ddof=1) * math.sqrt(252.0)) if len(r) > 1 else math.nan
    return {
        "period": period,
        "cagr": cagr,
        "total_return": total,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": ann_return / ann_vol if ann_vol and not math.isnan(ann_vol) else math.nan,
        "max_dd": max_drawdown(r),
        "n_days": int(len(r)),
        "avg_exposure": float(frame["exposure"].mean()) if "exposure" in frame else math.nan,
        "ann_turnover": float(frame["turnover"].mean() * 252.0) if "turnover" in frame else math.nan,
    }


def load_panel(path: Path = OHLCV_PATH) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ohlcv = pd.read_parquet(path)
    ohlcv["date"] = pd.to_datetime(ohlcv["date"]).dt.normalize()
    ohlcv["adj_open"] = pd.to_numeric(ohlcv["adj_open"], errors="coerce")
    ohlcv["adj_close"] = pd.to_numeric(ohlcv["adj_close"], errors="coerce")
    ohlcv["dollar_volume"] = pd.to_numeric(ohlcv["dollar_volume"], errors="coerce")
    open_px = ohlcv.pivot(index="date", columns="symbol", values="adj_open").sort_index()
    close_px = ohlcv.pivot(index="date", columns="symbol", values="adj_close").reindex_like(open_px)
    dvol = ohlcv.pivot(index="date", columns="symbol", values="dollar_volume").reindex_like(open_px)
    return open_px, close_px, dvol


def build_signal_matrices(close_px: pd.DataFrame, dvol: pd.DataFrame, market_symbol: str = "QQQ") -> dict[str, pd.DataFrame]:
    close_ret = close_px.pct_change(fill_method=None)
    market = close_ret[market_symbol] if market_symbol in close_ret.columns else close_ret.mean(axis=1, skipna=True)
    residual = residual_reversal_signal(close_ret, market, lookback=5, beta_window=60)
    vol60 = close_ret.rolling(60, min_periods=60).std(ddof=0)
    lowvol_mask = vol60.le(vol60.median(axis=1), axis=0)
    momentum_12_1 = close_px.shift(21) / close_px.shift(252) - 1.0
    momentum_mask = momentum_12_1.ge(momentum_12_1.median(axis=1), axis=0)
    liquid_mask = dvol.rolling(60, min_periods=20).mean().ge(20_000_000.0)
    return {
        "US_R1_residual_5d_reversal": residual.where(liquid_mask),
        "US_R2_lowvol_residual_5d_reversal": residual.where(lowvol_mask & liquid_mask),
        "US_R3_lowvol_momentum_residual_5d_reversal": residual.where(lowvol_mask & momentum_mask & liquid_mask),
        "US_R4_lowvol_momentum_residual_10d_reversal": residual_reversal_signal(close_ret, market, lookback=10, beta_window=60).where(lowvol_mask & momentum_mask & liquid_mask),
    }


def qqq_risk_on(close_px: pd.DataFrame, ma: int = 175, market_symbol: str = "QQQ") -> pd.Series:
    close = close_px[market_symbol] if market_symbol in close_px.columns else close_px.mean(axis=1, skipna=True)
    return close.shift(1).gt(close.shift(1).rolling(ma, min_periods=ma).mean())


def backtest_signal(
    signal: pd.DataFrame,
    forward_returns: pd.DataFrame,
    spec: StrategySpec,
    risk_on: pd.Series,
) -> pd.DataFrame:
    dates = list(forward_returns.index)
    symbols = list(forward_returns.columns)
    prev_weights = pd.Series(0.0, index=symbols)
    current_weights = prev_weights.copy()
    rows = []
    for i, date in enumerate(dates):
        if i == 0:
            target = pd.Series(0.0, index=symbols)
        else:
            signal_day = dates[i - 1]
            if ((i - 1) % spec.rebalance_days) == 0:
                if spec.risk_filter == "ma175" and not bool(risk_on.get(signal_day, False)):
                    current_weights = pd.Series(0.0, index=symbols)
                else:
                    current_weights = weights_from_scores(signal.loc[signal_day].reindex(symbols), spec.quantile)
            target = current_weights.copy()
        turnover = float((target - prev_weights).abs().sum() / 2.0)
        day_returns = forward_returns.loc[date]
        valid = day_returns.notna()
        gross = float((target.loc[valid] * day_returns.loc[valid]).sum()) if valid.any() else 0.0
        cost = turnover * (spec.cost_bps / 10000.0) * 2.0
        rows.append(
            {
                "date": date,
                "strategy_id": spec.strategy_id,
                "signal_id": spec.signal_id,
                "net_return": gross - cost,
                "gross_return": gross,
                "turnover": turnover,
                "exposure": float(target.abs().sum()),
                "n_long": int(target.gt(0).sum()),
            }
        )
        prev_weights = target.copy()
    return pd.DataFrame(rows)


def summarize_results(pnls: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    weekly_rows = []
    for strategy_id, frame in pnls.groupby("strategy_id"):
        for period, (start, end) in SUBPERIODS.items():
            sub = frame.loc[frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
            if not len(sub):
                continue
            row = performance_metrics(sub, period)
            row["strategy_id"] = strategy_id
            row["signal_id"] = frame["signal_id"].iloc[0]
            metric_rows.append(row)
        weekly = weekly_metrics(frame)
        weekly["strategy_id"] = strategy_id
        weekly["signal_id"] = frame["signal_id"].iloc[0]
        weekly_rows.append(weekly)
    return pd.DataFrame(metric_rows), pd.DataFrame(weekly_rows)


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    data = frame.loc[:, columns].head(max_rows).copy()
    return data.to_markdown(index=False)


def write_report(metrics: pd.DataFrame, weekly: pd.DataFrame, summary: dict[str, object]) -> None:
    full = metrics.loc[metrics["period"].eq("Full 2020-2026")].merge(weekly, on=["strategy_id", "signal_id"], how="left")
    stable = full.sort_values(["weekly_win_rate", "cagr"], ascending=False)
    balanced = full.loc[full["max_dd"].ge(-0.30)].sort_values(["cagr", "weekly_win_rate"], ascending=False)
    lines = [
        "# US Residual Reversal Individual Stock Experiment",
        "",
        "- Universe/data: Nasdaq 100 PIT-lite expanded individual stocks, yfinance adjusted OHLCV.",
        "- Research basis: short-term residual reversal, low-volatility anomaly, and conservative formula style low-vol/momentum filtering.",
        "- Quality limitation: no point-in-time US fundamentals are available locally, so `US_R3` and `US_R4` use a price-only low-volatility plus 12-1 momentum proxy rather than gross profitability or leverage.",
        "- Tax limitation: these are daily return simulations; Korean US-stock capital-gains tax requires realized executions, trade-date USD/KRW FX, and lot-level gains.",
        f"- Rows tested: `{summary['pnl_rows']}` daily rows across `{summary['strategies']}` strategy variants.",
        "",
        "## Most Weekly-Stable Candidates",
        markdown_table(
            stable,
            [
                "strategy_id",
                "cagr",
                "sharpe",
                "max_dd",
                "weekly_win_rate",
                "p05_weekly_return",
                "worst_weekly_return",
                "max_consecutive_losing_weeks",
                "avg_exposure",
                "ann_turnover",
            ],
            12,
        ),
        "",
        "## Balanced Candidates With MDD No Worse Than -30%",
        markdown_table(
            balanced,
            [
                "strategy_id",
                "cagr",
                "sharpe",
                "max_dd",
                "weekly_win_rate",
                "p05_weekly_return",
                "worst_weekly_return",
                "max_consecutive_losing_weeks",
                "avg_exposure",
                "ann_turnover",
            ],
            12,
        ),
        "",
        "## Interpretation",
        "",
        "- No individual-stock strategy should be expected to make money every week; the weekly-stability ranking is a loss-frequency diagnostic, not a guarantee.",
        "- Variants with the `ma175` risk filter are the practical candidates because they reduce market-regime damage.",
        "- If any residual-reversal candidate is promoted, the next mandatory step is exact after-tax lot accounting with USD/KRW FX and point-in-time fundamental data for a real quality filter.",
        "",
        "## Artifacts",
        "",
        "- Daily returns: `data/cache/us/nasdaq100_pitlite/strategy_compare/residual_reversal/residual_reversal_pnl_daily.parquet`",
        "- Full metrics: `data/cache/us/nasdaq100_pitlite/strategy_compare/residual_reversal/residual_reversal_metrics.parquet`",
        "- Weekly metrics: `data/cache/us/nasdaq100_pitlite/strategy_compare/residual_reversal/residual_reversal_weekly.parquet`",
    ]
    atomic_write_text("\n".join(lines) + "\n", REPORT_PATH)


def run() -> dict[str, object]:
    open_px, close_px, dvol = load_panel()
    forward_returns = open_px.shift(-1) / open_px - 1.0
    forward_returns = forward_returns.loc[forward_returns.index <= pd.Timestamp("2026-05-28")]
    signals = build_signal_matrices(close_px, dvol)
    risk_on = qqq_risk_on(close_px)
    specs = []
    for signal_id in signals:
        for quantile in [0.1, 0.2]:
            for rebalance in [5, 10]:
                for risk_filter in ["always", "ma175"]:
                    specs.append(StrategySpec(signal_id, quantile, rebalance, risk_filter))
    pnl_frames = []
    for spec in specs:
        signal = signals[spec.signal_id].reindex(index=forward_returns.index, columns=forward_returns.columns)
        pnl_frames.append(backtest_signal(signal, forward_returns, spec, risk_on))
    pnls = pd.concat(pnl_frames, ignore_index=True)
    metrics, weekly = summarize_results(pnls)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_parquet(pnls, OUT_DIR / "residual_reversal_pnl_daily.parquet")
    atomic_write_parquet(metrics, OUT_DIR / "residual_reversal_metrics.parquet")
    atomic_write_parquet(weekly, OUT_DIR / "residual_reversal_weekly.parquet")
    summary = {"strategies": int(pnls["strategy_id"].nunique()), "pnl_rows": int(len(pnls))}
    write_report(metrics, weekly, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run US residual reversal individual-stock experiments.")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Use --run")
        return
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
