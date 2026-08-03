from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.us_research_paths import us_research_paths  # noqa: E402
from v2.tax.us_korea_capital_gains import KoreanUsStockTaxConfig  # noqa: E402

V2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = us_research_paths("sp500")
SIGNALS_DIR = DEFAULT_PATHS.signals_dir
RETURNS_PATH = DEFAULT_PATHS.returns_path
BENCHMARK_PATH = DEFAULT_PATHS.benchmark_path
OUTPUT_DIR = DEFAULT_PATHS.backtest_dir
METRICS_PATH = DEFAULT_PATHS.metrics_path
REPORT_PATH = DEFAULT_PATHS.backtest_report_path

PORTFOLIOS = ["LO_decile", "LO_quintile", "LS_decile", "LS_quintile"]
REBALANCES = [5, 20]
LONG_ONLY_COSTS = [5, 10, 20, 30]
LONG_SHORT_COSTS = [10, 20, 30, 50]
SUBPERIODS = {
    "sub1_2020_2021": ("2020-01-01", "2021-12-31"),
    "sub2_2022": ("2022-01-01", "2022-12-31"),
    "sub3_2023_2024": ("2023-01-01", "2024-12-31"),
    "sub4_2025_plus": ("2025-01-01", "2026-12-31"),
}

KOREAN_US_STOCK_TAX = KoreanUsStockTaxConfig()


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


def korean_tax_policy_lines() -> list[str]:
    return [
        (
            "- Korean tax model for US sale strategies: yearly realized gains use trade-date USD/KRW FX, "
            f"{KOREAN_US_STOCK_TAX.annual_deduction_krw:,.0f} KRW annual deduction, "
            f"then {KOREAN_US_STOCK_TAX.tax_rate:.0%} tax."
        ),
        "- Daily-return-only reports remain pre-tax until executions/lots and FX are supplied for realized sale tax calculation.",
    ]


def weights_from_signal(values: pd.Series, portfolio: str) -> pd.Series:
    valid = values.dropna().sort_values()
    weights = pd.Series(0.0, index=values.index)
    n = len(valid)
    if n < 30:
        return weights
    bucket = max(int(math.floor(n * (0.2 if "quintile" in portfolio else 0.1))), 1)
    longs = valid.tail(bucket).index
    weights.loc[longs] = 1.0 / bucket
    if portfolio.startswith("LS_"):
        shorts = valid.head(bucket).index
        weights.loc[shorts] = -1.0 / bucket
    return weights


def max_drawdown(returns: pd.Series) -> float:
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min()) if len(drawdown) else math.nan


def metrics(frame: pd.DataFrame, period: str) -> dict[str, object]:
    r = frame["net_return"].astype("float64")
    ann_return = float(r.mean() * 252) if len(r) else math.nan
    ann_vol = float(r.std(ddof=1) * math.sqrt(252)) if len(r) > 1 else math.nan
    return {
        "portfolio": frame["portfolio"].iloc[0],
        "rebalance": frame["rebalance"].iloc[0],
        "cost_bps": int(frame["cost_bps"].iloc[0]),
        "period": period,
        "sharpe": ann_return / ann_vol if ann_vol and not math.isnan(ann_vol) else math.nan,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "max_dd": max_drawdown(r),
        "avg_turnover": float(frame["turnover"].mean()) if len(frame) else math.nan,
        "n_days": int(len(frame)),
    }


def build_pnl(signal: pd.DataFrame, returns: pd.DataFrame, portfolio: str, rebalance_days: int) -> pd.DataFrame:
    dates = list(returns.index)
    prev_weights = pd.Series(0.0, index=returns.columns)
    current_weights = prev_weights.copy()
    rows = []
    for i, date in enumerate(dates):
        if i == 0:
            target = pd.Series(0.0, index=returns.columns)
        else:
            signal_day = dates[i - 1]
            if ((i - 1) % rebalance_days) == 0:
                current_weights = weights_from_signal(signal.loc[signal_day], portfolio)
            target = current_weights.copy()
        turnover = float((target - prev_weights).abs().sum() / 2.0)
        day_ret = returns.loc[date]
        valid = day_ret.notna()
        gross = float((target.loc[valid] * day_ret.loc[valid]).sum()) if valid.any() else 0.0
        rows.append({"date": date, "portfolio": portfolio, "rebalance": f"{rebalance_days}d", "gross_return": gross, "turnover": turnover})
        prev_weights = target.copy()
    return pd.DataFrame(rows)


def add_costs(base: pd.DataFrame, costs: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    pnls = []
    metric_rows = []
    for cost in costs:
        frame = base.copy()
        frame["cost_bps"] = cost
        frame["borrow_cost_bps"] = 0.0
        frame["cost"] = frame["turnover"] * (cost / 10000.0) * 2.0
        frame["net_return"] = frame["gross_return"] - frame["cost"]
        pnls.append(frame)
        metric_rows.append(metrics(frame, "full"))
        for name, (start, end) in SUBPERIODS.items():
            sub = frame.loc[frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
            if len(sub):
                metric_rows.append(metrics(sub, name))
    return pd.concat(pnls, ignore_index=True), pd.DataFrame(metric_rows)


def load_returns_matrix(returns_path: Path = RETURNS_PATH) -> pd.DataFrame:
    returns = pd.read_parquet(returns_path)
    returns["date"] = pd.to_datetime(returns["date"]).dt.normalize()
    returns = returns.loc[returns["ret_valid_1d"].astype(bool)]
    return returns.pivot(index="date", columns="symbol", values="forward_return_1d").sort_index()


def load_signal_matrix(path: Path, dates: pd.Index, symbols: pd.Index) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    return frame.pivot(index="date", columns="symbol", values="signal_cs_z").reindex(index=dates, columns=symbols)


def long_only_alpha(pnl: pd.DataFrame, benchmark_path: Path = BENCHMARK_PATH) -> pd.DataFrame:
    if not benchmark_path.exists():
        return pd.DataFrame()
    bench = pd.read_parquet(benchmark_path)
    bench["date"] = pd.to_datetime(bench["date"]).dt.normalize()
    rows = []
    for (signal_id, portfolio, rebalance, cost), group in pnl.loc[pnl["portfolio"].str.startswith("LO_")].groupby(["signal_id", "portfolio", "rebalance", "cost_bps"]):
        merged = group.merge(bench[["date", "daily_return"]], on="date", how="left")
        excess = merged["net_return"] - merged["daily_return"].fillna(0.0)
        ann_alpha = float(excess.mean() * 252)
        te = float(excess.std(ddof=1) * math.sqrt(252)) if len(excess) > 1 else math.nan
        rows.append({"signal_id": signal_id, "portfolio": portfolio, "rebalance": rebalance, "cost_bps": int(cost), "ann_alpha": ann_alpha, "tracking_error": te, "ir": ann_alpha / te if te and not math.isnan(te) else math.nan})
    return pd.DataFrame(rows)


def verdict_table(metrics_all: pd.DataFrame, alpha: pd.DataFrame) -> pd.DataFrame:
    rows = []
    focus = metrics_all.loc[metrics_all["period"].eq("full")].copy()
    for row in focus.itertuples(index=False):
        sub = metrics_all.loc[
            metrics_all["signal_id"].eq(row.signal_id)
            & metrics_all["portfolio"].eq(row.portfolio)
            & metrics_all["rebalance"].eq(row.rebalance)
            & metrics_all["cost_bps"].eq(row.cost_bps)
            & metrics_all["period"].str.startswith("sub")
        ]
        alpha_row = alpha.loc[
            alpha["signal_id"].eq(row.signal_id)
            & alpha["portfolio"].eq(row.portfolio)
            & alpha["rebalance"].eq(row.rebalance)
            & alpha["cost_bps"].eq(row.cost_bps)
        ] if not alpha.empty else pd.DataFrame()
        ann_alpha = float(alpha_row["ann_alpha"].iloc[0]) if not alpha_row.empty else math.nan
        ir = float(alpha_row["ir"].iloc[0]) if not alpha_row.empty else math.nan
        gate_a = bool(row.sharpe >= 0.8)
        gate_b = bool(len(sub) and sub["sharpe"].min() >= 0.0)
        gate_c = bool(row.portfolio.startswith("LS_") or (ann_alpha > 0.0 and ir >= 0.3))
        gate_d = bool(row.max_dd >= -0.35)
        verdict = "PASS" if gate_a and gate_b and gate_c and gate_d else "FAIL"
        rows.append({**row._asdict(), "ann_alpha": ann_alpha, "ir": ir, "gate_a_full_sharpe": gate_a, "gate_b_subperiod": gate_b, "gate_c_benchmark_alpha": gate_c, "gate_d_drawdown": gate_d, "verdict": verdict})
    return pd.DataFrame(rows)


def run(universe_key: str = "sp500") -> dict[str, object]:
    paths = us_research_paths(universe_key)
    returns = load_returns_matrix(paths.returns_path)
    pnl_frames = []
    metric_frames = []
    for path in sorted(paths.signals_dir.glob("*_cs_zscore.parquet")):
        signal_id = path.stem.replace("_cs_zscore", "")
        signal = load_signal_matrix(path, returns.index, returns.columns)
        for rebalance in REBALANCES:
            for portfolio in PORTFOLIOS:
                costs = LONG_ONLY_COSTS if portfolio.startswith("LO_") else LONG_SHORT_COSTS
                base = build_pnl(signal, returns, portfolio, rebalance)
                pnl, metric = add_costs(base, costs)
                pnl.insert(0, "signal_id", signal_id)
                metric.insert(0, "signal_id", signal_id)
                pnl_frames.append(pnl)
                metric_frames.append(metric)
    pnl_all = pd.concat(pnl_frames, ignore_index=True)
    metrics_all = pd.concat(metric_frames, ignore_index=True)
    alpha = long_only_alpha(pnl_all, paths.benchmark_path)
    verdicts = verdict_table(metrics_all, alpha)
    metrics_out = metrics_all.merge(
        verdicts[["signal_id", "portfolio", "rebalance", "cost_bps", "period", "ann_alpha", "ir", "verdict"]],
        on=["signal_id", "portfolio", "rebalance", "cost_bps", "period"],
        how="left",
    )
    atomic_write_parquet(metrics_out, paths.metrics_path)
    for signal_id, frame in pnl_all.groupby("signal_id"):
        atomic_write_parquet(frame, paths.backtest_dir / f"option_{signal_id}_pnl_daily.parquet")
    atomic_write_parquet(verdicts, paths.verdicts_path)
    lines = [
        "# US Backtest Batch",
        "",
        f"- Universe key: `{paths.universe_key}`.",
        "- Universe mode: `survivorship_biased_current_universe`.",
        "- Data source mode: `free_yfinance_research_data`.",
        *korean_tax_policy_lines(),
        "- Borrow costs are not modeled: `borrow_cost_not_modeled`.",
        "",
        "## Verdicts",
        verdicts.loc[verdicts["period"].eq("full")].sort_values(["verdict", "sharpe"], ascending=[True, False]).to_markdown(index=False),
        "",
    ]
    atomic_write_text("\n".join(lines), paths.backtest_report_path)
    return {"universe_key": paths.universe_key, "signals": int(verdicts["signal_id"].nunique()), "metrics_rows": int(len(metrics_out)), "pass_count": int(verdicts["verdict"].eq("PASS").sum())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run US batch backtests.")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--universe-key", default="sp500")
    args = parser.parse_args()
    if not args.run:
        print("Use --run")
        return
    print(json.dumps(run(args.universe_key), indent=2))


if __name__ == "__main__":
    main()
