"""TA 시그널 회전율 통제 탐색 - 순수익 기준 데일리 롱숏 승률 찾기.

Step 1(explore_ta_signals)에서 gross alpha는 확인됨. 여기서는 비용 후 생존 조합 탐색:
버퍼(히스테리시스) 리밸런싱 / 보유일 스무딩 / 버킷 폭 / 시그널 합성.
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

from explore_ta_signals import (  # noqa: E402
    TRAIN_END,
    build_signals,
    cs_zscore,
    eligibility,
    forward_returns,
    load_panel,
    markdown_table,
    metrics,
)

OUTPUT_DIR = ROOT / "v2/data/cache/ta_explore"
REPORT_PATH = ROOT / "v2/reports/ta_turnover_exploration.md"

COST_BPS = [0, 10, 15]  # cost_bps x 2 = 왕복 bps. 15 => 왕복 30bp (한국 세금+수수료+슬리피지)
ENTRY_PCT = [0.05, 0.10, 0.20]
BUFFER_MULT = [1.0, 2.0, 3.0]  # exit rank = entry_pct * mult
SMOOTH = [1, 3, 5]
CANDIDATES = ["TA11_intraday_close_pos", "TA9_mfi14", "TA8_obv_slope20", "TA1_rsi14", "TA10_disparity20", "TA2_bollinger_pctb"]


def buffered_weights(z: pd.DataFrame, entry_pct: float, exit_pct: float) -> pd.DataFrame:
    """랭크 상위 entry_pct 진입, exit_pct 밖으로 나가야 청산(히스테리시스)."""
    rank = z.rank(axis=1, pct=True).to_numpy()
    valid = z.notna().to_numpy()
    enough = z.notna().sum(axis=1).to_numpy() >= 50
    n_days, n_codes = rank.shape
    long_state = np.zeros(n_codes, dtype=bool)
    short_state = np.zeros(n_codes, dtype=bool)
    out = np.zeros((n_days, n_codes))
    for i in range(n_days):
        if not enough[i]:
            long_state[:] = False
            short_state[:] = False
            continue
        r = rank[i]
        ok = valid[i]
        long_state = np.where(ok, (long_state & (r > 1.0 - exit_pct)) | (r > 1.0 - entry_pct), False)
        short_state = np.where(ok, (short_state & (r <= exit_pct)) | (r <= entry_pct), False)
        n_long, n_short = long_state.sum(), short_state.sum()
        if n_long:
            out[i, long_state] = 1.0 / n_long
        if n_short:
            out[i, short_state] = -1.0 / n_short
    return pd.DataFrame(out, index=z.index, columns=z.columns)


def backtest(weights: pd.DataFrame, ret: pd.DataFrame, smooth: int) -> pd.DataFrame:
    if smooth > 1:
        weights = weights.rolling(smooth, min_periods=1).mean()
    held = weights.shift(1).fillna(0.0)
    return pd.DataFrame(
        {
            "gross_return": (held * ret.fillna(0.0)).sum(axis=1),
            "turnover": held.diff().abs().sum(axis=1).fillna(0.0) / 2.0,
        }
    )


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    mask = eligibility(panel)
    ret = forward_returns(panel, mask)
    raw_signals = build_signals(panel)
    signals = {name: cs_zscore(raw_signals[name], mask) for name in CANDIDATES}
    # step1 결과: 모두 reversal 방향(sign=-1)이 우세
    signals = {name: -z for name, z in signals.items()}
    signals["COMBO_rev3"] = (signals["TA11_intraday_close_pos"] + signals["TA9_mfi14"] + signals["TA1_rsi14"]) / 3.0

    train = ret.index <= TRAIN_END
    rows = []
    best_pnl: dict[str, pd.DataFrame] = {}
    for name, entry, mult, smooth in product(signals, ENTRY_PCT, BUFFER_MULT, SMOOTH):
        exit_pct = min(entry * mult, 0.5)
        weights = buffered_weights(signals[name], entry, exit_pct)
        pnl = backtest(weights, ret, smooth)
        key = f"{name}|e{entry}|x{exit_pct:.2f}|s{smooth}"
        best_pnl[key] = pnl
        for cost in COST_BPS:
            for period, sel in [("train", train), ("test", ~train), ("full", np.ones(len(ret), bool))]:
                rows.append(
                    metrics(pnl.loc[sel], cost, {"signal": name, "entry_pct": entry, "exit_pct": exit_pct, "smooth": smooth, "period": period})
                )
    result = pd.DataFrame(rows).dropna(subset=["win_rate"])
    result.to_parquet(OUTPUT_DIR / "ta_turnover_metrics.parquet", index=False)

    cols = ["signal", "entry_pct", "exit_pct", "smooth", "win_rate", "sharpe", "ann_return", "ann_vol", "max_dd", "avg_turnover"]
    train15 = result.loc[result["period"].eq("train") & result["cost_bps"].eq(15)].sort_values("sharpe", ascending=False)
    top_keys = train15.head(10)[["signal", "entry_pct", "exit_pct", "smooth"]]
    test15 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(15)]
    selected = top_keys.merge(test15, on=["signal", "entry_pct", "exit_pct", "smooth"], how="left")
    test_sorted = test15.sort_values("sharpe", ascending=False)

    best = selected.iloc[0].to_dict() if len(selected) else {}
    if best:
        key = f"{best['signal']}|e{best['entry_pct']}|x{best['exit_pct']:.2f}|s{int(best['smooth'])}"
        best_pnl[key].to_parquet(OUTPUT_DIR / "best_pnl_daily.parquet")

    report = f"""# TA 시그널 회전율 통제 탐색 (데일리 롱숏)

- 비용 표기: cost_bps x 2 = 왕복. **15 = 왕복 30bp** (한국 거래세+수수료+슬리피지 가정)
- 버퍼: 랭크 상위 entry_pct 진입, exit_pct 밖으로 나갈 때까지 보유
- smooth: 최근 N일 목표비중 평균(추가 회전율 완화)
- 방향: step1 결과대로 전부 reversal(-) 부호 고정

## 1. Train(~{TRAIN_END.date()}) 상위 10개 조합의 Test 성과 (왕복 30bp)
{markdown_table(selected, cols)}

## 2. Test 구간 전체 상위 15 (왕복 30bp, in-sample 아님에 주의 - 이건 사후 최고치)
{markdown_table(test_sorted.head(15), cols)}

## 3. 무비용(0bp) Test 상위 10 - 시그널 원천 알파 확인용
{markdown_table(result.loc[result["period"].eq("test") & result["cost_bps"].eq(0)].sort_values("sharpe", ascending=False).head(10), cols)}

## Caveats
- 공매도: 개인 계좌는 KOSPI 개별종목 대차/차입공매도 제약. 롱숏 그대로 실행 불가할 수 있음.
- 부호/후보 선택은 step1 train 결과 기반. 2번 표는 test 사후 최적화이므로 실제 기대치 아님.
- 일간 수익 ±35% 클립, 상폐 종목은 데이터 존재 구간까지만 포함.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    return {"rows": len(result), "best_train_selected_test": best}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    if not parser.parse_args().run:
        print("use --run")
        return
    print(run())


if __name__ == "__main__":
    main()
