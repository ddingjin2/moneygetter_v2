from __future__ import annotations

import pandas as pd


PROXIMITY_COLUMNS = [
    "symbol",
    "as_of_date",
    "proximity",
    "past_high_date",
    "past_high_value",
    "past_high_age_days",
]


def _prepare_ohlcv(ohlcv: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "symbol", "high", "close"}
    missing = required - set(ohlcv.columns)
    if missing:
        raise KeyError(f"ohlcv is missing required columns: {sorted(missing)}")

    frame = ohlcv[list(required)].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
    frame["high"] = pd.to_numeric(frame["high"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.loc[frame["date"].notna() & frame["symbol"].notna()].copy()
    return frame.sort_values(["symbol", "date"]).reset_index(drop=True)


def compute_proximity(
    ohlcv: pd.DataFrame,
    as_of_date: pd.Timestamp,
    lookback_days: int = 252,
) -> pd.DataFrame:
    """
    Compute current close divided by the trailing 52-week high.

    Point-in-time contract:
      - Uses only rows with date <= as_of_date.
      - Uses the last `lookback_days` trading observations per symbol.
      - Returns NaN proximity for symbols without a full lookback window.
    """

    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")

    as_of = pd.Timestamp(as_of_date).normalize()
    frame = _prepare_ohlcv(ohlcv)
    frame = frame.loc[frame["date"].le(as_of)].copy()
    if frame.empty:
        return pd.DataFrame(columns=PROXIMITY_COLUMNS)

    current = frame.groupby("symbol", sort=False).tail(1).copy()
    rows: list[dict[str, object]] = []
    for row in current.itertuples(index=False):
        symbol = str(row.symbol)
        history = frame.loc[frame["symbol"].eq(symbol)].tail(lookback_days)
        result: dict[str, object] = {
            "symbol": symbol,
            "as_of_date": as_of,
            "proximity": float("nan"),
            "past_high_date": pd.NaT,
            "past_high_value": float("nan"),
            "past_high_age_days": float("nan"),
        }
        if len(history) < lookback_days:
            rows.append(result)
            continue

        highs = pd.to_numeric(history["high"], errors="coerce")
        if highs.isna().all() or pd.isna(row.close):
            rows.append(result)
            continue

        high_value = float(highs.max())
        if high_value <= 0:
            rows.append(result)
            continue

        high_rows = history.loc[highs.eq(high_value)]
        high_date = pd.Timestamp(high_rows.iloc[-1]["date"]).normalize()
        result.update(
            {
                "proximity": float(row.close) / high_value,
                "past_high_date": high_date,
                "past_high_value": high_value,
                "past_high_age_days": int((as_of - high_date).days),
            }
        )
        rows.append(result)

    return pd.DataFrame(rows, columns=PROXIMITY_COLUMNS)


def compute_daily_proximity(ohlcv: pd.DataFrame, lookback_days: int = 252) -> pd.DataFrame:
    """Compute trailing-high proximity for every available symbol/date row."""

    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")

    frame = _prepare_ohlcv(ohlcv)
    if frame.empty:
        return pd.DataFrame(columns=["symbol", "as_of_date", "proximity"])

    rolling_high = (
        frame.groupby("symbol", sort=False)["high"]
        .rolling(window=lookback_days, min_periods=lookback_days)
        .max()
        .reset_index(level=0, drop=True)
    )
    frame["proximity"] = frame["close"] / rolling_high
    return frame.rename(columns={"date": "as_of_date"})[["symbol", "as_of_date", "proximity"]]
