from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.kospi_loader import DEFAULT_CACHE_PATH, load_or_fetch_kospi_daily  # noqa: E402
from v2.evaluation.walkforward import STAGE6_FOLDS  # noqa: E402


REPORT_PATH = Path("v2/reports/pr4_7_regime_reevaluation.md")
SCATTER_PATH = Path("v2/reports/pr4_7_a_kospi_scatter.png")
TRADES_DIR = Path("v2/data/cache/trades")
LEDGER_FILES = {
    "A": TRADES_DIR / "pr4_a_sue_only_latest.parquet",
    "B": TRADES_DIR / "pr4_b_sue_near_high_latest.parquet",
    "C": TRADES_DIR / "pr4_c_sue_far_from_high_latest.parquet",
    "D": TRADES_DIR / "pr4_d_proximity_only_latest.parquet",
}
ABNORMAL_START = pd.Timestamp("2025-05-01")
ABNORMAL_END = pd.Timestamp("2026-04-17")


def _fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number):
        return ""
    if math.isinf(number):
        return "inf" if number > 0 else "-inf"
    return f"{number:.{digits}f}"


def _markdown_table(rows: Iterable[dict[str, object]], columns: list[str]) -> str:
    rows = list(rows)
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def _profit_factor(returns: pd.Series) -> float:
    values = pd.to_numeric(returns, errors="coerce").dropna()
    gross_profit = float(values.loc[values > 0].sum())
    gross_loss = abs(float(values.loc[values < 0].sum()))
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _trade_stats(trades: pd.DataFrame) -> dict[str, float | int]:
    if trades.empty:
        return {"trades": 0, "pf": 0.0, "win_rate": math.nan, "avg_win": math.nan, "avg_loss": math.nan}
    returns = pd.to_numeric(trades["net_return"], errors="coerce")
    pnl = pd.to_numeric(trades["pnl_krw"], errors="coerce")
    wins = returns.loc[returns > 0]
    losses = returns.loc[returns < 0]
    return {
        "trades": int(len(trades)),
        "pf": _profit_factor(pnl),
        "win_rate": float((returns > 0).mean()),
        "avg_win": float(wins.mean()) if len(wins) else math.nan,
        "avg_loss": float(losses.mean()) if len(losses) else math.nan,
    }


def _load_ledgers() -> dict[str, pd.DataFrame]:
    missing = [str(path) for path in LEDGER_FILES.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing ledger files: {missing}")

    ledgers: dict[str, pd.DataFrame] = {}
    for variant, path in LEDGER_FILES.items():
        frame = pd.read_parquet(path)
        for column in ["entry_date", "exit_date"]:
            frame[column] = pd.to_datetime(frame[column]).dt.normalize()
        frame["fold"] = pd.to_numeric(frame["fold"], errors="coerce").astype("Int64")
        ledgers[variant] = frame
    return ledgers


def _period_slice(kospi: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return kospi.loc[kospi["date"].between(start, end)].copy()


def _period_return(kospi: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    period = _period_slice(kospi, start, end)
    if period.empty:
        return math.nan
    return float(period.iloc[-1]["close"] / period.iloc[0]["close"] - 1.0)


def _period_vol(kospi: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    period = _period_slice(kospi, start, end)
    returns = pd.to_numeric(period["returns"], errors="coerce").dropna()
    if returns.empty:
        return math.nan
    return float(returns.std(ddof=0) * math.sqrt(252))


def _max_drawdown(close: pd.Series) -> float:
    values = pd.to_numeric(close, errors="coerce").dropna()
    if values.empty:
        return math.nan
    running_max = values.cummax()
    drawdown = values / running_max - 1.0
    return float(drawdown.min())


def _monthly_regimes(kospi: pd.DataFrame) -> pd.DataFrame:
    data = kospi.copy()
    data["month"] = data["date"].dt.to_period("M")
    rows: list[dict[str, object]] = []
    for month, group in data.groupby("month", sort=True):
        group = group.sort_values("date")
        month_return = float(group.iloc[-1]["close"] / group.iloc[0]["close"] - 1.0)
        daily_returns = pd.to_numeric(group["returns"], errors="coerce").dropna()
        volatility = float(daily_returns.std(ddof=0) * math.sqrt(21)) if len(daily_returns) else math.nan
        if month_return >= 0.05:
            regime = "Bull Extreme"
        elif month_return >= 0:
            regime = "Bull Normal"
        elif month_return > -0.05:
            regime = "Bear Normal"
        else:
            regime = "Bear Extreme"
        rows.append(
            {
                "month": str(month),
                "start_close": float(group.iloc[0]["close"]),
                "end_close": float(group.iloc[-1]["close"]),
                "return": month_return,
                "volatility": volatility,
                "mdd": _max_drawdown(group["close"]),
                "regime": regime,
            }
        )
    return pd.DataFrame(rows)


def _monthly_table(monthly: pd.DataFrame) -> str:
    rows = []
    for row in monthly.to_dict("records"):
        rows.append(
            {
                "Month": row["month"],
                "Start Close": _fmt(row["start_close"], 2),
                "End Close": _fmt(row["end_close"], 2),
                "Return %": _fmt(row["return"] * 100, 2),
                "Vol %": _fmt(row["volatility"] * 100, 2),
                "MDD %": _fmt(row["mdd"] * 100, 2),
                "Regime": row["regime"],
            }
        )
    return _markdown_table(rows, ["Month", "Start Close", "End Close", "Return %", "Vol %", "MDD %", "Regime"])


def _regime_for_month(monthly: pd.DataFrame) -> dict[str, str]:
    return dict(zip(monthly["month"], monthly["regime"], strict=False))


def _fold_rows(kospi: pd.DataFrame, monthly: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for index, fold in enumerate(STAGE6_FOLDS, start=1):
        start = pd.Timestamp(fold.test_start)
        end = pd.Timestamp(fold.test_end)
        months = pd.period_range(start=start, end=end, freq="M").astype(str)
        bull_extreme = int(monthly.loc[monthly["month"].isin(months) & monthly["regime"].eq("Bull Extreme")].shape[0])
        rows.append(
            {
                "Fold": index,
                "Test Start": start.date().isoformat(),
                "Test End": end.date().isoformat(),
                "KOSPI Return %": _fmt(_period_return(kospi, start, end) * 100, 2),
                "KOSPI Vol %": _fmt(_period_vol(kospi, start, end) * 100, 2),
                "Bull Extreme Months": bull_extreme,
            }
        )
    return rows


def _strategy_vs_kospi_rows(
    ledgers: dict[str, pd.DataFrame],
    kospi: pd.DataFrame,
) -> list[dict[str, object]]:
    rows = []
    for variant in ["A", "B"]:
        wf = ledgers[variant].loc[ledgers[variant]["fold"].isin([1, 2, 3])].copy()
        for index, fold in enumerate(STAGE6_FOLDS, start=1):
            trades = wf.loc[wf["fold"].eq(index)]
            start = pd.Timestamp(fold.test_start)
            end = pd.Timestamp(fold.test_end)
            period = _period_slice(kospi, start, end)
            rows.append(
                {
                    "Variant": variant,
                    "Fold": index,
                    "Strategy Net PF": _fmt(_profit_factor(trades["pnl_krw"]), 4),
                    "KOSPI Return %": _fmt(_period_return(kospi, start, end) * 100, 2),
                    "Strategy Raw Return Avg %": _fmt(pd.to_numeric(trades["raw_return"], errors="coerce").mean() * 100, 2),
                    "KOSPI Daily Return Avg %": _fmt(pd.to_numeric(period["returns"], errors="coerce").mean() * 100, 4),
                }
            )
    return rows


def _exclude_bull_extreme(trades: pd.DataFrame, month_to_regime: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = trades.copy()
    data["entry_month"] = data["entry_date"].dt.to_period("M").astype(str)
    bull_mask = data["entry_month"].map(month_to_regime).eq("Bull Extreme")
    return data.loc[~bull_mask].copy(), data.loc[bull_mask].copy()


def _trade_kospi_returns(trades: pd.DataFrame, kospi: pd.DataFrame) -> pd.Series:
    returns: list[float] = []
    for trade in trades.itertuples(index=False):
        returns.append(_period_return(kospi, pd.Timestamp(trade.entry_date), pd.Timestamp(trade.exit_date)))
    return pd.Series(returns, index=trades.index, dtype="float64")


def _ols_alpha_beta(trades: pd.DataFrame, kospi: pd.DataFrame) -> dict[str, float]:
    data = trades.copy()
    data["kospi_return"] = _trade_kospi_returns(data, kospi)
    data["strategy_raw_return"] = pd.to_numeric(data["raw_return"], errors="coerce")
    data = data.dropna(subset=["kospi_return", "strategy_raw_return"])
    if len(data) < 2 or data["kospi_return"].nunique() < 2:
        return {"alpha": math.nan, "beta": math.nan, "r2": math.nan, "n": int(len(data))}

    x = data["kospi_return"].to_numpy(dtype=float)
    y = data["strategy_raw_return"].to_numpy(dtype=float)
    beta, alpha = np.polyfit(x, y, 1)
    predicted = alpha + beta * x
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = math.nan if ss_tot == 0 else 1.0 - ss_res / ss_tot
    return {"alpha": float(alpha), "beta": float(beta), "r2": float(r2), "n": int(len(data))}


def _write_scatter_plot(trades: pd.DataFrame, kospi: pd.DataFrame, alpha_beta: dict[str, float]) -> None:
    data = trades.copy()
    data["kospi_return"] = _trade_kospi_returns(data, kospi)
    data["strategy_raw_return"] = pd.to_numeric(data["raw_return"], errors="coerce")
    data = data.dropna(subset=["kospi_return", "strategy_raw_return"])
    if data.empty:
        return

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = data["kospi_return"].to_numpy(dtype=float)
    y = data["strategy_raw_return"].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(x, y, s=16, alpha=0.65)
    if not math.isnan(float(alpha_beta["alpha"])) and not math.isnan(float(alpha_beta["beta"])):
        x_line = np.linspace(float(np.min(x)), float(np.max(x)), 100)
        y_line = float(alpha_beta["alpha"]) + float(alpha_beta["beta"]) * x_line
        ax.plot(x_line, y_line, color="black", linewidth=1.2)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.axvline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("KOSPI holding-period return")
    ax.set_ylabel("A strategy raw return")
    ax.set_title("PR-4.7 A Trades vs KOSPI Holding-Period Return")
    fig.tight_layout()
    SCATTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SCATTER_PATH, dpi=140)
    plt.close(fig)


def _analysis_rows_for_variant(
    ledgers: dict[str, pd.DataFrame],
    monthly: pd.DataFrame,
    variant: str,
) -> dict[str, object]:
    wf = ledgers[variant].loc[ledgers[variant]["fold"].isin([1, 2, 3])].copy()
    fold12 = wf.loc[wf["fold"].isin([1, 2])]
    non_bull, bull = _exclude_bull_extreme(wf, _regime_for_month(monthly))
    return {
        "fold12": _trade_stats(fold12),
        "non_bull": _trade_stats(non_bull),
        "bull_only": _trade_stats(bull),
    }


def _scenario(a_fold12_pf: float, a_non_bull_pf: float, data_ok: bool) -> str:
    if not data_ok:
        return "Scenario D"
    if a_fold12_pf >= 1.3 and a_non_bull_pf >= 1.3:
        return "Scenario A"
    if a_fold12_pf < 1.0 or a_non_bull_pf < 1.0:
        return "Scenario C"
    return "Scenario B"


def _overlap_pct(start: pd.Timestamp, end: pd.Timestamp, other_start: pd.Timestamp, other_end: pd.Timestamp) -> float:
    overlap_start = max(start, other_start)
    overlap_end = min(end, other_end)
    if overlap_end < overlap_start:
        return 0.0
    overlap_days = (overlap_end - overlap_start).days + 1
    total_days = (end - start).days + 1
    return overlap_days / total_days


def main() -> None:
    ledgers = _load_ledgers()
    kospi = load_or_fetch_kospi_daily(cache_path=DEFAULT_CACHE_PATH)
    monthly = _monthly_regimes(kospi)
    month_to_regime = _regime_for_month(monthly)

    recent = monthly.loc[monthly["month"].between("2025-05", "2026-04")].copy()
    previous = monthly.loc[monthly["month"].between("2020-03", "2025-04")].copy()
    recent_bull_extreme = int(recent["regime"].eq("Bull Extreme").sum())
    previous_bull_extreme = int(previous["regime"].eq("Bull Extreme").sum())
    previous_annual_average = previous_bull_extreme / (len(previous) / 12.0) if len(previous) else math.nan
    recent_period_return = _period_return(kospi, ABNORMAL_START, ABNORMAL_END)
    abnormal_ratio = recent_bull_extreme / previous_annual_average if previous_annual_average else math.inf
    abnormal_status = (
        "abnormal by 3x Bull Extreme criterion"
        if abnormal_ratio >= 3.0
        else "not abnormal by 3x Bull Extreme criterion"
    )

    fold_regime_rows = _fold_rows(kospi, monthly)
    strategy_rows = _strategy_vs_kospi_rows(ledgers, kospi)

    a_stats = _analysis_rows_for_variant(ledgers, monthly, "A")
    b_stats = _analysis_rows_for_variant(ledgers, monthly, "B")
    a_wf = ledgers["A"].loc[ledgers["A"]["fold"].isin([1, 2, 3])].copy()
    b_wf = ledgers["B"].loc[ledgers["B"]["fold"].isin([1, 2, 3])].copy()
    a_non_bull, a_bull = _exclude_bull_extreme(a_wf, month_to_regime)
    b_non_bull, b_bull = _exclude_bull_extreme(b_wf, month_to_regime)
    alpha_beta = _ols_alpha_beta(a_wf, kospi)
    _write_scatter_plot(a_wf, kospi, alpha_beta)

    fold3 = STAGE6_FOLDS[2]
    fold3_overlap = _overlap_pct(pd.Timestamp(fold3.test_start), pd.Timestamp(fold3.test_end), ABNORMAL_START, ABNORMAL_END)
    scenario = _scenario(float(a_stats["fold12"]["pf"]), float(a_stats["non_bull"]["pf"]), not kospi.empty)
    date_gaps = kospi["date"].sort_values().diff().dt.days.dropna()
    gap_gt_one = int((date_gaps > 1).sum())
    max_gap = int(date_gaps.max()) if len(date_gaps) else 0

    section_4_rows = []
    for variant, stats in (("A", a_stats), ("B", b_stats)):
        for scope, values in (
            ("Fold 1/2 pooled", stats["fold12"]),
            ("Full WF excluding Bull Extreme entry months", stats["non_bull"]),
            ("Bull Extreme entry months only", stats["bull_only"]),
        ):
            section_4_rows.append(
                {
                    "Variant": variant,
                    "Scope": scope,
                    "Trades": values["trades"],
                    "PF": _fmt(values["pf"], 4),
                    "Win Rate %": _fmt(values["win_rate"] * 100, 2),
                    "Avg Win %": _fmt(values["avg_win"] * 100, 2),
                    "Avg Loss %": _fmt(values["avg_loss"] * 100, 2),
                }
            )

    bull_month_rows = [
        {
            "Regime": regime,
            "Month Count": int(count),
        }
        for regime, count in monthly["regime"].value_counts().sort_index().items()
    ]

    recent_summary_rows = [
        {
            "Metric": "2025-05 to 2026-04 Bull Extreme months",
            "Value": recent_bull_extreme,
        },
        {
            "Metric": "2025-05 to 2026-04 KOSPI return %",
            "Value": _fmt(recent_period_return * 100, 2),
        },
        {
            "Metric": "2020-03 to 2025-04 Bull Extreme months",
            "Value": previous_bull_extreme,
        },
        {
            "Metric": "Prior period annualized Bull Extreme count",
            "Value": _fmt(previous_annual_average, 2),
        },
        {
            "Metric": "Recent / prior annualized ratio",
            "Value": _fmt(abnormal_ratio, 2),
        },
        {
            "Metric": "Criterion result",
            "Value": abnormal_status,
        },
    ]

    lines = [
        "# PR-4.7 Regime Reevaluation",
        "",
        "Diagnostic-only report. Inputs are PR-4.6 trade-level ledgers and cached KOSPI daily data.",
        "",
        "## Step 1. KOSPI Daily Data",
        f"- Cache path: `{DEFAULT_CACHE_PATH}`",
        "- Loader preference: pykrx/KRX first; Naver Finance fallback if pykrx/KRX returns empty or fails.",
        f"- Rows: {len(kospi)}",
        f"- Date range: {kospi['date'].min().date()} ~ {kospi['date'].max().date()}",
        f"- Missing values by column: {kospi.isna().sum().to_dict()}",
        f"- Calendar gaps greater than 1 day: {gap_gt_one}; max calendar gap: {max_gap} days. Exchange holiday validation is skipped.",
        f"- 2025-05-01 to 2026-04-17 KOSPI return: {_fmt(recent_period_return * 100, 2)}%",
        "",
        "## Step 2. Monthly Market Regimes",
        "### 2.1 Monthly KOSPI Returns",
        _monthly_table(monthly),
        "",
        "### 2.2 Regime Distribution",
        _markdown_table(bull_month_rows, ["Regime", "Month Count"]),
        "",
        "### 2.3 Abnormal Period Check",
        _markdown_table(recent_summary_rows, ["Metric", "Value"]),
        "",
        "## Step 3. Fold-Level KOSPI Mapping",
        "### 3.1 Fold Periods And KOSPI Performance",
        _markdown_table(
            fold_regime_rows,
            ["Fold", "Test Start", "Test End", "KOSPI Return %", "KOSPI Vol %", "Bull Extreme Months"],
        ),
        "",
        "### 3.2 Strategy Vs KOSPI",
        _markdown_table(
            strategy_rows,
            [
                "Variant",
                "Fold",
                "Strategy Net PF",
                "KOSPI Return %",
                "Strategy Raw Return Avg %",
                "KOSPI Daily Return Avg %",
            ],
        ),
        "",
        "## Step 4. Regime-Conditional Recheck",
        "### 4.1 Fold 1/2 And Bull Extreme Exclusion",
        _markdown_table(
            section_4_rows,
            ["Variant", "Scope", "Trades", "PF", "Win Rate %", "Avg Win %", "Avg Loss %"],
        ),
        "",
        "A Fold 1/2 criterion bucket: "
        + (
            "normal-regime edge present"
            if a_stats["fold12"]["pf"] >= 1.3 and _profit_factor(a_wf.loc[a_wf["fold"].eq(2), "pnl_krw"]) >= 0.9
            else "normal-regime edge weak"
            if a_stats["fold12"]["pf"] >= 1.0
            else "normal-regime edge absent"
        ),
        "",
        "## Step 5. Alpha Decomposition",
        f"Scatter plot: `{SCATTER_PATH}`",
        "",
        _markdown_table(
            [
                {
                    "Variant": "A",
                    "N": alpha_beta["n"],
                    "Alpha": _fmt(alpha_beta["alpha"], 4),
                    "Beta": _fmt(alpha_beta["beta"], 4),
                    "R2": _fmt(alpha_beta["r2"], 4),
                }
            ],
            ["Variant", "N", "Alpha", "Beta", "R2"],
        ),
        "",
        "## Step 6. Final Summary",
        "### 6.1 Facts Only",
        _markdown_table(
            [
                {
                    "Question": "2025-05 to 2026-04 abnormal rise status",
                    "Fact": f"{abnormal_status}; KOSPI return {_fmt(recent_period_return * 100, 2)}%, Bull Extreme months {recent_bull_extreme}",
                },
                {
                    "Question": "Fold_3 overlap with abnormal window",
                    "Fact": f"{_fmt(fold3_overlap * 100, 2)}% calendar-day overlap",
                },
                {
                    "Question": "A Fold_1/2 pooled PF",
                    "Fact": _fmt(a_stats["fold12"]["pf"], 4),
                },
                {
                    "Question": "A full WF excluding Bull Extreme entry months PF",
                    "Fact": _fmt(a_stats["non_bull"]["pf"], 4),
                },
                {
                    "Question": "B Fold_1/2 pooled PF / Bull Extreme excluded PF",
                    "Fact": f"{_fmt(b_stats['fold12']['pf'], 4)} / {_fmt(b_stats['non_bull']['pf'], 4)}",
                },
                {
                    "Question": "A alpha, beta, R2",
                    "Fact": f"{_fmt(alpha_beta['alpha'], 4)}, {_fmt(alpha_beta['beta'], 4)}, {_fmt(alpha_beta['r2'], 4)}",
                },
            ],
            ["Question", "Fact"],
        ),
        "",
        "### 6.2 User Decision Scenarios",
        _markdown_table(
            [
                {
                    "Scenario": "Scenario A",
                    "Condition": "A Fold_1/2 pooled PF >= 1.3 and Bull Extreme excluded PF >= 1.3",
                },
                {
                    "Scenario": "Scenario B",
                    "Condition": "At least one of the two PF values is between 1.0 and 1.3, and neither is below 1.0",
                },
                {
                    "Scenario": "Scenario C",
                    "Condition": "At least one of the two PF values is below 1.0",
                },
                {
                    "Scenario": "Scenario D",
                    "Condition": "Data limitation prevents classification",
                },
                {
                    "Scenario": "Current result",
                    "Condition": (
                        f"{scenario}: A Fold_1/2 PF {_fmt(a_stats['fold12']['pf'], 4)}, "
                        f"A Bull Extreme excluded PF {_fmt(a_stats['non_bull']['pf'], 4)}"
                    ),
                },
            ],
            ["Scenario", "Condition"],
        ),
    ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
