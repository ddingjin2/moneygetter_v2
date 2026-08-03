from __future__ import annotations

from pathlib import Path
from typing import Iterable
import warnings

import numpy as np
import pandas as pd

REQUIRED_FUNDAMENTAL_COLUMNS = {
    "symbol",
    "fiscal_period_end",
    "filing_date",
    "gross_profit",
    "net_income",
    "total_assets",
    "total_liabilities",
}

SEC_FACT_MAP = {
    "gross_profit": ["GrossProfit"],
    "net_income": ["NetIncomeLoss"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
}


def normalize_fundamentals(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_FUNDAMENTAL_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"fundamentals missing required columns: {sorted(missing)}")
    out = frame.copy()
    out["symbol"] = out["symbol"].astype(str)
    out["fiscal_period_end"] = pd.to_datetime(out["fiscal_period_end"]).dt.normalize()
    out["filing_date"] = pd.to_datetime(out["filing_date"]).dt.normalize()
    for column in REQUIRED_FUNDAMENTAL_COLUMNS - {"symbol", "fiscal_period_end", "filing_date"}:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out.sort_values(["symbol", "filing_date", "fiscal_period_end"])


def load_fundamentals(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() == ".parquet":
        frame = pd.read_parquet(p)
    elif p.suffix.lower() in {".csv", ".txt"}:
        frame = pd.read_csv(p)
    else:
        raise ValueError(f"unsupported fundamentals file extension: {p.suffix}")
    return normalize_fundamentals(frame)


def _sec_fact_units(payload: dict, fact_names: list[str]) -> list[dict]:
    us_gaap = payload.get("facts", {}).get("us-gaap", {})
    for name in fact_names:
        fact = us_gaap.get(name)
        if not fact:
            continue
        units = fact.get("units", {})
        for unit_name in ("USD", "shares"):
            rows = units.get(unit_name)
            if rows:
                return rows
    return []


def extract_sec_companyfacts_fundamentals(symbol: str, payload: dict) -> pd.DataFrame:
    keyed: dict[tuple[pd.Timestamp, pd.Timestamp], dict[str, object]] = {}
    for output_column, fact_names in SEC_FACT_MAP.items():
        for row in _sec_fact_units(payload, fact_names):
            if row.get("form") not in {"10-Q", "10-K", "20-F", "40-F"}:
                continue
            if "end" not in row or "filed" not in row or "val" not in row:
                continue
            key = (pd.Timestamp(row["end"]).normalize(), pd.Timestamp(row["filed"]).normalize())
            current = keyed.setdefault(
                key,
                {
                    "symbol": str(symbol),
                    "fiscal_period_end": key[0],
                    "filing_date": key[1],
                    "gross_profit": np.nan,
                    "net_income": np.nan,
                    "total_assets": np.nan,
                    "total_liabilities": np.nan,
                },
            )
            current[output_column] = row.get("val")
    if not keyed:
        return pd.DataFrame(columns=sorted(REQUIRED_FUNDAMENTAL_COLUMNS))
    out = pd.DataFrame(keyed.values())
    return normalize_fundamentals(out)


def align_fundamentals_asof(
    fundamentals: pd.DataFrame,
    dates: Iterable[pd.Timestamp],
    symbols: Iterable[str],
) -> pd.DataFrame:
    data = normalize_fundamentals(fundamentals)
    date_index = pd.DatetimeIndex(pd.to_datetime(list(dates))).normalize().sort_values().unique()
    symbol_index = pd.Index([str(symbol) for symbol in symbols], name="symbol")
    pieces: list[pd.DataFrame] = []
    value_columns = [column for column in data.columns if column not in {"symbol", "filing_date"}]
    for symbol in symbol_index:
        rows = data.loc[data["symbol"].eq(symbol)].sort_values("filing_date")
        base = pd.DataFrame({"date": date_index})
        if rows.empty:
            aligned = base.assign(symbol=symbol)
            for column in value_columns:
                aligned[column] = np.nan
        else:
            aligned = pd.merge_asof(
                base,
                rows.drop(columns=["symbol"]),
                left_on="date",
                right_on="filing_date",
                direction="backward",
                allow_exact_matches=True,
            )
            aligned["symbol"] = symbol
        pieces.append(aligned)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        out = pd.concat(pieces, ignore_index=True)
    return out.set_index(["date", "symbol"]).sort_index()


def _cross_sectional_zscore(values: pd.Series) -> pd.Series:
    valid = values.astype("float64")
    if valid.notna().sum() == 0:
        return pd.Series(np.nan, index=values.index)
    std = valid.std(ddof=0)
    if not std or np.isnan(std):
        return pd.Series(np.where(valid.notna(), 0.0, np.nan), index=values.index)
    return (valid - valid.mean()) / std


def quality_score(aligned: pd.DataFrame) -> pd.Series:
    assets = aligned["total_assets"].replace(0.0, np.nan)
    factors = pd.DataFrame(index=aligned.index)
    factors["gross_profitability"] = aligned["gross_profit"] / assets
    factors["roa"] = aligned["net_income"] / assets
    factors["low_leverage"] = -(aligned["total_liabilities"] / assets)
    zscores = factors.groupby(level="date").transform(_cross_sectional_zscore)
    score = zscores.mean(axis=1)
    score.name = "quality_score"
    return score
