"""TA11 선물 외 대안 2종 검증.

(1) 수익 분해: t+1 시가 진입 후 알파가 장중에 있나 오버나이트에 있나.
    좋은 구간만 잡으면 회전율 그대로 알파(=손익분기 비용)가 올라감.
(2) 거래세 없는 시장: 미국(S&P500). 증권거래세 0, 수수료 ~0.
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

from explore_ta_signals import TRAIN_END, cs_zscore, eligibility, load_panel, markdown_table  # noqa: E402
from explore_ta_turnover import buffered_weights  # noqa: E402

US_PATH = ROOT / "v2/data/processed/us_market_ohlcv.parquet"
OUTPUT_DIR = ROOT / "v2/data/cache/ta_explore"
REPORT_PATH = ROOT / "v2/reports/ta11_alternatives.md"

TOP_N = 150
TAIL = 0.05
US_TOP_N = 150


def ta11_z(panel: dict[str, pd.DataFrame], umask: pd.DataFrame) -> pd.DataFrame:
    close, high, low = panel["close"], panel["high"], panel["low"]
    raw = (close - low) / (high - low).replace(0.0, np.nan)
    return -cs_zscore(raw, umask)


def liquidity_mask(panel: dict[str, pd.DataFrame], mask: pd.DataFrame, top_n: int) -> pd.DataFrame:
    dvol = panel.get("trading_value")
    dvol = panel["close"] * panel["volume"] if dvol is None else dvol.fillna(panel["close"] * panel["volume"])
    rank = dvol.rolling(60, min_periods=40).mean().where(mask).rank(axis=1, ascending=False)
    return mask & rank.le(top_n)


def leg_returns(panel: dict[str, pd.DataFrame], valid: pd.DataFrame) -> dict[str, pd.DataFrame]:
    open_px, close_px = panel["open"], panel["close"]
    # 인덱스 t 행 = t+1일에 실현되는 수익 (신호 t -> t+1 진입)
    nxt_open, nxt_close = open_px.shift(-1), close_px.shift(-1)
    return {
        "open_to_open": (open_px.shift(-2) / nxt_open - 1.0).where(valid),
        "intraday_only": (nxt_close / nxt_open - 1.0).where(valid),
        "overnight_only": (open_px.shift(-2) / nxt_close - 1.0).where(valid),
    }


def evaluate(weights: pd.DataFrame, legs: dict[str, pd.DataFrame], train: np.ndarray, label: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    gross_turnover = weights.diff().abs().sum(axis=1).fillna(0.0) / 2.0
    flat_turnover = weights.abs().sum(axis=1)  # 매일 청산하는 변형: 진입+청산
    for leg, ret in legs.items():
        gross = (weights * ret.fillna(0.0)).sum(axis=1)
        turnover = gross_turnover if leg == "open_to_open" else flat_turnover
        for period, sel in [("train", train), ("test", ~train)]:
            g, t = gross[sel], turnover[sel]
            rows.append(
                {
                    **label,
                    "leg": leg,
                    "period": period,
                    "alpha_bps": float(g.mean() / t.mean() * 10000) if t.mean() else np.nan,
                    "gross_sharpe": float(g.mean() / g.std(ddof=1) * np.sqrt(252)),
                    "gross_ann": float(g.mean() * 252),
                    "avg_turnover": float(t.mean()),
                }
            )
    return rows


def net_ladder(weights: pd.DataFrame, ret: pd.DataFrame, turnover: pd.Series, train: np.ndarray, costs: list[float], label: dict[str, object]) -> list[dict[str, object]]:
    gross = (weights * ret.fillna(0.0)).sum(axis=1)
    rows = []
    for cost in costs:
        net = gross - turnover * (cost / 10000.0)
        for period, sel in [("train", train), ("test", ~train)]:
            r = net[sel]
            equity = (1.0 + r).cumprod()
            rows.append(
                {
                    **label,
                    "cost_bps": cost,
                    "period": period,
                    "sharpe": float(r.mean() / r.std(ddof=1) * np.sqrt(252)),
                    "ann_return": float(r.mean() * 252),
                    "win_rate": float((r > 0).mean()),
                    "max_dd": float((equity / equity.cummax() - 1.0).min()),
                }
            )
    return rows


def load_us_panel() -> dict[str, pd.DataFrame]:
    raw = pd.read_parquet(US_PATH, columns=["date", "symbol", "adj_open", "adj_high", "adj_low", "adj_close", "volume"])
    raw["date"] = pd.to_datetime(raw["date"]).dt.normalize()
    raw = raw.drop_duplicates(["date", "symbol"], keep="last")
    out = {}
    for src, dst in [("adj_open", "open"), ("adj_high", "high"), ("adj_low", "low"), ("adj_close", "close"), ("volume", "volume")]:
        out[dst] = raw.pivot(index="date", columns="symbol", values=src).sort_index().astype("float64").replace(0.0, np.nan)
    return out


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # (1) 한국 수익 분해
    kr = load_panel()
    kr_mask = eligibility(kr)
    kr_umask = liquidity_mask(kr, kr_mask, TOP_N)
    kr_valid = kr_umask & kr_umask.shift(-1).fillna(False) & kr["open"].shift(-1).gt(0)
    kr_legs = leg_returns(kr, kr_valid)
    kr_weights = buffered_weights(ta11_z(kr, kr_umask), TAIL, TAIL)  # legs가 이미 t+1 실현 기준
    kr_train = np.asarray(kr["close"].index <= TRAIN_END)
    decomp = pd.DataFrame(evaluate(kr_weights, kr_legs, kr_train, {"market": "KOSPI"}))

    best_leg = decomp.loc[decomp["period"].eq("test")].sort_values("alpha_bps", ascending=False).iloc[0]["leg"]
    kr_turnover = kr_weights.abs().sum(axis=1) if best_leg != "open_to_open" else kr_weights.diff().abs().sum(axis=1).fillna(0.0) / 2.0
    kr_ladder = pd.DataFrame(
        net_ladder(kr_weights, kr_legs[best_leg], kr_turnover, kr_train, [0, 3, 10, 18, 25], {"market": "KOSPI", "leg": best_leg})
    )

    # (2) 미국
    us = load_us_panel()
    us_mask = us["close"].notna() & us["open"].notna()
    us_umask = liquidity_mask(us, us_mask, US_TOP_N)
    us_valid = us_umask & us_umask.shift(-1).fillna(False) & us["open"].shift(-1).gt(0)
    us_legs = leg_returns(us, us_valid)
    us_weights = buffered_weights(ta11_z(us, us_umask), TAIL, TAIL)
    us_train = np.asarray(us["close"].index <= TRAIN_END)
    us_decomp = pd.DataFrame(evaluate(us_weights, us_legs, us_train, {"market": "US_SP500"}))
    us_best = us_decomp.loc[us_decomp["period"].eq("test")].sort_values("alpha_bps", ascending=False).iloc[0]["leg"]
    us_turnover = us_weights.abs().sum(axis=1) if us_best != "open_to_open" else us_weights.diff().abs().sum(axis=1).fillna(0.0) / 2.0
    us_ladder = pd.DataFrame(
        net_ladder(us_weights, us_legs[us_best], us_turnover, us_train, [0, 2, 5, 10], {"market": "US_SP500", "leg": us_best})
    )
    us_oo_ladder = pd.DataFrame(
        net_ladder(
            us_weights,
            us_legs["open_to_open"],
            us_weights.diff().abs().sum(axis=1).fillna(0.0) / 2.0,
            us_train,
            [0, 2, 5, 10],
            {"market": "US_SP500", "leg": "open_to_open"},
        )
    )

    all_decomp = pd.concat([decomp, us_decomp], ignore_index=True)
    all_ladder = pd.concat([kr_ladder, us_ladder, us_oo_ladder], ignore_index=True)
    all_decomp.to_parquet(OUTPUT_DIR / "ta11_alternatives_decomp.parquet", index=False)
    all_ladder.to_parquet(OUTPUT_DIR / "ta11_alternatives_ladder.parquet", index=False)

    report = f"""# TA11 대안 검증: 수익 분해 + 미국 시장

유니버스: 유동성 상위 {TOP_N}종목, 상하위 {TAIL:.0%} 롱숏, 일간 리밸런스.

## 1. 수익 분해 - 알파가 어디 있나
- open_to_open: t+1 시가 진입 -> t+2 시가 청산 (기존 가정)
- intraday_only: t+1 시가 진입 -> t+1 종가 청산
- overnight_only: t+1 종가 진입 -> t+2 시가 청산
- alpha_bps = 회전율 1단위당 수익. 이 값이 실행비용보다 커야 생존.

{markdown_table(all_decomp, ["market", "leg", "period", "alpha_bps", "gross_sharpe", "gross_ann", "avg_turnover"])}

## 2. 비용 사다리
{markdown_table(all_ladder, ["market", "leg", "cost_bps", "period", "sharpe", "ann_return", "win_rate", "max_dd"])}

## Caveats
- 미국: adj OHLC 사용(배당/분할 조정). S&P500 현 구성 기준이라 생존편향 있음.
- 미국 비용: 증권거래세 없음, 수수료 ~0, 스프레드 대형주 1~2bp. 공매도는 대차 가능.
- intraday_only / overnight_only 는 매일 전량 청산이라 회전율 정의가 다름(진입+청산 = 1.0).
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    return {
        "kr_best_leg": best_leg,
        "us_best_leg": us_best,
        "kr_test_alpha": float(decomp.loc[decomp["period"].eq("test")].set_index("leg").loc[best_leg, "alpha_bps"]),
        "us_test_alpha": float(us_decomp.loc[us_decomp["period"].eq("test")].set_index("leg").loc[us_best, "alpha_bps"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    if not parser.parse_args().run:
        print("use --run")
        return
    print(run())


if __name__ == "__main__":
    main()
