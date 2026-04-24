from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_KOSPI_UNIVERSE_PATH = Path(__file__).resolve().parents[1] / "data/cache/universe/kospi_universe.parquet"


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


def load_kospi_universe(
    path: str | Path = DEFAULT_KOSPI_UNIVERSE_PATH,
) -> pd.DataFrame:
    """Load the PR-7.A.2.a KOSPI common-stock universe index."""

    frame = pd.read_parquet(path).copy()
    for column in ("listed_date", "delisted_date"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    return frame.sort_values("code").reset_index(drop=True)


def get_active_universe(
    value: str | pd.Timestamp,
    universe: pd.DataFrame | None = None,
    *,
    path: str | Path = DEFAULT_KOSPI_UNIVERSE_PATH,
) -> list[str]:
    """Return point-in-time active codes from the PR-7.A.2.a universe index."""

    frame = load_kospi_universe(path) if universe is None else universe.copy()
    current = pd.Timestamp(value).normalize()
    frame["listed_date"] = pd.to_datetime(frame["listed_date"], errors="coerce")
    frame["delisted_date"] = pd.to_datetime(frame["delisted_date"], errors="coerce")

    active = frame.loc[
        (frame["listed_date"].isna() | (frame["listed_date"] <= current))
        & (frame["delisted_date"].isna() | (frame["delisted_date"] >= current)),
        "code",
    ]
    return sorted(active.astype(str).str.zfill(6).unique().tolist())
