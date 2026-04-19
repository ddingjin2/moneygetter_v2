from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from v2.signals.proximity import compute_daily_proximity
from v2.signals.sue_baseline import (
    SIGNAL_COLUMNS as BASELINE_SIGNAL_COLUMNS,
    _prepare_entry_universe,
    _top_quintile_by_day,
    default_nonmicrocap_filter,
    generate_signals as generate_sue_baseline_signals,
)


SIGNAL_COLUMNS = [
    "entry_date",
    "symbol",
    "signal_score",
    "sue_score",
    "proximity",
    "proximity_as_of_date",
    "tradable_entry_price",
]


def _all_event_candidates(
    earnings_events: pd.DataFrame,
    ohlcv: pd.DataFrame,
    universe_filter: Callable[[pd.DataFrame], pd.DataFrame],
) -> pd.DataFrame:
    required_events = {"stock_code", "tradable_entry_date"}
    missing_events = required_events - set(earnings_events.columns)
    if missing_events:
        raise KeyError(f"earnings_events is missing required columns: {sorted(missing_events)}")

    events = earnings_events.copy()
    events["entry_date"] = pd.to_datetime(events["tradable_entry_date"]).dt.normalize()
    events["symbol"] = events["stock_code"].astype(str).str.zfill(6)
    events["sue_score"] = pd.to_numeric(events["sue"], errors="coerce") if "sue" in events.columns else pd.NA
    events = events.loc[events["entry_date"].notna()].copy()
    if events.empty:
        return pd.DataFrame(columns=SIGNAL_COLUMNS)

    entry_universe = _prepare_entry_universe(ohlcv, universe_filter)
    prices = entry_universe.rename(columns={"date": "entry_date", "open": "tradable_entry_price"})
    candidates = events.merge(
        prices[["entry_date", "symbol", "tradable_entry_price"]],
        on=["entry_date", "symbol"],
        how="inner",
    )
    candidates = candidates.sort_values(["entry_date", "symbol", "sue_score"], ascending=[True, True, False])
    candidates = candidates.drop_duplicates(["entry_date", "symbol"], keep="first")
    candidates["signal_score"] = 0.0
    return candidates


def _previous_day_proximity(
    ohlcv: pd.DataFrame,
    *,
    lookback_days: int,
    precomputed_proximity: pd.DataFrame | None,
) -> pd.DataFrame:
    if precomputed_proximity is None:
        proximity = compute_daily_proximity(ohlcv, lookback_days=lookback_days)
    else:
        proximity = precomputed_proximity.copy()

    proximity["symbol"] = proximity["symbol"].astype(str).str.zfill(6)
    proximity["as_of_date"] = pd.to_datetime(proximity["as_of_date"]).dt.normalize()
    proximity["proximity"] = pd.to_numeric(proximity["proximity"], errors="coerce")
    proximity = proximity.sort_values(["symbol", "as_of_date"]).reset_index(drop=True)
    proximity["entry_date"] = proximity.groupby("symbol", sort=False)["as_of_date"].shift(-1)
    return proximity.rename(columns={"as_of_date": "proximity_as_of_date"})[
        ["symbol", "entry_date", "proximity_as_of_date", "proximity"]
    ]


def _attach_proximity(
    candidates: pd.DataFrame,
    ohlcv: pd.DataFrame,
    *,
    lookback_days: int,
    precomputed_proximity: pd.DataFrame | None,
) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=SIGNAL_COLUMNS)

    proximity = _previous_day_proximity(
        ohlcv,
        lookback_days=lookback_days,
        precomputed_proximity=precomputed_proximity,
    )
    frame = candidates.merge(proximity, on=["entry_date", "symbol"], how="left")
    return frame


def generate_signals(
    earnings_events: pd.DataFrame,
    ohlcv: pd.DataFrame,
    universe_filter: Callable[[pd.DataFrame], pd.DataFrame] = default_nonmicrocap_filter,
    proximity_threshold: float = 0.95,
    sue_top_quintile: bool = True,
    proximity_direction: str = "near",
    lookback_days: int = 252,
    precomputed_proximity: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Generate PR-4 proximity-conditioned signals.

    The SUE path reuses PR-3 top-quintile candidate selection unchanged, then
    filters candidates by prior-trading-day proximity. With sue_top_quintile
    disabled, earnings event timing is retained and proximity becomes the rank.
    """

    if proximity_direction not in {"near", "far"}:
        raise ValueError("proximity_direction must be 'near' or 'far'")

    if sue_top_quintile:
        baseline = generate_sue_baseline_signals(
            earnings_events=earnings_events,
            ohlcv=ohlcv,
            universe_filter=universe_filter,
        )
        if baseline.empty:
            return pd.DataFrame(columns=SIGNAL_COLUMNS)
        candidates = baseline.copy()
        candidates["sue_score"] = pd.to_numeric(candidates["signal_score"], errors="coerce")
    else:
        candidates = _all_event_candidates(earnings_events, ohlcv, universe_filter)

    frame = _attach_proximity(
        candidates,
        ohlcv,
        lookback_days=lookback_days,
        precomputed_proximity=precomputed_proximity,
    )
    frame = frame.loc[frame["proximity"].notna()].copy()
    if proximity_direction == "near":
        frame = frame.loc[frame["proximity"].ge(proximity_threshold)].copy()
    else:
        frame = frame.loc[frame["proximity"].le(proximity_threshold)].copy()

    if not sue_top_quintile:
        frame["signal_score"] = pd.to_numeric(frame["proximity"], errors="coerce")

    frame = frame.sort_values(["entry_date", "signal_score", "symbol"], ascending=[True, False, True])
    missing = [column for column in SIGNAL_COLUMNS if column not in frame.columns]
    for column in missing:
        frame[column] = pd.NA
    return frame[SIGNAL_COLUMNS].reset_index(drop=True)


def top_quintile_candidates(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """Test hook matching the PR-3 daily top-quintile selection."""

    if not set(BASELINE_SIGNAL_COLUMNS).issubset(frame.columns):
        return pd.DataFrame(columns=frame.columns)
    return _top_quintile_by_day(frame)
