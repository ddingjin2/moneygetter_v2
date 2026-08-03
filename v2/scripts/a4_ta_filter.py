from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.scripts.a4_risk_overlay import (  # noqa: E402
    PRICE_DIR,
    SIGNAL_PATH,
    RiskOverlayConfig,
    _atomic_parquet,
    _atomic_text,
    markdown_table,
    metrics,
    simulate_risk_overlay,
)

OUTPUT_DIR = ROOT / "v2/data/cache/a4_ta_filter"
REPORT_PATH = ROOT / "v2/reports/a4_ta_filter.md"


def load_panel() -> dict[str, pd.DataFrame]:
    frames = []
    for path in sorted(PRICE_DIR.glob("[0-9][0-9][0-9][0-9][0-9][0-9].parquet")):
        frame = pd.read_parquet(path, columns=["date", "open", "high", "low", "close"])
        frame["code"] = path.stem
        frames.append(frame)
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    out = {}
    for column in ["open", "high", "low", "close"]:
        out[column] = panel.pivot(index="date", columns="code", values=column).sort_index().astype("float64")
    return out


def load_signal(like: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_parquet(SIGNAL_PATH)
    raw["date"] = pd.to_datetime(raw["date"]).dt.normalize()
    return raw.pivot(index="date", columns="code", values="signal_cs_z").reindex(index=like.index, columns=like.columns)


def build_masks(panel: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    close, high, low = panel["close"], panel["high"], panel["low"]
    delta = close.diff()
    up = delta.clip(lower=0.0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    down = (-delta).clip(lower=0.0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rsi14 = 100.0 - 100.0 / (1.0 + up / down.replace(0.0, np.nan))
    ma20 = close.rolling(20, min_periods=20).mean()
    disparity = close / ma20 - 1.0
    intraday_pos = (close - low) / (high - low).replace(0.0, np.nan)
    # NaN indicator = keep the stock (no exclusion without evidence)
    return {
        "rsi_gt70": rsi14.gt(70).fillna(False),
        "disp_gt10": disparity.gt(0.10).fillna(False),
        "below_ma20": disparity.lt(0.0).fillna(False),
        "ta11_gt80": intraday_pos.gt(0.80).fillna(False),
    }


def run_experiment() -> dict[str, object]:
    panel = load_panel()
    signal = load_signal(panel["close"])
    masks: dict[str, pd.DataFrame | None] = {"baseline": None, **build_masks(panel)}
    result_rows = []
    daily_frames = []
    for cost_bps in [10, 30]:
        for name, mask in masks.items():
            daily, events = simulate_risk_overlay(
                panel["open"],
                panel["close"],
                signal,
                RiskOverlayConfig(),
                rebalance_days=20,
                top_q=0.10,
                min_universe=30,
                cost_bps=cost_bps,
                initial_capital=100_000_000.0,
                exclude=mask,
            )
            summary = metrics(daily)
            summary.update(
                {
                    "variant": name,
                    "cost_bps": cost_bps,
                    "avg_positions": float(daily["position_count"].mean()),
                    "min_positions": int(daily.loc[daily["position_count"].gt(0), "position_count"].min()),
                }
            )
            result_rows.append(summary)
            daily.insert(0, "cost_bps", cost_bps)
            daily.insert(0, "variant", name)
            daily_frames.append(daily)

    results = pd.DataFrame(result_rows)
    for cost_bps in [10, 30]:
        baseline = results.loc[results["cost_bps"].eq(cost_bps) & results["variant"].eq("baseline")].iloc[0]
        mask_rows = results["cost_bps"].eq(cost_bps)
        results.loc[mask_rows, "sharpe_vs_baseline"] = results.loc[mask_rows, "sharpe"] - float(baseline["sharpe"])
        results.loc[mask_rows, "ann_return_vs_baseline"] = results.loc[mask_rows, "ann_return"] - float(baseline["ann_return"])
        results.loc[mask_rows, "max_dd_vs_baseline"] = results.loc[mask_rows, "max_dd"] - float(baseline["max_dd"])
        results.loc[mask_rows, "improve_pass"] = (
            results.loc[mask_rows, "sharpe_vs_baseline"].ge(0.02)
            & results.loc[mask_rows, "ann_return_vs_baseline"].ge(-0.01)
            & results.loc[mask_rows, "max_dd_vs_baseline"].ge(-0.01)
            & results.loc[mask_rows, "variant"].ne("baseline")
        )

    daily_all = pd.concat(daily_frames, ignore_index=True)
    _atomic_parquet(results, OUTPUT_DIR / "metrics.parquet")
    _atomic_parquet(daily_all, OUTPUT_DIR / "daily.parquet")

    view = results[
        [
            "variant",
            "cost_bps",
            "sharpe",
            "ann_return",
            "max_dd",
            "sharpe_vs_baseline",
            "ann_return_vs_baseline",
            "max_dd_vs_baseline",
            "avg_positions",
            "min_positions",
            "improve_pass",
        ]
    ].sort_values(["cost_bps", "improve_pass", "sharpe"], ascending=[True, False, False])
    text = f"""# A4 + TA rebalance filter backtest

## Rules

- Baseline: A4 cross-sectional z-score, top decile, 20-trading-day rebalance, next-open fills (same engine as a4_risk_overlay).
- Filter applied only at rebalance selection, using the decision-day close. Excluded names are dropped; capital redistributes equally among survivors.
- Filters: `rsi_gt70` RSI14 > 70, `disp_gt10` close more than 10% above MA20, `below_ma20` close below MA20, `ta11_gt80` intraday close position above 0.8.
- NaN indicator keeps the stock.
- Improvement pass at each cost: Sharpe at least +0.02 over baseline, annual return no more than 1%p lower, MDD no more than 1%p worse.

## Results

{markdown_table(view)}

## Decision

- 30bp pass count: {int(results.loc[results['cost_bps'].eq(30), 'improve_pass'].sum())}
"""
    _atomic_text(text, REPORT_PATH)
    pass_rows = results.loc[results["cost_bps"].eq(30) & results["improve_pass"]]
    return {
        "variants": len(masks),
        "latest_date": pd.to_datetime(daily_all["date"]).max().date().isoformat(),
        "pass_count_30bp": int(len(pass_rows)),
        "passing_variants_30bp": pass_rows["variant"].tolist(),
        "report": str(REPORT_PATH),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest TA-based exclusion filters on A4 rebalance selection.")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print(json.dumps(list(build_masks(load_panel()).keys()), ensure_ascii=False))
        return
    print(json.dumps(run_experiment(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
