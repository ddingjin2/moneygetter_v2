from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Any, Callable

import pandas as pd


class CollectorError(RuntimeError):
    """Raised when market data collection fails after retries."""


@dataclass(frozen=True)
class TickerRecord:
    ticker: str
    market: str
    name: str | None = None
    source: str = "pykrx"


class PykrxCollector:
    def __init__(
        self,
        retry_count: int = 3,
        retry_sleep_seconds: float = 1.0,
        symbol_request_sleep_seconds: float = 0.1,
        stock_api: Any | None = None,
    ) -> None:
        self.retry_count = retry_count
        self.retry_sleep_seconds = retry_sleep_seconds
        self.symbol_request_sleep_seconds = symbol_request_sleep_seconds
        self._stock_api = stock_api

    @property
    def stock_api(self) -> Any:
        if self._stock_api is None:
            try:
                from pykrx import stock
            except ImportError as exc:
                raise CollectorError("pykrx is required to use PykrxCollector") from exc
            self._stock_api = stock
        return self._stock_api

    def _retry(self, operation_name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_count + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == self.retry_count:
                    break
                sleep(self.retry_sleep_seconds)
        raise CollectorError(f"{operation_name} failed after {self.retry_count} attempts") from last_error

    def fetch_ticker_records(self, market: str, as_of_date: str | None = None) -> list[TickerRecord]:
        market_name = market.upper()
        if market_name == "ALL":
            records: list[TickerRecord] = []
            for scoped_market in ["KOSPI", "KOSDAQ"]:
                records.extend(self.fetch_ticker_records(scoped_market, as_of_date=as_of_date))
            return sorted({record.ticker: record for record in records}.values(), key=lambda item: item.ticker)
        if market_name not in {"KOSPI", "KOSDAQ", "KONEX"}:
            raise ValueError("market must be one of: KOSPI, KOSDAQ, KONEX, ALL")

        query_date = as_of_date or pd.Timestamp.now(tz="Asia/Seoul").strftime("%Y%m%d")
        tickers = list(self._retry(f"fetch_tickers({market_name}, {query_date})", self.stock_api.get_market_ticker_list, query_date, market=market_name))
        records = []
        for ticker in tickers:
            code = str(ticker).zfill(6)
            name = None
            get_name = getattr(self.stock_api, "get_market_ticker_name", None)
            if get_name is not None:
                try:
                    name = str(self._retry(f"fetch_ticker_name({code})", get_name, code))
                except CollectorError:
                    name = None
            records.append(TickerRecord(ticker=code, market=market_name, name=name))
        return records

    def fetch_ohlcv(self, symbol: str, start_date: str, end_date: str, adjusted: bool = True) -> pd.DataFrame:
        fetch = getattr(self.stock_api, "get_market_ohlcv_by_date", self.stock_api.get_market_ohlcv)
        frame = self._retry(
            f"fetch_ohlcv({symbol})",
            fetch,
            start_date,
            end_date,
            str(symbol).zfill(6),
            adjusted=adjusted,
        )
        sleep(self.symbol_request_sleep_seconds)
        if frame is None or frame.empty:
            return pd.DataFrame()
        return frame.reset_index()

    def fetch_market_cap(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        fetch = getattr(self.stock_api, "get_market_cap_by_date", None)
        if fetch is None:
            return pd.DataFrame()
        frame = self._retry(f"fetch_market_cap({symbol})", fetch, start_date, end_date, str(symbol).zfill(6))
        if frame is None or frame.empty:
            return pd.DataFrame()
        return frame.reset_index()

    def fetch_ohlcv_with_market_cap(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjusted: bool = True,
        include_market_cap: bool = False,
    ) -> pd.DataFrame:
        ohlcv = self.fetch_ohlcv(symbol, start_date, end_date, adjusted=adjusted)
        if ohlcv.empty or not include_market_cap:
            return ohlcv
        cap = self.fetch_market_cap(symbol, start_date, end_date)
        if cap.empty:
            return ohlcv
        date_column = "날짜" if "날짜" in ohlcv.columns else ohlcv.columns[0]
        cap_date_column = "날짜" if "날짜" in cap.columns else cap.columns[0]
        columns = [cap_date_column] + [column for column in ["시가총액", "상장주식수", "거래대금", "거래량"] if column in cap.columns]
        return ohlcv.merge(cap.loc[:, columns], left_on=date_column, right_on=cap_date_column, how="left", suffixes=("", "_cap"))
