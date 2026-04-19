from __future__ import annotations

import ast
from pathlib import Path
from typing import Callable

import pandas as pd


KOSPI_TICKER = "1001"
DEFAULT_START = "20200101"
DEFAULT_END = "20260417"
DEFAULT_CACHE_PATH = Path("v2/data/cache/kospi_daily.parquet")
KOSPI_COLUMNS = ["date", "open", "high", "low", "close", "volume", "returns"]


def _normalize_kospi_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=KOSPI_COLUMNS)

    data = frame.copy()
    if "date" not in data.columns:
        data = data.reset_index()
    if "날짜" in data.columns and "date" not in data.columns:
        data = data.rename(columns={"날짜": "date"})
    if data.columns[0] not in {"date", "날짜"} and "date" not in data.columns:
        data = data.rename(columns={data.columns[0]: "date"})

    rename_map = {
        "시가": "open",
        "고가": "high",
        "저가": "low",
        "종가": "close",
        "거래량": "volume",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    data = data.rename(columns=rename_map)

    missing = {"date", "open", "high", "low", "close", "volume"} - set(data.columns)
    if missing:
        raise ValueError(f"Missing KOSPI columns after normalization: {sorted(missing)}")

    data = data[["date", "open", "high", "low", "close", "volume"]].copy()
    data["date"] = pd.to_datetime(data["date"]).dt.normalize()
    for column in ["open", "high", "low", "close", "volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date")
    data = data.drop_duplicates("date", keep="last").reset_index(drop=True)
    data["returns"] = data["close"].pct_change()
    return data[KOSPI_COLUMNS]


def _fetch_naver_kospi_daily(start: str, end: str, ticker: str) -> pd.DataFrame:
    if ticker != KOSPI_TICKER:
        raise ValueError(f"Naver fallback only supports KOSPI ticker {KOSPI_TICKER}")

    import requests

    response = requests.get(
        "https://api.finance.naver.com/siseJson.naver",
        params={
            "symbol": "KOSPI",
            "requestType": "1",
            "startTime": start,
            "endTime": end,
            "timeframe": "day",
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    payload = ast.literal_eval(response.text.strip())
    if len(payload) <= 1:
        return pd.DataFrame(columns=KOSPI_COLUMNS)

    header = payload[0]
    rows = payload[1:]
    return pd.DataFrame(rows, columns=header)


def fetch_kospi_daily(
    *,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    ticker: str = KOSPI_TICKER,
    fetcher: Callable[[str, str, str], pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Fetch KOSPI composite index daily OHLCV from pykrx."""

    if fetcher is not None:
        return _normalize_kospi_frame(fetcher(start, end, ticker))

    try:
        from pykrx import stock

        fetcher = lambda start_date, end_date, index_ticker: stock.get_index_ohlcv_by_date(  # noqa: E731
            start_date,
            end_date,
            index_ticker,
            name_display=False,
        )
        data = _normalize_kospi_frame(fetcher(start, end, ticker))
    except Exception:
        data = pd.DataFrame(columns=KOSPI_COLUMNS)

    if data.empty:
        data = _normalize_kospi_frame(_fetch_naver_kospi_daily(start, end, ticker))
    return data


def load_or_fetch_kospi_daily(
    *,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    force_refresh: bool = False,
    fetcher: Callable[[str, str, str], pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Load cached KOSPI daily data, or fetch once and cache it."""

    path = Path(cache_path)
    if path.exists() and not force_refresh:
        data = pd.read_parquet(path)
        data["date"] = pd.to_datetime(data["date"]).dt.normalize()
        return data[KOSPI_COLUMNS].sort_values("date").reset_index(drop=True)

    data = fetch_kospi_daily(start=start, end=end, fetcher=fetcher)
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(path, index=False)
    return data
