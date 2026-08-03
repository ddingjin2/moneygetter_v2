from __future__ import annotations

from typing import Iterable

import pandas as pd

US_UNIVERSE_COLUMNS = [
    "symbol",
    "name",
    "exchange",
    "security_type",
    "currency",
    "country",
    "active_start_date",
    "active_end_date",
    "is_current_member",
    "source",
    "collected_at",
]

US_OHLCV_COLUMNS = [
    "date",
    "symbol",
    "exchange",
    "name",
    "open",
    "high",
    "low",
    "close",
    "adj_open",
    "adj_high",
    "adj_low",
    "adj_close",
    "volume",
    "dollar_volume",
    "split_factor",
    "dividend",
    "source",
    "collected_at",
    "adjustment_quality",
]


def _require(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"US frame is missing required columns: {missing}")


def normalize_symbol(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().str.replace(".", "-", regex=False)


def normalize_us_universe(frame: pd.DataFrame) -> pd.DataFrame:
    _require(frame, ["symbol", "name", "exchange", "security_type", "active_start_date"])
    out = frame.copy()
    out["symbol"] = normalize_symbol(out["symbol"])
    out["exchange"] = out["exchange"].astype(str).str.strip().str.upper()
    out["name"] = out["name"].astype(str).str.strip()
    out["security_type"] = out["security_type"].astype(str).str.strip().str.lower()
    out["active_start_date"] = pd.to_datetime(out["active_start_date"], errors="coerce").dt.normalize()
    if "active_end_date" not in out.columns:
        out["active_end_date"] = pd.NaT
    out["active_end_date"] = pd.to_datetime(out["active_end_date"].replace("", pd.NA), errors="coerce").dt.normalize()
    if "currency" not in out.columns:
        out["currency"] = "USD"
    if "country" not in out.columns:
        out["country"] = "US"
    if "is_current_member" not in out.columns:
        out["is_current_member"] = out["active_end_date"].isna()
    if "source" not in out.columns:
        out["source"] = "unknown"
    if "collected_at" not in out.columns:
        out["collected_at"] = pd.Timestamp.now(tz="UTC")
    else:
        out["collected_at"] = pd.to_datetime(out["collected_at"], errors="coerce")
    ordered = [column for column in US_UNIVERSE_COLUMNS if column in out.columns]
    return out[ordered].dropna(subset=["symbol"]).drop_duplicates("symbol", keep="last").sort_values("symbol").reset_index(drop=True)


def normalize_us_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    _require(frame, ["date", "symbol", "open", "high", "low", "close", "volume"])
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.normalize()
    out["symbol"] = normalize_symbol(out["symbol"])
    for column in ["open", "high", "low", "close", "adj_open", "adj_high", "adj_low", "adj_close", "volume", "split_factor", "dividend"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    for column in ["adj_open", "adj_high", "adj_low", "adj_close", "split_factor", "dividend"]:
        if column not in out.columns:
            out[column] = pd.NA
    if "exchange" not in out.columns:
        out["exchange"] = "UNKNOWN"
    if "name" not in out.columns:
        out["name"] = out["symbol"]
    if "source" not in out.columns:
        out["source"] = "unknown"
    if "collected_at" not in out.columns:
        out["collected_at"] = pd.Timestamp.now(tz="UTC")
    else:
        out["collected_at"] = pd.to_datetime(out["collected_at"], errors="coerce")
    out["dollar_volume"] = pd.to_numeric(out["close"], errors="coerce") * pd.to_numeric(out["volume"], errors="coerce")
    out["adjustment_quality"] = out["adj_open"].notna().map({True: "adjusted_open_available", False: "raw_open_only"})
    ordered = [column for column in US_OHLCV_COLUMNS if column in out.columns]
    return (
        out[ordered]
        .dropna(subset=["date", "symbol"])
        .drop_duplicates(["date", "symbol"], keep="last")
        .sort_values(["symbol", "date"])
        .reset_index(drop=True)
    )
