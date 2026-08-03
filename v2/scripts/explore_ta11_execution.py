"""TA11 실행 가능성 검증: 유동성 구간별 알파 vs 추정 체결비용.

핵심 질문 - TA11 손익분기(왕복 26~30bp)를 실제 비용이 밑돌 수 있나?
비용 바닥 = 농특세 15bp(매도) + 수수료 + 스프레드(호가단위/가격) 절반 x 2회.
알파가 소형 저유동성에만 있으면 스프레드가 더 커서 사망, 대형주에도 있으면 생존.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
for path in (str(ROOT), str(SCRIPTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from explore_ta_signals import TRAIN_END, build_signals, cs_zscore, eligibility, forward_returns, load_panel, markdown_table  # noqa: E402
from explore_ta_turnover import buffered_weights  # noqa: E402

OUTPUT_DIR = ROOT / "v2/data/cache/ta_explore"
REPORT_PATH = ROOT / "v2/reports/ta11_execution_feasibility.md"

SELL_TAX_BPS = 15.0  # 농어촌특별세 0.15% (매도 시)
COMMISSION_BPS_PER_SIDE = 1.5  # 온라인 수수료 가정
LIQUIDITY_BUCKETS = 3
TAIL_PCT = [0.02, 0.05, 0.10]


def tick_size(price: pd.DataFrame) -> pd.DataFrame:
    """KRX 유가증권 호가단위(2023 개편)."""
    bounds = [(2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500)]
    tick = pd.DataFrame(1000.0, index=price.index, columns=price.columns)
    for limit, size in reversed(bounds):
        tick = tick.where(price >= limit, float(size))
    return tick.where(price.notna())


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    mask = eligibility(panel)
    ret = forward_returns(panel, mask)
    close = panel["close"]
    dvol = panel["trading_value"].fillna(close * panel["volume"])
    dvol60 = dvol.rolling(60, min_periods=40).mean()

    raw = build_signals(panel)["TA11_intraday_close_pos"]
    z_all = -cs_zscore(raw, mask)

    # 유동성 3분위 마스크
    rank = dvol60.where(mask).rank(axis=1, pct=True)
    bucket_masks = {
        "low_liquidity": mask & rank.le(1 / 3),
        "mid_liquidity": mask & rank.gt(1 / 3) & rank.le(2 / 3),
        "high_liquidity": mask & rank.gt(2 / 3),
        "all": mask,
    }

    half_spread_bps = (tick_size(close) / close * 10000.0) / 2.0
    train = np.asarray(ret.index <= TRAIN_END)

    rows = []
    for bucket, bmask in bucket_masks.items():
        z = cs_zscore(raw, bmask).mul(-1.0)
        for tail in TAIL_PCT:
            weights = buffered_weights(z, tail, tail)
            gross = (weights.shift(1).fillna(0.0) * ret.fillna(0.0)).sum(axis=1)
            turnover = weights.shift(1).fillna(0.0).diff().abs().sum(axis=1).fillna(0.0) / 2.0
            traded = weights.abs().gt(0)
            spread_cost = (half_spread_bps.where(traded).mean(axis=1)).mean()
            cost_floor = SELL_TAX_BPS + 2 * COMMISSION_BPS_PER_SIDE + 2 * spread_cost
            for period, sel in [("train", train), ("test", ~train), ("full", np.ones(len(ret), bool))]:
                g, t = gross[sel], turnover[sel]
                breakeven = float(g.mean() / t.mean() * 10000) if t.mean() else np.nan
                net = g - t * (cost_floor / 10000.0)
                rows.append(
                    {
                        "bucket": bucket,
                        "tail_pct": tail,
                        "period": period,
                        "alpha_bps_per_turnover": breakeven,
                        "est_cost_floor_bps": float(cost_floor),
                        "margin_bps": float(breakeven - cost_floor),
                        "net_sharpe": float(net.mean() / net.std(ddof=1) * np.sqrt(252)),
                        "net_win_rate": float((net > 0).mean()),
                        "gross_sharpe": float(g.mean() / g.std(ddof=1) * np.sqrt(252)),
                        "avg_turnover": float(t.mean()),
                        "avg_names": float(weights.ne(0).sum(axis=1)[sel].mean()),
                    }
                )
    result = pd.DataFrame(rows)
    result.to_parquet(OUTPUT_DIR / "ta11_execution_metrics.parquet", index=False)

    cols = ["bucket", "tail_pct", "period", "alpha_bps_per_turnover", "est_cost_floor_bps", "margin_bps", "net_sharpe", "net_win_rate", "gross_sharpe", "avg_turnover", "avg_names"]
    oos = result.loc[result["period"].ne("full")].sort_values(["bucket", "tail_pct", "period"])
    survivors = result.loc[result["period"].eq("test") & result["margin_bps"].gt(0)].sort_values("margin_bps", ascending=False)

    report = f"""# TA11 실행 가능성: 유동성 구간별 알파 vs 체결비용

- 알파(bps/회전율) = mean(gross) / mean(turnover) x 10000. 회전율 1 단위 거래로 버는 bps.
- 추정 비용 바닥 = 농특세 {SELL_TAX_BPS:.0f}bp(매도) + 수수료 {COMMISSION_BPS_PER_SIDE * 2:.0f}bp + 호가스프레드 절반 x 2회(종목별 실제 호가단위/가격 기반)
- margin_bps > 0 이어야 실제로 돈이 남음.

## 1. 구간별 결과 (train/test)
{markdown_table(oos, cols)}

## 2. Test에서 마진 양수인 조합 ({len(survivors)}개)
{markdown_table(survivors, cols) if len(survivors) else "없음. 추정 비용 바닥에서 TA11은 실행 불가."}

## Caveats
- 스프레드는 호가단위 기반 하한 추정. 실제 체결은 시장충격/부분체결로 더 나쁠 수 있음.
- 공매도 제약/대차수수료 미반영 (롱숏 전제).
- 시가 단일가 체결 가정, 주문 규모 미반영.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    return {"rows": len(result), "test_survivors": int(len(survivors)), "best": survivors.head(1).to_dict("records")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    if not parser.parse_args().run:
        print("use --run")
        return
    print(run())


if __name__ == "__main__":
    main()
