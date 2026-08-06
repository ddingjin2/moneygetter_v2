"""FIRE 2040 몬테카를로 — 확정 포트(NDX50/SMH25/QLD25) 목표 달성 확률.

블록 부트스트랩(^NDX 1985~, ^SOX 1994~), 실질수익률(인플레 2.5% 차감), 세후 22%.
기준선 보수 원칙: 인센티브·절세계좌 미반영. 월 170만 고정 납입.

usage:
    python -m v2.fire.fire_mc                 # 확정 포트
    python -m v2.fire.fire_mc --sweep         # 대안 배분 비교
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

CACHE = ROOT / "v2/data/cache/fire"
PRICES = CACHE / "index_daily.parquet"

TICKERS = {"NDX": "^NDX", "SOX": "^SOX", "SPX": "^GSPC"}

# 확정 가정 (memory: fire-plan-2040)
SEED_KRW = 168_000_000
MONTHLY_KRW = 1_700_000
YEARS = 13.4
INFLATION = 0.025
CAP_GAINS_TAX = 0.22
N_PATHS = 2000
BLOCK_DAYS = 63  # 분기 블록 — 변동성 군집 보존
TRADING_DAYS = 252

# 레버리지 ETF 마찰: 일간 2배 리셋 + 차입비용 + 보수
LEV_FINANCING = 0.045  # 연 차입비용 (SOFR 근사)
LEV_EXPENSE = 0.0095  # QLD 총보수

PORTFOLIOS = {
    "NDX50/SMH25/QLD25": {"NDX": 0.50, "SOX": 0.25, "QLD": 0.25},
    "NDX100": {"NDX": 1.00},
    "NDX70/SOX30": {"NDX": 0.70, "SOX": 0.30},
    "SPX100": {"SPX": 1.00},
}

# 목표 총액 (집값 + 월 300만 배당@5%)
GOALS = {"시골 11.2억": 11.2e8, "수도권 16억": 16e8, "서울 22억": 22e8}
FLOOR = 6e8  # 심각미달 기준


def load_prices(refresh: bool = False) -> pd.DataFrame:
    """일간 종가. 캐시 없으면 yfinance 다운로드."""
    if PRICES.exists() and not refresh:
        return pd.read_parquet(PRICES)

    import yfinance as yf

    frames = {}
    for name, symbol in TICKERS.items():
        hist = yf.Ticker(symbol).history(period="max", auto_adjust=True)
        if hist.empty:
            raise RuntimeError(f"{symbol} 다운로드 실패")
        frames[name] = hist["Close"]
    px = pd.DataFrame(frames)
    px.index = pd.to_datetime(px.index).tz_localize(None).normalize()
    CACHE.mkdir(parents=True, exist_ok=True)
    px.to_parquet(PRICES)
    return px


def daily_returns(px: pd.DataFrame) -> pd.DataFrame:
    """일간 수익률 + QLD 합성(2x NDX 일간 리셋 - 차입 - 보수)."""
    ret = px.pct_change()
    drag = (LEV_FINANCING + LEV_EXPENSE) / TRADING_DAYS
    ret["QLD"] = 2.0 * ret["NDX"] - drag
    return ret


def block_bootstrap(ret: pd.DataFrame, n_paths: int, n_days: int, rng: np.random.Generator) -> np.ndarray:
    """열 간 상관 유지 위해 같은 시점 블록을 통째로 뽑음. (paths, days, assets)"""
    arr = ret.to_numpy()
    n_blocks = int(np.ceil(n_days / BLOCK_DAYS))
    max_start = len(arr) - BLOCK_DAYS
    starts = rng.integers(0, max_start, size=(n_paths, n_blocks))
    idx = starts[:, :, None] + np.arange(BLOCK_DAYS)[None, None, :]
    return arr[idx.reshape(n_paths, -1)[:, :n_days]]


def simulate(weights: dict[str, float], ret: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """세후 실질 최종자산 (원). 매월 적립, 연 1회 리밸런스."""
    cols = list(weights)
    w = np.array([weights[c] for c in cols])
    sub = ret[cols].dropna()

    n_days = int(YEARS * TRADING_DAYS)
    paths = block_bootstrap(sub, N_PATHS, n_days, rng)

    # 실질 전환: 일간 인플레 차감
    paths = paths - (INFLATION / TRADING_DAYS)

    # 자산별 잔고 (paths, assets). 매월 적립 후 연 1회 리밸런스.
    bal = SEED_KRW * w[None, :].repeat(N_PATHS, axis=0)
    contributed = float(SEED_KRW)
    month_len = TRADING_DAYS // 12

    for d in range(n_days):
        bal *= 1.0 + paths[:, d, :]
        if d % month_len == month_len - 1:
            bal += MONTHLY_KRW * w[None, :]
            contributed += MONTHLY_KRW
        if d % TRADING_DAYS == TRADING_DAYS - 1:
            total = bal.sum(axis=1, keepdims=True)
            bal = total * w[None, :]  # 리밸런스 (계좌 내 이동, 과세 미반영 = 낙관)

    final = bal.sum(axis=1)
    gain = np.maximum(final - contributed, 0.0)
    return final - gain * CAP_GAINS_TAX


def summarize(name: str, final: np.ndarray) -> dict:
    row = {"포트": name, "중앙값": f"{np.median(final) / 1e8:.1f}억", "하위10%": f"{np.percentile(final, 10) / 1e8:.1f}억"}
    for label, target in GOALS.items():
        row[label] = f"{(final >= target).mean() * 100:.0f}%"
    row["심각미달"] = f"{(final < FLOOR).mean() * 100:.0f}%"
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true", help="대안 배분까지 비교")
    ap.add_argument("--refresh", action="store_true", help="가격 재다운로드")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    ret = daily_returns(load_prices(refresh=args.refresh))
    rng = np.random.default_rng(args.seed)

    names = list(PORTFOLIOS) if args.sweep else ["NDX50/SMH25/QLD25"]
    rows = [summarize(n, simulate(PORTFOLIOS[n], ret, rng)) for n in names]

    print(f"\n시드 {SEED_KRW / 1e8:.2f}억 + 월 {MONTHLY_KRW / 1e4:.0f}만 x {YEARS}년, 실질·세후 {CAP_GAINS_TAX:.0%}, {N_PATHS}경로\n")
    print(pd.DataFrame(rows).to_markdown(index=False))


def demo() -> None:
    """자체 점검 — 부트스트랩 형상, 레버리지 드래그, 세후 단조성."""
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2000-01-01", periods=1000)
    fake = pd.DataFrame({"NDX": rng.normal(0.0004, 0.012, 1000), "SOX": rng.normal(0.0005, 0.018, 1000)}, index=idx)

    paths = block_bootstrap(fake, 50, 500, rng)
    assert paths.shape == (50, 500, 2), paths.shape

    # QLD 합성: 무변동 구간이면 2x 지수보다 반드시 낮아야 함 (차입+보수)
    flat = pd.DataFrame({"NDX": np.zeros(300), "SOX": np.zeros(300), "SPX": np.zeros(300)})
    assert daily_returns((1 + flat).cumprod())["QLD"].dropna().max() < 0, "레버리지 드래그 미반영"

    # 블록 통째로 뽑히므로 자산 간 동시점 상관 유지 (열 셔플 없음)
    row = paths[0, :BLOCK_DAYS, :]
    hits = [(fake.to_numpy()[s : s + BLOCK_DAYS] == row).all() for s in range(len(fake) - BLOCK_DAYS)]
    assert any(hits), "블록이 원본 연속 구간과 불일치"

    print("demo ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main()
