from __future__ import annotations

import pandas as pd

DATE_COLUMN = "날짜"
OPEN_COLUMN = "시가"
HIGH_COLUMN = "고가"
LOW_COLUMN = "저가"
CLOSE_COLUMN = "종가"
VOLUME_COLUMN = "거래량"
TURNOVER_COLUMN = "거래대금"
MARKET_CAP_COLUMN = "시가총액"
SHARES_OUTSTANDING_COLUMN = "상장주식수"

COLUMN_MAP = {
    DATE_COLUMN: "date",
    "date": "date",
    "ticker": "ticker",
    "symbol": "ticker",
    "market": "market",
    "name": "name",
    OPEN_COLUMN: "open",
    HIGH_COLUMN: "high",
    LOW_COLUMN: "low",
    CLOSE_COLUMN: "close",
    VOLUME_COLUMN: "volume",
    TURNOVER_COLUMN: "turnover",
    MARKET_CAP_COLUMN: "market_cap",
    SHARES_OUTSTANDING_COLUMN: "shares_outstanding",
    "source": "source",
    "collected_at": "collected_at",
}

ORDERED_COLUMNS = [
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


def clean_ohlcv(raw_df: pd.DataFrame, ticker: str, market: str | None = None, name: str | None = None) -> pd.DataFrame:
    if raw_df.empty:
        raise ValueError(f"raw_df is empty for ticker {ticker}")

    working = raw_df.copy().rename(columns=COLUMN_MAP)
    missing = {"date", "open", "high", "low", "close", "volume"} - set(working.columns)
    if missing:
        raise ValueError(f"raw_df is missing columns after rename: {sorted(missing)}")

    working["date"] = pd.to_datetime(working["date"], errors="raise").dt.normalize()
    working["ticker"] = str(ticker).zfill(6)
    working["symbol"] = working["ticker"]
    working["market"] = str(market or working.get("market", "UNKNOWN"))
    if "name" not in working.columns or working["name"].isna().all():
        working["name"] = name or working["ticker"]
    else:
        working["name"] = working["name"].fillna(name or working["ticker"])

    if "turnover" not in working.columns:
        working["turnover"] = pd.NA
    if "trading_value" not in working.columns:
        working["trading_value"] = working["turnover"]
    if "market_cap" not in working.columns:
        working["market_cap"] = pd.NA
    if "shares_outstanding" not in working.columns:
        working["shares_outstanding"] = pd.NA
    if "source" not in working.columns:
        working["source"] = "pykrx"
    if "collected_at" not in working.columns:
        working["collected_at"] = pd.Timestamp.utcnow().tz_localize(None)

    for column in ["open", "high", "low", "close", "volume", "turnover", "trading_value", "market_cap", "shares_outstanding"]:
        working[column] = pd.to_numeric(working[column], errors="coerce")

    halted_mask = (
        (working["open"] == 0)
        & (working["high"] == 0)
        & (working["low"] == 0)
        & (working["close"] > 0)
        & (working["volume"] == 0)
    )
    if bool(halted_mask.any()):
        for column in ["open", "high", "low"]:
            working.loc[halted_mask, column] = working.loc[halted_mask, "close"]

    working["high"] = working[["open", "high", "low", "close"]].max(axis=1)
    working["low"] = working[["open", "high", "low", "close"]].min(axis=1)
    return working.loc[:, ORDERED_COLUMNS].drop_duplicates(["date", "symbol"], keep="last").sort_values(["date", "symbol"]).reset_index(drop=True)
