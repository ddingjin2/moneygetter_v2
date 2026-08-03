"""KR TA 카탈로그(11종) + 일목(5종) 미국 S&P500 이식.

explore_ta_signals.py / explore_ichimoku.py 프레임워크 재사용.
비용 사다리: 0/10/20/30bp (토스 20bp 기준). train 2020-2023 / test 2024~.
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

import v2.scripts.explore_ta_signals as ta  # noqa: E402
from v2.scripts.explore_ichimoku import build_ichimoku_signals  # noqa: E402
from v2.scripts.explore_ta_signals import (  # noqa: E402
    TRAIN_END,
    build_signals,
    cs_zscore,
    forward_returns,
    markdown_table,
    metrics,
    run_backtest,
)

US_OHLCV = ROOT / "v2/data/processed/us_market_ohlcv.parquet"
OUTPUT_DIR = ROOT / "v2/data/cache/us/ta_explore"
REPORT_PATH = ROOT / "v2/reports/us/us_ta_catalog.md"

COST_BPS = [0, 10, 20, 30]
HOLD_DAYS = [1, 5]
MIN_DVOL_USD = 10e6  # 60일 평균 거래대금 $10M


def load_us_panel() -> dict[str, pd.DataFrame]:
    cols = ["date", "symbol", "adj_open", "adj_high", "adj_low", "adj_close", "volume", "dollar_volume"]
    raw = pd.read_parquet(US_OHLCV, columns=cols)
    raw["date"] = pd.to_datetime(raw["date"]).dt.normalize()
    raw = raw.drop_duplicates(["date", "symbol"], keep="last")
    rename = {"adj_open": "open", "adj_high": "high", "adj_low": "low", "adj_close": "close",
              "dollar_volume": "trading_value", "volume": "volume"}
    out = {}
    for src, dst in rename.items():
        wide = raw.pivot(index="date", columns="symbol", values=src).sort_index()
        out[dst] = wide.astype("float64").replace(0.0, np.nan)
    return out


def us_eligibility(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    dvol = panel["trading_value"].fillna(panel["close"] * panel["volume"])
    liquid = dvol.rolling(60, min_periods=40).mean() >= MIN_DVOL_USD
    return liquid & panel["close"].notna() & panel["open"].notna()


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_us_panel()
    mask = us_eligibility(panel)
    ret = forward_returns(panel, mask)
    all_signals = {**build_signals(panel), **build_ichimoku_signals(panel)}
    signals = {name: cs_zscore(frame, mask) for name, frame in all_signals.items()}

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
    result.to_parquet(OUTPUT_DIR / "us_ta_metrics.parquet", index=False)

    cols = ["signal", "hold", "sign", "win_rate", "sharpe", "ann_return", "max_dd", "avg_turnover", "n_days"]
    test0 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(0)].sort_values("sharpe", ascending=False)
    test20 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(20)].sort_values("sharpe", ascending=False)
    report = f"""# 미국 S&P500 TA 카탈로그 이식 (KR 11종 + 일목 5종)

- 데이터: `us_market_ohlcv.parquet` adj OHLCV, {ret.index.min().date()} ~ {ret.index.max().date()}, 평균 {mask.sum(axis=1).mean():.0f}종목/일
- 유니버스: 60일 평균 거래대금 >= ${MIN_DVOL_USD / 1e6:.0f}M
- 실행: t 종가 신호 -> t+1 시가, open-to-open, 상하위 10% 동일가중 롱숏
- 부호: train(~{TRAIN_END.date()}) 결정, test(2024~) out-of-sample
- 비교 기준: KR TA11 test 0bp Sharpe 1.91 / 한국 현물 비용 바닥 18bp, 미국 토스 기준 ~20bp

## Test (0bp) 상위
{markdown_table(test0.head(12), cols)}

## Test (20bp, 토스 기준) 상위
{markdown_table(test20.head(12), cols)}

## 전체
{markdown_table(result.sort_values(["signal", "hold", "period", "cost_bps"]), ["signal", "hold", "period", "cost_bps", "win_rate", "sharpe", "ann_return", "max_dd", "avg_turnover"])}

## Caveats
- 현재 구성 S&P500 유니버스 (생존편향 있음) — 생존자가 나오면 PIT 마스크 재검 필수.
- 공매도 비용/가능 여부 미반영. 부호 선택 train in-sample.
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    best = test20.iloc[0].to_dict() if len(test20) else {}
    return {"rows": len(result), "best_test_20bp": {k: best.get(k) for k in ["signal", "hold", "sharpe", "win_rate"]}}


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
