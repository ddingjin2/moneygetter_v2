from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


PRICE_DIR = ROOT / "v2/data/cache/price_market_cap_full"
SIGNALS_DIR = ROOT / "v2/data/cache/signals_batch"
OUTPUT_DIR = ROOT / "v2/data/cache/backtest_batch"
KOSPI_PATH = ROOT / "v2/data/cache/benchmarks/kospi_daily_returns.parquet"
OPTION_A_METRICS_PATH = ROOT / "v2/data/cache/backtest/option_a_metrics.parquet"
SIZE_BUCKETS_PATH = PRICE_DIR / "_size_buckets.parquet"
REPORT_PATH = ROOT / "v2/reports/pr7_a_X_step8_4_backtest.md"

SIGNALS = ["A3", "A4", "A10", "A2", "B1", "C3"]
PORTFOLIOS = ["LS_decile", "LS_quintile", "LO_decile"]
COST_BPS = [0, 15, 30, 50]
REBALANCES = {"A3": [1, 5, 20], "C3": [1, 5, 20], "A4": [1, 5], "A10": [1, 5], "A2": [1, 5], "B1": [1, 5]}
SUBPERIODS = {
    "sub1_2020_2021": ("2020-01-01", "2021-12-31"),
    "sub2_2022": ("2022-01-01", "2022-12-31"),
    "sub3_2023_2024": ("2023-01-01", "2024-12-31"),
    "sub4_2025_2026": ("2025-01-01", "2026-12-31"),
}


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


def stock_codes() -> list[str]:
    return sorted(path.stem for path in PRICE_DIR.glob("*.parquet") if path.stem.isdigit() and len(path.stem) == 6)


def load_price_panel() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames = []
    for code in stock_codes():
        frame = pd.read_parquet(PRICE_DIR / f"{code}.parquet", columns=["date", "open", "volume"])
        frame["code"] = code
        frames.append(frame)
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel["open"] = pd.to_numeric(panel["open"], errors="coerce").astype("float64")
    panel["volume"] = pd.to_numeric(panel["volume"], errors="coerce").astype("float64")
    panel["halt"] = panel["open"].eq(0) & panel["volume"].eq(0)
    open_px = panel.pivot(index="date", columns="code", values="open").sort_index()
    halt_raw = panel.pivot(index="date", columns="code", values="halt").reindex_like(open_px)
    halt = pd.DataFrame(np.where(pd.isna(halt_raw), True, halt_raw), index=halt_raw.index, columns=halt_raw.columns).astype(bool)
    ret = open_px.shift(-1) / open_px - 1.0
    next_halt_raw = halt.shift(-1)
    next_halt = pd.DataFrame(
        np.where(pd.isna(next_halt_raw), True, next_halt_raw),
        index=next_halt_raw.index,
        columns=next_halt_raw.columns,
    ).astype(bool)
    valid_ret = (~halt) & (~next_halt) & open_px.gt(0) & open_px.shift(-1).gt(0)
    ret = ret.where(valid_ret)
    return open_px, halt, ret


def load_signal(signal_id: str, dates: pd.Index, codes: pd.Index) -> pd.DataFrame:
    frame = pd.read_parquet(SIGNALS_DIR / f"{signal_id}_cs_zscore.parquet")
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    if signal_id == "C3":
        frame["signal_cs_z"] = -frame["signal_cs_z"]
    signal = frame.pivot(index="date", columns="code", values="signal_cs_z").reindex(index=dates, columns=codes)
    return signal


def weights_from_signal(values: pd.Series, portfolio: str) -> pd.Series:
    valid = values.dropna().sort_values()
    weights = pd.Series(0.0, index=values.index)
    n = len(valid)
    if n < 30:
        return weights
    if portfolio == "LS_decile":
        bucket = max(int(math.floor(n * 0.1)), 1)
    elif portfolio == "LS_quintile":
        bucket = max(int(math.floor(n * 0.2)), 1)
    elif portfolio == "LO_decile":
        bucket = max(int(math.floor(n * 0.1)), 1)
    else:
        raise ValueError(f"Unknown portfolio: {portfolio}")
    longs = valid.tail(bucket).index
    weights.loc[longs] = 1.0 / bucket
    if portfolio.startswith("LS_"):
        shorts = valid.head(bucket).index
        weights.loc[shorts] = -1.0 / bucket
    return weights


def build_base_pnl(signal: pd.DataFrame, returns: pd.DataFrame, portfolio: str, rebalance_days: int, *, sparse_cash: bool) -> pd.DataFrame:
    dates = list(returns.index)
    prev_weights = pd.Series(0.0, index=returns.columns)
    current_weights = prev_weights.copy()
    rows = []
    for i, date in enumerate(dates):
        if i == 0:
            target = pd.Series(0.0, index=returns.columns)
        else:
            signal_day = dates[i - 1]
            should_rebalance = ((i - 1) % rebalance_days) == 0
            if sparse_cash and signal.loc[signal_day].isna().all():
                target = pd.Series(0.0, index=returns.columns)
                current_weights = target.copy()
            elif sparse_cash:
                target = weights_from_signal(signal.loc[signal_day], portfolio)
                current_weights = target.copy()
            elif should_rebalance:
                target = weights_from_signal(signal.loc[signal_day], portfolio)
                current_weights = target.copy()
            else:
                target = current_weights.copy()
        turnover = float((target - prev_weights).abs().sum() / 2.0)
        day_ret = returns.loc[date]
        valid = day_ret.notna()
        gross_return = float((target.loc[valid] * day_ret.loc[valid]).sum()) if valid.any() else 0.0
        rows.append(
            {
                "date": date,
                "portfolio": portfolio,
                "rebalance": f"{rebalance_days}d",
                "gross_return": gross_return,
                "position_count_long": int((target > 0).sum()),
                "position_count_short": int((target < 0).sum()),
                "turnover": turnover,
            }
        )
        prev_weights = target.copy()
    return pd.DataFrame(rows)


def max_drawdown(returns: pd.Series) -> float:
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min()) if len(drawdown) else math.nan


def metric_from_returns(frame: pd.DataFrame, period: str) -> dict[str, object]:
    r = frame["net_return"].astype("float64")
    ann_return = float(r.mean() * 252) if len(r) else math.nan
    ann_vol = float(r.std(ddof=1) * math.sqrt(252)) if len(r) > 1 else math.nan
    sharpe = ann_return / ann_vol if ann_vol and not math.isnan(ann_vol) else math.nan
    return {
        "portfolio": frame["portfolio"].iloc[0],
        "rebalance": frame["rebalance"].iloc[0],
        "cost_bps": int(frame["cost_bps"].iloc[0]),
        "period": period,
        "sharpe": sharpe,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "max_dd": max_drawdown(r),
        "hit_ratio": float((r > 0).mean()) if len(r) else math.nan,
        "avg_turnover": float(frame["turnover"].mean()) if len(frame) else math.nan,
        "n_days": int(len(frame)),
    }


def add_costs(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pnl_rows = []
    metrics = []
    for cost_bps in COST_BPS:
        frame = base.copy()
        frame["cost_bps"] = cost_bps
        frame["cost"] = frame["turnover"] * (cost_bps / 10000.0) * 2.0
        frame["net_return"] = frame["gross_return"] - frame["cost"]
        frame = frame[["date", "portfolio", "rebalance", "cost_bps", "gross_return", "cost", "net_return", "position_count_long", "position_count_short", "turnover"]]
        pnl_rows.append(frame)
        metrics.append(metric_from_returns(frame, "full"))
        for name, (start, end) in SUBPERIODS.items():
            sub = frame.loc[frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
            if len(sub):
                metrics.append(metric_from_returns(sub, name))
        for year, group in frame.groupby(frame["date"].dt.year):
            metrics.append(metric_from_returns(group, f"year_{year}"))
    return pd.concat(pnl_rows, ignore_index=True), pd.DataFrame(metrics)


def long_only_alpha(pnl: pd.DataFrame) -> pd.DataFrame:
    kospi = pd.read_parquet(KOSPI_PATH)
    kospi["date"] = pd.to_datetime(kospi["date"]).dt.normalize()
    rows = []
    lo = pnl.loc[pnl["portfolio"].eq("LO_decile")]
    for (rebalance, cost_bps), group in lo.groupby(["rebalance", "cost_bps"], sort=True):
        merged = group.merge(kospi[["date", "daily_return"]], on="date", how="left")
        excess = merged["net_return"] - merged["daily_return"].fillna(0.0)
        ann_alpha = float(excess.mean() * 252)
        tracking_error = float(excess.std(ddof=1) * math.sqrt(252)) if len(excess) > 1 else math.nan
        rows.append(
            {
                "rebalance": rebalance,
                "cost_bps": int(cost_bps),
                "ann_alpha": ann_alpha,
                "tracking_error": tracking_error,
                "ir": ann_alpha / tracking_error if tracking_error and not math.isnan(tracking_error) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def size_bucket_metrics(signal: pd.DataFrame, returns: pd.DataFrame, rebalance_days: int, signal_id: str) -> pd.DataFrame:
    buckets = pd.read_parquet(SIZE_BUCKETS_PATH)
    rows = []
    for bucket, codes in buckets.groupby("size_bucket")["code"]:
        sub_codes = [code for code in codes.astype(str).str.zfill(6).tolist() if code in signal.columns]
        if not sub_codes:
            continue
        base = build_base_pnl(signal[sub_codes], returns[sub_codes], "LS_decile", rebalance_days, sparse_cash=(signal_id == "C3"))
        pnl, metrics = add_costs(base)
        row = metrics.loc[metrics["period"].eq("full") & metrics["cost_bps"].eq(30)].iloc[0].to_dict()
        row["signal_id"] = signal_id
        row["size_bucket"] = bucket
        rows.append(row)
    return pd.DataFrame(rows)


def run_signal(signal_id: str, signal: pd.DataFrame, returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pnl_frames = []
    metric_frames = []
    alpha_frames = []
    size_frames = []
    for rebalance in REBALANCES[signal_id]:
        for portfolio in PORTFOLIOS:
            base = build_base_pnl(signal, returns, portfolio, rebalance, sparse_cash=(signal_id == "C3"))
            pnl, metrics = add_costs(base)
            pnl.insert(0, "signal_id", signal_id)
            metrics.insert(0, "signal_id", signal_id)
            pnl_frames.append(pnl)
            metric_frames.append(metrics)
        rebalance_pnl = pd.concat([frame for frame in pnl_frames if frame["rebalance"].iloc[0] == f"{rebalance}d"], ignore_index=True)
        alpha = long_only_alpha(rebalance_pnl)
        alpha.insert(0, "signal_id", signal_id)
        alpha_frames.append(alpha)
        size_frames.append(size_bucket_metrics(signal, returns, rebalance, signal_id))
    return (
        pd.concat(pnl_frames, ignore_index=True),
        pd.concat(metric_frames, ignore_index=True),
        pd.concat(alpha_frames, ignore_index=True),
        pd.concat(size_frames, ignore_index=True),
    )


def verdict_table(metrics: pd.DataFrame, alpha: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gate_pairs = [("A3", "5d"), ("A3", "20d"), ("C3", "5d"), ("C3", "20d"), ("A4", "5d"), ("A10", "5d"), ("A2", "5d"), ("B1", "5d")]
    for signal_id, rebalance in gate_pairs:
        ls = metrics.loc[
            metrics["signal_id"].eq(signal_id)
            & metrics["portfolio"].eq("LS_decile")
            & metrics["rebalance"].eq(rebalance)
            & metrics["cost_bps"].eq(30)
        ]
        full = ls.loc[ls["period"].eq("full")].iloc[0]
        subs = ls.loc[ls["period"].str.startswith("sub")]
        lo_alpha = alpha.loc[
            alpha["signal_id"].eq(signal_id) & alpha["rebalance"].eq(rebalance) & alpha["cost_bps"].eq(30)
        ].iloc[0]
        gate_a = bool(full["sharpe"] >= 0.5)
        gate_b = bool(subs["sharpe"].min() >= -0.30)
        gate_c = bool(lo_alpha["ann_alpha"] >= 0.02)
        reasons = []
        if not gate_a:
            reasons.append("sharpe")
        if not gate_b:
            reasons.append("subperiod")
        if not gate_c:
            reasons.append("lo_alpha")
        rows.append(
            {
                "signal_id": signal_id,
                "rebalance": rebalance,
                "gate_a_30bp_sharpe": gate_a,
                "gate_b_subperiod": gate_b,
                "gate_c_lo_alpha": gate_c,
                "verdict": "PASS" if not reasons else "FAIL_" + "+".join(reasons),
                "ls_decile_30bp_sharpe": float(full["sharpe"]),
                "subperiod_min_sharpe": float(subs["sharpe"].min()),
                "lo_decile_30bp_alpha": float(lo_alpha["ann_alpha"]),
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, *, max_rows: int | None = None) -> str:
    out = frame.copy()
    if columns is not None:
        out = out.loc[:, columns]
    if max_rows is not None:
        out = out.head(max_rows)
    cols = list(out.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in out.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("NA" if math.isnan(value) else f"{value:.4f}")
            elif pd.isna(value):
                values.append("NA")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(all_metrics: pd.DataFrame, all_alpha: pd.DataFrame, all_size: pd.DataFrame, verdicts: pd.DataFrame, c3_exposure: float) -> None:
    full = all_metrics.loc[all_metrics["period"].eq("full")].copy()
    option_a = pd.read_parquet(OPTION_A_METRICS_PATH)
    text = f"""# PR-7.A.X Step 8.4 Multi-signal Backtest

## 1. Scope & Setup
- 6 signals: A3, A4, A10, A2, B1, C3.
- A3, C3: 20d rebalance added.
- Direction alignment: C3 is sign-flipped; A3, A4, A10, A2, B1 use existing cs_z direction.
- Framework: Option A Step 7 style with t+1 open execution, equal-weight portfolios, and halt mask.

## 2. Backtest Rules
- Signal observed at day t close; portfolio enters at t+1 open and earns open-to-open daily returns.
- Portfolios: LS_decile, LS_quintile, LO_decile.
- Costs: 0, 15, 30, 50 bps one-way; daily cost = turnover x cost_rate x 2.
- C3 sparse days: NaN signal days hold cash; no carry-forward.

## 3. Universe & Data Summary
- Universe stocks: 808.
- Period: 2020-03-27 ~ 2026-04-17.
- Trading days: 1486.
- Alive-only KOSPI universe.

## 4. Full Result Matrix
{markdown_table(full, ["signal_id", "portfolio", "rebalance", "cost_bps", "sharpe", "ann_return", "ann_vol", "max_dd", "avg_turnover"])}

## 5. Recommended Combination Details
"""
    for signal_id in SIGNALS:
        text += f"\n### Signal {signal_id}\n"
        keep_rebalances = ["1d", "5d"] + (["20d"] if signal_id in {"A3", "C3"} else [])
        for rebalance in keep_rebalances:
            section = full.loc[
                full["signal_id"].eq(signal_id) & full["rebalance"].eq(rebalance) & full["cost_bps"].eq(30)
            ]
            text += f"\n#### {rebalance} 30bp Results\n"
            text += markdown_table(section, ["portfolio", "sharpe", "ann_return", "ann_vol", "max_dd", "avg_turnover"]) + "\n"
        year = all_metrics.loc[
            all_metrics["signal_id"].eq(signal_id)
            & all_metrics["portfolio"].eq("LS_decile")
            & all_metrics["rebalance"].eq("5d")
            & all_metrics["cost_bps"].eq(30)
            & all_metrics["period"].str.startswith("year_")
        ]
        sub = all_metrics.loc[
            all_metrics["signal_id"].eq(signal_id)
            & all_metrics["portfolio"].eq("LS_decile")
            & all_metrics["rebalance"].eq("5d")
            & all_metrics["cost_bps"].eq(30)
            & all_metrics["period"].str.startswith("sub")
        ]
        alpha = all_alpha.loc[all_alpha["signal_id"].eq(signal_id) & all_alpha["rebalance"].eq("5d") & all_alpha["cost_bps"].eq(30)]
        size = all_size.loc[all_size["signal_id"].eq(signal_id) & all_size["rebalance"].eq("5d")]
        text += "\n#### Yearly Summary: LS_decile 5d 30bp\n" + markdown_table(year, ["period", "sharpe", "ann_return", "max_dd"]) + "\n"
        text += "\n#### Subperiod Analysis: LS_decile 5d 30bp\n" + markdown_table(sub, ["period", "sharpe", "ann_return", "max_dd", "hit_ratio"]) + "\n"
        text += "\n#### Size Bucket Analysis: LS_decile 5d 30bp\n" + markdown_table(size, ["size_bucket", "sharpe", "ann_return", "ann_vol", "max_dd", "avg_turnover"]) + "\n"
        text += "\n#### LO Alpha vs KOSPI: 5d 30bp\n" + markdown_table(alpha, ["ann_alpha", "tracking_error", "ir"]) + "\n"
    text += f"""

## 6. Cross-signal Verdict Table
{markdown_table(verdicts, ["signal_id", "rebalance", "gate_a_30bp_sharpe", "gate_b_subperiod", "gate_c_lo_alpha", "verdict", "ls_decile_30bp_sharpe", "subperiod_min_sharpe", "lo_decile_30bp_alpha"])}

## 7. Reference: Option A Baseline
- LS_decile 5d 30bp Sharpe: -3.24.
- LO_decile 5d 30bp alpha: -22.3%.
- Verdict: FAIL (already discarded).

## 8. C3 Sparsity
- avg_exposure_pct: {c3_exposure:.1%}
- C3 has shorter exposure because non-stress days are cash by rule; annualized Sharpe has this exposure caveat.

## 9. Caveats
- Several tested signals have non-trivial IC time-series correlation from Step 8.3.
- C3 uses sign flip after observing negative IC; this post-hoc sign flip risk is explicitly noted.
- Equal-weight portfolios, alive-only universe, flat bps costs, and unavailable market-cap data remain structural caveats.

## 10. Artifacts
- `v2/data/cache/backtest_batch/all_metrics.parquet`
- `v2/data/cache/backtest_batch/option_<signal>_metrics.parquet`
- `v2/data/cache/backtest_batch/option_<signal>_pnl_daily.parquet`

## Gate
Step 8.4 raw measurement complete. PASS/FAIL labels are automatically applied, but standalone entry, combination, and discard decisions are user-owned.
"""
    atomic_write_text(text, REPORT_PATH)


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _, _, returns = load_price_panel()
    all_pnl = []
    all_metrics = []
    all_alpha = []
    all_size = []
    c3_exposure = math.nan
    for signal_id in SIGNALS:
        signal = load_signal(signal_id, returns.index, returns.columns)
        if signal_id == "C3":
            c3_exposure = float(signal.notna().any(axis=1).mean())
        pnl, metrics, alpha, size = run_signal(signal_id, signal, returns)
        atomic_write_parquet(pnl, OUTPUT_DIR / f"option_{signal_id}_pnl_daily.parquet")
        atomic_write_parquet(metrics, OUTPUT_DIR / f"option_{signal_id}_metrics.parquet")
        all_pnl.append(pnl)
        all_metrics.append(metrics)
        all_alpha.append(alpha)
        all_size.append(size)
    metrics_all = pd.concat(all_metrics, ignore_index=True)
    alpha_all = pd.concat(all_alpha, ignore_index=True)
    size_all = pd.concat(all_size, ignore_index=True)
    verdicts = verdict_table(metrics_all, alpha_all)
    metrics_out = metrics_all.merge(alpha_all, on=["signal_id", "rebalance", "cost_bps"], how="left")
    metrics_out = metrics_out.merge(verdicts, on=["signal_id", "rebalance"], how="left")
    atomic_write_parquet(metrics_out, OUTPUT_DIR / "all_metrics.parquet")
    write_report(metrics_all, alpha_all, size_all, verdicts, c3_exposure)
    return {
        "signals": len(SIGNALS),
        "metrics_rows": int(len(metrics_out)),
        "verdict_rows": int(len(verdicts)),
        "c3_exposure": c3_exposure,
        "pass_count": int(verdicts["verdict"].eq("PASS").sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PR-7.A.X Step 8.4 multi-signal backtest.")
    parser.add_argument("--run", action="store_true", help="Write Step 8.4 backtest artifacts and report.")
    args = parser.parse_args()
    if not args.run:
        print("signals", ",".join(SIGNALS))
        return
    print(run())


if __name__ == "__main__":
    main()
