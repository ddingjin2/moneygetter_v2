from __future__ import annotations

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


PRICE_DIR = ROOT / "v2/data/cache/price_market_cap_full"
FLOW_DIR = ROOT / "v2/data/cache/investor_flow_full"
TRADING_STATUS_PATH = PRICE_DIR / "_trading_status.parquet"
KOSPI_PATH = ROOT / "v2/data/cache/benchmarks/kospi_daily_returns.parquet"
BASELINE_SIGNAL_PATH = ROOT / "v2/data/cache/signals/option_a_divergence_5d.parquet"
FORWARD_RETURNS_PATH = ROOT / "v2/data/cache/returns/forward_returns.parquet"
STEP6_IC_PATH = ROOT / "v2/data/cache/ic/ic_full_universe.parquet"
OUTPUT_DIR = ROOT / "v2/data/cache/signals_batch"
REPORT_PATH = ROOT / "v2/reports/pr7_a_X_step8_1_signal_catalog.md"

STEP6_A0_5D_IC = -0.0094
GREEN_ABS_DIFF_THRESHOLD = 0.0001


ComputeFunc = Callable[[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None], pd.Series]


@dataclass(frozen=True)
class SignalSpec:
    signal_id: str
    name: str
    formula_text: str
    compute_func: ComputeFunc
    requires_kospi: bool
    requires_flow: bool
    min_history_days: int
    expected_horizons: list[int]


def _safe_divide(numerator: pd.Series, denominator: pd.Series | float) -> pd.Series:
    result = numerator.astype("float64") / denominator
    return result.replace([np.inf, -np.inf], np.nan)


def _ret(close: pd.Series, periods: int) -> pd.Series:
    return close.astype("float64") / close.astype("float64").shift(periods) - 1.0


def _dvol(ohlcv: pd.DataFrame) -> pd.Series:
    if "trading_value" in ohlcv.columns:
        return pd.to_numeric(ohlcv["trading_value"], errors="coerce").astype("float64")
    return pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64") * pd.to_numeric(
        ohlcv["volume"], errors="coerce"
    ).astype("float64")


def _flow_total(flow: pd.DataFrame) -> pd.Series:
    foreign = pd.to_numeric(flow["foreign_net_buy_shares"], errors="coerce").astype("float64")
    institutional = pd.to_numeric(flow["institutional_net_buy_shares"], errors="coerce").astype("float64")
    return foreign + institutional


def _rolling_mean(series: pd.Series, window: int, min_periods: int | None = None) -> pd.Series:
    return series.rolling(window, min_periods=window if min_periods is None else min_periods).mean()


def _rolling_std(series: pd.Series, window: int, min_periods: int | None = None) -> pd.Series:
    return series.rolling(window, min_periods=window if min_periods is None else min_periods).std(ddof=0)


def _cs_z(frame: pd.DataFrame, value_column: str) -> pd.Series:
    grouped = frame.groupby("date", sort=False)[value_column]
    mean = grouped.transform("mean")
    std = grouped.transform(lambda values: values.std(ddof=0))
    z = (frame[value_column] - mean) / std.replace(0.0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)


def _own_z(series: pd.Series, window: int) -> pd.Series:
    denom = _rolling_std(series, window)
    return _safe_divide(series, denom)


def compute_a0_baseline(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if flow is None:
        raise ValueError("A0_baseline requires investor flow")
    foreign = pd.to_numeric(flow["foreign_net_buy_shares"], errors="coerce").astype("float64")
    institutional = pd.to_numeric(flow["institutional_net_buy_shares"], errors="coerce").astype("float64")
    return _rolling_mean(institutional, 5) - _rolling_mean(foreign, 5)


def compute_a1(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    close = pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64")
    return close.shift(21) / close.shift(252) - 1.0


def compute_a2(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    return -_ret(pd.to_numeric(ohlcv["close"], errors="coerce"), 21)


def compute_a3(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    close = pd.to_numeric(ohlcv["close"], errors="coerce")
    return -_rolling_std(close.pct_change(), 60)


def compute_a4(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    mean_dvol = _rolling_mean(_dvol(ohlcv).replace(0.0, np.nan), 60)
    return -np.log(mean_dvol)


def compute_a5(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    close = pd.to_numeric(ohlcv["close"], errors="coerce")
    dvol = _dvol(ohlcv).replace(0.0, np.nan)
    illiq = close.pct_change().abs() / dvol
    return _rolling_mean(illiq.replace([np.inf, -np.inf], np.nan), 60)


def compute_a6(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    close = pd.to_numeric(ohlcv["close"], errors="coerce")
    volume = pd.to_numeric(ohlcv["volume"], errors="coerce").astype("float64")
    base_volume = volume.shift(6).rolling(55, min_periods=55).mean()
    volume_shock = np.log(volume / base_volume.replace(0.0, np.nan))
    return -(close / close.shift(5) - 1.0) * volume_shock


def compute_a7(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    close = pd.to_numeric(ohlcv["close"], errors="coerce")
    volume = pd.to_numeric(ohlcv["volume"], errors="coerce").astype("float64")
    ret_20d = close / close.shift(20) - 1.0
    recent_volume = volume.rolling(5, min_periods=5).mean()
    prior_volume = volume.shift(5).rolling(20, min_periods=20).mean()
    volume_ratio_log = np.log(recent_volume / prior_volume.replace(0.0, np.nan))
    return ret_20d * volume_ratio_log


def compute_a8(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    open_ = pd.to_numeric(ohlcv["open"], errors="coerce").astype("float64")
    close = pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64")
    gap = open_ / close.shift(1) - 1.0
    intraday = close / open_.replace(0.0, np.nan) - 1.0
    return -(gap - intraday)


def compute_a9(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    close = pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64")
    high = pd.to_numeric(ohlcv["high"], errors="coerce").astype("float64")
    return close / high.rolling(252, min_periods=252).max()


def compute_a10(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if kospi is None:
        raise ValueError("A10 requires KOSPI returns")
    close = pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64")
    data = ohlcv[["date"]].copy()
    data["stock_ret"] = close.pct_change()
    data = data.merge(kospi[["date", "daily_return"]], on="date", how="left")
    stock_ret = data["stock_ret"].astype("float64")
    mkt_ret = data["daily_return"].astype("float64")
    beta = stock_ret.rolling(60, min_periods=60).cov(mkt_ret) / mkt_ret.rolling(60, min_periods=60).var(ddof=0)
    resid_5d = close / close.shift(5) - 1.0 - beta * ((1.0 + mkt_ret).rolling(5, min_periods=5).apply(np.prod, raw=True) - 1.0)
    return -resid_5d


def compute_b1(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if flow is None:
        raise ValueError("B1 requires investor flow")
    foreign = pd.to_numeric(flow["foreign_net_buy_shares"], errors="coerce").astype("float64")
    volume = pd.to_numeric(ohlcv["volume"], errors="coerce").astype("float64")
    close = pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64")
    foreign_flow_5d = foreign.rolling(5, min_periods=5).sum() / volume.rolling(5, min_periods=5).sum().replace(0.0, np.nan)
    return foreign_flow_5d - (close / close.shift(5) - 1.0)


def compute_b2(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if flow is None:
        raise ValueError("B2 requires investor flow")
    institutional = pd.to_numeric(flow["institutional_net_buy_shares"], errors="coerce").astype("float64")
    return (institutional > 0).astype("float64").rolling(20, min_periods=20).mean()


def compute_b3(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if flow is None:
        raise ValueError("B3 requires investor flow")
    total = _flow_total(flow)
    denom = _rolling_std(total, 60).shift(1)
    return _safe_divide(total, denom)


def compute_b4(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if flow is None:
        raise ValueError("B4 requires investor flow")
    total = _flow_total(flow)
    sign = np.sign(total)
    flip = (sign != sign.shift(1)).astype("float64")
    flip.loc[sign.isna() | sign.shift(1).isna()] = np.nan
    return -flip.rolling(19, min_periods=19).mean()


def compute_b5(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if flow is None:
        raise ValueError("B5 requires investor flow")
    foreign = pd.to_numeric(flow["foreign_net_buy_shares"], errors="coerce").astype("float64")
    institutional = pd.to_numeric(flow["institutional_net_buy_shares"], errors="coerce").astype("float64")
    volume = pd.to_numeric(ohlcv["volume"], errors="coerce").astype("float64")
    co_buy_10 = ((foreign > 0) & (institutional > 0)).astype("float64").rolling(10, min_periods=10).mean()
    positive_flow = foreign.clip(lower=0.0) + institutional.clip(lower=0.0)
    flow_intensity_10 = positive_flow.rolling(10, min_periods=10).sum() / volume.rolling(10, min_periods=10).sum().replace(
        0.0, np.nan
    )
    return co_buy_10 + flow_intensity_10


def compute_c1(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if flow is None:
        raise ValueError("C1 requires investor flow")
    abs_sum = (
        pd.to_numeric(flow["foreign_net_buy_shares"], errors="coerce").abs()
        + pd.to_numeric(flow["institutional_net_buy_shares"], errors="coerce").abs()
    ).astype("float64")
    q_small = abs_sum.expanding(min_periods=20).quantile(0.05).shift(1).fillna(0.0)
    silent = (abs_sum <= q_small).astype("float64")
    return -silent.rolling(20, min_periods=20).mean()


def compute_c2(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    close = pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64")
    ret_1d = close / close.shift(1) - 1.0
    signal = pd.Series(0.0, index=ohlcv.index)
    signal.loc[ret_1d >= 0.27] = 1.0
    signal.loc[ret_1d <= -0.27] = -1.0
    signal.loc[ret_1d.isna()] = np.nan
    return signal


def compute_c3(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if kospi is None:
        raise ValueError("C3 requires KOSPI returns")
    close = pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64")
    data = ohlcv[["date"]].copy()
    data["stock_ret"] = close.pct_change()
    data = data.merge(kospi[["date", "daily_return"]], on="date", how="left")
    stock_ret = data["stock_ret"].astype("float64")
    mkt_ret = data["daily_return"].astype("float64")
    beta = stock_ret.rolling(60, min_periods=60).cov(mkt_ret) / mkt_ret.rolling(60, min_periods=60).var(ddof=0)
    mkt_threshold = mkt_ret.expanding(min_periods=60).quantile(0.10).shift(1)
    stress_day = mkt_ret <= mkt_threshold
    residual = stock_ret - beta * mkt_ret
    residual.loc[~stress_day] = np.nan
    return residual


def compute_c4(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    dvol = _dvol(ohlcv).replace(0.0, np.nan)
    recent = dvol.rolling(5, min_periods=5).mean()
    base = dvol.shift(25).rolling(100, min_periods=100).mean()
    dvol_jump = np.log(recent / base)
    low_base = -np.log(base)
    return dvol_jump + low_base


def compute_c5(ohlcv: pd.DataFrame, flow: pd.DataFrame | None, kospi: pd.DataFrame | None) -> pd.Series:
    if kospi is None:
        raise ValueError("C5 requires KOSPI returns")
    close = pd.to_numeric(ohlcv["close"], errors="coerce").astype("float64")
    data = ohlcv[["date"]].copy()
    data["ret_1d"] = close.pct_change()
    data = data.merge(kospi[["date", "daily_return"]], on="date", how="left")
    stock_ret = data["ret_1d"].astype("float64")
    mkt_ret = data["daily_return"].astype("float64")
    mkt_threshold = mkt_ret.abs().expanding(min_periods=60).quantile(0.50).shift(1)
    anti_mkt = -np.sign(stock_ret * mkt_ret) * stock_ret.abs()
    anti_mkt.loc[mkt_ret.abs() < mkt_threshold] = np.nan
    return anti_mkt


SIGNAL_CATALOG: list[SignalSpec] = [
    SignalSpec(
        "A0_baseline",
        "Option A divergence_5d baseline",
        "divergence_5d = institutional_5d_mean - foreign_5d_mean",
        compute_a0_baseline,
        False,
        True,
        5,
        [5],
    ),
    SignalSpec("A1", "12-1개월 가격 모멘텀", "signal_A1(code,t) = cs_z_t(close_{t-21} / close_{t-252} - 1)", compute_a1, False, False, 252, [5, 21]),
    SignalSpec("A2", "1개월 단기 reversal", "signal_A2(code,t) = -cs_z_t(close_t / close_{t-21} - 1)", compute_a2, False, False, 21, [1, 5]),
    SignalSpec("A3", "저변동성 anomaly", "signal_A3(code,t) = -cs_z_t(std(ret_1d(code,t-59:t)))", compute_a3, False, False, 60, [21]),
    SignalSpec("A4", "거래대금 size proxy", "signal_A4(code,t) = -cs_z_t(log(mean(dvol(code,t-59:t))))", compute_a4, False, False, 60, [21]),
    SignalSpec(
        "A5",
        "Amihud illiquidity",
        "signal_A5(code,t) = cs_z_t(mean(abs(ret_1d(code,s)) / max(dvol(code,s), eps), s=t-59:t))",
        compute_a5,
        False,
        False,
        60,
        [21],
    ),
    SignalSpec(
        "A6",
        "거래량 충격 reversal",
        "signal_A6(code,t) = -cs_z_t(ret_5d(code,t) * log(volume_t / mean(volume_{t-60:t-6})))",
        compute_a6,
        False,
        False,
        60,
        [1, 5],
    ),
    SignalSpec(
        "A7",
        "가격-거래량 divergence",
        "signal_A7(code,t) = -cs_z_t(ret_20d(code,t) * (-cs_z_t(log(mean(volume_{t-4:t}) / mean(volume_{t-24:t-5})))))",
        compute_a7,
        False,
        False,
        25,
        [5, 21],
    ),
    SignalSpec(
        "A8",
        "overnight gap reversal proxy",
        "signal_A8(code,t) = -cs_z_t((open_t / close_{t-1} - 1) - (close_t / open_t - 1))",
        compute_a8,
        False,
        False,
        1,
        [1],
    ),
    SignalSpec("A9", "52주 고점 proximity", "signal_A9(code,t) = cs_z_t(close_t / max(high_{t-251:t}))", compute_a9, False, False, 252, [21]),
    SignalSpec(
        "A10",
        "시장 beta residual reversal",
        "signal_A10(code,t) = -cs_z_t(resid_5d)",
        compute_a10,
        True,
        False,
        60,
        [5],
    ),
    SignalSpec(
        "B1",
        "외국인 순매수 가격 비동조",
        "signal_B1(code,t) = cs_z_t(foreign_flow_5d) - cs_z_t(ret_5d(code,t))",
        compute_b1,
        False,
        True,
        5,
        [5, 21],
    ),
    SignalSpec("B2", "기관 순매수 consistency", "signal_B2(code,t) = cs_z_t(mean(1[institutional_net_buy_shares_s > 0], s=t-19:t))", compute_b2, False, True, 20, [5, 21]),
    SignalSpec(
        "B3",
        "수급 충격 대비 평소 수급 변동성",
        "signal_B3(code,t) = cs_z_t(flow_total_t / max(std(flow_total_{t-60:t-1}), eps))",
        compute_b3,
        False,
        True,
        60,
        [1, 5],
    ),
    SignalSpec(
        "B4",
        "수급 불확실성 penalty",
        "signal_B4(code,t) = -cs_z_t(flip_rate_20)",
        compute_b4,
        False,
        True,
        20,
        [5, 21],
    ),
    SignalSpec(
        "B5",
        "쌍방 순매수 concentration",
        "signal_B5(code,t) = cs_z_t(co_buy_10) + cs_z_t(flow_intensity_10)",
        compute_b5,
        False,
        True,
        10,
        [5, 21],
    ),
    SignalSpec(
        "C1",
        "무수급 침묵 후 가격 drift",
        "signal_C1(code,t) = -cs_z_t(mean(silent_day_s, s=t-19:t))",
        compute_c1,
        False,
        True,
        20,
        [5, 21],
    ),
    SignalSpec(
        "C2",
        "가격제한폭 근접 후 후유증",
        "signal_C2(code,t) = 1[ret_1d >= 0.27] - 1[ret_1d <= -0.27]",
        compute_c2,
        False,
        False,
        1,
        [1, 5],
    ),
    SignalSpec(
        "C3",
        "KOSPI 급락일 저항력",
        "signal_C3(code,t) = cs_z_t(ret_1d(code,t) - beta_60(code,t) * mkt_ret_1d(t)) on stress days",
        compute_c3,
        True,
        False,
        60,
        [5, 21],
    ),
    SignalSpec(
        "C4",
        "거래대금 regime jump",
        "signal_C4(code,t) = cs_z_t(dvol_jump) + cs_z_t(low_base)",
        compute_c4,
        False,
        False,
        125,
        [5, 21],
    ),
    SignalSpec(
        "C5",
        "유니버스 내부 동조 붕괴",
        "signal_C5(code,t) = cs_z_t(anti_mkt) where anti_mkt = -sign(ret_1d * mkt_ret_1d) * abs(ret_1d), defined only on days where abs(mkt_ret_1d(t)) >= expanding_median(abs(mkt_ret_1d), min_periods=60).shift(1); else NaN",
        compute_c5,
        True,
        False,
        60,
        [1, 5],
    ),
]


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_code_list() -> list[str]:
    codes = sorted(path.stem for path in PRICE_DIR.glob("*.parquet") if path.name[:6].isdigit() and len(path.stem) == 6)
    if len(codes) != 808:
        raise RuntimeError(f"Expected 808 stock parquet files, found {len(codes)}")
    return codes


def load_kospi() -> pd.DataFrame:
    frame = pd.read_parquet(KOSPI_PATH, columns=["date", "daily_return"])
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["daily_return"] = pd.to_numeric(frame["daily_return"], errors="coerce")
    return frame.sort_values("date").reset_index(drop=True)


def load_trading_status() -> pd.DataFrame:
    frame = pd.read_parquet(TRADING_STATUS_PATH, columns=["code", "date", "trading_halt"])
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["trading_halt"] = frame["trading_halt"].astype(bool)
    return frame


def load_stock_inputs(code: str, trading_status: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ohlcv = pd.read_parquet(PRICE_DIR / f"{code}.parquet")
    ohlcv["date"] = pd.to_datetime(ohlcv["date"]).dt.normalize()
    ohlcv = ohlcv.sort_values("date").reset_index(drop=True)
    ohlcv["code"] = code
    halted = trading_status.loc[trading_status["code"].eq(code), ["date", "trading_halt"]]
    ohlcv = ohlcv.merge(halted, on="date", how="left")
    ohlcv["trading_halt"] = ohlcv["trading_halt"].fillna(
        pd.to_numeric(ohlcv["volume"], errors="coerce").eq(0) & pd.to_numeric(ohlcv["open"], errors="coerce").eq(0)
    )
    mask = ohlcv["trading_halt"].astype(bool)
    numeric_cols = ["open", "high", "low", "close", "volume", "trading_value", "turnover"]
    for column in numeric_cols:
        if column in ohlcv.columns:
            ohlcv[column] = pd.to_numeric(ohlcv[column], errors="coerce").astype("float64")
            ohlcv.loc[mask, column] = np.nan

    flow = pd.read_parquet(FLOW_DIR / f"{code}.parquet")
    flow["date"] = pd.to_datetime(flow["date"]).dt.normalize()
    flow = flow.sort_values("date").reset_index(drop=True)
    flow["code"] = code
    for column in ["foreign_net_buy_shares", "institutional_net_buy_shares", "volume", "close"]:
        if column in flow.columns:
            flow[column] = pd.to_numeric(flow[column], errors="coerce").astype("float64")
            flow.loc[mask.reindex(flow.index, fill_value=False), column] = np.nan
    return ohlcv, flow


def compute_raw_signal(spec: SignalSpec, codes: list[str], trading_status: pd.DataFrame, kospi: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for code in codes:
        ohlcv, flow = load_stock_inputs(code, trading_status)
        raw = spec.compute_func(ohlcv, flow if spec.requires_flow else None, kospi if spec.requires_kospi else None)
        frame = pd.DataFrame({"code": code, "date": ohlcv["date"], "signal_value": raw.astype("float64")})
        frames.append(frame)
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    out["signal_value"] = out["signal_value"].replace([np.inf, -np.inf], np.nan)
    return out[["code", "date", "signal_value"]].sort_values(["code", "date"]).reset_index(drop=True)


def write_signal_outputs(spec: SignalSpec, raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    raw_path = OUTPUT_DIR / f"{spec.signal_id}.parquet"
    z_path = OUTPUT_DIR / f"{spec.signal_id}_cs_zscore.parquet"
    z = raw[["code", "date", "signal_value"]].copy()
    z["signal_cs_z"] = _cs_z(z, "signal_value")
    z = z[["code", "date", "signal_cs_z"]]
    atomic_write_parquet(raw, raw_path)
    atomic_write_parquet(z, z_path)
    stats = sanity_stats(spec, raw, z)
    return z, stats


def sanity_stats(spec: SignalSpec, raw: pd.DataFrame, z: pd.DataFrame) -> dict[str, object]:
    total_pairs = int(len(raw))
    non_nan = int(raw["signal_value"].notna().sum())
    z_non_nan = z["signal_cs_z"].dropna()
    date_dispersion = raw.groupby("date", sort=False)["signal_value"].std(ddof=0).replace([np.inf, -np.inf], np.nan)
    return {
        "signal_id": spec.signal_id,
        "name": spec.name,
        "total_pairs": total_pairs,
        "non_nan_count": non_nan,
        "non_nan_ratio": non_nan / total_pairs if total_pairs else math.nan,
        "cs_z_mean": float(z_non_nan.mean()) if len(z_non_nan) else math.nan,
        "cs_z_std": float(z_non_nan.std(ddof=0)) if len(z_non_nan) else math.nan,
        "cs_z_min": float(z_non_nan.min()) if len(z_non_nan) else math.nan,
        "cs_z_p01": float(z_non_nan.quantile(0.01)) if len(z_non_nan) else math.nan,
        "cs_z_p99": float(z_non_nan.quantile(0.99)) if len(z_non_nan) else math.nan,
        "cs_z_max": float(z_non_nan.max()) if len(z_non_nan) else math.nan,
        "mean_cross_section_dispersion": float(date_dispersion.mean()) if len(date_dispersion.dropna()) else math.nan,
        "min_history_days": spec.min_history_days,
        "expected_horizons": ",".join(str(h) for h in spec.expected_horizons),
        "requires_kospi": spec.requires_kospi,
        "requires_flow": spec.requires_flow,
    }


def baseline_regression_check(a0_z: pd.DataFrame) -> dict[str, object]:
    returns = pd.read_parquet(FORWARD_RETURNS_PATH, columns=["code", "date", "forward_return_5d", "ret_valid_5d"])
    returns["code"] = returns["code"].astype(str).str.zfill(6)
    returns["date"] = pd.to_datetime(returns["date"]).dt.normalize()
    merged = a0_z.merge(returns, on=["code", "date"], how="inner")
    valid = merged["signal_cs_z"].notna() & merged["forward_return_5d"].notna() & merged["ret_valid_5d"].astype(bool)
    per_date = []
    for date, group in merged.loc[valid].groupby("date", sort=True):
        if len(group) < 30:
            continue
        ic = group["signal_cs_z"].rank().corr(group["forward_return_5d"].rank())
        if pd.notna(ic):
            per_date.append({"date": date, "ic": float(ic), "n_valid": int(len(group))})
    ic_frame = pd.DataFrame(per_date)
    current_ic = float(ic_frame["ic"].mean()) if len(ic_frame) else math.nan
    diff = abs(current_ic - STEP6_A0_5D_IC) if pd.notna(current_ic) else math.nan
    status = "GREEN" if pd.notna(diff) and diff < GREEN_ABS_DIFF_THRESHOLD else "RED"
    step6 = pd.read_parquet(STEP6_IC_PATH)
    step6["date"] = pd.to_datetime(step6["date"]).dt.normalize()
    step6_5d_mean = float(step6.loc[step6["horizon"].eq("5d"), "ic"].mean())
    return {
        "status": status,
        "step6_prompt_5d_ic": STEP6_A0_5D_IC,
        "step6_cache_5d_ic": step6_5d_mean,
        "current_5d_ic": current_ic,
        "abs_diff_vs_prompt": diff,
        "n_dates": int(len(ic_frame)),
    }


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                values.append("NA" if math.isnan(value) else f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(sanity: pd.DataFrame, baseline_check: dict[str, object]) -> None:
    catalog_rows = [
        {
            "signal_id": spec.signal_id,
            "name": spec.name,
            "requires_flow": spec.requires_flow,
            "requires_kospi": spec.requires_kospi,
            "min_history_days": spec.min_history_days,
            "expected_horizons": ",".join(str(h) for h in spec.expected_horizons),
            "formula_text": spec.formula_text,
        }
        for spec in SIGNAL_CATALOG
    ]
    sanity_rows = sanity.to_dict("records")
    abnormal = sanity.loc[
        sanity["cs_z_mean"].abs().gt(1e-10)
        | sanity["cs_z_std"].sub(1.0).abs().gt(0.05)
        | sanity["cs_z_std"].isna()
    ]
    abnormal_text = "None" if abnormal.empty else ", ".join(abnormal["signal_id"].astype(str).tolist())
    text = f"""# PR-7.A.X Step 8.1 Signal Catalog

## Scope
- Step 8.1 only: common signal infrastructure and batch signal calculation.
- No hypothesis evaluation, ranking, backtest, or Step 8.2 batch IC measurement.
- C2 uses proxy coding: +1 if `ret_1d >= 0.27`, -1 if `ret_1d <= -0.27`, else 0.
- Trading halt masking reuses `v2/data/cache/price_market_cap_full/_trading_status.parquet`.

## Signal Catalog
{markdown_table(catalog_rows, ["signal_id", "name", "requires_flow", "requires_kospi", "min_history_days", "expected_horizons", "formula_text"])}

## Sanity Check
{markdown_table(sanity_rows, ["signal_id", "total_pairs", "non_nan_ratio", "cs_z_mean", "cs_z_std", "cs_z_min", "cs_z_p01", "cs_z_p99", "cs_z_max", "mean_cross_section_dispersion"])}

## A0_baseline Regression Check
- Status: {baseline_check["status"]}
- Step 6 prompt 5d IC: {baseline_check["step6_prompt_5d_ic"]:.6f}
- Step 6 cache 5d IC: {baseline_check["step6_cache_5d_ic"]:.6f}
- Current 5d IC: {baseline_check["current_5d_ic"]:.6f}
- Absolute diff vs prompt: {baseline_check["abs_diff_vs_prompt"]:.6f}
- IC dates: {baseline_check["n_dates"]}
- GREEN rule: absolute diff vs prompt < {GREEN_ABS_DIFF_THRESHOLD:.6f}

## Step 8.2 Readiness
- Signals written: 20 raw parquet files and 20 cross-sectional z-score parquet files under `v2/data/cache/signals_batch/`.
- Sanity abnormal items: {abnormal_text}
- If A0_baseline status is RED, stop before Step 8.2 and inspect baseline regression mismatch.
"""
    atomic_write_text(text, REPORT_PATH)


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    codes = load_code_list()
    trading_status = load_trading_status()
    kospi = load_kospi()
    sanity_rows = []
    a0_z: pd.DataFrame | None = None
    for spec in SIGNAL_CATALOG:
        raw_path = OUTPUT_DIR / f"{spec.signal_id}.parquet"
        z_path = OUTPUT_DIR / f"{spec.signal_id}_cs_zscore.parquet"
        if raw_path.exists() and z_path.exists():
            raw = pd.read_parquet(raw_path)
            z = pd.read_parquet(z_path)
            stats = sanity_stats(spec, raw, z)
        else:
            raw = compute_raw_signal(spec, codes, trading_status, kospi)
            z, stats = write_signal_outputs(spec, raw)
        sanity_rows.append(stats)
        if spec.signal_id == "A0_baseline":
            a0_z = z
    sanity = pd.DataFrame(sanity_rows)
    if a0_z is None:
        raise RuntimeError("A0_baseline was not computed")
    baseline_check = baseline_regression_check(a0_z)
    sanity["a0_regression_status"] = baseline_check["status"]
    sanity["a0_current_5d_ic"] = baseline_check["current_5d_ic"]
    sanity["a0_abs_diff_vs_step6_prompt"] = baseline_check["abs_diff_vs_prompt"]
    atomic_write_parquet(sanity, OUTPUT_DIR / "_sanity_check.parquet")
    write_report(sanity, baseline_check)
    return {
        "signals": len(SIGNAL_CATALOG),
        "total_pairs_per_signal": int(sanity["total_pairs"].iloc[0]),
        "mean_non_nan_ratio": float(sanity["non_nan_ratio"].mean()),
        "baseline_check": baseline_check,
        "abnormal": sanity.loc[
            sanity["cs_z_mean"].abs().gt(1e-10)
            | sanity["cs_z_std"].sub(1.0).abs().gt(0.05)
            | sanity["cs_z_std"].isna()
        ]["signal_id"].tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute PR-7.A.X Step 8.1 batch hypothesis signals.")
    parser.add_argument("--run", action="store_true", help="Compute and write all Step 8.1 outputs.")
    args = parser.parse_args()
    if not args.run:
        print(f"catalog_size={len(SIGNAL_CATALOG)}")
        for spec in SIGNAL_CATALOG:
            print(spec.signal_id)
        return
    result = run()
    print(result)


if __name__ == "__main__":
    main()
