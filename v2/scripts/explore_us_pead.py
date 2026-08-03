"""PEAD(실적발표 후 드리프트) 탐색 — SEC Company Facts net_income 기반.

SUE = (NI_q - NI_{q-4}) / std(최근 8개 YoY 변화). 이벤트 = SEC filing_date.
1) 이벤트 스터디: filing 후 +1~+5/+20/+60 거래일 초과수익(CAR, 유니버스 평균 대비) SUE 5분위별.
2) 포트폴리오: 최근 60거래일 내 filing 종목 대상 SUE 상위 5분위 LO / 상하위 롱숏, 일간 마크.

주의: filing_date(10-Q/10-K 제출일)는 실적 보도자료(press release)보다 늦다 —
진짜 PEAD보다 약하게 측정되는 보수적 세팅.
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

from v2.scripts.explore_ta_signals import markdown_table, metrics  # noqa: E402

FUND_PATH = ROOT / "v2/data/cache/us/nasdaq100_pitlite/strategy_compare/quality_fundamental/sec_companyfacts_fundamentals.parquet"
OHLCV_PATH = ROOT / "v2/data/processed/us_nasdaq100_pitlite_ohlcv.parquet"
OUTPUT_DIR = ROOT / "v2/data/cache/us/pead"
REPORT_PATH = ROOT / "v2/reports/us/us_pead.md"

TRAIN_END = pd.Timestamp("2023-12-31")
HOLD_TD = 60  # filing 후 시그널 유효 거래일
COST_BPS = [0, 10, 20, 30]
CAR_WINDOWS = [5, 20, 60]
MIN_NAMES = 20


def load_prices() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_parquet(OHLCV_PATH, columns=["date", "symbol", "adj_open", "adj_close"])
    raw["date"] = pd.to_datetime(raw["date"]).dt.normalize()
    raw = raw.drop_duplicates(["date", "symbol"], keep="last")
    open_px = raw.pivot(index="date", columns="symbol", values="adj_open").sort_index().astype("float64").replace(0.0, np.nan)
    close_px = raw.pivot(index="date", columns="symbol", values="adj_close").sort_index().astype("float64").replace(0.0, np.nan)
    return open_px, close_px


def compute_sue() -> pd.DataFrame:
    f = pd.read_parquet(FUND_PATH)
    f = f.dropna(subset=["net_income", "filing_date", "fiscal_period_end"])
    f["filing_date"] = pd.to_datetime(f["filing_date"])
    f["fiscal_period_end"] = pd.to_datetime(f["fiscal_period_end"])
    # 같은 회계기간 재공시는 최초 filing만
    f = f.sort_values("filing_date").drop_duplicates(["symbol", "fiscal_period_end"], keep="first")
    f = f.sort_values(["symbol", "fiscal_period_end"])
    g = f.groupby("symbol", group_keys=False)
    f["ni_yoy"] = g["net_income"].diff(4)
    f["sue"] = f["ni_yoy"] / g["ni_yoy"].transform(lambda s: s.rolling(8, min_periods=6).std(ddof=0)).replace(0.0, np.nan)
    f = f.dropna(subset=["sue"])
    f["sue"] = f["sue"].clip(-10, 10)
    return f[["symbol", "fiscal_period_end", "filing_date", "sue"]]


def event_study(events: pd.DataFrame, open_px: pd.DataFrame) -> pd.DataFrame:
    ret = (open_px.shift(-1) / open_px - 1.0).clip(-0.35, 0.35)
    abn = ret.sub(ret.mean(axis=1), axis=0)
    dates = open_px.index
    rows = []
    for ev in events.itertuples():
        if ev.symbol not in abn.columns:
            continue
        pos = dates.searchsorted(ev.filing_date, side="right")  # filing 다음 거래일부터
        if pos >= len(dates) - 5:
            continue
        window = abn[ev.symbol].iloc[pos : pos + max(CAR_WINDOWS)]
        if window.isna().all():
            continue
        row = {"symbol": ev.symbol, "filing_date": ev.filing_date, "sue": ev.sue}
        for w in CAR_WINDOWS:
            car = window.iloc[:w]
            row[f"car_{w}d"] = float(car.sum()) if car.notna().sum() >= w * 0.7 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def quintile_table(ev: pd.DataFrame, label: str) -> pd.DataFrame:
    ev = ev.copy()
    ev["q"] = pd.qcut(ev["sue"], 5, labels=False, duplicates="drop") + 1
    agg = ev.groupby("q").agg(
        n=("sue", "size"),
        **{f"car_{w}d_mean": (f"car_{w}d", "mean") for w in CAR_WINDOWS},
    ).reset_index()
    for w in CAR_WINDOWS:
        s = ev.groupby("q")[f"car_{w}d"]
        agg[f"car_{w}d_t"] = (s.mean() / (s.std() / np.sqrt(s.count()))).values
    agg.insert(0, "period", label)
    return agg


def portfolio_backtest(events: pd.DataFrame, open_px: pd.DataFrame) -> pd.DataFrame:
    dates = open_px.index
    sue = pd.DataFrame(np.nan, index=dates, columns=open_px.columns)
    for ev in events.itertuples():
        if ev.symbol not in sue.columns:
            continue
        pos = dates.searchsorted(ev.filing_date, side="right")
        if pos >= len(dates):
            continue
        sue.iloc[pos : pos + HOLD_TD, sue.columns.get_loc(ev.symbol)] = ev.sue

    ret = (open_px.shift(-1) / open_px - 1.0).clip(-0.35, 0.35)
    rank = sue.rank(axis=1, pct=True)
    count = sue.notna().sum(axis=1)
    enough = count.ge(MIN_NAMES)
    long = rank.gt(0.8).mul(enough, axis=0).astype(bool)
    short = rank.le(0.2).mul(enough, axis=0).astype(bool)
    n_long = long.sum(axis=1).replace(0, np.nan)
    n_short = short.sum(axis=1).replace(0, np.nan)
    w_ls = long.div(n_long, axis=0).fillna(0.0) - short.div(n_short, axis=0).fillna(0.0)
    w_lo = long.div(n_long, axis=0).fillna(0.0)
    out = {}
    for name, w in [("PEAD_LS", w_ls), ("PEAD_LO_top_quintile", w_lo)]:
        held = w.shift(1).fillna(0.0)
        gross = (held * ret.fillna(0.0)).sum(axis=1)
        turnover = held.diff().abs().sum(axis=1).fillna(0.0) / 2.0
        out[name] = pd.DataFrame({"gross_return": gross, "turnover": turnover})
    return out


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    open_px, _ = load_prices()
    sue = compute_sue()
    events = sue[sue["filing_date"] >= open_px.index.min()]
    ev = event_study(events, open_px)
    ev.to_parquet(OUTPUT_DIR / "pead_events.parquet", index=False)

    train_ev = ev[ev["filing_date"] <= TRAIN_END]
    test_ev = ev[ev["filing_date"] > TRAIN_END]
    qt = pd.concat([quintile_table(train_ev, "train"), quintile_table(test_ev, "test")], ignore_index=True)

    pnls = portfolio_backtest(events, open_px)
    train = open_px.index <= TRAIN_END
    rows = []
    for name, pnl in pnls.items():
        for cost in COST_BPS:
            for period, sel in [("train", train), ("test", ~train), ("full", np.ones(len(open_px), bool))]:
                rows.append(metrics(pnl.loc[sel], cost, {"signal": name, "hold": HOLD_TD, "sign": 1.0, "period": period}))
    result = pd.DataFrame(rows).dropna(subset=["win_rate"])
    result.to_parquet(OUTPUT_DIR / "pead_metrics.parquet", index=False)

    qcols = ["period", "q", "n"] + [f"car_{w}d_mean" for w in CAR_WINDOWS] + [f"car_{w}d_t" for w in CAR_WINDOWS]
    pcols = ["signal", "period", "cost_bps", "win_rate", "sharpe", "ann_return", "max_dd", "avg_turnover", "n_days"]
    report = f"""# 미국 PEAD 탐색 (SEC filing 기반, Nasdaq100 PIT-lite)

- 이벤트 수: train {len(train_ev)}, test {len(test_ev)} (SUE 계산 가능분)
- SUE = NI YoY 변화 / 최근 8개 YoY 표준편차, filing 다음 거래일부터 반영
- CAR = 유니버스 동일가중 평균 대비 초과수익 누적, open-to-open

## SUE 5분위별 CAR (q5=최고 서프라이즈)
{markdown_table(qt, qcols)}

## 포트폴리오 백테스트 (filing 후 {HOLD_TD}거래일 보유)
{markdown_table(result.sort_values(["signal", "period", "cost_bps"]), pcols)}

## Caveats
- filing_date는 press release보다 1일~수주 늦음 — 실제 PEAD 대비 보수적(약하게) 측정.
- net_income 단일 지표 SUE. 애널리스트 컨센서스 서프라이즈 아님.
- PIT-lite 유니버스, 배당 제외 adj 가격. 공매도 비용 미반영.
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    t20 = result[(result["period"] == "test") & (result["cost_bps"] == 20)]
    return {"events": len(ev), "test_20bp": t20[["signal", "sharpe", "win_rate"]].to_dict("records")}


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
