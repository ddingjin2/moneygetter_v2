"""TA(보조지표) 계열 시그널 탐색 - 데일리 롱숏 승률 우선.

signal at t close -> t+1 open 진입 -> open-to-open 일간 수익.
부호는 train 구간(2020-2023)에서 결정, test 구간(2024~)에서 평가.
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

OHLCV_PATH = ROOT / "v2/data/processed/market_ohlcv.parquet"
OUTPUT_DIR = ROOT / "v2/data/cache/ta_explore"
REPORT_PATH = ROOT / "v2/reports/ta_signal_exploration.md"

TRAIN_END = pd.Timestamp("2023-12-31")
MIN_DVOL = 1e9  # 60일 평균 거래대금 10억 이상만 유니버스
COST_BPS = [0, 15, 30]
HOLD_DAYS = [1, 5]
BUCKET_PCT = 0.1


def load_panel() -> dict[str, pd.DataFrame]:
    cols = ["date", "ticker", "market", "open", "high", "low", "close", "volume", "trading_value"]
    raw = pd.read_parquet(OHLCV_PATH, columns=cols)
    raw = raw.loc[raw["market"].eq("KOSPI")]
    raw["date"] = pd.to_datetime(raw["date"]).dt.normalize()
    raw = raw.drop_duplicates(["date", "ticker"], keep="last")
    out = {}
    for col in ["open", "high", "low", "close", "volume", "trading_value"]:
        wide = raw.pivot(index="date", columns="ticker", values=col).sort_index()
        out[col] = wide.astype("float64").replace(0.0, np.nan)
    return out


def eligibility(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    dvol = panel["trading_value"].fillna(panel["close"] * panel["volume"])
    liquid = dvol.rolling(60, min_periods=40).mean() >= MIN_DVOL
    priced = panel["close"].notna() & panel["open"].notna()
    return liquid & priced


def _ewm(frame: pd.DataFrame, span: int) -> pd.DataFrame:
    return frame.ewm(span=span, adjust=False, min_periods=span).mean()


def build_signals(panel: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    close, high, low, volume = panel["close"], panel["high"], panel["low"], panel["volume"]
    delta = close.diff()
    up = delta.clip(lower=0.0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    down = (-delta).clip(lower=0.0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rsi14 = 100.0 - 100.0 / (1.0 + up / down.replace(0.0, np.nan))

    ma20 = close.rolling(20, min_periods=20).mean()
    sd20 = close.rolling(20, min_periods=20).std(ddof=0)
    pct_b = (close - ma20) / (2.0 * sd20).replace(0.0, np.nan)

    macd = _ewm(close, 12) - _ewm(close, 26)
    macd_hist = (macd - _ewm(macd, 9)) / close

    ma5 = close.rolling(5, min_periods=5).mean()
    ma_cross = ma5 / ma20 - 1.0

    hh14 = high.rolling(14, min_periods=14).max()
    ll14 = low.rolling(14, min_periods=14).min()
    stoch_k = (close - ll14) / (hh14 - ll14).replace(0.0, np.nan)

    tp = (high + low + close) / 3.0
    tp_ma = tp.rolling(20, min_periods=20).mean()
    mad = (tp - tp_ma).abs().rolling(20, min_periods=20).mean()
    cci20 = (tp - tp_ma) / (0.015 * mad).replace(0.0, np.nan)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).stack(), (high - prev_close).abs().stack(), (low - prev_close).abs().stack()], axis=1
    ).max(axis=1).unstack()
    atr14 = tr.reindex_like(close).rolling(14, min_periods=14).mean()
    atr_mom5 = (close - close.shift(5)) / atr14.replace(0.0, np.nan)

    obv = (np.sign(delta).fillna(0.0) * volume.fillna(0.0)).cumsum()
    obv_slope = (obv - obv.shift(20)) / volume.rolling(20, min_periods=20).mean().replace(0.0, np.nan)

    money_flow = tp * volume
    pos_mf = money_flow.where(tp.diff() > 0, 0.0).rolling(14, min_periods=14).sum()
    neg_mf = money_flow.where(tp.diff() < 0, 0.0).rolling(14, min_periods=14).sum()
    mfi14 = pos_mf / (pos_mf + neg_mf).replace(0.0, np.nan)

    disparity = close / ma20 - 1.0
    intraday_pos = (close - low) / (high - low).replace(0.0, np.nan)

    return {
        "TA1_rsi14": rsi14,
        "TA2_bollinger_pctb": pct_b,
        "TA3_macd_hist": macd_hist,
        "TA4_ma5_20_cross": ma_cross,
        "TA5_stoch_k14": stoch_k,
        "TA6_cci20": cci20,
        "TA7_atr_mom5": atr_mom5,
        "TA8_obv_slope20": obv_slope,
        "TA9_mfi14": mfi14,
        "TA10_disparity20": disparity,
        "TA11_intraday_close_pos": intraday_pos,
    }


def cs_zscore(frame: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    values = frame.where(mask)
    mean = values.mean(axis=1)
    std = values.std(axis=1, ddof=0).replace(0.0, np.nan)
    return values.sub(mean, axis=0).div(std, axis=0).replace([np.inf, -np.inf], np.nan)


def forward_returns(panel: dict[str, pd.DataFrame], mask: pd.DataFrame) -> pd.DataFrame:
    open_px = panel["open"]
    ret = open_px.shift(-1) / open_px - 1.0
    valid = mask & mask.shift(-1).fillna(False) & open_px.gt(0) & open_px.shift(-1).gt(0)
    return ret.where(valid).clip(-0.35, 0.35)


def target_weights(z: pd.DataFrame) -> pd.DataFrame:
    rank = z.rank(axis=1, pct=True)
    count = z.notna().sum(axis=1)
    enough = count.ge(50)
    long = rank.gt(1.0 - BUCKET_PCT).mul(enough, axis=0).astype(bool)
    short = rank.le(BUCKET_PCT).mul(enough, axis=0).astype(bool)
    n_long = long.sum(axis=1).replace(0, np.nan)
    n_short = short.sum(axis=1).replace(0, np.nan)
    return long.div(n_long, axis=0).fillna(0.0) - short.div(n_short, axis=0).fillna(0.0)


def run_backtest(z: pd.DataFrame, ret: pd.DataFrame, hold: int, sign: float) -> pd.DataFrame:
    weights = target_weights(sign * z)
    if hold > 1:
        weights = weights.rolling(hold, min_periods=1).mean()
    held = weights.shift(1).fillna(0.0)  # t 신호 -> t+1 보유
    gross = (held * ret.fillna(0.0)).sum(axis=1)
    turnover = held.diff().abs().sum(axis=1).fillna(0.0) / 2.0
    return pd.DataFrame({"gross_return": gross, "turnover": turnover})


def metrics(pnl: pd.DataFrame, cost_bps: int, label: dict[str, object]) -> dict[str, object]:
    net = pnl["gross_return"] - pnl["turnover"] * (cost_bps / 10000.0) * 2.0
    net = net.dropna()
    if len(net) < 30:
        return {**label, "cost_bps": cost_bps, "n_days": len(net)}
    ann_ret = float(net.mean() * 252)
    ann_vol = float(net.std(ddof=1) * math.sqrt(252))
    equity = (1.0 + net).cumprod()
    return {
        **label,
        "cost_bps": cost_bps,
        "win_rate": float((net > 0).mean()),
        "sharpe": ann_ret / ann_vol if ann_vol else math.nan,
        "ann_return": ann_ret,
        "ann_vol": ann_vol,
        "max_dd": float((equity / equity.cummax() - 1.0).min()),
        "avg_turnover": float(pnl["turnover"].mean()),
        "n_days": int(len(net)),
    }


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    out = frame.loc[:, columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in out.itertuples(index=False):
        cells = [f"{v:.4f}" if isinstance(v, float) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    mask = eligibility(panel)
    ret = forward_returns(panel, mask)
    signals = {name: cs_zscore(frame, mask) for name, frame in build_signals(panel).items()}

    train = ret.index <= TRAIN_END
    rows = []
    pnl_store = {}
    for name, z in signals.items():
        for hold in HOLD_DAYS:
            raw = run_backtest(z, ret, hold, 1.0)
            sign = 1.0 if raw.loc[train, "gross_return"].mean() >= 0 else -1.0
            pnl = raw if sign > 0 else pd.DataFrame({"gross_return": -raw["gross_return"], "turnover": raw["turnover"]})
            pnl_store[(name, hold)] = (pnl, sign)
            for cost in COST_BPS:
                for period, sel in [("train", train), ("test", ~train), ("full", np.ones(len(ret), bool))]:
                    rows.append(metrics(pnl.loc[sel], cost, {"signal": name, "hold": hold, "sign": sign, "period": period}))

    result = pd.DataFrame(rows).dropna(subset=["win_rate"])

    # 상위 3개(train sharpe, 30bp) z-score 합성 콤보
    train30 = result.loc[result["period"].eq("train") & result["cost_bps"].eq(30)].sort_values("sharpe", ascending=False)
    combo_rows = []
    for hold in HOLD_DAYS:
        top = train30.loc[train30["hold"].eq(hold)].head(3)
        if len(top) < 3:
            continue
        combo_z = sum(row.sign * signals[row.signal] for row in top.itertuples())
        pnl = run_backtest(combo_z, ret, hold, 1.0)
        pnl_store[(f"COMBO_top3_{hold}d", hold)] = (pnl, 1.0)
        for cost in COST_BPS:
            for period, sel in [("train", train), ("test", ~train), ("full", np.ones(len(ret), bool))]:
                combo_rows.append(
                    metrics(pnl.loc[sel], cost, {"signal": "COMBO_top3(" + ",".join(top["signal"]) + ")", "hold": hold, "sign": 1.0, "period": period})
                )
    result = pd.concat([result, pd.DataFrame(combo_rows)], ignore_index=True)
    result.to_parquet(OUTPUT_DIR / "ta_metrics.parquet", index=False)
    pd.concat({k[0] + f"_{k[1]}d": v[0] for k, v in pnl_store.items()}, names=["variant", "date"]).to_parquet(
        OUTPUT_DIR / "ta_pnl_daily.parquet"
    )

    test30 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(30)].sort_values("win_rate", ascending=False)
    test0 = result.loc[result["period"].eq("test") & result["cost_bps"].eq(0)].sort_values("win_rate", ascending=False)
    cols = ["signal", "hold", "sign", "win_rate", "sharpe", "ann_return", "max_dd", "avg_turnover", "n_days"]
    report = f"""# TA(보조지표) 시그널 데일리 롱숏 탐색

- 데이터: `v2/data/processed/market_ohlcv.parquet` KOSPI, {ret.index.min().date()} ~ {ret.index.max().date()}, {mask.sum(axis=1).mean():.0f}종목/일 평균
- 유니버스: 60일 평균 거래대금 >= {MIN_DVOL:,.0f}원
- 실행: t 종가 신호 -> t+1 시가 진입, open-to-open, 상하위 {BUCKET_PCT:.0%} 동일가중 롱숏
- 부호: train(~{TRAIN_END.date()}) 평균수익 기준 결정, test는 out-of-sample
- hold=5는 최근 5일 목표비중 평균 보유(회전율 감소)

## Test 구간 (비용 0bp) - 신호 자체 승률
{markdown_table(test0, cols)}

## Test 구간 (비용 30bp 왕복) - 실전 승률
{markdown_table(test30, cols)}

## 전체 결과
{markdown_table(result.sort_values(["signal", "hold", "period", "cost_bps"]), ["signal", "hold", "period", "cost_bps", "win_rate", "sharpe", "ann_return", "max_dd", "avg_turnover"])}

## Caveats
- 부호 선택은 train 구간 in-sample. test 숫자만 신뢰할 것.
- 일간 수익률 ±35% 클립, 상장폐지 종목은 데이터 존재 구간까지만 포함.
- 공매도 가능 여부/대차 비용 미반영.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    best = test30.iloc[0].to_dict() if len(test30) else {}
    return {"rows": len(result), "best_test_30bp": best}


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
