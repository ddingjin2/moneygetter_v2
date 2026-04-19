from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


DEFAULT_V1_ROOT = Path("C:/dev/moneygetter")
DEFAULT_V1_OHLCV_PATH = Path("data/processed/market_ohlcv.parquet")


def resolve_v1_root(v1_root: str | Path | None = None) -> Path:
    """Resolve the read-only v1 project root used for shared market data."""

    configured = v1_root or os.environ.get("MONEYGETTER_V1_ROOT")
    return Path(configured) if configured else DEFAULT_V1_ROOT


def load_ohlcv(
    path: str | Path | None = None,
    *,
    v1_root: str | Path | None = None,
) -> pd.DataFrame:
    """Load OHLCV data from a v2 path or the read-only v1 data location.

    This wrapper intentionally does not mutate or import v1 strategy code. It
    only reads a tabular OHLCV file so v2 can share the established data store.
    """

    source = Path(path) if path is not None else resolve_v1_root(v1_root) / DEFAULT_V1_OHLCV_PATH
    if not source.exists():
        raise FileNotFoundError(source)

    suffix = source.suffix.lower()
    if suffix == ".parquet":
        frame = pd.read_parquet(source)
    elif suffix == ".csv":
        frame = pd.read_csv(source)
    else:
        raise ValueError(f"Unsupported OHLCV file format: {source.suffix}")

    if "date" in frame.columns:
        frame = frame.copy()
        frame["date"] = pd.to_datetime(frame["date"])
    if "symbol" not in frame.columns and "ticker" in frame.columns:
        frame = frame.copy()
        frame["symbol"] = frame["ticker"].astype(str)
    return frame

