from __future__ import annotations

import pandas as pd


def filter_nonmicrocap(
    universe: pd.DataFrame,
    *,
    market_cap_column: str = "market_cap",
    date_column: str | None = "date",
    bottom_quantile: float = 0.20,
) -> pd.DataFrame:
    """Exclude the bottom market-cap quantile using point-in-time rows only.

    If a date column is present, the bottom 20% threshold is computed separately
    for each date so later market-cap information cannot affect earlier dates.
    """

    if market_cap_column not in universe.columns:
        raise KeyError(f"Missing market-cap column: {market_cap_column}")
    if not 0 <= bottom_quantile < 1:
        raise ValueError("bottom_quantile must be in the [0, 1) range")

    frame = universe.copy()
    if date_column and date_column in frame.columns:
        frame[date_column] = pd.to_datetime(frame[date_column])
        threshold = frame.groupby(date_column)[market_cap_column].transform(
            lambda values: values.quantile(bottom_quantile)
        )
    else:
        threshold = frame[market_cap_column].quantile(bottom_quantile)

    return frame.loc[frame[market_cap_column] >= threshold].copy()

