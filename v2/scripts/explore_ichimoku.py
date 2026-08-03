"""일목균형표 시그널 탐색 - explore_ta_signals.py 프레임워크 재사용.

signal at t close -> t+1 open 진입 -> open-to-open 일간 수익.
부호는 train 구간(2020-2023)에서 결정, test 구간(2024~)에서 평가.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.scripts.explore_ta_signals import (  # noqa: E402
    COST_BPS,
    HOLD_DAYS,
    TRAIN_END,
    cs_zscore,
    eligibility,
    forward_returns,
    load_panel,
    markdown_table,
    metrics,
    run_backtest,
)

OUTPUT_DIR = ROOT / "v2/data/cache/ta_explore"
REPORT_PATH = ROOT / "v2/reports/ichimoku_exploration.md"


def build_ichimoku_signals(panel: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    close, high, low = panel["close"], panel["high"], panel["low"]

    def hl_mid(n: int) -> pd.DataFrame:
        return (high.rolling(n, min_periods=n).max() + low.rolling(n, min_periods=n).min()) / 2.0

    tenkan = hl_mid(9)
    kijun = hl_mid(26)
    # 구름은 26일 전에 계산된 값이 오늘에 투영됨 (선행스팬)
    senkou_a = ((tenkan + kijun) / 2.0).shift(26)
    senkou_b = hl_mid(52).shift(26)
    cloud_top = pd.concat([senkou_a.stack(), senkou_b.stack()], axis=1).max(axis=1).unstack()
    cloud_bot = pd.concat([senkou_a.stack(), senkou_b.stack()], axis=1).min(axis=1).unstack()

    tk_spread = (tenkan - kijun) / close
    price_vs_kijun = close / kijun - 1.0
    cloud_mid = (cloud_top + cloud_bot) / 2.0
    price_vs_cloud = (close - cloud_mid) / close
    # 구름 밖 이탈 거리: 위로 뚫으면 +, 아래로 뚫으면 -, 구름 안이면 0
    breakout = (close - cloud_top).clip(lower=0.0) / close + (close - cloud_bot).clip(upper=0.0) / close
    # 후행스팬: 26일 전 종가 대비 현재 (치코스팬이 가격 위/아래)
    chikou_mom = close / close.shift(26) - 1.0

    return {
        "ICH1_tk_spread": tk_spread,
        "ICH2_price_vs_kijun": price_vs_kijun,
        "ICH3_price_vs_cloud": price_vs_cloud,
        "ICH4_cloud_breakout": breakout,
        "ICH5_chikou_mom26": chikou_mom,
    }


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    mask = eligibility(panel)
    ret = forward_returns(panel, mask)
    signals = {name: cs_zscore(frame, mask) for name, frame in build_ichimoku_signals(panel).items()}

    train = ret.index <= TRAIN_END
    rows = []
    for name, z in signals.items():
        for hold in HOLD_DAYS:
            raw = run_backtest(z, ret, hold, 1.0)
            sign = 1.0 if raw.loc[train, "gross_return"].mean() >= 0 else -1.0
            pnl = raw if sign > 0 else pd.DataFrame({"gross_return": -raw["gross_return"], "turnover": raw["turnover"]})
            for cost in COST_BPS:
                for period, sel in [("train", train), ("test", ~train), ("full", np.ones(len(ret), bool))]:
                    rows.append(metrics(pnl.loc[sel], cost, {"signal": name, "hold": hold, "sign": sign, "period": period}))

    result = pd.DataFrame(rows).dropna(subset=["win_rate"])
    result.to_parquet(OUTPUT_DIR / "ichimoku_metrics.parquet", index=False)

    test30 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(30)].sort_values("sharpe", ascending=False)
    test0 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(0)].sort_values("sharpe", ascending=False)
    cols = ["signal", "hold", "sign", "win_rate", "sharpe", "ann_return", "max_dd", "avg_turnover", "n_days"]
    report = f"""# 일목균형표 시그널 데일리 롱숏 탐색

- 프레임워크: `explore_ta_signals.py`와 동일 (KOSPI, 거래대금 10억+, t종가 신호 -> t+1시가, 상하위 10% 롱숏)
- 기간: {ret.index.min().date()} ~ {ret.index.max().date()}, train ~{TRAIN_END.date()} / test 이후
- 컴포넌트: 전환-기준 스프레드, 가격/기준선, 가격/구름 중심, 구름 이탈 거리, 후행스팬 모멘텀(26d)

## Test 구간 (비용 0bp)
{markdown_table(test0, cols)}

## Test 구간 (비용 30bp 왕복)
{markdown_table(test30, cols)}

## 전체 결과
{markdown_table(result.sort_values(["signal", "hold", "period", "cost_bps"]), ["signal", "hold", "period", "cost_bps", "win_rate", "sharpe", "ann_return", "max_dd", "avg_turnover"])}

## Caveats
- 부호 선택은 train in-sample. test 숫자만 신뢰할 것.
- 비교 기준: 기존 TA 최강 TA11(종가위치 반전) test 0bp Sharpe 1.91 / 알파 17.9bp/회전율.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    best = test0.iloc[0].to_dict() if len(test0) else {}
    return {"rows": len(result), "best_test_0bp": best}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("use --run")
        return
    print(run())


if __name__ == "__main__":
    main()
