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


BACKTEST_DIR = ROOT / "v2/data/cache/backtest_batch"
SIGNALS_DIR = ROOT / "v2/data/cache/signals_batch"
DIAGNOSTIC_DIR = ROOT / "v2/data/cache/diagnostic"
KOSPI_PATH = ROOT / "v2/data/cache/benchmarks/kospi_daily_returns.parquet"
SIZE_BUCKETS_PATH = ROOT / "v2/data/cache/price_market_cap_full/_size_buckets.parquet"
IC_FULL_PATH = ROOT / "v2/data/cache/ic/ic_batch_full.parquet"
REPORT_PATH = ROOT / "v2/reports/pr7_a_X_step8_5_diagnostic.md"

SIGNALS = ["A4", "A3"]
SPLITS = {
    "IS": (pd.Timestamp("2020-03-27"), pd.Timestamp("2024-12-31")),
    "OOS": (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-04-17")),
    "FULL": (pd.Timestamp("2020-03-27"), pd.Timestamp("2026-04-17")),
}
SUBPERIODS = {
    "sub1": (pd.Timestamp("2020-03-27"), pd.Timestamp("2021-12-31")),
    "sub2": (pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
    "sub3": (pd.Timestamp("2023-01-01"), pd.Timestamp("2024-12-31")),
    "sub4": (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-04-17")),
}


def stock_codes() -> list[str]:
    return sorted(path.stem for path in (ROOT / "v2/data/cache/price_market_cap_full").glob("*.parquet") if path.stem.isdigit() and len(path.stem) == 6)


def load_open_returns() -> pd.DataFrame:
    frames = []
    price_dir = ROOT / "v2/data/cache/price_market_cap_full"
    for code in stock_codes():
        frame = pd.read_parquet(price_dir / f"{code}.parquet", columns=["date", "open", "volume"])
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
    next_halt_raw = halt.shift(-1)
    next_halt = pd.DataFrame(np.where(pd.isna(next_halt_raw), True, next_halt_raw), index=halt.index, columns=halt.columns).astype(bool)
    returns = open_px.shift(-1) / open_px - 1.0
    return returns.where((~halt) & (~next_halt) & open_px.gt(0) & open_px.shift(-1).gt(0))


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


def max_drawdown(returns: pd.Series) -> float:
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    dd = equity / equity.cummax() - 1.0
    return float(dd.min()) if len(dd) else math.nan


def metrics(series: pd.Series) -> dict[str, float]:
    r = series.astype("float64").dropna()
    if r.empty:
        return {"sharpe": math.nan, "ann_return": math.nan, "ann_vol": math.nan, "max_dd": math.nan}
    ann_return = float(r.mean() * 252)
    ann_vol = float(r.std(ddof=1) * math.sqrt(252)) if len(r) > 1 else math.nan
    return {
        "sharpe": ann_return / ann_vol if ann_vol and not math.isnan(ann_vol) else math.nan,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "max_dd": max_drawdown(r),
    }


def load_pnl(signal: str) -> pd.DataFrame:
    frame = pd.read_parquet(BACKTEST_DIR / f"option_{signal}_pnl_daily.parquet")
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    return frame


def walkforward_metrics() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for signal in SIGNALS:
        pnl = load_pnl(signal)
        rebalances = ["1d", "5d"] + (["20d"] if signal == "A3" else [])
        subset = pnl.loc[
            pnl["portfolio"].isin(["LS_decile", "LO_decile"])
            & pnl["rebalance"].isin(rebalances)
            & pnl["cost_bps"].isin([0, 15, 30])
        ].copy()
        for (portfolio, rebalance, cost_bps), group in subset.groupby(["portfolio", "rebalance", "cost_bps"], sort=True):
            for period, (start, end) in {"IS": SPLITS["IS"], "OOS": SPLITS["OOS"]}.items():
                sub = group.loc[group["date"].between(start, end)]
                m = metrics(sub["net_return"])
                m["avg_turnover"] = float(sub["turnover"].mean()) if len(sub) else math.nan
                for metric_name, value in m.items():
                    rows.append(
                        {
                            "signal": signal,
                            "portfolio": portfolio,
                            "rebalance": rebalance,
                            "cost_bps": int(cost_bps),
                            "period": period,
                            "metric_name": metric_name,
                            "value": value,
                        }
                    )
    return pd.DataFrame(rows)


def ic_walkforward() -> pd.DataFrame:
    ic = pd.read_parquet(IC_FULL_PATH)
    ic["date"] = pd.to_datetime(ic["date"]).dt.normalize()
    rows: list[dict[str, object]] = []
    means: dict[tuple[str, str, str], float] = {}
    for signal in SIGNALS:
        for horizon in ["1d", "5d", "20d"]:
            base = ic.loc[ic["signal_id"].eq(signal) & ic["horizon"].eq(horizon)]
            for period, (start, end) in {"IS": SPLITS["IS"], "OOS": SPLITS["OOS"]}.items():
                sub = base.loc[base["date"].between(start, end) & base["ic"].notna()]
                n = int(len(sub))
                mean_ic = float(sub["ic"].mean()) if n else math.nan
                std = float(sub["ic"].std(ddof=1)) if n > 1 else math.nan
                t_stat = mean_ic / (std / math.sqrt(n)) if n > 1 and std and not math.isnan(std) else math.nan
                means[(signal, horizon, period)] = mean_ic
                rows.append(
                    {
                        "signal": signal,
                        "horizon": horizon,
                        "period": period,
                        "mean_ic": mean_ic,
                        "t_stat": t_stat,
                        "n_days": n,
                    }
                )
            is_mean = means[(signal, horizon, "IS")]
            oos_mean = means[(signal, horizon, "OOS")]
            sign_match = np.sign(is_mean) == np.sign(oos_mean) if pd.notna(is_mean) and pd.notna(oos_mean) else pd.NA
            ratio = oos_mean / is_mean if pd.notna(is_mean) and is_mean != 0 and pd.notna(oos_mean) else math.nan
            rows.append(
                {
                    "signal": signal,
                    "horizon": horizon,
                    "period": "IS_OOS_COMPARE",
                    "mean_ic": math.nan,
                    "t_stat": math.nan,
                    "n_days": 0,
                    "sign_match": sign_match,
                    "oos_over_is_mean_ic": ratio,
                }
            )
    return pd.DataFrame(rows)


def monthly_compounded(group: pd.DataFrame, value_col: str) -> pd.Series:
    return group.groupby(group["date"].dt.to_period("M"))[value_col].apply(lambda s: float((1.0 + s).prod() - 1.0))


def lo_monthly_returns() -> pd.DataFrame:
    kospi = pd.read_parquet(KOSPI_PATH)
    kospi["date"] = pd.to_datetime(kospi["date"]).dt.normalize()
    kospi_monthly = monthly_compounded(kospi, "daily_return").rename("kospi_return")
    rows = []
    for signal in SIGNALS:
        pnl = load_pnl(signal)
        lo = pnl.loc[pnl["portfolio"].eq("LO_decile") & pnl["rebalance"].eq("5d") & pnl["cost_bps"].eq(30)]
        lo_monthly = monthly_compounded(lo, "net_return").rename("lo_return")
        merged = pd.concat([lo_monthly, kospi_monthly], axis=1).dropna().reset_index()
        merged["month"] = merged["date"].astype(str)
        merged["signal"] = signal
        merged["spread"] = merged["lo_return"] - merged["kospi_return"]
        merged = merged.loc[merged["month"].ge("2020-04")]
        rows.append(merged[["signal", "month", "lo_return", "kospi_return", "spread"]])
    return pd.concat(rows, ignore_index=True)


def monthly_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for signal in SIGNALS:
        frame = monthly.loc[monthly["signal"].eq(signal)].copy()
        frame["month_ts"] = pd.to_datetime(frame["month"] + "-01")
        for period, (start, end) in {"IS": SPLITS["IS"], "OOS": SPLITS["OOS"]}.items():
            sub = frame.loc[frame["month_ts"].between(start.replace(day=1), end)]
            rows.append(
                {
                    "signal": signal,
                    "period": period,
                    "months": int(len(sub)),
                    "mean_monthly_lo": float(sub["lo_return"].mean()) if len(sub) else math.nan,
                    "mean_monthly_kospi": float(sub["kospi_return"].mean()) if len(sub) else math.nan,
                    "mean_spread": float(sub["spread"].mean()) if len(sub) else math.nan,
                    "win_rate": float((sub["spread"] > 0).mean()) if len(sub) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def regime_analysis(monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_months = monthly.drop_duplicates("month")[["month", "kospi_return"]].copy()
    unique_months["regime"] = np.select(
        [unique_months["kospi_return"] > 0.03, unique_months["kospi_return"] < -0.03],
        ["bull", "bear"],
        default="flat",
    )
    regime_dist = (
        unique_months.groupby("regime", sort=True)
        .agg(n_months=("month", "count"), mean_kospi_return=("kospi_return", "mean"))
        .reset_index()
    )
    merged = monthly.merge(unique_months[["month", "regime"]], on="month", how="left")
    perf = (
        merged.groupby(["signal", "regime"], sort=True)
        .agg(
            n_months=("month", "count"),
            mean_monthly_lo=("lo_return", "mean"),
            std=("lo_return", "std"),
            mean_spread=("spread", "mean"),
        )
        .reset_index()
    )
    return regime_dist, perf


def signal_matrix(signal: str) -> pd.DataFrame:
    frame = pd.read_parquet(SIGNALS_DIR / f"{signal}_cs_zscore.parquet")
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    return frame.pivot(index="date", columns="code", values="signal_cs_z").sort_index()


def holdings_monthly() -> tuple[pd.DataFrame, pd.DataFrame]:
    holdings_rows = []
    turnover_rows = []
    for signal in SIGNALS:
        matrix = signal_matrix(signal)
        rebalance_dates = list(matrix.index[::5])
        month_ends = pd.Series(matrix.index, index=matrix.index).groupby(matrix.index.to_period("M")).max()
        prev_set: set[str] | None = None
        for period, month_end in month_ends.items():
            eligible = [d for d in rebalance_dates if d <= month_end]
            if not eligible:
                continue
            d = eligible[-1]
            values = matrix.loc[d].dropna().sort_values()
            n = len(values)
            if n < 30:
                current = set()
            else:
                bucket = max(int(math.floor(n * 0.1)), 1)
                current = set(values.tail(bucket).index)
            month = str(period)
            if month < "2020-04":
                continue
            for code in sorted(current):
                holdings_rows.append({"signal": signal, "month": month, "code": code})
            turnover = math.nan if prev_set is None or len(current) == 0 else 1.0 - len(current & prev_set) / len(current)
            turnover_rows.append({"signal": signal, "month": month, "turnover_rate": turnover})
            prev_set = current
    turnover = pd.DataFrame(turnover_rows)
    turnover["month_ts"] = pd.to_datetime(turnover["month"] + "-01")
    for period, (start, end) in {"IS": SPLITS["IS"], "OOS": SPLITS["OOS"]}.items():
        pass
    return pd.DataFrame(holdings_rows), turnover.drop(columns=["month_ts"])


def holding_period_summary(turnover: pd.DataFrame) -> pd.DataFrame:
    frame = turnover.copy()
    frame["month_ts"] = pd.to_datetime(frame["month"] + "-01")
    rows = []
    for signal in SIGNALS:
        for period, (start, end) in {"IS": SPLITS["IS"], "OOS": SPLITS["OOS"]}.items():
            sub = frame.loc[frame["signal"].eq(signal) & frame["month_ts"].between(start.replace(day=1), end)]
            mean_turnover = float(sub["turnover_rate"].dropna().mean()) if len(sub["turnover_rate"].dropna()) else math.nan
            rows.append(
                {
                    "signal": signal,
                    "period": period,
                    "mean_monthly_turnover": mean_turnover,
                    "implied_avg_holding_months": 1.0 / mean_turnover if mean_turnover and not math.isnan(mean_turnover) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def size_subperiod_matrix() -> pd.DataFrame:
    buckets = pd.read_parquet(SIZE_BUCKETS_PATH)
    returns = load_open_returns()
    rows = []
    for signal in SIGNALS:
        matrix_all = signal_matrix(signal).reindex(index=returns.index, columns=returns.columns)
        for bucket, bucket_codes in buckets.groupby("size_bucket")["code"]:
            codes = [code for code in bucket_codes.astype(str).str.zfill(6).tolist() if code in matrix_all.columns]
            matrix = matrix_all[codes]
            ret = returns[codes]
            prev_weights = pd.Series(0.0, index=codes)
            current_weights = prev_weights.copy()
            pnl_rows = []
            dates = list(ret.index)
            for i, date in enumerate(dates):
                if i == 0:
                    target = pd.Series(0.0, index=codes)
                else:
                    signal_day = dates[i - 1]
                    if ((i - 1) % 5) == 0:
                        values = matrix.loc[signal_day].dropna().sort_values()
                        target = pd.Series(0.0, index=codes)
                        if len(values) >= 30:
                            n = max(int(math.floor(len(values) * 0.1)), 1)
                            target.loc[values.tail(n).index] = 1.0 / n
                        current_weights = target.copy()
                    else:
                        target = current_weights.copy()
                turnover = float((target - prev_weights).abs().sum() / 2.0)
                day_ret = ret.loc[date]
                valid = day_ret.notna()
                gross = float((target.loc[valid] * day_ret.loc[valid]).sum()) if valid.any() else 0.0
                net = gross - turnover * (30 / 10000.0) * 2.0
                pnl_rows.append({"date": date, "net_return": net})
                prev_weights = target.copy()
            lo_dates = pd.DataFrame(pnl_rows)
            for sub_name, (start, end) in SUBPERIODS.items():
                sub = lo_dates.loc[lo_dates["date"].between(start, end)]
                m = metrics(sub["net_return"])
                rows.append(
                    {
                        "signal": signal,
                        "size_bucket": bucket,
                        "subperiod": sub_name,
                        "ann_return": m["ann_return"],
                        "sharpe": m["sharpe"],
                    }
                )
    return pd.DataFrame(rows)


def kospi_reference() -> pd.DataFrame:
    kospi = pd.read_parquet(KOSPI_PATH)
    kospi["date"] = pd.to_datetime(kospi["date"]).dt.normalize()
    rows = []
    for period, (start, end) in SPLITS.items():
        sub = kospi.loc[kospi["date"].between(start, end)]
        m = metrics(sub["daily_return"])
        m["period"] = period
        rows.append(m)
    return pd.DataFrame(rows)[["period", "sharpe", "ann_return", "ann_vol", "max_dd"]]


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int | None = None) -> str:
    out = frame.copy()
    if columns is not None:
        out = out.loc[:, columns]
    if max_rows is not None:
        out = out.head(max_rows)
    cols = list(out.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in out.itertuples(index=False):
        vals = []
        for value in row:
            if isinstance(value, float):
                vals.append("NA" if math.isnan(value) else f"{value:.4f}")
            elif pd.isna(value):
                vals.append("NA")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def metric_wide(wf: pd.DataFrame, signal: str) -> pd.DataFrame:
    frame = wf.loc[wf["signal"].eq(signal)]
    return frame.pivot_table(
        index=["signal", "portfolio", "rebalance", "cost_bps", "period"],
        columns="metric_name",
        values="value",
        aggfunc="first",
    ).reset_index()


def matrix_from_size(size: pd.DataFrame, signal: str, metric: str) -> pd.DataFrame:
    frame = size.loc[size["signal"].eq(signal)]
    return frame.pivot(index="size_bucket", columns="subperiod", values=metric).reset_index()


def write_report(
    wf: pd.DataFrame,
    icwf: pd.DataFrame,
    monthly: pd.DataFrame,
    monthly_stats: pd.DataFrame,
    regime_dist: pd.DataFrame,
    regime_perf: pd.DataFrame,
    holdings: pd.DataFrame,
    turnover: pd.DataFrame,
    holding_summary: pd.DataFrame,
    size_matrix: pd.DataFrame,
    kospi_ref: pd.DataFrame,
) -> None:
    text = """# PR-7.A.X Step 8.5 A4/A3 Walk-forward Diagnostic

## 1. Scope & Setup
- A4, A3 diagnostic analysis: walk-forward, monthly breakdown, regime analysis, and holdings stability.
- Walk-forward: IS=2020-03-27~2024-12-31, OOS=2025-01-01~2026-04-17.
- No gate application or judgment.

## 2. Walk-forward Metrics
"""
    for signal in ["A4", "A3"]:
        text += f"\n### {signal}\n"
        text += markdown_table(metric_wide(wf, signal), ["signal", "portfolio", "rebalance", "cost_bps", "period", "sharpe", "ann_return", "ann_vol", "max_dd", "avg_turnover"]) + "\n"
    text += "\n## 3. IC Walk-forward\n"
    text += markdown_table(icwf, ["signal", "horizon", "period", "mean_ic", "t_stat", "n_days", "sign_match", "oos_over_is_mean_ic"]) + "\n"
    text += "\n## 4. Monthly LO 5d 30bp Returns\n"
    for signal in ["A4", "A3"]:
        text += f"\n### {signal}\n"
        text += markdown_table(monthly.loc[monthly["signal"].eq(signal)], ["month", "lo_return", "kospi_return", "spread"]) + "\n"
    text += "\n### Summary statistics\n"
    text += markdown_table(monthly_stats, ["signal", "period", "months", "mean_monthly_lo", "mean_monthly_kospi", "mean_spread", "win_rate"]) + "\n"
    text += "\n## 5. KOSPI Regime Analysis\n\n### 5.1 Regime definition and month counts\n"
    text += markdown_table(regime_dist, ["regime", "n_months", "mean_kospi_return"]) + "\n"
    text += "\n### 5.2 LO performance by regime\n"
    text += markdown_table(regime_perf, ["signal", "regime", "n_months", "mean_monthly_lo", "std", "mean_spread"]) + "\n"
    text += "\n## 6. Size x Subperiod Matrix (LO 5d 30bp)\n"
    for signal in ["A4", "A3"]:
        text += f"\n### {signal} ann_return\n"
        text += markdown_table(matrix_from_size(size_matrix, signal, "ann_return")) + "\n"
        text += f"\n### {signal} Sharpe\n"
        text += markdown_table(matrix_from_size(size_matrix, signal, "sharpe")) + "\n"
    text += "\n## 7. LO Holdings Stability\n\n### 7.1 Monthly turnover rate time series\n"
    text += markdown_table(turnover, ["signal", "month", "turnover_rate"]) + "\n"
    text += "\n### 7.2 Implied average holding period\n"
    text += markdown_table(holding_summary, ["signal", "period", "mean_monthly_turnover", "implied_avg_holding_months"]) + "\n"
    text += "\n## 8. KOSPI Reference (Buy-and-hold)\n"
    text += markdown_table(kospi_ref, ["period", "sharpe", "ann_return", "ann_vol", "max_dd"]) + "\n"
    text += """

## 9. Caveats
- OOS is about 16 months, so sample size is small.
- Alive-only universe remains a structural caveat.
- Strong-market alpha versus KOSPI can be mechanically difficult for defensive or low-volatility signals.
- Redesigning gates after this diagnostic would introduce data-snooping risk.
- Size bucket matrix uses the same LO decile, 5d rebalance, 30bp cost, and open-to-open return rule inside each size bucket for diagnostic decomposition.

## 10. Artifacts
- `v2/data/cache/diagnostic/walkforward_metrics.parquet`
- `v2/data/cache/diagnostic/ic_walkforward.parquet`
- `v2/data/cache/diagnostic/lo_monthly_returns.parquet`
- `v2/data/cache/diagnostic/lo_holdings_monthly.parquet`
- `v2/data/cache/diagnostic/regime_analysis.parquet`

## Gate
Step 8.5 raw diagnostic complete. Live entry, gate redesign, and discard decisions are user-owned.
"""
    atomic_write_text(text, REPORT_PATH)


def run() -> dict[str, object]:
    DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)
    wf = walkforward_metrics()
    icwf = ic_walkforward()
    monthly = lo_monthly_returns()
    monthly_stats = monthly_summary(monthly)
    regime_dist, regime_perf = regime_analysis(monthly)
    holdings, turnover = holdings_monthly()
    holding_summary = holding_period_summary(turnover)
    size_matrix = size_subperiod_matrix()
    kospi_ref = kospi_reference()
    regime_all = regime_perf.copy()
    regime_all["table"] = "performance"
    regime_dist_copy = regime_dist.copy()
    regime_dist_copy["signal"] = "KOSPI"
    regime_dist_copy["table"] = "distribution"
    regime_out = pd.concat([regime_all, regime_dist_copy], ignore_index=True, sort=False)
    atomic_write_parquet(wf, DIAGNOSTIC_DIR / "walkforward_metrics.parquet")
    atomic_write_parquet(icwf, DIAGNOSTIC_DIR / "ic_walkforward.parquet")
    atomic_write_parquet(monthly, DIAGNOSTIC_DIR / "lo_monthly_returns.parquet")
    atomic_write_parquet(holdings, DIAGNOSTIC_DIR / "lo_holdings_monthly.parquet")
    atomic_write_parquet(regime_out, DIAGNOSTIC_DIR / "regime_analysis.parquet")
    atomic_write_parquet(turnover, DIAGNOSTIC_DIR / "lo_turnover_monthly.parquet")
    atomic_write_parquet(holding_summary, DIAGNOSTIC_DIR / "holding_period_summary.parquet")
    atomic_write_parquet(size_matrix, DIAGNOSTIC_DIR / "size_subperiod_matrix.parquet")
    atomic_write_parquet(kospi_ref, DIAGNOSTIC_DIR / "kospi_reference.parquet")
    write_report(wf, icwf, monthly, monthly_stats, regime_dist, regime_perf, holdings, turnover, holding_summary, size_matrix, kospi_ref)
    return {
        "walkforward_rows": int(len(wf)),
        "ic_walkforward_rows": int(len(icwf)),
        "monthly_rows": int(len(monthly)),
        "holdings_rows": int(len(holdings)),
        "regime_rows": int(len(regime_out)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PR-7.A.X Step 8.5 A4/A3 diagnostic.")
    parser.add_argument("--run", action="store_true", help="Write diagnostic artifacts and report.")
    args = parser.parse_args()
    if not args.run:
        print("signals", ",".join(SIGNALS))
        return
    print(run())


if __name__ == "__main__":
    main()
