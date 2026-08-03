from __future__ import annotations

import itertools
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRICE_DIR = ROOT / "v2/data/cache/price_market_cap_full"
SIGNALS_DIR = ROOT / "v2/data/cache/signals_batch"
OUT_DIR = ROOT / "v2/data/cache/a4_plus_explore"
REPORT_PATH = ROOT / "v2/reports/a4_plus_exploration.md"
KOSPI_PATH = ROOT / "v2/data/cache/benchmarks/kospi_daily_returns.parquet"

IS = (pd.Timestamp("2020-03-27"), pd.Timestamp("2024-12-31"))
OOS = (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-04-17"))
FULL = (pd.Timestamp("2020-03-27"), pd.Timestamp("2026-04-17"))
SUBPERIODS = {
    "sub1_2020_2021": (pd.Timestamp("2020-03-27"), pd.Timestamp("2021-12-31")),
    "sub2_2022": (pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
    "sub3_2023_2024": (pd.Timestamp("2023-01-01"), pd.Timestamp("2024-12-31")),
    "sub4_2025_2026": (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-04-17")),
}

# Predeclared directions from Step 8.2 5d IC sign. Avoid re-estimating weights on OOS.
DIR = {
    "A1": 1, "A2": 1, "A3": 1, "A4": 1, "A5": 1, "A6": 1, "A9": 1,
    "A10": 1, "B1": 1, "B4": 1,
    "A7": -1, "A8": -1, "B2": -1, "B5": -1, "C1": -1, "C5": -1,
}

MANUAL_CANDIDATES = {
    "A4": ["A4"],
    "A3": ["A3"],
    "A3_A4": ["A3", "A4"],
    "A3_A4_A9": ["A3", "A4", "A9"],
    "A3_A4_A6": ["A3", "A4", "A6"],
    "A3_A4_A9_A6": ["A3", "A4", "A9", "A6"],
    "A3_A4_B4": ["A3", "A4", "B4"],
    "A3_A4_A10": ["A3", "A4", "A10"],
    "A3_A4_A7rev": ["A3", "A4", "A7"],
    "A3_A4_A8rev": ["A3", "A4", "A8"],
}

SCREEN_BASE = ["A3", "A4", "A6", "A9", "A10", "B1", "B4", "A7", "A8", "B2", "C1", "C5"]


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


def load_open_returns() -> pd.DataFrame:
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
    next_halt_raw = halt.shift(-1)
    next_halt = pd.DataFrame(np.where(pd.isna(next_halt_raw), True, next_halt_raw), index=halt.index, columns=halt.columns).astype(bool)
    ret = open_px.shift(-1) / open_px - 1.0
    return ret.where((~halt) & (~next_halt) & open_px.gt(0) & open_px.shift(-1).gt(0))


def load_signal(signal: str, dates: pd.Index, codes: pd.Index) -> pd.DataFrame:
    f = pd.read_parquet(SIGNALS_DIR / f"{signal}_cs_zscore.parquet")
    f["date"] = pd.to_datetime(f["date"]).dt.normalize()
    mat = f.pivot(index="date", columns="code", values="signal_cs_z").reindex(index=dates, columns=codes)
    return mat.astype("float64") * DIR.get(signal, 1)


def composite_signal(signals: dict[str, pd.DataFrame], components: list[str]) -> pd.DataFrame:
    # Equal-weight blend of already cross-sectionally z-scored components.
    acc = None
    cnt = None
    for c in components:
        m = signals[c]
        if acc is None:
            acc = m.copy()
            cnt = m.notna().astype("float64")
        else:
            acc = acc.add(m, fill_value=0.0)
            cnt = cnt.add(m.notna().astype("float64"), fill_value=0.0)
    out = acc / cnt.replace(0.0, np.nan)
    # Re-standardize cross-sectionally each day so deciles are stable.
    mean = out.mean(axis=1, skipna=True)
    std = out.std(axis=1, skipna=True, ddof=0).replace(0.0, np.nan)
    return out.sub(mean, axis=0).div(std, axis=0)


def max_drawdown(r: pd.Series) -> float:
    eq = (1.0 + r.fillna(0.0)).cumprod()
    dd = eq / eq.cummax() - 1.0
    return float(dd.min()) if len(dd) else math.nan


def metrics(r: pd.Series) -> dict[str, float]:
    r = r.astype("float64").dropna()
    if r.empty:
        return {"sharpe": math.nan, "ann_return": math.nan, "ann_vol": math.nan, "max_dd": math.nan, "hit_ratio": math.nan}
    ann_return = float(r.mean() * 252)
    ann_vol = float(r.std(ddof=1) * math.sqrt(252)) if len(r) > 1 else math.nan
    return {
        "sharpe": ann_return / ann_vol if ann_vol and not math.isnan(ann_vol) else math.nan,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "max_dd": max_drawdown(r),
        "hit_ratio": float((r > 0).mean()),
    }


def backtest_lo(signal: pd.DataFrame, returns: pd.DataFrame, rebalance_days: int, q: float, cost_bps: int = 30) -> pd.DataFrame:
    dates = list(returns.index)
    codes = list(returns.columns)
    prev_w = pd.Series(0.0, index=codes)
    cur_w = prev_w.copy()
    rows = []
    for i, date in enumerate(dates):
        if i == 0:
            target = pd.Series(0.0, index=codes)
        else:
            sig_day = dates[i - 1]
            if ((i - 1) % rebalance_days) == 0:
                vals = signal.loc[sig_day].dropna().sort_values()
                target = pd.Series(0.0, index=codes)
                if len(vals) >= 30:
                    n = max(int(math.floor(len(vals) * q)), 1)
                    names = vals.tail(n).index
                    target.loc[names] = 1.0 / n
                cur_w = target.copy()
            else:
                target = cur_w.copy()
        turnover = float((target - prev_w).abs().sum() / 2.0)
        day_ret = returns.loc[date]
        valid = day_ret.notna()
        gross = float((target.loc[valid] * day_ret.loc[valid]).sum()) if valid.any() else 0.0
        cost = turnover * (cost_bps / 10000.0) * 2.0
        rows.append({"date": date, "net_return": gross - cost, "gross_return": gross, "turnover": turnover, "n_long": int((target > 0).sum())})
        prev_w = target.copy()
    return pd.DataFrame(rows)


def evaluate(name: str, components: list[str], signal: pd.DataFrame, returns: pd.DataFrame, rebalance: int, q: float) -> tuple[list[dict[str, object]], pd.DataFrame]:
    pnl = backtest_lo(signal, returns, rebalance, q)
    rows = []
    for period, (start, end) in {"IS": IS, "OOS": OOS, "FULL": FULL, **SUBPERIODS}.items():
        sub = pnl.loc[pnl["date"].between(start, end)]
        m = metrics(sub["net_return"])
        rows.append({"strategy": name, "components": "+".join(components), "rebalance": f"{rebalance}d", "q": q, "period": period, **m, "avg_turnover": float(sub["turnover"].mean()) if len(sub) else math.nan})
    pnl.insert(0, "strategy", name)
    pnl.insert(1, "rebalance", f"{rebalance}d")
    pnl.insert(2, "q", q)
    return rows, pnl


def monthly_alpha(pnl: pd.DataFrame, strategy: str) -> dict[str, float]:
    kospi = pd.read_parquet(KOSPI_PATH)
    kospi["date"] = pd.to_datetime(kospi["date"]).dt.normalize()
    p = pnl.loc[pnl["strategy"].eq(strategy), ["date", "net_return"]].copy()
    p = p.merge(kospi[["date", "daily_return"]], on="date", how="left")
    p["date"] = pd.to_datetime(p["date"])
    p["month"] = p["date"].dt.to_period("M")
    mon = p.groupby("month").agg(
        lo_return=("net_return", lambda x: float((1+x).prod()-1)),
        kospi_return=("daily_return", lambda x: float((1+x).prod()-1)),
    ).reset_index()
    mon["spread"] = mon["lo_return"] - mon["kospi_return"]
    mon["month_ts"] = mon["month"].dt.to_timestamp()
    out = {}
    for label, (start, end) in {"IS": IS, "OOS": OOS}.items():
        sub = mon.loc[mon["month_ts"].between(start.replace(day=1), end)]
        out[f"{label}_mean_monthly_spread"] = float(sub["spread"].mean()) if len(sub) else math.nan
        out[f"{label}_spread_win_rate"] = float((sub["spread"] > 0).mean()) if len(sub) else math.nan
    return out


def markdown_table(df: pd.DataFrame, cols: list[str], max_rows: int | None = None) -> str:
    out = df.loc[:, cols].copy()
    if max_rows:
        out = out.head(max_rows)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in out.itertuples(index=False):
        vals = []
        for v in row:
            if isinstance(v, float):
                vals.append("NA" if math.isnan(v) else f"{v:.4f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    returns = load_open_returns()
    needed = sorted(set(itertools.chain.from_iterable(MANUAL_CANDIDATES.values())) | set(SCREEN_BASE))
    sigs = {s: load_signal(s, returns.index, returns.columns) for s in needed}

    candidates = dict(MANUAL_CANDIDATES)
    # Broad but transparent exploratory screen: all 2-3 signal equal-weight blends including A4 or A3.
    for k in [2, 3]:
        for combo in itertools.combinations(SCREEN_BASE, k):
            if "A4" not in combo and "A3" not in combo:
                continue
            name = "SCR_" + "_".join(combo)
            candidates[name] = list(combo)

    rows = []
    pnl_frames = []
    for name, comps in candidates.items():
        comp = composite_signal(sigs, comps)
        for reb in [5, 20]:
            for q in [0.10, 0.15, 0.20]:
                eval_rows, pnl = evaluate(name, comps, comp, returns, reb, q)
                rows.extend(eval_rows)
                pnl_frames.append(pnl)
    metrics_df = pd.DataFrame(rows)
    pnl_all = pd.concat(pnl_frames, ignore_index=True)
    atomic_write_parquet(metrics_df, OUT_DIR / "metrics.parquet")
    atomic_write_parquet(pnl_all, OUT_DIR / "pnl_daily.parquet")

    wide = metrics_df.pivot_table(index=["strategy", "components", "rebalance", "q"], columns="period", values=["sharpe", "ann_return", "ann_vol", "max_dd", "avg_turnover"], aggfunc="first")
    wide.columns = [f"{metric}_{period}" for metric, period in wide.columns]
    wide = wide.reset_index()
    # Add A4-relative screen. Need both robust IS and OOS, not pure OOS cherry-pick.
    subs = metrics_df[metrics_df["period"].str.startswith("sub")].groupby(["strategy","rebalance","q"])["sharpe"].min().reset_index(name="min_sub_sharpe")
    wide = wide.merge(subs, on=["strategy","rebalance","q"], how="left")
    wide = wide.sort_values(["sharpe_OOS", "sharpe_IS"], ascending=False)
    atomic_write_parquet(wide, OUT_DIR / "summary_wide.parquet")

    # Monthly spread stats only for top 10 + A4 baseline rows.
    top_keys = wide.head(10)[["strategy","rebalance","q"]].apply(tuple, axis=1).tolist()
    a4_keys = wide[wide["strategy"].eq("A4")][["strategy","rebalance","q"]].apply(tuple, axis=1).tolist()
    monthly_rows = []
    for strategy, reb, q in top_keys + a4_keys:
        strat_pnl = pnl_all[(pnl_all.strategy == strategy) & (pnl_all.rebalance == reb) & (pnl_all.q == q)]
        if strat_pnl.empty:
            continue
        stats = monthly_alpha(strat_pnl, strategy)
        monthly_rows.append({"strategy": strategy, "rebalance": reb, "q": q, **stats})
    monthly_df = pd.DataFrame(monthly_rows).drop_duplicates()
    atomic_write_parquet(monthly_df, OUT_DIR / "monthly_spread_summary.parquet")

    top = wide.merge(monthly_df, on=["strategy","rebalance","q"], how="left").sort_values(["sharpe_OOS", "sharpe_IS"], ascending=False)
    a4 = top[top.strategy.eq("A4")].sort_values(["rebalance","q"])
    robust = top[(top["sharpe_OOS"] > 3.115) & (top["sharpe_IS"] > 1.0) & (top["max_dd_OOS"] > -0.08)].head(20)

    text = "# A4-plus exploratory backtest\n\n"
    text += "Scope: equal-weight blends of existing Step 8.1 cross-sectional z-score signals. LO only, t+1 open-to-open, 30bp one-way, 5d/20d rebalance, top 10/15/20%. This is exploratory and data-snooping-prone.\n\n"
    text += "## A4 baseline rows\n"
    text += markdown_table(a4, ["strategy","components","rebalance","q","sharpe_IS","sharpe_OOS","ann_return_OOS","ann_vol_OOS","max_dd_OOS","avg_turnover_OOS","OOS_mean_monthly_spread","OOS_spread_win_rate"]) + "\n\n"
    text += "## Top rows by OOS Sharpe\n"
    text += markdown_table(top, ["strategy","components","rebalance","q","sharpe_IS","sharpe_OOS","ann_return_OOS","ann_vol_OOS","max_dd_OOS","avg_turnover_OOS","min_sub_sharpe","OOS_mean_monthly_spread","OOS_spread_win_rate"], max_rows=30) + "\n\n"
    text += "## Rows beating A4 5d q=10 OOS Sharpe with IS>1 and OOS MDD better than -8%\n"
    if robust.empty:
        text += "None.\n"
    else:
        text += markdown_table(robust, ["strategy","components","rebalance","q","sharpe_IS","sharpe_OOS","ann_return_OOS","ann_vol_OOS","max_dd_OOS","avg_turnover_OOS","min_sub_sharpe","OOS_mean_monthly_spread","OOS_spread_win_rate"]) + "\n"
    text += "\n## Artifacts\n- v2/data/cache/a4_plus_explore/metrics.parquet\n- v2/data/cache/a4_plus_explore/summary_wide.parquet\n- v2/data/cache/a4_plus_explore/pnl_daily.parquet\n- v2/data/cache/a4_plus_explore/monthly_spread_summary.parquet\n"
    atomic_write_text(text, REPORT_PATH)
    print({"n_rows": len(metrics_df), "n_strategies": len(candidates), "report": str(REPORT_PATH)})


if __name__ == "__main__":
    run()
