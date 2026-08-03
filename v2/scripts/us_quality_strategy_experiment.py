from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.us_fundamentals import (  # noqa: E402
    align_fundamentals_asof,
    extract_sec_companyfacts_fundamentals,
    load_fundamentals,
    quality_score,
)
from v2.scripts.us_residual_reversal_experiment import (  # noqa: E402
    StrategySpec,
    atomic_write_parquet,
    atomic_write_text,
    backtest_signal,
    load_panel,
    markdown_table,
    performance_metrics,
    qqq_risk_on,
    residual_reversal_signal,
    summarize_results,
    weekly_metrics,
)

V2_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = V2_ROOT / "data/cache/us/nasdaq100_pitlite/strategy_compare/quality_fundamental"
FUNDAMENTALS_PATH = OUT_DIR / "sec_companyfacts_fundamentals.parquet"
REPORT_PATH = V2_ROOT / "reports/us/quality_fundamental_strategy_experiment.md"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "moneygetter-v2 research contact@example.com")


def experiment_rebalance_days() -> list[int]:
    return [2, 5, 10, 20]


def stock_leverage_grid() -> list[float]:
    return [1.0, 1.25, 1.5, 1.75, 2.0]


def stop_loss_grid() -> list[float]:
    return [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]


def stopped_forward_returns(
    open_px: pd.DataFrame,
    low_px: pd.DataFrame,
    stop_loss: float,
    stop_slippage_bps: float = 10.0,
) -> pd.DataFrame:
    base = open_px.shift(-1) / open_px - 1.0
    intraday_low_return = low_px / open_px - 1.0
    stop_return = -float(stop_loss) - (float(stop_slippage_bps) / 10000.0)
    return base.mask(intraday_low_return.le(-float(stop_loss)), stop_return)


def load_panel_with_low(path: Path = V2_ROOT / "data/processed/us_nasdaq100_pitlite_ohlcv.parquet") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ohlcv = pd.read_parquet(path)
    ohlcv["date"] = pd.to_datetime(ohlcv["date"]).dt.normalize()
    for column in ["adj_open", "adj_low", "adj_close", "dollar_volume"]:
        ohlcv[column] = pd.to_numeric(ohlcv[column], errors="coerce")
    open_px = ohlcv.pivot(index="date", columns="symbol", values="adj_open").sort_index()
    low_px = ohlcv.pivot(index="date", columns="symbol", values="adj_low").reindex_like(open_px)
    close_px = ohlcv.pivot(index="date", columns="symbol", values="adj_close").reindex_like(open_px)
    dvol = ohlcv.pivot(index="date", columns="symbol", values="dollar_volume").reindex_like(open_px)
    return open_px, low_px, close_px, dvol


def market_riskoff_ma(close_px: pd.DataFrame, ma: int = 175, market_symbol: str = "QQQ") -> pd.Series:
    close = close_px[market_symbol] if market_symbol in close_px.columns else close_px.mean(axis=1, skipna=True)
    return close.shift(1).lt(close.shift(1).rolling(ma, min_periods=ma).mean()).fillna(False)


def apply_market_hedge_overlay(
    frame: pd.DataFrame,
    market_returns: pd.Series,
    riskoff: pd.Series,
    stock_leverage: float,
    hedge_ratio: float,
    financing_rate: float = 0.07,
    hedge_rebalance_cost_bps: float = 10.0,
) -> pd.DataFrame:
    out = frame.copy()
    dates = pd.to_datetime(out["date"]).dt.normalize()
    market = market_returns.reindex(dates).fillna(0.0).to_numpy()
    hedge_on = riskoff.reindex(dates).fillna(False).astype(bool).to_numpy()
    hedge_exposure = np.where(hedge_on, -float(hedge_ratio), 0.0)
    stock_exposure = float(stock_leverage)
    financing = max(stock_exposure - 1.0, 0.0) * float(financing_rate) / 252.0
    hedge_turnover_cost = np.abs(pd.Series(hedge_exposure).diff().fillna(hedge_exposure[0] if len(hedge_exposure) else 0.0)).to_numpy()
    hedge_turnover_cost = hedge_turnover_cost * (float(hedge_rebalance_cost_bps) / 10000.0)
    out["base_net_return"] = out["net_return"].astype("float64")
    out["stock_exposure"] = stock_exposure
    out["hedge_exposure"] = hedge_exposure
    out["hedge_return"] = hedge_exposure * market
    out["net_return"] = out["base_net_return"] * stock_exposure + hedge_exposure * market - financing - hedge_turnover_cost
    out["gross_return"] = out["net_return"]
    out["exposure"] = stock_exposure + np.abs(hedge_exposure)
    return out


def max_consecutive_true(values: pd.Series) -> int:
    return max((sum(1 for _ in group) for key, group in itertools.groupby(values.fillna(False)) if key), default=0)


def monthly_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"])
    monthly = data.groupby(data["date"].dt.to_period("M"))["net_return"].apply(lambda s: float((1.0 + s).prod() - 1.0))
    return {
        "n_months": int(len(monthly)),
        "monthly_win_rate": float((monthly > 0.0).mean()) if len(monthly) else math.nan,
        "monthly_loss_rate": float((monthly < 0.0).mean()) if len(monthly) else math.nan,
        "mean_monthly_return": float(monthly.mean()) if len(monthly) else math.nan,
        "median_monthly_return": float(monthly.median()) if len(monthly) else math.nan,
        "p05_monthly_return": float(monthly.quantile(0.05)) if len(monthly) else math.nan,
        "worst_monthly_return": float(monthly.min()) if len(monthly) else math.nan,
        "max_consecutive_losing_months": max_consecutive_true(monthly < 0.0),
    }


def cross_sectional_zscore_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
    mean = matrix.mean(axis=1, skipna=True)
    std = matrix.std(axis=1, skipna=True, ddof=0).replace(0.0, np.nan)
    return matrix.sub(mean, axis=0).div(std, axis=0).fillna(0.0)


def combine_signal_matrices(price_signal: pd.DataFrame, quality_signal: pd.DataFrame, quality_weight: float = 0.5) -> pd.DataFrame:
    price_z = cross_sectional_zscore_matrix(price_signal)
    quality_z = cross_sectional_zscore_matrix(quality_signal.reindex_like(price_signal))
    usable_quality = quality_signal.reindex_like(price_signal).notna()
    combined = price_z + quality_z.mul(float(quality_weight))
    return combined.where(usable_quality)


def quality_matrix_from_fundamentals(
    fundamentals: pd.DataFrame,
    dates: pd.Index,
    symbols: list[str] | pd.Index,
) -> pd.DataFrame:
    aligned = align_fundamentals_asof(fundamentals, pd.DatetimeIndex(dates), symbols)
    scores = quality_score(aligned)
    return scores.unstack("symbol").reindex(index=dates, columns=symbols)


def build_price_signal_matrices(close_px: pd.DataFrame, dvol: pd.DataFrame, market_symbol: str = "QQQ") -> dict[str, pd.DataFrame]:
    close_ret = close_px.pct_change(fill_method=None)
    market = close_ret[market_symbol] if market_symbol in close_ret.columns else close_ret.mean(axis=1, skipna=True)
    amihud = -(close_ret.abs() / dvol.replace(0.0, np.nan))
    residual = residual_reversal_signal(close_ret, market, lookback=5, beta_window=60)
    vol60 = -close_ret.rolling(60, min_periods=60).std(ddof=0)
    momentum_12_1 = close_px.shift(21) / close_px.shift(252) - 1.0
    liquid_mask = dvol.rolling(60, min_periods=20).mean().ge(20_000_000.0)
    return {
        "US_QP1_quality_plus_amihud_liquidity": amihud.where(liquid_mask),
        "US_QP2_quality_plus_residual_reversal": residual.where(liquid_mask),
        "US_QP3_quality_plus_lowvol": vol60.where(liquid_mask),
        "US_QP4_quality_plus_momentum": momentum_12_1.where(liquid_mask),
    }


def sec_get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": SEC_USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def sec_symbol_to_cik() -> dict[str, int]:
    payload = sec_get_json(SEC_TICKERS_URL)
    return {str(row["ticker"]).upper(): int(row["cik_str"]) for row in payload.values()}


def collect_sec_fundamentals(symbols: list[str], sleep_seconds: float = 0.12) -> pd.DataFrame:
    cik_map = sec_symbol_to_cik()
    frames = []
    skipped = []
    for symbol in sorted({s.upper() for s in symbols if s.upper() not in {"QQQ", "SPY"}}):
        cik = cik_map.get(symbol)
        if cik is None:
            skipped.append(symbol)
            continue
        try:
            payload = sec_get_json(SEC_FACTS_URL.format(cik=cik))
            frame = extract_sec_companyfacts_fundamentals(symbol, payload)
            if len(frame):
                frames.append(frame)
        except Exception:
            skipped.append(symbol)
        time.sleep(sleep_seconds)
    if not frames:
        return pd.DataFrame(columns=["symbol", "fiscal_period_end", "filing_date", "gross_profit", "net_income", "total_assets", "total_liabilities"])
    out = pd.concat(frames, ignore_index=True)
    out.attrs["skipped_symbols"] = skipped
    return out


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


def build_market_hedge_overlays(pnls: pd.DataFrame, market_returns: pd.Series, riskoff: pd.Series) -> pd.DataFrame:
    overlays = []
    eligible = pnls.loc[pnls["strategy_id"].str.contains("quality_plus_momentum") & ~pnls["strategy_id"].str.contains("_stop")]
    for strategy_id, frame in eligible.groupby("strategy_id"):
        for stock_leverage in stock_leverage_grid():
            for hedge_ratio in [0.25, 0.5, 0.75, 1.0, 1.25]:
                hedged = apply_market_hedge_overlay(
                    frame.sort_values("date"),
                    market_returns,
                    riskoff,
                    stock_leverage=stock_leverage,
                    hedge_ratio=hedge_ratio,
                )
                hedged["strategy_id"] = (
                    f"{strategy_id}_stock{stock_leverage:g}x_q{hedge_ratio:g}x_ma175hedge"
                )
                overlays.append(hedged)
    return pd.concat(overlays, ignore_index=True) if overlays else pd.DataFrame(columns=pnls.columns)


def build_stop_loss_variants(
    signals: dict[str, pd.DataFrame],
    open_px: pd.DataFrame,
    low_px: pd.DataFrame,
    risk_on: pd.Series,
) -> pd.DataFrame:
    frames = []
    base_index = open_px.index[open_px.index <= pd.Timestamp("2026-05-28")]
    for stop_loss in stop_loss_grid():
        returns = stopped_forward_returns(open_px, low_px, stop_loss=stop_loss).loc[base_index]
        for signal_id, signal in signals.items():
            if "quality_plus_momentum" not in signal_id:
                continue
            for quantile in [0.1, 0.2]:
                for rebalance in [2, 5, 10, 20]:
                    for risk_filter in ["always", "ma175"]:
                        spec = StrategySpec(signal_id, quantile, rebalance, risk_filter, cost_bps=30)
                        signal_matrix = signal.reindex(index=returns.index, columns=returns.columns)
                        frame = backtest_signal(signal_matrix, returns, spec, risk_on)
                        frame["strategy_id"] = f"{spec.strategy_id}_stop{int(stop_loss * 100)}"
                        frame["stop_loss"] = stop_loss
                        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def write_report(metrics: pd.DataFrame, weekly: pd.DataFrame, monthly: pd.DataFrame, summary: dict[str, object]) -> None:
    full = metrics.loc[metrics["period"].eq("Full 2020-2026")].merge(weekly, on=["strategy_id", "signal_id"], how="left")
    full = full.merge(monthly, on=["strategy_id", "signal_id"], how="left")
    stable = full.sort_values(["weekly_win_rate", "cagr"], ascending=False)
    balanced = full.loc[full["max_dd"].ge(-0.30)].sort_values(["cagr", "weekly_win_rate"], ascending=False)
    baseline = full.loc[full["strategy_id"].eq("US_QP4_quality_plus_momentum_LO_decile_5d_always_30bps")]
    if len(baseline):
        base = baseline.iloc[0]
        beats_base = full.loc[full["cagr"].gt(base["cagr"]) & full["max_dd"].gt(base["max_dd"])].sort_values(["cagr", "max_dd"], ascending=[False, False])
    else:
        beats_base = full.iloc[0:0]
    two_x = full.loc[full["strategy_id"].str.contains("stock2x")].sort_values("cagr", ascending=False)
    lines = [
        "# US Quality Fundamental Strategy Experiment",
        "",
        "- Universe/data: Nasdaq 100 PIT-lite expanded individual stocks, yfinance adjusted OHLCV.",
        "- Fundamentals: SEC Company Facts parsed with SEC `filed` dates; signals only see fundamentals after filing date.",
        "- Quality score: gross profitability, ROA, and low leverage, cross-sectionally standardized by date.",
        "- Strategy candidates: quality combined with Amihud liquidity, residual reversal, low volatility, and 12-1 momentum.",
        f"- Rebalance frequencies tested: `{', '.join(f'{d}d' for d in experiment_rebalance_days())}`.",
        f"- Stock leverage grid for hedge overlays: `{', '.join(f'{x:g}x' for x in stock_leverage_grid())}`.",
        f"- Stock-only stop-loss grid: `{', '.join(f'{x:.0%}' for x in stop_loss_grid())}` using adjusted daily lows; stop variants do not trade index ETFs.",
        "- Overlay candidates: selected quality+momentum sleeves can add a QQQ short hedge only when QQQ is below its shifted MA175 risk-off filter.",
        "- Cost model: 30 bps one-way stock trading cost in daily-return simulation; hedge overlay uses 10 bps rebalance cost and 7% annual financing cost above 1x stock exposure. Korean tax still needs lot-level executions and USD/KRW FX for exact after-tax results.",
        f"- Fundamental rows: `{summary['fundamental_rows']}` across `{summary['fundamental_symbols']}` symbols.",
        f"- Rows tested: `{summary['pnl_rows']}` daily rows across `{summary['strategies']}` strategy variants.",
        "",
        "## Candidates Beating `quality+momentum 5d always`",
        markdown_table(
            beats_base,
            [
                "strategy_id",
                "cagr",
                "sharpe",
                "max_dd",
                "weekly_win_rate",
                "p05_weekly_return",
                "worst_weekly_return",
                "monthly_win_rate",
                "p05_monthly_return",
                "worst_monthly_return",
                "ann_turnover",
            ],
            15,
        ) if len(beats_base) else "None",
        "",
        "## Top 2x Individual-Stock Leverage Candidates",
        markdown_table(
            two_x,
            [
                "strategy_id",
                "cagr",
                "sharpe",
                "max_dd",
                "weekly_win_rate",
                "p05_weekly_return",
                "worst_weekly_return",
                "monthly_win_rate",
                "p05_monthly_return",
                "worst_monthly_return",
                "ann_turnover",
            ],
            10,
        ) if len(two_x) else "None",
        "",
        "## Top Stock-Only Stop-Loss Candidates",
        markdown_table(
            full.loc[full["strategy_id"].str.contains("_stop")].sort_values(["cagr", "max_dd"], ascending=[False, False]),
            [
                "strategy_id",
                "cagr",
                "sharpe",
                "max_dd",
                "weekly_win_rate",
                "p05_weekly_return",
                "worst_weekly_return",
                "monthly_win_rate",
                "p05_monthly_return",
                "worst_monthly_return",
                "ann_turnover",
            ],
            15,
        ),
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
                "monthly_win_rate",
                "worst_monthly_return",
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
                "monthly_win_rate",
                "worst_monthly_return",
                "max_consecutive_losing_weeks",
                "avg_exposure",
                "ann_turnover",
            ],
            12,
        ),
        "",
        "## Interpretation",
        "",
        "- This is still PIT-lite because the tradable universe is not a fully historical delisting-aware US universe.",
        "- The 2x individual-stock leverage candidates raise CAGR sharply but do not beat `quality+momentum 5d always` on MDD; their drawdowns are too deep for the current lower-MDD objective.",
        "- A quality candidate only matters if it beats the prior practical stock candidate: `US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol60_target30_cap1_realistic` at 20.5% CAGR and -17.5% MDD.",
        "- Exact Toss-style after-tax ranking remains the next gate once a candidate survives pre-tax and cost-aware checks.",
    ]
    atomic_write_text("\n".join(lines) + "\n", REPORT_PATH)


def run(collect: bool = False) -> dict[str, object]:
    open_px, low_px, close_px, dvol = load_panel_with_low()
    symbols = list(close_px.columns)
    if collect or not FUNDAMENTALS_PATH.exists():
        fundamentals = collect_sec_fundamentals(symbols)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_parquet(fundamentals, FUNDAMENTALS_PATH)
    else:
        fundamentals = load_fundamentals(FUNDAMENTALS_PATH)
    forward_returns = open_px.shift(-1) / open_px - 1.0
    forward_returns = forward_returns.loc[forward_returns.index <= pd.Timestamp("2026-05-28")]
    quality = quality_matrix_from_fundamentals(fundamentals, close_px.index, symbols)
    price_signals = build_price_signal_matrices(close_px, dvol)
    signals = {
        "US_Q0_quality_only": quality,
        **{signal_id: combine_signal_matrices(signal, quality, quality_weight=0.5) for signal_id, signal in price_signals.items()},
    }
    risk_on = qqq_risk_on(close_px)
    riskoff = market_riskoff_ma(close_px)
    market_returns = forward_returns["QQQ"] if "QQQ" in forward_returns.columns else forward_returns.mean(axis=1, skipna=True)
    specs = []
    for signal_id in signals:
        for quantile in [0.1, 0.2]:
            for rebalance in experiment_rebalance_days():
                for risk_filter in ["always", "ma175"]:
                    specs.append(StrategySpec(signal_id, quantile, rebalance, risk_filter, cost_bps=30))
    pnl_frames = []
    for spec in specs:
        signal = signals[spec.signal_id].reindex(index=forward_returns.index, columns=forward_returns.columns)
        pnl_frames.append(backtest_signal(signal, forward_returns, spec, risk_on))
    pnls = pd.concat(pnl_frames, ignore_index=True)
    stop_variants = build_stop_loss_variants(signals, open_px, low_px, risk_on)
    if len(stop_variants):
        pnls = pd.concat([pnls, stop_variants], ignore_index=True)
    overlays = build_market_hedge_overlays(pnls, market_returns, riskoff)
    if len(overlays):
        pnls = pd.concat([pnls, overlays], ignore_index=True)
    metrics, weekly = summarize_results(pnls)
    monthly = pd.DataFrame([{**monthly_metrics(frame), "strategy_id": strategy_id, "signal_id": frame["signal_id"].iloc[0]} for strategy_id, frame in pnls.groupby("strategy_id")])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_parquet(pnls, OUT_DIR / "quality_fundamental_pnl_daily.parquet")
    atomic_write_parquet(metrics, OUT_DIR / "quality_fundamental_metrics.parquet")
    atomic_write_parquet(weekly, OUT_DIR / "quality_fundamental_weekly.parquet")
    atomic_write_parquet(monthly, OUT_DIR / "quality_fundamental_monthly.parquet")
    summary = {
        "strategies": int(pnls["strategy_id"].nunique()),
        "pnl_rows": int(len(pnls)),
        "fundamental_rows": int(len(fundamentals)),
        "fundamental_symbols": int(fundamentals["symbol"].nunique()) if "symbol" in fundamentals else 0,
    }
    write_report(metrics, weekly, monthly, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run US quality-plus-price individual-stock experiments.")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--collect", action="store_true", help="Fetch SEC Company Facts before running.")
    args = parser.parse_args()
    if not args.run:
        print("Use --run")
        return
    print(json.dumps(run(collect=args.collect), indent=2))


if __name__ == "__main__":
    main()
