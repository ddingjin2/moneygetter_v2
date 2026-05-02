from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

import mpmath as mp
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.scripts.signal_catalog import SIGNAL_CATALOG  # noqa: E402


SIGNALS_DIR = ROOT / "v2/data/cache/signals_batch"
RETURNS_PATH = ROOT / "v2/data/cache/returns/forward_returns.parquet"
TRADING_STATUS_PATH = ROOT / "v2/data/cache/price_market_cap_full/_trading_status.parquet"
FULL_OUTPUT_PATH = ROOT / "v2/data/cache/ic/ic_batch_full.parquet"
SUMMARY_OUTPUT_PATH = ROOT / "v2/data/cache/ic/ic_batch_summary.parquet"
REPORT_PATH = ROOT / "v2/reports/pr7_a_X_step8_2_ic_batch.md"

HORIZONS = ["1d", "5d", "20d"]
STEP8_1_A0_5D_IC = -0.009385
A0_GREEN_THRESHOLD = 0.0001
BONFERRONI_THRESHOLD_63 = 0.05 / 63
BONFERRONI_THRESHOLD_60 = 0.05 / 60


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


def two_sided_t_p_value(t_stat: float, df: int) -> float:
    if pd.isna(t_stat) or df <= 0:
        return math.nan
    t_abs = abs(float(t_stat))
    x = df / (df + t_abs * t_abs)
    return float(mp.betainc(df / 2, 0.5, 0, x, regularized=True))


def bh_q_values(p_values: pd.Series, *, total_tests: int) -> pd.Series:
    q = pd.Series(np.nan, index=p_values.index, dtype="float64")
    valid = p_values.dropna().sort_values()
    if valid.empty:
        return q
    ranks = np.arange(1, len(valid) + 1, dtype="float64")
    raw_q = valid.to_numpy(dtype="float64") * total_tests / ranks
    monotone_q = np.minimum.accumulate(raw_q[::-1])[::-1]
    q.loc[valid.index] = np.minimum(monotone_q, 1.0)
    return q


def load_returns() -> pd.DataFrame:
    required = ["code", "date"]
    for horizon in HORIZONS:
        required.extend([f"forward_return_{horizon}", f"ret_valid_{horizon}"])
    frame = pd.read_parquet(RETURNS_PATH)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise RuntimeError(f"forward_returns.parquet is missing required columns: {missing}")
    frame = frame[required].copy()
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    return frame


def load_signal(signal_id: str) -> pd.DataFrame:
    path = SIGNALS_DIR / f"{signal_id}_cs_zscore.parquet"
    if not path.exists():
        raise RuntimeError(f"Missing signal z-score file: {path}")
    frame = pd.read_parquet(path)
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    return frame[["code", "date", "signal_cs_z"]]


def rank_ic_by_date(signal: pd.DataFrame, returns: pd.DataFrame, horizon: str) -> pd.DataFrame:
    ret_col = f"forward_return_{horizon}"
    valid_col = f"ret_valid_{horizon}"
    merged = signal.merge(returns[["code", "date", ret_col, valid_col]], on=["code", "date"], how="inner")
    valid = merged["signal_cs_z"].notna() & merged[ret_col].notna() & merged[valid_col].astype(bool)
    rows: list[dict[str, object]] = []
    for date, group in merged.loc[valid, ["date", "signal_cs_z", ret_col]].groupby("date", sort=True):
        n_valid = int(len(group))
        ic = math.nan
        if n_valid >= 30:
            ic = float(group["signal_cs_z"].rank().corr(group[ret_col].rank()))
        rows.append({"date": date, "ic": ic, "n_valid": n_valid})
    return pd.DataFrame(rows, columns=["date", "ic", "n_valid"])


def summarize_ic(full: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (signal_id, horizon), group in full.groupby(["signal_id", "horizon"], sort=False):
        valid = group.loc[group["ic"].notna()].copy()
        n_days = int(len(valid))
        mean_ic = float(valid["ic"].mean()) if n_days else math.nan
        std_ic = float(valid["ic"].std(ddof=1)) if n_days > 1 else math.nan
        t_stat = mean_ic / (std_ic / math.sqrt(n_days)) if n_days > 1 and std_ic and not math.isnan(std_ic) else math.nan
        rows.append(
            {
                "signal_id": signal_id,
                "horizon": horizon,
                "mean_ic": mean_ic,
                "std_ic": std_ic,
                "t_stat": t_stat,
                "p_value_raw": two_sided_t_p_value(t_stat, n_days - 1),
                "positive_ratio": float((valid["ic"] > 0).mean()) if n_days else math.nan,
                "n_days": n_days,
                "avg_n_valid": float(valid["n_valid"].mean()) if n_days else math.nan,
                "ic_p05": float(valid["ic"].quantile(0.05)) if n_days else math.nan,
                "ic_p25": float(valid["ic"].quantile(0.25)) if n_days else math.nan,
                "ic_median": float(valid["ic"].median()) if n_days else math.nan,
                "ic_p75": float(valid["ic"].quantile(0.75)) if n_days else math.nan,
                "ic_p95": float(valid["ic"].quantile(0.95)) if n_days else math.nan,
            }
        )
    summary = pd.DataFrame(rows)
    summary["bonferroni_threshold_63"] = BONFERRONI_THRESHOLD_63
    summary["bonferroni_threshold_60"] = BONFERRONI_THRESHOLD_60
    summary["bonferroni_pass_63"] = summary["p_value_raw"] < BONFERRONI_THRESHOLD_63
    summary["bonferroni_pass_60"] = (summary["p_value_raw"] < BONFERRONI_THRESHOLD_60).astype("object")
    summary.loc[summary["signal_id"].eq("A0_baseline"), "bonferroni_pass_60"] = pd.NA
    summary["bh_q_63"] = bh_q_values(summary["p_value_raw"], total_tests=63)
    summary["bh_fdr_pass_63"] = summary["bh_q_63"] <= 0.05
    non_a0 = ~summary["signal_id"].eq("A0_baseline")
    summary["bh_q_60"] = np.nan
    summary.loc[non_a0, "bh_q_60"] = bh_q_values(summary.loc[non_a0, "p_value_raw"], total_tests=60)
    summary["bh_fdr_pass_60"] = (summary["bh_q_60"] <= 0.05).astype("object")
    summary.loc[~non_a0, "bh_fdr_pass_60"] = pd.NA
    return summary


def compute_full_ic() -> pd.DataFrame:
    returns = load_returns()
    rows: list[pd.DataFrame] = []
    for spec in SIGNAL_CATALOG:
        signal = load_signal(spec.signal_id)
        for horizon in HORIZONS:
            ic = rank_ic_by_date(signal, returns, horizon)
            ic.insert(0, "horizon", horizon)
            ic.insert(0, "signal_id", spec.signal_id)
            rows.append(ic)
    full = pd.concat(rows, ignore_index=True)
    return full[["signal_id", "horizon", "date", "ic", "n_valid"]]


def a0_regression_check(summary: pd.DataFrame) -> dict[str, object]:
    row = summary.loc[summary["signal_id"].eq("A0_baseline") & summary["horizon"].eq("5d")]
    if row.empty:
        return {"status": "RED", "current_5d_ic": math.nan, "abs_diff": math.nan}
    current = float(row.iloc[0]["mean_ic"])
    diff = abs(current - STEP8_1_A0_5D_IC)
    return {
        "status": "GREEN" if diff < A0_GREEN_THRESHOLD else "RED",
        "current_5d_ic": current,
        "abs_diff": diff,
    }


def bool_list(summary: pd.DataFrame, column: str) -> list[str]:
    mask = summary[column].map(lambda value: bool(value) if pd.notna(value) else False)
    frame = summary.loc[mask, ["signal_id", "horizon", "mean_ic", "p_value_raw"]]
    frame = frame.sort_values(["signal_id", "horizon"])
    return [f"{row.signal_id}/{row.horizon} (mean_ic={row.mean_ic:.6f}, p={row.p_value_raw:.3g})" for row in frame.itertuples()]


def markdown_table(frame: pd.DataFrame, columns: list[str], *, max_rows: int | None = None) -> str:
    out = frame.loc[:, columns].copy()
    if max_rows is not None:
        out = out.head(max_rows)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in out.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("NA" if math.isnan(value) else f"{value:.6f}")
            elif pd.isna(value):
                values.append("NA")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def bullet_list(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def data_summary() -> dict[str, object]:
    returns = pd.read_parquet(RETURNS_PATH)
    trading = pd.read_parquet(TRADING_STATUS_PATH)
    return {
        "universe_stocks": int(returns["code"].nunique()),
        "date_min": pd.to_datetime(returns["date"]).min().date().isoformat(),
        "date_max": pd.to_datetime(returns["date"]).max().date().isoformat(),
        "total_pairs": int(len(returns)),
        "ret_valid_1d": float(returns["ret_valid_1d"].mean()),
        "ret_valid_5d": float(returns["ret_valid_5d"].mean()),
        "ret_valid_20d": float(returns["ret_valid_20d"].mean()),
        "trading_halt_rows": int(trading["trading_halt"].sum()),
    }


def write_report(full: pd.DataFrame, summary: pd.DataFrame, a0_check: dict[str, object]) -> None:
    summary_sorted = summary.assign(abs_mean_ic=summary["mean_ic"].abs()).sort_values(
        "abs_mean_ic", ascending=False
    )
    sparse_base = summary.groupby("horizon")["n_days"].transform("mean") * 0.80
    sparse = summary.loc[
        summary["signal_id"].isin(["C3", "C5"]) | summary["n_days"].lt(sparse_base),
        ["signal_id", "horizon", "n_days", "avg_n_valid"],
    ].sort_values(["signal_id", "horizon"])
    cross_signal_5d = summary.loc[summary["horizon"].eq("5d"), ["signal_id", "mean_ic", "t_stat"]].sort_values(
        "signal_id"
    )
    ds = data_summary()
    text = f"""# PR-7.A.X Step 8.2 Batch IC Measurement

## 1. Scope & Setup
- Scope: 21 signals x 3 horizons = 63 tests. Raw IC + multiple testing adjustment.
- Catalog `expected_horizons` value 21 is mapped into 20d to avoid duplicate monthly horizon reporting.
- Universe stocks: `{ds["universe_stocks"]}`
- Date range: `{ds["date_min"]} ~ {ds["date_max"]}`
- Total `(code, date)` pairs: `{ds["total_pairs"]}`
- Return valid ratios: `1d={ds["ret_valid_1d"]:.1%}`, `5d={ds["ret_valid_5d"]:.1%}`, `20d={ds["ret_valid_20d"]:.1%}`
- Trading halt rows in status cache: `{ds["trading_halt_rows"]}`
- Multiple testing: Bonferroni N=63 / N=60, BH-FDR N=63 / N=60.

## 2. A0_baseline Regression Re-check
- Step 8.1 5d IC: `{STEP8_1_A0_5D_IC:.6f}`
- Current 5d IC: `{a0_check["current_5d_ic"]:.6f}`
- Absolute diff: `{a0_check["abs_diff"]:.6f}`
- Status: `{a0_check["status"]}`

## 3. Full IC Summary Table
{markdown_table(summary_sorted, ["signal_id", "horizon", "mean_ic", "std_ic", "t_stat", "p_value_raw", "positive_ratio", "n_days", "avg_n_valid", "ic_p05", "ic_p25", "ic_median", "ic_p75", "ic_p95", "bh_q_63", "bh_q_60", "bonferroni_pass_63", "bonferroni_pass_60", "bh_fdr_pass_63", "bh_fdr_pass_60"])}

## 4. Significant Pairs Listing (descriptive only)

### Bonferroni N=63
Count: `{int(summary["bonferroni_pass_63"].fillna(False).sum())}`
{bullet_list(bool_list(summary, "bonferroni_pass_63"))}

### Bonferroni N=60
Count: `{int(summary["bonferroni_pass_60"].map(lambda value: bool(value) if pd.notna(value) else False).sum())}`
{bullet_list(bool_list(summary, "bonferroni_pass_60"))}

### BH-FDR N=63
Count: `{int(summary["bh_fdr_pass_63"].fillna(False).sum())}`
{bullet_list(bool_list(summary, "bh_fdr_pass_63"))}

### BH-FDR N=60
Count: `{int(summary["bh_fdr_pass_60"].map(lambda value: bool(value) if pd.notna(value) else False).sum())}`
{bullet_list(bool_list(summary, "bh_fdr_pass_60"))}

## 5. Sparsity Caveat
{markdown_table(sparse, ["signal_id", "horizon", "n_days", "avg_n_valid"])}

## 6. Cross-signal IC Distribution (descriptive)
{markdown_table(cross_signal_5d, ["signal_id", "mean_ic", "t_stat"])}

## 7. Caveats
- Alive-only universe.
- Market capitalization unavailable.
- Equal-weight assumption for later portfolio work; cross-sectional IC itself is rank based and unweighted.
- Both A0-included N=63 and A0-excluded N=60 adjustments are reported because A0 handling is a user decision.
- C3 and C5 use stress-day filters, producing different statistical power.
- Catalog 21d expected horizon is mapped to 20d in this Step 8.2 report.

## 8. Artifacts
- `v2/data/cache/ic/ic_batch_full.parquet`
- `v2/data/cache/ic/ic_batch_summary.parquet`

## Gate
Step 8.2 raw measurement complete. Step 8.3 requires user approval. Raw result interpretation and PASS/FAIL judgment remain user-owned.
"""
    atomic_write_text(text, REPORT_PATH)


def run() -> dict[str, object]:
    full = compute_full_ic()
    summary = summarize_ic(full)
    a0_check = a0_regression_check(summary)
    if a0_check["status"] != "GREEN":
        atomic_write_parquet(full, FULL_OUTPUT_PATH)
        atomic_write_parquet(summary, SUMMARY_OUTPUT_PATH)
        raise RuntimeError(f"A0_baseline regression re-check RED: {a0_check}")
    atomic_write_parquet(full, FULL_OUTPUT_PATH)
    atomic_write_parquet(summary, SUMMARY_OUTPUT_PATH)
    write_report(full, summary, a0_check)
    return {
        "full_rows": int(len(full)),
        "summary_rows": int(len(summary)),
        "a0_check": a0_check,
        "bonferroni_63_count": int(summary["bonferroni_pass_63"].fillna(False).sum()),
        "bonferroni_60_count": int(summary["bonferroni_pass_60"].map(lambda value: bool(value) if pd.notna(value) else False).sum()),
        "bh_fdr_63_count": int(summary["bh_fdr_pass_63"].fillna(False).sum()),
        "bh_fdr_60_count": int(summary["bh_fdr_pass_60"].map(lambda value: bool(value) if pd.notna(value) else False).sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PR-7.A.X Step 8.2 batch IC measurement.")
    parser.add_argument("--run", action="store_true", help="Write Step 8.2 IC artifacts and report.")
    args = parser.parse_args()
    if not args.run:
        print("signals", len(SIGNAL_CATALOG))
        print("horizons", ",".join(HORIZONS))
        print("tests", len(SIGNAL_CATALOG) * len(HORIZONS))
        return
    print(run())


if __name__ == "__main__":
    main()
