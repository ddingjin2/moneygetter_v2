"""Spike: point-in-time financial factors combined with A4."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.earnings import validate_earnings_point_in_time  # noqa: E402
from v2.evaluation.walkforward import STAGE6_FOLDS  # noqa: E402
from v2.scripts.a4_risk_overlay import (  # noqa: E402
    PRICE_DIR,
    RiskOverlayConfig,
    _atomic_parquet,
    _atomic_text,
    load_inputs,
    markdown_table,
    metrics,
    simulate_risk_overlay,
)


EARNINGS_PATH = ROOT / "v2/data/cache/earnings_events.parquet"
KOSPI_PATH = ROOT / "v2/data/cache/benchmarks/kospi_daily_returns.parquet"
OUTPUT_DIR = ROOT / "v2/data/cache/a4_financial_multifactor_spike"
SHADOW_HISTORY_PATH = OUTPUT_DIR / "shadow_history.parquet"
REPORT_PATH = ROOT / "v2/spikes/001-a4-financial-multifactor/README.md"


FACTOR_COLUMNS = ("sue", "revenue_growth", "operating_margin", "roa")


def _asof_panel(
    events: pd.DataFrame,
    dates: pd.DatetimeIndex,
    codes: pd.Index,
    value_column: str,
) -> pd.DataFrame:
    panel = pd.DataFrame(np.nan, index=dates, columns=codes, dtype="float64")
    for code, group in events.groupby("stock_code", sort=False):
        if code not in panel.columns:
            continue
        series = (
            group.sort_values("tradable_entry_date")
            .drop_duplicates("tradable_entry_date", keep="last")
            .set_index("tradable_entry_date")[value_column]
        )
        series = pd.to_numeric(series, errors="coerce").astype("float64")
        expanded = series.reindex(dates.union(series.index).sort_values()).ffill().reindex(dates)
        panel[code] = expanded
    return panel


def _cross_sectional_zscore(panel: pd.DataFrame, min_cross_section: int) -> pd.DataFrame:
    rows: list[pd.Series] = []
    for _, values in panel.iterrows():
        valid = pd.to_numeric(values, errors="coerce").dropna()
        result = pd.Series(np.nan, index=panel.columns, dtype="float64")
        if len(valid) >= min_cross_section:
            lower, upper = valid.quantile([0.025, 0.975])
            clipped = valid.clip(lower=float(lower), upper=float(upper))
            std = float(clipped.std(ddof=0))
            if std > 0:
                result.loc[clipped.index] = (clipped - float(clipped.mean())) / std
        rows.append(result)
    return pd.DataFrame(rows, index=panel.index, columns=panel.columns)


def build_point_in_time_financial_panels(
    events: pd.DataFrame,
    dates: Sequence[pd.Timestamp],
    codes: Sequence[str],
    *,
    min_cross_section: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build entry-day financial score and known-loss exclusion panels."""

    frame = events.copy()
    frame["stock_code"] = frame["stock_code"].astype(str)
    frame["tradable_entry_date"] = pd.to_datetime(frame["tradable_entry_date"]).dt.normalize()
    dates_index = pd.DatetimeIndex(pd.to_datetime(list(dates))).normalize().sort_values()
    codes_index = pd.Index([str(code) for code in codes])

    revenue = pd.to_numeric(frame["revenue"], errors="coerce")
    previous_revenue = pd.to_numeric(frame["prev_revenue"], errors="coerce")
    operating_income = pd.to_numeric(frame["operating_income"], errors="coerce")
    net_income = pd.to_numeric(frame["net_income"], errors="coerce")
    total_assets = pd.to_numeric(frame["total_assets"], errors="coerce")
    total_equity = pd.to_numeric(frame["total_equity"], errors="coerce")

    frame["sue"] = pd.to_numeric(frame["sue"], errors="coerce")
    frame["revenue_growth"] = (revenue / previous_revenue - 1.0).where(previous_revenue.gt(0))
    frame["operating_margin"] = (operating_income / revenue).where(revenue.gt(0))
    frame["roa"] = (net_income / total_assets).where(total_assets.gt(0))
    frame["known_loss"] = (net_income.le(0) | total_equity.le(0)).where(
        net_income.notna() | total_equity.notna()
    )

    factor_panels = [
        _cross_sectional_zscore(
            _asof_panel(frame, dates_index, codes_index, factor),
            min_cross_section,
        )
        for factor in FACTOR_COLUMNS
    ]
    available = sum((panel.notna().astype("int16") for panel in factor_panels))
    score = sum((panel.fillna(0.0) for panel in factor_panels)) / available.replace(0, np.nan)
    score = score.where(available.ge(2))

    loss_raw = _asof_panel(frame, dates_index, codes_index, "known_loss")
    loss_exclusion = loss_raw.eq(1.0).fillna(False).astype(bool)
    return score, loss_exclusion


def combine_a4_with_next_open_financial(
    a4_signal: pd.DataFrame,
    financial_entry_signal: pd.DataFrame,
    *,
    a4_weight: float,
) -> pd.DataFrame:
    if not 0.0 <= a4_weight <= 1.0:
        raise ValueError("a4_weight must be between 0 and 1")
    financial_for_next_open = financial_entry_signal.shift(-1).reindex_like(a4_signal)
    return a4_weight * a4_signal + (1.0 - a4_weight) * financial_for_next_open.fillna(0.0)


def bottom_financial_exclusion(
    financial_signal: pd.DataFrame,
    *,
    bottom_fraction: float = 0.20,
    min_cross_section: int = 30,
) -> pd.DataFrame:
    if not 0.0 < bottom_fraction < 1.0:
        raise ValueError("bottom_fraction must be between 0 and 1")
    excluded = pd.DataFrame(False, index=financial_signal.index, columns=financial_signal.columns)
    for date, values in financial_signal.iterrows():
        valid = values.dropna().sort_values()
        if len(valid) < min_cross_section:
            continue
        count = max(int(np.floor(len(valid) * bottom_fraction)), 1)
        excluded.loc[date, valid.head(count).index] = True
    return excluded


def _variant_inputs(
    a4_signal: pd.DataFrame,
    financial_entry: pd.DataFrame,
    loss_entry: pd.DataFrame,
) -> dict[str, tuple[pd.DataFrame, pd.DataFrame | None]]:
    bottom_entry = bottom_financial_exclusion(financial_entry)
    bottom_decision = bottom_entry.shift(-1, fill_value=False).astype(bool)
    loss_decision = loss_entry.shift(-1, fill_value=False).astype(bool)
    score_75 = combine_a4_with_next_open_financial(a4_signal, financial_entry, a4_weight=0.75)
    return {
        "baseline_a4": (a4_signal, None),
        "score_a4_75_fin25": (score_75, None),
        "score_a4_50_fin50": (
            combine_a4_with_next_open_financial(a4_signal, financial_entry, a4_weight=0.50),
            None,
        ),
        "score_a4_25_fin75": (
            combine_a4_with_next_open_financial(a4_signal, financial_entry, a4_weight=0.25),
            None,
        ),
        "gate_bottom20_fin": (a4_signal, bottom_decision),
        "gate_known_loss": (a4_signal, loss_decision),
        "score75_gate_loss": (score_75, loss_decision),
    }


def _simulate_window(
    open_px: pd.DataFrame,
    close_px: pd.DataFrame,
    signal: pd.DataFrame,
    exclude: pd.DataFrame | None,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    cost_bps: int = 30,
) -> pd.DataFrame:
    calendar = open_px.index
    active = calendar[(calendar >= start) & (calendar <= end)]
    if len(active) == 0:
        return pd.DataFrame()
    start_position = calendar.get_loc(active[0])
    seed_position = max(int(start_position) - 1, 0)
    selected_dates = calendar[seed_position : calendar.get_loc(active[-1]) + 1]
    daily, _ = simulate_risk_overlay(
        open_px.loc[selected_dates],
        close_px.loc[selected_dates],
        signal.loc[selected_dates],
        RiskOverlayConfig(),
        rebalance_days=20,
        top_q=0.10,
        min_universe=30,
        cost_bps=cost_bps,
        initial_capital=100_000_000.0,
        exclude=None if exclude is None else exclude.loc[selected_dates],
    )
    return daily.loc[pd.to_datetime(daily["date"]).between(start, end)].reset_index(drop=True)


def _summary_row(daily: pd.DataFrame) -> dict[str, float]:
    if daily.empty:
        return {
            "sharpe": math.nan,
            "ann_return": math.nan,
            "ann_vol": math.nan,
            "max_dd": math.nan,
            "final_equity": math.nan,
            "avg_exposure": math.nan,
            "avg_positions": math.nan,
        }
    result = metrics(daily)
    return {
        "sharpe": float(result["sharpe"]),
        "ann_return": float(result["ann_return"]),
        "ann_vol": float(result["ann_vol"]),
        "max_dd": float(result["max_dd"]),
        "final_equity": float(result["final_equity"]),
        "avg_exposure": float(result["avg_exposure"]),
        "avg_positions": float(daily["position_count"].mean()),
    }


def persist_shadow_snapshot(snapshot: pd.DataFrame, path: Path = SHADOW_HISTORY_PATH) -> None:
    """Atomically upsert one market-date snapshot per strategy variant."""

    frame = snapshot.copy()
    frame["market_date"] = pd.to_datetime(frame["market_date"]).dt.normalize()
    if path.exists():
        existing = pd.read_parquet(path)
        existing["market_date"] = pd.to_datetime(existing["market_date"]).dt.normalize()
        frame = pd.concat([existing, frame], ignore_index=True)
    frame = (
        frame.drop_duplicates(["market_date", "variant"], keep="last")
        .sort_values(["market_date", "variant"])
        .reset_index(drop=True)
    )
    _atomic_parquet(frame, path)


def _annual_alpha(daily: pd.DataFrame) -> float:
    benchmark = pd.read_parquet(KOSPI_PATH, columns=["date", "daily_return"])
    benchmark["date"] = pd.to_datetime(benchmark["date"]).dt.normalize()
    merged = daily.merge(benchmark, on="date", how="left")
    excess = pd.to_numeric(merged["net_return"], errors="coerce") - pd.to_numeric(
        merged["daily_return"], errors="coerce"
    ).fillna(0.0)
    return float(excess.mean() * 252)


def run_experiment() -> dict[str, object]:
    open_px, close_px, a4_signal = load_inputs()
    events = pd.read_parquet(EARNINGS_PATH)
    violations = validate_earnings_point_in_time(events)
    violation_count = sum(len(values) for values in violations.values())
    if violation_count:
        raise RuntimeError(f"Financial point-in-time violations: {violations}")

    financial_entry, loss_entry = build_point_in_time_financial_panels(
        events,
        open_px.index,
        open_px.columns,
    )
    variants = _variant_inputs(a4_signal, financial_entry, loss_entry)

    fold_rows: list[dict[str, object]] = []
    daily_frames: list[pd.DataFrame] = []
    for variant, (signal, exclude) in variants.items():
        for fold in STAGE6_FOLDS:
            for phase in ("train", "test"):
                start = pd.Timestamp(fold.train_start if phase == "train" else fold.test_start)
                end = pd.Timestamp(fold.train_end if phase == "train" else fold.test_end)
                daily = _simulate_window(
                    open_px,
                    close_px,
                    signal,
                    exclude,
                    start=start,
                    end=end,
                )
                row = {
                    "variant": variant,
                    "fold_id": fold.fold_id,
                    "phase": phase,
                    "start": start,
                    "end": end,
                    **_summary_row(daily),
                    "days": int(len(daily)),
                }
                fold_rows.append(row)
                daily.insert(0, "phase", phase)
                daily.insert(0, "fold_id", fold.fold_id)
                daily.insert(0, "variant", variant)
                daily_frames.append(daily)

    folds = pd.DataFrame(fold_rows)
    daily_all = pd.concat(daily_frames, ignore_index=True)
    test_daily = daily_all.loc[daily_all["phase"].eq("test")].copy()
    pooled_rows: list[dict[str, object]] = []
    for variant, group in test_daily.groupby("variant", sort=False):
        group = group.sort_values("date").drop_duplicates("date", keep="first")
        pooled_rows.append(
            {
                "variant": variant,
                **_summary_row(group),
                "ann_alpha": _annual_alpha(group),
                "days": int(len(group)),
            }
        )
    pooled = pd.DataFrame(pooled_rows)

    baseline = pooled.loc[pooled["variant"].eq("baseline_a4")].iloc[0]
    pooled["sharpe_vs_baseline"] = pooled["sharpe"] - float(baseline["sharpe"])
    pooled["ann_return_vs_baseline"] = pooled["ann_return"] - float(baseline["ann_return"])
    pooled["max_dd_improvement"] = pooled["max_dd"] - float(baseline["max_dd"])

    baseline_folds = folds.loc[
        folds["variant"].eq("baseline_a4") & folds["phase"].eq("test"),
        ["fold_id", "sharpe"],
    ].rename(columns={"sharpe": "baseline_fold_sharpe"})
    fold_compare = folds.loc[folds["phase"].eq("test")].merge(baseline_folds, on="fold_id", how="left")
    fold_compare["fold_sharpe_delta"] = fold_compare["sharpe"] - fold_compare["baseline_fold_sharpe"]
    stability = (
        fold_compare.groupby("variant")["fold_sharpe_delta"]
        .min()
        .rename("min_fold_sharpe_delta")
        .reset_index()
    )
    pooled = pooled.merge(stability, on="variant", how="left")
    pooled["balanced_pass"] = (
        pooled["variant"].ne("baseline_a4")
        & pooled["sharpe_vs_baseline"].ge(0.0)
        & pooled["max_dd_improvement"].ge(0.03)
        & pooled["ann_return_vs_baseline"].ge(-0.03)
    )
    pooled["strict_walkforward_pass"] = pooled["balanced_pass"] & pooled[
        "min_fold_sharpe_delta"
    ].ge(-0.25)

    forward_rows: list[dict[str, object]] = []
    forward_start = pd.Timestamp("2026-03-27")
    forward_end = open_px.index.max()
    for variant, (signal, exclude) in variants.items():
        daily = _simulate_window(
            open_px,
            close_px,
            signal,
            exclude,
            start=forward_start,
            end=forward_end,
        )
        forward_rows.append(
            {
                "variant": variant,
                **_summary_row(daily),
                "ann_alpha": _annual_alpha(daily),
                "days": int(len(daily)),
            }
        )
    forward = pd.DataFrame(forward_rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _atomic_parquet(folds, OUTPUT_DIR / "fold_metrics.parquet")
    _atomic_parquet(pooled, OUTPUT_DIR / "pooled_oos_metrics.parquet")
    _atomic_parquet(forward, OUTPUT_DIR / "forward_partial_metrics.parquet")
    _atomic_parquet(daily_all, OUTPUT_DIR / "fold_daily.parquet")

    latest_financial_coverage = float(financial_entry.iloc[-1].notna().mean())
    latest_loss_coverage = float(
        events.loc[pd.to_datetime(events["rcept_dt"]).dt.year.eq(2026), "revenue"].notna().mean()
    )
    forward_snapshot = forward.add_prefix("forward_").rename(columns={"forward_variant": "variant"})
    oos_snapshot = pooled.add_prefix("oos_").rename(columns={"oos_variant": "variant"})
    snapshot = forward_snapshot.merge(oos_snapshot, on="variant", how="inner")
    snapshot.insert(0, "market_date", pd.Timestamp(forward_end).normalize())
    snapshot["financial_events"] = int(len(events))
    snapshot["point_in_time_violations"] = int(violation_count)
    snapshot["latest_financial_coverage"] = latest_financial_coverage
    snapshot["latest_year_revenue_coverage"] = latest_loss_coverage
    persist_shadow_snapshot(snapshot)

    report = f"""# A4 + 재무 복합 팩터 스파이크

## Verdict: {'VALIDATED' if pooled['strict_walkforward_pass'].any() else 'INVALIDATED'}

### 001. Point-in-time 재무 데이터
- 이벤트: {len(events):,}건, 종목: {events['stock_code'].nunique():,}개
- 최신 공시일: {pd.to_datetime(events['rcept_dt']).max().date()}
- 미래정보 누수 위반: {violation_count}건
- 최신 거래일 재무 점수 커버리지: {latest_financial_coverage:.1%}
- 2026 revenue non-null 비율: {latest_loss_coverage:.1%}
- 공시 데이터는 `tradable_entry_date`부터만 유효하며 A4 전일 종가 신호와 다음 시가에서 결합한다.

### 002. 사전 고정 후보
- 점수형: A4/재무 가중치 75/25, 50/50, 25/75
- 게이트형: 재무 점수 하위 20% 제외, 확인된 적자·자본잠식 제외
- 결합형: A4/재무 75/25 + 적자 게이트
- 재무 점수: SUE, 매출 YoY, 영업이익률, ROA의 일별 횡단면 winsorized z-score 평균

### 003. 엄격 워크포워드
- 3년 학습/1년 테스트의 완결된 3개 fold, fold마다 계좌 초기화
- A4 20거래일 리밸런싱, 상위 10%, 다음 시가 체결, 편도 30bp
- 후보와 가중치는 OOS 결과를 보기 전에 고정했다.
- 균형 통과: OOS Sharpe 기준선 이상, MDD 3%p 이상 개선, 연수익 하락 3%p 이내
- 엄격 통과: 균형 통과 + 최악 fold Sharpe 열화 0.25 이내

#### Pooled OOS
{markdown_table(pooled[[
    'variant', 'sharpe', 'ann_return', 'max_dd', 'ann_alpha',
    'sharpe_vs_baseline', 'ann_return_vs_baseline', 'max_dd_improvement',
    'min_fold_sharpe_delta', 'strict_walkforward_pass'
]])}

#### Fold별 테스트
{markdown_table(fold_compare[[
    'variant', 'fold_id', 'start', 'end', 'sharpe', 'ann_return', 'max_dd',
    'fold_sharpe_delta', 'avg_positions'
]])}

#### 2026-03-27 이후 미완결 forward 구간
이 구간은 1년이 완결되지 않아 통과 판정에는 사용하지 않는다.

{markdown_table(forward[[
    'variant', 'sharpe', 'ann_return', 'max_dd', 'final_equity', 'ann_alpha', 'avg_positions', 'days'
]])}

- 일별 shadow snapshot: `{SHADOW_HISTORY_PATH}`
- 동일 거래일 재실행은 `(market_date, variant)` 키로 덮어써 중복하지 않는다.

### Recommendation for the real build
- strict pass 후보가 없으면 paper 전략을 변경하지 않는다.
- strict pass 후보가 있더라도 최신 재무 커버리지를 복구하고 별도 재현 후 paper 적용 여부를 결정한다.
- 실주문에는 사용하지 않는다.
"""
    _atomic_text(report, REPORT_PATH)
    passing = pooled.loc[pooled["strict_walkforward_pass"], "variant"].tolist()
    return {
        "variants": len(variants),
        "folds": len(STAGE6_FOLDS),
        "latest_market_date": str(open_px.index.max().date()),
        "financial_events": int(len(events)),
        "point_in_time_violations": int(violation_count),
        "strict_pass_count": int(len(passing)),
        "strict_passing_variants": passing,
        "shadow_history": str(SHADOW_HISTORY_PATH),
        "report": str(REPORT_PATH),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Spike A4 with point-in-time financial factors.")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({"status": "ready", "report": str(REPORT_PATH)}, ensure_ascii=False))
        return
    print(json.dumps(run_experiment(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
