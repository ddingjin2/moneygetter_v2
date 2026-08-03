from __future__ import annotations

import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Protocol

import pandas as pd

from v2.data.us_schema import normalize_symbol, normalize_us_ohlcv, normalize_us_universe


class UsMarketDataProvider(Protocol):
    def fetch_universe(self) -> pd.DataFrame:
        ...

    def fetch_daily_bars(self, symbols: list[str], start: str, end: str | None) -> pd.DataFrame:
        ...


@dataclass(frozen=True)
class CsvLocalUsProvider:
    raw_universe_csv: str | Path
    raw_ohlcv_dir: str | Path

    def fetch_universe(self) -> pd.DataFrame:
        frame = pd.read_csv(self.raw_universe_csv)
        return normalize_us_universe(frame)

    def fetch_daily_bars(self, symbols: list[str], start: str, end: str | None) -> pd.DataFrame:
        start_ts = pd.Timestamp(start).normalize()
        end_ts = pd.Timestamp(end).normalize() if end else pd.Timestamp.max.normalize()
        frames: list[pd.DataFrame] = []
        base = Path(self.raw_ohlcv_dir)
        for symbol in normalize_symbol(pd.Series(symbols)).tolist():
            path = base / f"{symbol}.csv"
            if not path.exists():
                continue
            frame = pd.read_csv(path)
            frame["symbol"] = symbol
            frame = normalize_us_ohlcv(frame)
            frame = frame.loc[pd.to_datetime(frame["date"]).between(start_ts, end_ts)]
            frames.append(frame)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


@dataclass(frozen=True)
class YFinanceSp500Provider:
    universe_url: str = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    batch_size: int = 60
    pause_seconds: float = 0.2

    def fetch_universe(self) -> pd.DataFrame:
        import requests

        response = requests.get(self.universe_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        raw = tables[0].rename(columns={"Symbol": "symbol", "Security": "name", "GICS Sector": "sector"})
        frame = pd.DataFrame(
            {
                "symbol": raw["symbol"].astype(str).str.replace(".", "-", regex=False),
                "name": raw["name"],
                "exchange": "UNKNOWN",
                "security_type": "common_stock",
                "active_start_date": "2000-01-01",
                "active_end_date": pd.NA,
                "is_current_member": True,
                "source": "wikipedia_sp500_current",
            }
        )
        return normalize_us_universe(frame)

    def fetch_daily_bars(self, symbols: list[str], start: str, end: str | None) -> pd.DataFrame:
        try:
            import yfinance as yf  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("yfinance is required for provider=yfinance_sp500. Install with: python -m pip install yfinance") from exc

        norm_symbols = normalize_symbol(pd.Series(symbols)).tolist()
        frames: list[pd.DataFrame] = []
        yf_symbols = [symbol.replace("-", ".") for symbol in norm_symbols]
        for offset in range(0, len(yf_symbols), self.batch_size):
            batch_yf = yf_symbols[offset : offset + self.batch_size]
            batch_norm = norm_symbols[offset : offset + self.batch_size]
            data = yf.download(
                tickers=" ".join(batch_yf),
                start=start,
                end=end,
                auto_adjust=False,
                actions=True,
                group_by="ticker",
                progress=False,
                threads=True,
            )
            if data.empty:
                continue
            for yf_symbol, symbol in zip(batch_yf, batch_norm, strict=False):
                if isinstance(data.columns, pd.MultiIndex):
                    if yf_symbol not in data.columns.get_level_values(0):
                        continue
                    part = data[yf_symbol].copy()
                else:
                    part = data.copy()
                if part.empty or "Open" not in part.columns:
                    continue
                part = part.reset_index()
                if "Date" not in part.columns and "index" in part.columns:
                    part = part.rename(columns={"index": "Date"})
                if "Date" not in part.columns:
                    continue
                part = part.rename(
                    columns={
                        "Date": "date",
                        "Open": "open",
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Adj Close": "adj_close",
                        "Volume": "volume",
                        "Dividends": "dividend",
                        "Stock Splits": "split_factor",
                    }
                )
                part = part.dropna(subset=["open", "high", "low", "close"], how="all")
                if part.empty:
                    continue
                if "adj_close" in part.columns:
                    ratio = pd.to_numeric(part["adj_close"], errors="coerce") / pd.to_numeric(part["close"], errors="coerce")
                    part["adj_open"] = pd.to_numeric(part["open"], errors="coerce") * ratio
                    part["adj_high"] = pd.to_numeric(part["high"], errors="coerce") * ratio
                    part["adj_low"] = pd.to_numeric(part["low"], errors="coerce") * ratio
                part["symbol"] = symbol
                part["source"] = "yfinance"
                try:
                    frames.append(normalize_us_ohlcv(part))
                except ValueError:
                    continue
            if self.pause_seconds:
                time.sleep(self.pause_seconds)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


@dataclass(frozen=True)
class YFinanceNasdaq100Provider(YFinanceSp500Provider):
    universe_url: str = "https://en.wikipedia.org/wiki/Nasdaq-100"

    def fetch_universe(self) -> pd.DataFrame:
        import requests

        response = requests.get(self.universe_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        candidates = [table for table in tables if {"Ticker", "Company"}.issubset(set(table.columns))]
        if not candidates:
            raise RuntimeError("Could not find Nasdaq-100 constituents table")
        raw = candidates[0]
        frame = pd.DataFrame(
            {
                "symbol": raw["Ticker"].astype(str).str.replace(".", "-", regex=False),
                "name": raw["Company"],
                "exchange": "NASDAQ",
                "security_type": "common_stock",
                "active_start_date": "2000-01-01",
                "active_end_date": pd.NA,
                "is_current_member": True,
                "source": "wikipedia_nasdaq100_current",
            }
        )
        return normalize_us_universe(frame)


def provider_from_config(config: dict) -> UsMarketDataProvider:
    provider = config.get("provider", "csv_local")
    settings = config.get("provider_settings", {})
    if provider == "csv_local":
        return CsvLocalUsProvider(settings["raw_universe_csv"], settings["raw_ohlcv_dir"])
    if provider == "yfinance_sp500":
        return YFinanceSp500Provider(
            universe_url=settings.get("universe_url", YFinanceSp500Provider.universe_url),
            batch_size=int(settings.get("batch_size", 60)),
            pause_seconds=float(settings.get("pause_seconds", 0.2)),
        )
    if provider == "yfinance_nasdaq100":
        return YFinanceNasdaq100Provider(
            universe_url=settings.get("universe_url", YFinanceNasdaq100Provider.universe_url),
            batch_size=int(settings.get("batch_size", 60)),
            pause_seconds=float(settings.get("pause_seconds", 0.2)),
        )
    raise ValueError(f"Unsupported US provider: {provider}")
