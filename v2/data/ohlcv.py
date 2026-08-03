from __future__ import annotations

from pathlib import Path

import pandas as pd

from v2.data.market_dataset import load_ohlcv as load_v2_ohlcv

DEFAULT_V1_ROOT = Path("C:/dev/moneygetter")
DEFAULT_V1_OHLCV_PATH = Path("data/processed/market_ohlcv.parquet")


def load_ohlcv(path: str | Path | None = None, *, v1_root: str | Path | None = None) -> pd.DataFrame:
    """Load canonical v2 OHLCV data by default.

    The v1 root argument is kept for old callers but is no longer used unless a
    concrete path is passed explicitly. v2 standalone operation should read
    `v2/data/processed/market_ohlcv.parquet`.
    """

    if v1_root is not None and path is None:
        path = Path(v1_root).expanduser() / DEFAULT_V1_OHLCV_PATH
    return load_v2_ohlcv(path)


def load_ohlcv_from_v1_legacy(v1_root: str | Path | None = None) -> pd.DataFrame:
    root = Path(v1_root).expanduser() if v1_root is not None else DEFAULT_V1_ROOT
    return load_v2_ohlcv(root / DEFAULT_V1_OHLCV_PATH)
