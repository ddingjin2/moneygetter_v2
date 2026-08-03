from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OHLCV_PATH = ROOT / "data/processed/market_ohlcv.parquet"

REQUIRED_OHLCV_COLUMNS = [
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

OPTIONAL_OHLCV_COLUMNS = [
    "ticker",
    "market",
    "name",
    "turnover",
    "trading_value",
    "market_cap",
    "shares_outstanding",
    "source",
    "collected_at",
]

ORDERED_OHLCV_COLUMNS = [
    "date",
    "ticker",
    "symbol",
    "market",
    "name",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
    "trading_value",
    "market_cap",
    "shares_outstanding",
    "source",
    "collected_at",
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


def resolve_ohlcv_path(path: str | Path | None = None) -> Path:
    configured = path or os.environ.get("MONEYGETTER_V2_OHLCV_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_OHLCV_PATH


def normalize_ohlcv_frame(frame: pd.DataFrame, *, require_columns: Iterable[str] = REQUIRED_OHLCV_COLUMNS) -> pd.DataFrame:
    working = frame.copy()
    if "symbol" not in working.columns and "ticker" in working.columns:
        working["symbol"] = working["ticker"].astype(str)
    if "ticker" not in working.columns and "symbol" in working.columns:
        working["ticker"] = working["symbol"].astype(str)

    missing = [column for column in require_columns if column not in working.columns]
    if missing:
        raise ValueError(f"OHLCV frame is missing required columns: {missing}")

    working["date"] = pd.to_datetime(working["date"], errors="coerce").dt.normalize()
    working = working.dropna(subset=["date"])
    working["symbol"] = working["symbol"].astype(str).str.zfill(6)
    working["ticker"] = working["ticker"].astype(str).str.zfill(6)

    for column in ["open", "high", "low", "close", "volume", "turnover", "trading_value", "market_cap", "shares_outstanding"]:
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")

    if "trading_value" not in working.columns and "turnover" in working.columns:
        working["trading_value"] = working["turnover"]
    if "turnover" not in working.columns and "trading_value" in working.columns:
        working["turnover"] = working["trading_value"]
    if "name" not in working.columns:
        working["name"] = working["symbol"]
    if "market" not in working.columns:
        working["market"] = "UNKNOWN"
    if "source" not in working.columns:
        working["source"] = "unknown"
    if "collected_at" in working.columns:
        working["collected_at"] = pd.to_datetime(working["collected_at"], errors="coerce")

    ordered = [column for column in ORDERED_OHLCV_COLUMNS if column in working.columns]
    extras = [column for column in working.columns if column not in ordered]
    working = working.loc[:, ordered + extras]
    return working.drop_duplicates(["date", "symbol"], keep="last").sort_values(["date", "symbol"]).reset_index(drop=True)


def load_ohlcv(path: str | Path | None = None) -> pd.DataFrame:
    source = resolve_ohlcv_path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    if suffix == ".parquet":
        frame = pd.read_parquet(source)
    elif suffix == ".csv":
        frame = pd.read_csv(source)
    else:
        raise ValueError(f"Unsupported OHLCV file format: {source.suffix}")
    return normalize_ohlcv_frame(frame)


def save_ohlcv(frame: pd.DataFrame, path: str | Path | None = None) -> Path:
    target = resolve_ohlcv_path(path)
    atomic_write_parquet(normalize_ohlcv_frame(frame), target)
    return target


def merge_ohlcv(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        return normalize_ohlcv_frame(incoming)
    if incoming.empty:
        return normalize_ohlcv_frame(existing)
    return normalize_ohlcv_frame(pd.concat([existing, incoming], ignore_index=True))


def latest_ohlcv_date(path: str | Path | None = None) -> pd.Timestamp | None:
    source = resolve_ohlcv_path(path)
    if not source.exists():
        return None
    frame = pd.read_parquet(source, columns=["date"])
    if frame.empty:
        return None
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
    return pd.Timestamp(dates.max()).normalize() if not dates.empty else None
