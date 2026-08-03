from __future__ import annotations

import argparse
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PRICE_DIR = ROOT / "v2/data/cache/price_market_cap_full"
OUT_DIR = ROOT / "v2/data/cache/intraday_flat_explore"
REPORT_PATH = ROOT / "v2/reports/intraday_flat_strategy_exploration.md"
A4_PNL_PATH = ROOT / "v2/data/cache/backtest_batch/option_A4_pnl_daily.parquet"
KOSPI_INDEX_PATH = ROOT / "v2/data/cache/kospi_daily.parquet"

PERIODS = {
    "IS_2020_2023": (pd.Timestamp("2020-03-27"), pd.Timestamp("2023-12-31")),
    "VALID_2024": (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31")),
    "OOS_2025_PLUS": (pd.Timestamp("2025-01-01"), pd.Timestamp.max.normalize()),
    "FULL": (pd.Timestamp("2020-03-27"), pd.Timestamp.max.normalize()),
}


def select_long_weights(
    signal: pd.Series,
    eligible: pd.Series,
    *,
    top_fraction: float,
    max_positions: int,
    min_names: int,
    max_name_weight: float | None = None,
) -> pd.Series:
    """Build equal-weight long weights from information available before entry."""
    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction must be in (0, 1]")
    if max_positions < 1 or min_names < 1:
        raise ValueError("max_positions and min_names must be positive")

    weights = pd.Series(0.0, index=signal.index, dtype="float64")
    valid = signal.loc[eligible.reindex(signal.index).fillna(False).astype(bool)].dropna()
    if len(valid) < min_names:
        return weights
    count = min(max(int(math.ceil(len(valid) * top_fraction)), 1), max_positions)
    selected = valid.nlargest(count).index
    weight = 1.0 / count
    if max_name_weight is not None:
        weight = min(weight, max_name_weight)
    weights.loc[selected] = weight
    return weights


def build_candidate_signals(
    open_px: pd.DataFrame,
    high_px: pd.DataFrame,
    low_px: pd.DataFrame,
    close_px: pd.DataFrame,
    volume: pd.DataFrame,
    dvol: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Create a fixed menu of signals observable by each day's close."""
    oc_return = close_px.div(open_px).sub(1.0)
    cc_1 = close_px.pct_change(fill_method=None)
    cc_2 = close_px.div(close_px.shift(2)).sub(1.0)
    cc_5 = close_px.div(close_px.shift(5)).sub(1.0)
    cc_20 = close_px.div(close_px.shift(20)).sub(1.0)
    gap = open_px.div(close_px.shift(1)).sub(1.0)
    spread = high_px.sub(low_px).replace(0.0, np.nan)
    close_location = close_px.sub(low_px).div(spread).mul(2.0).sub(1.0)
    avg_volume_20 = volume.rolling(20, min_periods=10).mean()
    volume_surprise = np.log1p(volume.div(avg_volume_20.replace(0.0, np.nan)))
    avg_dvol_60 = dvol.rolling(60, min_periods=20).mean()

    signals = {
        "REV_OC_1": -oc_return,
        "MOM_OC_1": oc_return,
        "REV_CC_1": -cc_1,
        "MOM_CC_1": cc_1,
        "REV_CC_2": -cc_2,
        "REV_CC_5": -cc_5,
        "CLV_REV": -close_location,
        "CLV_CONT": close_location,
        "GAP_REV_1": -gap,
        "GAP_CONT_1": gap,
        "MOM_CC_20": cc_20,
        "VOLREV_CC_1": -cc_1 * volume_surprise,
        "A4_60": -np.log(avg_dvol_60.where(avg_dvol_60.gt(0))),
        "EVENT_OC_LOSER_3": (-oc_return).where(oc_return.le(-0.03)),
        "EVENT_CC_LOSER_3": (-cc_1).where(cc_1.le(-0.03)),
        "EVENT_CC_LOSER_5": (-cc_1).where(cc_1.le(-0.05)),
        "EVENT_OC_WINNER_3": oc_return.where(oc_return.ge(0.03)),
        "EVENT_CC_WINNER_3": cc_1.where(cc_1.ge(0.03)),
        "EVENT_CC_WINNER_5": cc_1.where(cc_1.ge(0.05)),
    }

    market_return = cc_1.median(axis=1, skipna=True)
    signals["REV_OC_1_MKT_DOWN_05"] = signals["REV_OC_1"].where(market_return.le(-0.005), axis=0)
    signals["REV_CC_1_MKT_DOWN_05"] = signals["REV_CC_1"].where(market_return.le(-0.005), axis=0)
    signals["MOM_OC_1_MKT_UP_05"] = signals["MOM_OC_1"].where(market_return.ge(0.005), axis=0)
    signals["MOM_CC_1_MKT_UP_05"] = signals["MOM_CC_1"].where(market_return.ge(0.005), axis=0)
    return signals


def backtest_index_gap_direction(
    index_frame: pd.DataFrame,
    *,
    one_way_cost_bps: float,
    gap_threshold: float = 0.0,
) -> pd.DataFrame:
    """Diagnostic upper bound: trade the opening gap direction at that same open."""
    frame = index_frame.copy().sort_values("date").reset_index(drop=True)
    prior_close = frame["close"].shift(1)
    gap = frame["open"].div(prior_close).sub(1.0)
    position = np.sign(gap).where(gap.abs().ge(gap_threshold), 0.0).fillna(0.0)
    intraday_return = frame["close"].div(frame["open"]).sub(1.0)
    deployed = position.abs()
    gross = position * intraday_return.fillna(0.0)
    round_trip_notional = 2.0 * deployed
    cost = round_trip_notional * (one_way_cost_bps / 10000.0)
    return pd.DataFrame(
        {
            "date": pd.to_datetime(frame["date"]).dt.normalize(),
            "position": position,
            "gross_return": gross,
            "cost": cost,
            "net_return": gross - cost,
            "n_long": deployed.astype(int),
            "deployed_weight": deployed,
            "cash_weight": 1.0 - deployed,
            "round_trip_notional": round_trip_notional,
        }
    )


def performance_metrics(pnl: pd.DataFrame) -> dict[str, float]:
    """Summarize a daily PnL frame with arithmetic annualized metrics."""
    returns = pnl["net_return"].astype("float64").fillna(0.0)
    if returns.empty:
        return {
            "sharpe": math.nan,
            "ann_return": math.nan,
            "cagr": math.nan,
            "ann_vol": math.nan,
            "max_dd": math.nan,
            "hit_ratio": math.nan,
            "trade_day_ratio": math.nan,
            "avg_deployed": math.nan,
            "avg_round_trip_notional": math.nan,
        }
    ann_return = float(returns.mean() * 252)
    ann_vol = float(returns.std(ddof=1) * math.sqrt(252)) if len(returns) > 1 else math.nan
    growth = (1.0 + returns).cumprod()
    years = len(returns) / 252.0
    cagr = float(growth.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 and growth.iloc[-1] > 0 else math.nan
    wealth = pd.concat([pd.Series([1.0]), growth.reset_index(drop=True)], ignore_index=True)
    max_dd = float((wealth.div(wealth.cummax()).sub(1.0)).min())
    traded = pnl["deployed_weight"].gt(0)
    return {
        "sharpe": ann_return / ann_vol if ann_vol and not math.isnan(ann_vol) else math.nan,
        "ann_return": ann_return,
        "cagr": cagr,
        "ann_vol": ann_vol,
        "max_dd": max_dd,
        "hit_ratio": float((returns.loc[traded] > 0).mean()) if traded.any() else math.nan,
        "trade_day_ratio": float(traded.mean()),
        "avg_deployed": float(pnl["deployed_weight"].mean()),
        "avg_round_trip_notional": float(pnl["round_trip_notional"].mean()),
    }


def backtest_flat(
    signal: pd.DataFrame,
    eligible: pd.DataFrame,
    open_px: pd.DataFrame,
    close_px: pd.DataFrame,
    execution_valid: pd.DataFrame,
    *,
    top_fraction: float,
    max_positions: int,
    min_names: int,
    one_way_cost_bps: float,
    max_name_weight: float | None = None,
    exit_blocked: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Enter at today's open from yesterday's close signal and exit at today's close."""
    dates = open_px.index
    columns = open_px.columns
    signal = signal.reindex(index=dates, columns=columns)
    eligible = eligible.reindex(index=dates, columns=columns).fillna(False)
    close_px = close_px.reindex(index=dates, columns=columns)
    execution_valid = execution_valid.reindex(index=dates, columns=columns).fillna(False)
    if exit_blocked is None:
        exit_blocked = pd.DataFrame(False, index=dates, columns=columns)
    else:
        exit_blocked = exit_blocked.reindex(index=dates, columns=columns).fillna(False)
    intraday_return = close_px.div(open_px).sub(1.0)

    rows: list[dict[str, object]] = []
    for i, date in enumerate(dates):
        if i == 0:
            target = pd.Series(0.0, index=columns)
        else:
            target = select_long_weights(
                signal.iloc[i - 1],
                eligible.iloc[i - 1],
                top_fraction=top_fraction,
                max_positions=max_positions,
                min_names=min_names,
                max_name_weight=max_name_weight,
            )
        filled = execution_valid.iloc[i].astype(bool) & intraday_return.iloc[i].notna()
        actual = target.where(filled, 0.0)
        deployed = float(actual.sum())
        gross = float((actual * intraday_return.iloc[i].fillna(0.0)).sum())
        round_trip_notional = 2.0 * deployed
        cost = round_trip_notional * (one_way_cost_bps / 10000.0)
        blocked_exit_weight = float(actual.where(exit_blocked.iloc[i].astype(bool), 0.0).sum())
        rows.append(
            {
                "date": date,
                "gross_return": gross,
                "cost": cost,
                "net_return": gross - cost,
                "n_long": int(actual.gt(0).sum()),
                "deployed_weight": deployed,
                "cash_weight": 1.0 - deployed,
                "round_trip_notional": round_trip_notional,
                "blocked_exit_weight": blocked_exit_weight,
                "has_blocked_exit": blocked_exit_weight > 0,
            }
        )
    return pd.DataFrame(rows)


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def _atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _load_price_panels() -> dict[str, pd.DataFrame]:
    frames = []
    paths = sorted(p for p in PRICE_DIR.glob("*.parquet") if p.stem.isdigit() and len(p.stem) == 6)
    for path in paths:
        frame = pd.read_parquet(
            path,
            columns=["date", "open", "high", "low", "close", "volume", "trading_value"],
        )
        frame["code"] = path.stem
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No stock price cache files under {PRICE_DIR}")
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel = panel.drop_duplicates(["date", "code"], keep="last")
    out = {}
    for column in ["open", "high", "low", "close", "volume", "trading_value"]:
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
        out[column] = panel.pivot(index="date", columns="code", values=column).sort_index().astype("float64")
    out["dvol"] = out["trading_value"].where(out["trading_value"].gt(0), out["close"] * out["volume"])
    return out


def _period_rows(pnl: pd.DataFrame, metadata: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    dates = pd.to_datetime(pnl["date"])
    for period, (start, end) in PERIODS.items():
        sub = pnl.loc[dates.between(start, end)]
        if sub.empty:
            continue
        rows.append({**metadata, "period": period, "n_days": int(len(sub)), **performance_metrics(sub)})
    return rows


def _markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    out = frame.loc[:, columns].copy()
    if max_rows is not None:
        out = out.head(max_rows)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in out.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                values.append("NA" if pd.isna(value) else f"{float(value):.4f}")
            else:
                values.append("NA" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def run() -> dict[str, object]:
    panels = _load_price_panels()
    open_px = panels["open"]
    high_px = panels["high"]
    low_px = panels["low"]
    close_px = panels["close"]
    volume = panels["volume"]
    dvol = panels["dvol"]

    signals = build_candidate_signals(open_px, high_px, low_px, close_px, volume, dvol)
    adv20 = dvol.rolling(20, min_periods=15).mean()
    history_ok = close_px.gt(0).rolling(20, min_periods=15).sum().ge(15)
    prior_close = close_px.shift(1)
    gap_from_prior_close = open_px.div(prior_close).sub(1.0)
    execution_valid = (
        open_px.gt(0)
        & close_px.gt(0)
        & volume.gt(0)
        & gap_from_prior_close.lt(0.29).fillna(False)
    )
    exit_blocked = close_px.div(prior_close).sub(1.0).le(-0.29) & close_px.eq(low_px) & volume.gt(0)

    regular = [
        "REV_OC_1", "MOM_OC_1", "REV_CC_1", "MOM_CC_1", "REV_CC_2", "REV_CC_5",
        "CLV_REV", "CLV_CONT", "GAP_REV_1", "GAP_CONT_1", "MOM_CC_20", "VOLREV_CC_1", "A4_60",
        "REV_OC_1_MKT_DOWN_05", "REV_CC_1_MKT_DOWN_05", "MOM_OC_1_MKT_UP_05", "MOM_CC_1_MKT_UP_05",
    ]
    event = [
        "EVENT_OC_LOSER_3", "EVENT_CC_LOSER_3", "EVENT_CC_LOSER_5",
        "EVENT_OC_WINNER_3", "EVENT_CC_WINNER_3", "EVENT_CC_WINNER_5",
    ]
    configs: list[dict[str, object]] = []
    for name in regular:
        for adv_floor in [1_000_000_000.0, 5_000_000_000.0]:
            for top_fraction in [0.02, 0.05, 0.10]:
                configs.append(
                    {"strategy": name, "adv_floor": adv_floor, "top_fraction": top_fraction, "min_names": 100}
                )
    for name in event:
        for adv_floor in [1_000_000_000.0, 5_000_000_000.0]:
            configs.append({"strategy": name, "adv_floor": adv_floor, "top_fraction": 1.0, "min_names": 1})

    metrics_rows: list[dict[str, object]] = []
    pnl_frames = []
    for config_id, config in enumerate(configs):
        eligible = (
            history_ok
            & close_px.ge(1_000.0)
            & adv20.ge(float(config["adv_floor"]))
            & volume.gt(0)
        )
        base = backtest_flat(
            signals[str(config["strategy"])],
            eligible,
            open_px,
            close_px,
            execution_valid,
            top_fraction=float(config["top_fraction"]),
            max_positions=50,
            min_names=int(config["min_names"]),
            one_way_cost_bps=0,
            max_name_weight=0.10,
            exit_blocked=exit_blocked,
        )
        for cost_bps in [15, 35, 50]:
            pnl = base.copy()
            pnl["cost"] = pnl["round_trip_notional"] * (cost_bps / 10000.0)
            pnl["net_return"] = pnl["gross_return"] - pnl["cost"]
            pnl.insert(0, "config_id", config_id)
            pnl.insert(1, "strategy", config["strategy"])
            pnl.insert(2, "adv_floor", config["adv_floor"])
            pnl.insert(3, "top_fraction", config["top_fraction"])
            pnl.insert(4, "cost_bps", cost_bps)
            pnl_frames.append(pnl)
            metadata = {"config_id": config_id, **config, "cost_bps": cost_bps}
            metrics_rows.extend(_period_rows(pnl, metadata))

    metrics = pd.DataFrame(metrics_rows)
    pnl_all = pd.concat(pnl_frames, ignore_index=True)

    a4 = pd.read_parquet(A4_PNL_PATH)
    a4["date"] = pd.to_datetime(a4["date"]).dt.normalize()
    a4 = a4.loc[
        a4["portfolio"].eq("LO_decile") & a4["rebalance"].eq("5d") & a4["cost_bps"].eq(30)
    ].copy()
    a4["deployed_weight"] = a4["position_count_long"].gt(0).astype(float)
    a4["round_trip_notional"] = a4["turnover"] * 2.0
    a4_rows = _period_rows(a4, {"config_id": -1, "strategy": "A4_LO_5D", "adv_floor": math.nan, "top_fraction": 0.10, "cost_bps": 30})
    benchmark = pd.DataFrame(a4_rows)

    index_frame = pd.read_parquet(KOSPI_INDEX_PATH, columns=["date", "open", "close"])
    gap_rows: list[dict[str, object]] = []
    gap_pnl_frames = []
    for threshold in [0.0, 0.005]:
        for cost_bps in [0.0, 0.5, 1.0, 3.0, 5.0]:
            gap_pnl = backtest_index_gap_direction(
                index_frame,
                one_way_cost_bps=cost_bps,
                gap_threshold=threshold,
            )
            gap_pnl.insert(0, "gap_threshold", threshold)
            gap_pnl.insert(1, "cost_bps", cost_bps)
            gap_pnl_frames.append(gap_pnl)
            gap_rows.extend(
                _period_rows(
                    gap_pnl,
                    {"strategy": "KOSPI_GAP_MOM_DIAGNOSTIC", "gap_threshold": threshold, "cost_bps": cost_bps},
                )
            )
    gap_metrics = pd.DataFrame(gap_rows)
    gap_pnl_all = pd.concat(gap_pnl_frames, ignore_index=True)

    base35 = metrics.loc[metrics["cost_bps"].eq(35)]
    wide = base35.pivot_table(
        index=["config_id", "strategy", "adv_floor", "top_fraction"],
        columns="period",
        values=["sharpe", "ann_return", "max_dd", "trade_day_ratio", "avg_deployed"],
        aggfunc="first",
    )
    wide.columns = [f"{metric}_{period}" for metric, period in wide.columns]
    wide = wide.reset_index()
    wide["selection_score"] = wide[["sharpe_IS_2020_2023", "sharpe_VALID_2024"]].min(axis=1)
    eligible_selection = wide.loc[
        wide["sharpe_IS_2020_2023"].gt(0)
        & wide["sharpe_VALID_2024"].gt(0)
        & wide["trade_day_ratio_VALID_2024"].ge(0.02)
    ]
    has_viable_flat = not eligible_selection.empty
    selection_pool = eligible_selection if has_viable_flat else wide
    selected = selection_pool.sort_values(
        ["selection_score", "sharpe_VALID_2024", "ann_return_VALID_2024"], ascending=False
    ).iloc[0]

    selected_metrics = metrics.loc[metrics["config_id"].eq(int(selected["config_id"])) & metrics["cost_bps"].eq(35)]
    selected_pnl = pnl_all.loc[pnl_all["config_id"].eq(int(selected["config_id"])) & pnl_all["cost_bps"].eq(35)]
    blocked_days = int(selected_pnl["has_blocked_exit"].sum())
    blocked_weight = float(selected_pnl["blocked_exit_weight"].sum())

    top_validation = wide.sort_values(
        ["selection_score", "sharpe_VALID_2024"], ascending=False
    ).head(15)
    comparison = pd.concat(
        [
            selected_metrics.assign(name="selected_flat"),
            benchmark.assign(name="A4_LO_5D"),
        ],
        ignore_index=True,
        sort=False,
    )
    oos = comparison.loc[comparison["period"].eq("OOS_2025_PLUS")].set_index("name")
    beats_a4_oos = bool(
        len(oos) == 2
        and oos.loc["selected_flat", "sharpe"] > oos.loc["A4_LO_5D", "sharpe"]
        and oos.loc["selected_flat", "ann_return"] > oos.loc["A4_LO_5D", "ann_return"]
    )

    _atomic_write_parquet(metrics, OUT_DIR / "metrics.parquet")
    _atomic_write_parquet(pnl_all, OUT_DIR / "pnl_daily.parquet")
    _atomic_write_parquet(wide, OUT_DIR / "selection_summary.parquet")
    _atomic_write_parquet(comparison, OUT_DIR / "selected_vs_a4.parquet")
    _atomic_write_parquet(gap_metrics, OUT_DIR / "kospi_gap_diagnostic_metrics.parquet")
    _atomic_write_parquet(gap_pnl_all, OUT_DIR / "kospi_gap_diagnostic_pnl.parquet")

    report = "# 당일 청산 기술전략 탐색\n\n"
    report += "## 설계\n"
    report += "- 전일 종가까지 확정된 일봉 신호로 다음 거래일 시가 매수, 같은 날 종가 매도. 의도상 익일 포지션 0.\n"
    report += "- 현재 A4와 동일한 KOSPI 가격 캐시 종목군, 롱온리, 균등비중. 20일 평균 거래대금 10억/50억원 하한.\n"
    report += "- 기본비용 편도 35bp(왕복 70bp), 스트레스 편도 15/50bp. 종목당 최대 10%, 최대 50종목.\n"
    report += "- 후보 선택은 OOS를 보지 않고 IS(2020~2023)와 검증(2024) Sharpe의 최솟값으로 고정. OOS는 2025년 이후.\n"
    report += "- 현재 캐시 종목군을 과거로 소급한 alive-only 편향은 A4와 동일하게 남아 있다.\n\n"
    report += "## IS/검증 상위 후보 (편도 35bp)\n"
    report += _markdown_table(
        top_validation,
        ["strategy", "adv_floor", "top_fraction", "selection_score", "sharpe_IS_2020_2023", "sharpe_VALID_2024", "ann_return_VALID_2024", "max_dd_VALID_2024", "trade_day_ratio_VALID_2024"],
    )
    report += f"\n\n- IS와 검증 구간 Sharpe가 모두 양수인 승격 후보: **{'있음' if has_viable_flat else '없음'}**\n"
    report += "\n## 가장 덜 나쁜 단일 후보 (승격 금지)\n"
    report += _markdown_table(
        selected_metrics,
        ["strategy", "adv_floor", "top_fraction", "cost_bps", "period", "sharpe", "ann_return", "cagr", "ann_vol", "max_dd", "hit_ratio", "trade_day_ratio", "avg_deployed"],
    )
    report += "\n\n## A4 비교\n"
    report += _markdown_table(
        comparison,
        ["name", "period", "cost_bps", "sharpe", "ann_return", "cagr", "ann_vol", "max_dd", "trade_day_ratio", "avg_deployed"],
    )
    report += f"\n\n- OOS Sharpe와 연환산 수익률을 모두 A4보다 높였는가: **{'YES' if beats_a4_oos else 'NO'}**\n"
    report += f"- 선택 후보의 보수적 종가 하한가 청산불능 플래그: {blocked_days}일, 누적 대상 비중 {blocked_weight:.4f}.\n"
    report += "\n## 다음 후보: KOSPI 시가 갭 방향 추종 진단\n"
    report += "당일 시가가 전일 종가보다 높으면 지수 롱, 낮으면 지수 숏 후 같은 날 종가 청산하는 진단이다. 당일 갭을 확정한 뒤 정확히 시가에 체결했다고 가정하므로 **실행 가능한 백테스트가 아니라 상한선**이다.\n\n"
    report += _markdown_table(
        gap_metrics.loc[gap_metrics["gap_threshold"].eq(0.0) & gap_metrics["cost_bps"].isin([0.0, 0.5, 1.0, 3.0])],
        ["gap_threshold", "cost_bps", "period", "sharpe", "ann_return", "cagr", "ann_vol", "max_dd", "trade_day_ratio"],
    )
    report += "\n\n- 이 진단은 2025+ OOS에서 강하지만 IS/검증의 절대 성과가 약하고, 09:00 시가 동시호가 체결 가정이 불가능하다. 09:05 진입 분봉 검증 전에는 후보일 뿐이다.\n"
    report += "\n## 실행상 핵심 제한\n"
    report += "- 일봉 종가는 종가 동시호가 체결을 보장하지 않는다. 특히 하한가/거래정지에서는 당일 청산이 실패해 overnight가 생길 수 있다.\n"
    report += "- 시가 주문은 전일 신호로 미리 제출할 수 있지만 실제 체결가·시장충격은 일봉만으로 검증할 수 없다.\n"
    report += "- 따라서 이 결과는 분봉 수집 전 1차 필터다. 승격하려면 KIS 1분봉으로 09:05 진입/15:15 청산, 체결량 참여율, VI·상하한가를 재검증해야 한다.\n"
    report += "\n## 산출물\n- `v2/data/cache/intraday_flat_explore/metrics.parquet`\n- `v2/data/cache/intraday_flat_explore/pnl_daily.parquet`\n- `v2/data/cache/intraday_flat_explore/selection_summary.parquet`\n- `v2/data/cache/intraday_flat_explore/selected_vs_a4.parquet`\n- `v2/data/cache/intraday_flat_explore/kospi_gap_diagnostic_metrics.parquet`\n- `v2/data/cache/intraday_flat_explore/kospi_gap_diagnostic_pnl.parquet`\n"
    _atomic_write_text(report, REPORT_PATH)

    return {
        "price_start": str(open_px.index.min().date()),
        "price_end": str(open_px.index.max().date()),
        "symbols": int(open_px.shape[1]),
        "configs": len(configs),
        "selected": str(selected["strategy"]),
        "selected_config_id": int(selected["config_id"]),
        "has_viable_flat": has_viable_flat,
        "beats_a4_oos": beats_a4_oos,
        "blocked_exit_days": blocked_days,
        "report": str(REPORT_PATH),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore next-open to same-close long-only strategies.")
    parser.add_argument("--run", action="store_true", help="Run the exploration and write artifacts.")
    args = parser.parse_args()
    if not args.run:
        print("Use --run to execute the fixed candidate screen.")
        return
    print(run())


if __name__ == "__main__":
    main()
