"""미국 오버나이트 아노말리 탐색.

1) 마켓 레벨: 유니버스 동일가중, 오버나이트(close->open)만 보유 vs 장중(open->close)만 vs buy-hold.
2) 크로스섹션: 과거 오버나이트 수익 누적 시그널(overnight momentum, Lou-Polk-Skouras 스타일) 롱숏,
   장중 반전 시그널 롱숏. explore_ta_signals 프레임워크 재사용.

주의: 오버나이트/장중 분리 보유는 매일 왕복이라 실비용에서 살 수 없음 — 신호 방향 확인용.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.scripts.explore_ta_signals import (  # noqa: E402
    TRAIN_END,
    cs_zscore,
    markdown_table,
    metrics,
    run_backtest,
)
from v2.scripts.explore_us_ta_catalog import load_us_panel, us_eligibility  # noqa: E402

OUTPUT_DIR = ROOT / "v2/data/cache/us/ta_explore"
REPORT_PATH = ROOT / "v2/reports/us/us_overnight.md"
COST_BPS = [0, 10, 20, 30]
HOLD_DAYS = [1, 5]


def ann_stats(r: pd.Series, label: str) -> dict:
    r = r.dropna()
    mean, vol = r.mean() * 252, r.std(ddof=1) * math.sqrt(252)
    eq = (1 + r).cumprod()
    return {"leg": label, "ann_return": float(mean), "ann_vol": float(vol),
            "sharpe": float(mean / vol) if vol else np.nan,
            "max_dd": float((eq / eq.cummax() - 1).min()), "win_rate": float((r > 0).mean()), "n_days": len(r)}


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_us_panel()
    mask = us_eligibility(panel)
    open_px, close_px = panel["open"], panel["close"]

    overnight = (open_px / close_px.shift(1) - 1.0).where(mask).clip(-0.35, 0.35)
    intraday = (close_px / open_px - 1.0).where(mask).clip(-0.35, 0.35)

    # 1) 마켓 레벨 동일가중
    market_rows = [
        ann_stats(overnight.mean(axis=1), "overnight_only(close->open)"),
        ann_stats(intraday.mean(axis=1), "intraday_only(open->close)"),
        ann_stats((close_px / close_px.shift(1) - 1.0).where(mask).clip(-0.35, 0.35).mean(axis=1), "buy_hold(close->close)"),
    ]
    market = pd.DataFrame(market_rows)

    # 기간 분해 (train/test)
    train_idx = overnight.index <= TRAIN_END
    market_split = pd.DataFrame(
        [ann_stats(overnight.mean(axis=1)[train_idx], "overnight_train"),
         ann_stats(overnight.mean(axis=1)[~train_idx], "overnight_test"),
         ann_stats(intraday.mean(axis=1)[train_idx], "intraday_train"),
         ann_stats(intraday.mean(axis=1)[~train_idx], "intraday_test")]
    )

    # 2) 크로스섹션 시그널: t+1 open 진입 open-to-open 수익 (기존 프레임워크와 동일 실행)
    ret = (open_px.shift(-1) / open_px - 1.0)
    valid = mask & mask.shift(-1).fillna(False) & open_px.gt(0) & open_px.shift(-1).gt(0)
    ret = ret.where(valid).clip(-0.35, 0.35)

    signals_raw = {
        "ON1_overnight_mom20": overnight.rolling(20, min_periods=15).sum(),
        "ON2_overnight_mom60": overnight.rolling(60, min_periods=40).sum(),
        "ON3_intraday_rev5": intraday.rolling(5, min_periods=5).sum(),
        "ON4_on_id_gap20": overnight.rolling(20, min_periods=15).sum() - intraday.rolling(20, min_periods=15).sum(),
    }
    signals = {k: cs_zscore(v, mask) for k, v in signals_raw.items()}

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
    result.to_parquet(OUTPUT_DIR / "us_overnight_metrics.parquet", index=False)

    cols = ["signal", "hold", "sign", "win_rate", "sharpe", "ann_return", "max_dd", "avg_turnover", "n_days"]
    test0 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(0)].sort_values("sharpe", ascending=False)
    test20 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(20)].sort_values("sharpe", ascending=False)
    mcols = ["leg", "ann_return", "ann_vol", "sharpe", "max_dd", "win_rate", "n_days"]
    report = f"""# 미국 오버나이트 아노말리 탐색

- 데이터: S&P500 adj OHLCV {overnight.index.min().date()} ~ {overnight.index.max().date()}, 평균 {mask.sum(axis=1).mean():.0f}종목/일
- 마켓 레벨 분해는 비용 0 가정 (매일 왕복이라 실거래 불가, 구조 확인용)

## 마켓 레벨: 수익은 어디서 나나 (full, 0bp)
{markdown_table(market, mcols)}

## 마켓 레벨 train/test 분해
{markdown_table(market_split, mcols)}

## 크로스섹션 시그널 Test (0bp)
{markdown_table(test0, cols)}

## 크로스섹션 시그널 Test (20bp 토스 기준)
{markdown_table(test20, cols)}

## Caveats
- 생존편향 유니버스. 부호 train in-sample. 공매도 비용 미반영.
- KR에서 TA11 장중/오버나이트 분리는 알파 감소로 기각됐던 것과 동일 구조 주의.
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
