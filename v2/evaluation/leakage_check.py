from __future__ import annotations

from collections import defaultdict
from datetime import time
from typing import Dict, List

import pandas as pd


MARKET_CLOSE = time(15, 30)
LEAKAGE_TYPES = (
    "point_in_time",
    "earnings_after_close",
    "future_price",
    "universe_lookahead",
)


def _timestamp(value: object) -> pd.Timestamp | None:
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _trade_label(row: pd.Series, index: object) -> str:
    if "trade_id" in row and not pd.isna(row["trade_id"]):
        return str(row["trade_id"])
    symbol = str(row.get("symbol", index))
    entry = _timestamp(row.get("entry_date"))
    entry_text = entry.date().isoformat() if entry is not None else str(index)
    return f"{symbol}|{entry_text}"


def _append_once(violations: dict[str, list[str]], kind: str, label: str) -> None:
    if label not in violations[kind]:
        violations[kind].append(label)


def _feature_mentions_future_price(features_used: List[str]) -> bool:
    text = " ".join(feature.lower() for feature in features_used)
    future_token = any(token in text for token in ("future", "lookahead", "forward"))
    price_token = any(token in text for token in ("price", "close", "high", "low", "52w", "52_week"))
    return future_token and price_token


def check_leakage(
    ledger: pd.DataFrame,
    features_used: List[str],
) -> Dict[str, List[str]]:
    """Return leakage violations by type.

    Any non-empty list invalidates the associated backtest result.
    """

    if "entry_date" not in ledger.columns:
        raise KeyError("ledger is missing required column: entry_date")

    violations: dict[str, list[str]] = defaultdict(list)
    future_price_feature = _feature_mentions_future_price(features_used)

    point_in_time_columns = [
        "feature_available_at",
        "feature_available_date",
        "data_available_at",
        "data_available_date",
        "feature_asof_date",
        "asof_date",
    ]
    earnings_columns = [
        "earnings_announcement_at",
        "disclosure_datetime",
        "announcement_datetime",
    ]
    future_price_columns = [
        "high_52w_window_end",
        "price_window_end",
        "lookback_end_date",
        "rolling_window_end",
    ]
    universe_columns = [
        "universe_asof_date",
        "universe_filter_date",
        "market_cap_asof_date",
        "index_membership_asof_date",
    ]

    for index, row in ledger.iterrows():
        entry = _timestamp(row.get("entry_date"))
        if entry is None:
            continue
        label = _trade_label(row, index)

        for column in point_in_time_columns:
            if column in ledger.columns:
                available_at = _timestamp(row.get(column))
                if available_at is not None and available_at > entry:
                    _append_once(violations, "point_in_time", label)

        for column in earnings_columns:
            if column not in ledger.columns:
                continue
            announced_at = _timestamp(row.get(column))
            if announced_at is None:
                continue
            next_trade_date = _timestamp(row.get("next_trade_date")) if "next_trade_date" in ledger.columns else None
            if announced_at.time() > MARKET_CLOSE:
                required_entry = next_trade_date.normalize() if next_trade_date is not None else announced_at.normalize() + pd.Timedelta(days=1)
                if entry.normalize() < required_entry:
                    _append_once(violations, "earnings_after_close", label)

        if future_price_feature:
            _append_once(violations, "future_price", label)
        for column in future_price_columns:
            if column in ledger.columns:
                window_end = _timestamp(row.get(column))
                if window_end is not None and window_end.normalize() > entry.normalize():
                    _append_once(violations, "future_price", label)

        for column in universe_columns:
            if column in ledger.columns:
                universe_asof = _timestamp(row.get(column))
                if universe_asof is not None and universe_asof > entry:
                    _append_once(violations, "universe_lookahead", label)

    return {kind: violations.get(kind, []) for kind in LEAKAGE_TYPES}

