from __future__ import annotations

from collections.abc import Callable

import pandas as pd


SIGNAL_COLUMNS = ["entry_date", "symbol", "signal_score", "tradable_entry_price"]


def default_nonmicrocap_filter(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Exclude the bottom 20% by positive market cap for each trading date."""

    if "market_cap" not in ohlcv.columns:
        return ohlcv.copy()

    frame = ohlcv.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    valid = frame["market_cap"].gt(0)
    if not bool(valid.any()):
        return frame

    thresholds = frame.loc[valid].groupby("date")["market_cap"].transform(lambda values: values.quantile(0.20))
    keep_valid = frame.loc[valid].copy()
    keep_valid = keep_valid.loc[keep_valid["market_cap"] >= thresholds]
    keep_invalid = frame.loc[~valid].copy()
    return pd.concat([keep_valid, keep_invalid], ignore_index=True)


def _is_limit_up_bar(row: pd.Series) -> bool:
    previous_close = row.get("previous_close")
    if pd.isna(previous_close) or float(previous_close) <= 0:
        return False
    upper_limit = float(previous_close) * 1.30
    return float(row["open"]) >= upper_limit or float(row["high"]) >= upper_limit


def _prepare_entry_universe(
    ohlcv: pd.DataFrame,
    universe_filter: Callable[[pd.DataFrame], pd.DataFrame],
) -> pd.DataFrame:
    required = {"date", "symbol", "open", "high", "close"}
    missing = required - set(ohlcv.columns)
    if missing:
        raise KeyError(f"ohlcv is missing required columns: {sorted(missing)}")

    frame = ohlcv.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
    frame = frame.sort_values(["symbol", "date"])
    frame["previous_close"] = frame.groupby("symbol")["close"].shift(1)
    frame = universe_filter(frame)
    frame = frame.loc[pd.to_numeric(frame["open"], errors="coerce") >= 1000].copy()
    frame = frame.loc[~frame.apply(_is_limit_up_bar, axis=1)].copy()
    return frame


def _top_quintile_by_day(frame: pd.DataFrame) -> pd.DataFrame:
    selected: list[pd.DataFrame] = []
    for _, group in frame.groupby("entry_date", sort=True):
        group = group.sort_values("signal_score", ascending=False)
        cutoff_count = max(1, int((len(group) * 0.20 + 0.999999)))
        selected.append(group.head(cutoff_count))
    if not selected:
        return pd.DataFrame(columns=frame.columns)
    return pd.concat(selected, ignore_index=True)


def generate_signals(
    earnings_events: pd.DataFrame,
    ohlcv: pd.DataFrame,
    universe_filter: Callable[[pd.DataFrame], pd.DataFrame] = default_nonmicrocap_filter,
    rebalance_freq: str = "daily",
) -> pd.DataFrame:
    """
    Returns: [entry_date, symbol, signal_score (SUE), tradable_entry_price]
    """

    if rebalance_freq != "daily":
        raise ValueError("PR-3 baseline only supports daily rebalance_freq")

    required_events = {"stock_code", "tradable_entry_date", "sue"}
    missing_events = required_events - set(earnings_events.columns)
    if missing_events:
        raise KeyError(f"earnings_events is missing required columns: {sorted(missing_events)}")

    events = earnings_events.copy()
    events["entry_date"] = pd.to_datetime(events["tradable_entry_date"]).dt.normalize()
    events["symbol"] = events["stock_code"].astype(str).str.zfill(6)
    events["signal_score"] = pd.to_numeric(events["sue"], errors="coerce")
    events = events.loc[events["signal_score"].notna()].copy()
    if events.empty:
        return pd.DataFrame(columns=SIGNAL_COLUMNS)

    entry_universe = _prepare_entry_universe(ohlcv, universe_filter)
    prices = entry_universe.rename(columns={"date": "entry_date", "open": "tradable_entry_price"})
    merge_columns = ["entry_date", "symbol", "tradable_entry_price"]
    signals = events.merge(prices[merge_columns], on=["entry_date", "symbol"], how="inner")
    signals = signals.sort_values(["entry_date", "symbol", "signal_score"], ascending=[True, True, False])
    signals = signals.drop_duplicates(["entry_date", "symbol"], keep="first")
    signals = _top_quintile_by_day(signals)
    signals = signals.sort_values(["entry_date", "signal_score", "symbol"], ascending=[True, False, True])
    return signals[SIGNAL_COLUMNS].reset_index(drop=True)

