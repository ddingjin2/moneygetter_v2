"""TA11(종가위치 반전) 비용 생존 탐색.

1) 알파 감쇠: t에 만든 롱숏 포트가 t+1..t+10 각 일자에 버는 스프레드.
2) 회전율 저감 조합(원신호 스무딩 / 버퍼 / 비중 스무딩) 그리드.
3) 조합별 손익분기 왕복 비용(bps) = mean(gross) / mean(turnover).
   실전 가정: 농특세 15bp(매도) + 수수료 3bp + 슬리피지 => 왕복 20~30bp.
"""
from __future__ import annotations

import argparse
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
for path in (str(ROOT), str(SCRIPTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from explore_ta_signals import TRAIN_END, build_signals, cs_zscore, eligibility, forward_returns, load_panel, markdown_table  # noqa: E402
from explore_ta_turnover import backtest, buffered_weights  # noqa: E402

OUTPUT_DIR = ROOT / "v2/data/cache/ta_explore"
REPORT_PATH = ROOT / "v2/reports/ta11_cost_survival.md"

SIGNAL_SMOOTH = [1, 2, 3, 5, 10]
ENTRY_PCT = [0.02, 0.05, 0.10]
EXIT_MULT = [1.0, 2.0, 4.0]
WEIGHT_SMOOTH = [1, 3, 5, 10]
TARGET_COST_BPS = 25.0  # 왕복 실행비용 가정


def alpha_decay(z: pd.DataFrame, ret: pd.DataFrame, horizons: int = 10) -> pd.DataFrame:
    weights = buffered_weights(z, 0.10, 0.10)
    rows = []
    for k in range(1, horizons + 1):
        # t 신호 -> t+k 시가에 진입해 t+k+1 시가까지 보유한 수익
        daily = (weights * ret.shift(-k).fillna(0.0)).sum(axis=1)
        rows.append({"day": k, "mean_bps": float(daily.mean() * 10000), "t_stat": float(daily.mean() / daily.std(ddof=1) * np.sqrt(len(daily)))})
    return pd.DataFrame(rows)


def summarize(pnl: pd.DataFrame, sel: np.ndarray, label: dict[str, object]) -> dict[str, object]:
    gross = pnl["gross_return"].loc[sel]
    turnover = pnl["turnover"].loc[sel]
    breakeven = float(gross.mean() / turnover.mean() * 10000) if turnover.mean() else np.nan
    net = gross - turnover * (TARGET_COST_BPS / 10000.0)
    equity = (1.0 + net).cumprod()
    by_cost = {}
    for cost in (10.0, 15.0, 20.0):
        series = gross - turnover * (cost / 10000.0)
        by_cost[f"net_sharpe_{int(cost)}bp"] = float(series.mean() / series.std(ddof=1) * np.sqrt(252))
    return {
        **label,
        "breakeven_bps": breakeven,
        **by_cost,
        "gross_sharpe": float(gross.mean() / gross.std(ddof=1) * np.sqrt(252)),
        "net_sharpe": float(net.mean() / net.std(ddof=1) * np.sqrt(252)),
        "net_ann_return": float(net.mean() * 252),
        "net_win_rate": float((net > 0).mean()),
        "net_max_dd": float((equity / equity.cummax() - 1.0).min()),
        "avg_turnover": float(turnover.mean()),
    }


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    mask = eligibility(panel)
    ret = forward_returns(panel, mask)
    raw = build_signals(panel)["TA11_intraday_close_pos"]

    train = np.asarray(ret.index <= TRAIN_END)
    test = ~train

    decay = alpha_decay(-cs_zscore(raw, mask), ret)

    rows = []
    for sig_s in SIGNAL_SMOOTH:
        smoothed = raw.rolling(sig_s, min_periods=sig_s).mean() if sig_s > 1 else raw
        z = -cs_zscore(smoothed, mask)
        for entry, mult, w_s in product(ENTRY_PCT, EXIT_MULT, WEIGHT_SMOOTH):
            exit_pct = min(entry * mult, 0.5)
            pnl = backtest(buffered_weights(z, entry, exit_pct), ret, w_s)
            label = {"signal_smooth": sig_s, "entry_pct": entry, "exit_pct": round(exit_pct, 3), "weight_smooth": w_s}
            rows.append(summarize(pnl, train, {**label, "period": "train"}))
            rows.append(summarize(pnl, test, {**label, "period": "test"}))
    result = pd.DataFrame(rows)
    result.to_parquet(OUTPUT_DIR / "ta11_cost_metrics.parquet", index=False)

    keys = ["signal_smooth", "entry_pct", "exit_pct", "weight_smooth"]
    train_frame = result.loc[result["period"].eq("train")].set_index(keys)
    test_frame = result.loc[result["period"].eq("test")].set_index(keys)
    joined = train_frame.join(test_frame, lsuffix="_train", rsuffix="_test").reset_index()
    joined["min_breakeven"] = joined[["breakeven_bps_train", "breakeven_bps_test"]].min(axis=1)
    survivors = joined.loc[joined["min_breakeven"] > TARGET_COST_BPS].sort_values("min_breakeven", ascending=False)

    cols = keys + [
        "min_breakeven",
        "breakeven_bps_train",
        "breakeven_bps_test",
        "net_sharpe_10bp_train",
        "net_sharpe_10bp_test",
        "net_sharpe_15bp_test",
        "net_sharpe_20bp_test",
        "net_win_rate_test",
        "net_max_dd_test",
        "avg_turnover_test",
    ]
    report = f"""# TA11 비용 생존 탐색

- 대상: TA11 종가위치 반전 = -(close - low) / (high - low), 횡단면 z
- 손익분기 왕복비용(bps) = mean(gross_return) / mean(turnover) x 10000. 이 값보다 실제 비용이 싸야 생존.
- 가정 실행비용: 왕복 {TARGET_COST_BPS:.0f}bp (농특세 15bp 매도 + 수수료 3bp + 슬리피지)

## 1. 알파 감쇠 (진입 상위/하위 10%, 버퍼 없음, 전구간)
{markdown_table(decay, ["day", "mean_bps", "t_stat"])}

## 2. train/test 양쪽에서 왕복 {TARGET_COST_BPS:.0f}bp를 넘긴 조합 ({len(survivors)}개)
{markdown_table(survivors.head(20), cols) if len(survivors) else "없음."}

## 3. 손익분기 상위 20 조합 (최소값 기준)
{markdown_table(joined.sort_values("min_breakeven", ascending=False).head(20), cols)}

## Caveats
- 손익분기는 선형 비용 가정. 실제 슬리피지는 주문 규모/유동성에 비례해 커짐.
- 공매도 제약 및 대차비용 미반영.
- 원신호 스무딩은 look-ahead 없음(과거 N일 평균).
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    best = survivors.head(1).to_dict("records")
    return {"configs": len(joined), "survivors": int(len(survivors)), "best": best[0] if best else None, "decay_day1_bps": float(decay.loc[0, "mean_bps"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    if not parser.parse_args().run:
        print("use --run")
        return
    print(run())


if __name__ == "__main__":
    main()
