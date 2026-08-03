from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd

from v2.data.us_schema import normalize_us_ohlcv, normalize_us_universe

ROOT = Path(__file__).resolve().parents[1]
US_DEFAULT_UNIVERSE_KEY = "sp500"
US_CACHE_ROOT = ROOT / "data/cache/us"
US_OHLCV_PATH = ROOT / "data/processed/us_market_ohlcv.parquet"
US_UNIVERSE_PATH = US_CACHE_ROOT / "universe/us_universe.parquet"


def normalize_universe_key(universe_key: str | None = None) -> str:
    return (universe_key or US_DEFAULT_UNIVERSE_KEY).strip().lower().replace("-", "_")


def us_universe_path(universe_key: str | None = None) -> Path:
    key = normalize_universe_key(universe_key)
    if key == US_DEFAULT_UNIVERSE_KEY:
        return US_UNIVERSE_PATH
    return US_CACHE_ROOT / key / "universe/us_universe.parquet"


def us_ohlcv_path(universe_key: str | None = None) -> Path:
    key = normalize_universe_key(universe_key)
    if key == US_DEFAULT_UNIVERSE_KEY:
        return US_OHLCV_PATH
    return ROOT / f"data/processed/us_{key}_ohlcv.parquet"


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


def save_us_universe(frame: pd.DataFrame, path: Path | None = None, universe_key: str | None = None) -> Path:
    target = path or us_universe_path(universe_key)
    atomic_write_parquet(normalize_us_universe(frame), target)
    return target


def load_us_universe(path: Path | None = None, universe_key: str | None = None) -> pd.DataFrame:
    return normalize_us_universe(pd.read_parquet(path or us_universe_path(universe_key)))


def merge_us_ohlcv(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        return normalize_us_ohlcv(incoming)
    if incoming.empty:
        return normalize_us_ohlcv(existing)
    return normalize_us_ohlcv(pd.concat([existing, incoming], ignore_index=True))


def save_us_ohlcv(frame: pd.DataFrame, path: Path | None = None, universe_key: str | None = None) -> Path:
    target = path or us_ohlcv_path(universe_key)
    atomic_write_parquet(normalize_us_ohlcv(frame), target)
    return target


def load_us_ohlcv(path: Path | None = None, universe_key: str | None = None) -> pd.DataFrame:
    return normalize_us_ohlcv(pd.read_parquet(path or us_ohlcv_path(universe_key)))


def latest_us_ohlcv_date(path: Path | None = None, universe_key: str | None = None) -> pd.Timestamp | None:
    target = path or us_ohlcv_path(universe_key)
    if not target.exists():
        return None
    frame = pd.read_parquet(target, columns=["date"])
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
    return pd.Timestamp(dates.max()).normalize() if not dates.empty else None
