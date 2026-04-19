from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree

import pandas as pd

from v2.evaluation.leakage_check import check_leakage


OPENDART_BASE_URL = "https://opendart.fss.or.kr/api"
DART_VIEWER_URL = "https://dart.fss.or.kr/dsaf001/main.do"
DEFAULT_START_DATE = date(2019, 1, 1)
DEFAULT_END_DATE = date(2026, 4, 17)
MARKET_CLOSE = "15:30"
REPORT_DETAIL_TYPES = {
    "A001": "annual_report",
    "A002": "semi_annual_report",
    "A003": "quarterly_report",
}
REPORT_CODES = {
    "11013": ("A003", 1),
    "11012": ("A002", 2),
    "11014": ("A003", 3),
    "11011": ("A001", 4),
}
REPORT_NAME_QUARTER_PATTERNS = (
    (re.compile("1분기"), "11013"),
    (re.compile("반기"), "11012"),
    (re.compile("3분기"), "11014"),
    (re.compile("사업보고서"), "11011"),
)
TARGET_ACCOUNTS = {
    "revenue": (
        "매출액",
        "수익(매출액)",
        "영업수익",
        "매출",
    ),
    "operating_income": (
        "영업이익",
        "영업이익(손실)",
    ),
    "net_income": (
        "당기순이익",
        "당기순이익(손실)",
        "분기순이익",
        "반기순이익",
        "연결당기순이익",
    ),
    "total_assets": (
        "자산총계",
    ),
    "total_equity": (
        "자본총계",
    ),
}
CACHE_DIR = Path("v2/data/cache")
RAW_DART_DIR = CACHE_DIR / "raw_dart"
EARNINGS_EVENTS_PATH = CACHE_DIR / "earnings_events.parquet"
EARNINGS_EVENTS_PARTIAL_PATH = CACHE_DIR / "earnings_events_partial.parquet"
DEFAULT_V1_OHLCV_PATH = Path("C:/dev/moneygetter/data/processed/market_ohlcv.parquet")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


class OpendartError(RuntimeError):
    pass


@dataclass(frozen=True)
class RateLimiter:
    max_calls_per_second: float = 90.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "_min_interval", 1.0 / self.max_calls_per_second)
        object.__setattr__(self, "_last_call", 0.0)
        object.__setattr__(self, "_lock", threading.Lock())

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            remaining = self._min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            object.__setattr__(self, "_last_call", time.monotonic())


class OpendartClient:
    """Small cached OPENDART client using official HTTP endpoints."""

    def __init__(
        self,
        api_key: str,
        *,
        raw_cache_dir: Path = RAW_DART_DIR,
        rate_limiter: RateLimiter | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        if not api_key:
            raise ValueError("OPENDART API key is required")
        self.api_key = api_key
        self.raw_cache_dir = raw_cache_dir
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout_seconds = timeout_seconds
        self.raw_cache_dir.mkdir(parents=True, exist_ok=True)

    def _request_json(self, endpoint: str, params: dict[str, Any], cache_name: str) -> dict[str, Any]:
        cache_path = self.raw_cache_dir / cache_name
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        request_params = {"crtfc_key": self.api_key, **params}
        url = f"{OPENDART_BASE_URL}/{endpoint}?{urllib.parse.urlencode(request_params)}"
        self.rate_limiter.wait()
        with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        cache_path.write_text(payload, encoding="utf-8")
        data = json.loads(payload)
        status = str(data.get("status", "000"))
        if status not in {"000", "013"}:
            raise OpendartError(f"OPENDART {endpoint} failed: {status} {data.get('message')}")
        return data

    def fetch_corp_codes(self) -> pd.DataFrame:
        cache_path = self.raw_cache_dir / "corpCode.zip"
        if not cache_path.exists():
            url = f"{OPENDART_BASE_URL}/corpCode.xml?{urllib.parse.urlencode({'crtfc_key': self.api_key})}"
            self.rate_limiter.wait()
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
                cache_path.write_bytes(response.read())

        with zipfile.ZipFile(cache_path) as archive:
            xml_name = archive.namelist()[0]
            xml_bytes = archive.read(xml_name)
        root = ElementTree.fromstring(xml_bytes)
        rows = []
        for item in root.findall("list"):
            rows.append(
                {
                    "corp_code": (item.findtext("corp_code") or "").strip(),
                    "corp_name": (item.findtext("corp_name") or "").strip(),
                    "corp_eng_name": (item.findtext("corp_eng_name") or "").strip(),
                    "stock_code": (item.findtext("stock_code") or "").strip().zfill(6),
                    "modify_date": (item.findtext("modify_date") or "").strip(),
                }
            )
        frame = pd.DataFrame(rows)
        return frame.loc[frame["stock_code"].str.fullmatch(r"\d{6}", na=False)].copy()

    def search_filings(
        self,
        *,
        bgn_de: date,
        end_de: date,
        detail_type: str,
        corp_cls: str = "Y",
        page_no: int = 1,
    ) -> dict[str, Any]:
        params = {
            "bgn_de": bgn_de.strftime("%Y%m%d"),
            "end_de": end_de.strftime("%Y%m%d"),
            "pblntf_ty": "A",
            "pblntf_detail_ty": detail_type,
            "corp_cls": corp_cls,
            "sort": "date",
            "sort_mth": "asc",
            "page_no": page_no,
            "page_count": 100,
        }
        cache_name = (
            f"list_{detail_type}_{params['bgn_de']}_{params['end_de']}_"
            f"{corp_cls}_{page_no}.json"
        )
        return self._request_json("list.json", params, cache_name)

    def fetch_financials(
        self,
        *,
        corp_code: str,
        business_year: int,
        report_code: str,
        fs_div: str,
    ) -> dict[str, Any]:
        params = {
            "corp_code": corp_code,
            "bsns_year": str(business_year),
            "reprt_code": report_code,
            "fs_div": fs_div,
        }
        cache_name = f"fnlttSinglAcntAll_{corp_code}_{business_year}_{report_code}_{fs_div}.json"
        return self._request_json("fnlttSinglAcntAll.json", params, cache_name)

    def fetch_receipt_time(self, rcept_no: str) -> str | None:
        cache_path = self.raw_cache_dir / f"viewer_{rcept_no}.html"
        if cache_path.exists():
            html = cache_path.read_text(encoding="utf-8", errors="ignore")
        else:
            url = f"{DART_VIEWER_URL}?{urllib.parse.urlencode({'rcpNo': rcept_no})}"
            self.rate_limiter.wait()
            try:
                with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
                    html = response.read().decode("utf-8", errors="ignore")
            except Exception:
                return None
            cache_path.write_text(html, encoding="utf-8")
        return parse_receipt_time_from_viewer(html)


def _read_dotenv_value(env_var: str, dotenv_path: Path = DEFAULT_ENV_PATH) -> str:
    if not dotenv_path.exists():
        return ""
    for raw_line in dotenv_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != env_var:
            continue
        return value.strip().strip('"').strip("'")
    return ""


def get_api_key_from_env(
    env_var: str = "OPENDART_API_KEY",
    *,
    dotenv_path: Path = DEFAULT_ENV_PATH,
) -> str:
    api_key = os.environ.get(env_var, "").strip() or _read_dotenv_value(env_var, dotenv_path)
    if not api_key:
        raise ValueError(
            f"{env_var} is not set. Get a free key at https://opendart.fss.or.kr "
            f"and set it in the environment or {dotenv_path}."
        )
    return api_key


def parse_receipt_time_from_viewer(html: str) -> str | None:
    patterns = (
        re.compile(r"접수(?:일자|일시|시간)[^0-9]*(?:\d{4}[./-]\d{2}[./-]\d{2})?[^0-9]*(\d{1,2}):(\d{2})"),
        re.compile(r"(\d{4}[./-]\d{2}[./-]\d{2})\s+(\d{1,2}):(\d{2})"),
    )
    for pattern in patterns:
        match = pattern.search(html)
        if not match:
            continue
        groups = match.groups()
        hour = groups[-2]
        minute = groups[-1]
        return f"{int(hour):02d}:{int(minute):02d}"
    return None


def _date_windows(start_date: date, end_date: date, window_days: int = 90) -> Iterable[tuple[date, date]]:
    current = start_date
    while current <= end_date:
        window_end = min(current + timedelta(days=window_days - 1), end_date)
        yield current, window_end
        current = window_end + timedelta(days=1)


def fetch_periodic_filings(
    client: OpendartClient,
    *,
    start_date: date = DEFAULT_START_DATE,
    end_date: date = DEFAULT_END_DATE,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for detail_type in REPORT_DETAIL_TYPES:
        for bgn_de, end_de in _date_windows(start_date, end_date):
            page_no = 1
            while True:
                payload = client.search_filings(
                    bgn_de=bgn_de,
                    end_de=end_de,
                    detail_type=detail_type,
                    page_no=page_no,
                )
                rows.extend(payload.get("list", []) or [])
                total_page = int(payload.get("total_page") or 1)
                if page_no >= total_page:
                    break
                page_no += 1

    if not rows:
        return pd.DataFrame()

    filings = pd.DataFrame(rows)
    filings["stock_code"] = filings["stock_code"].astype(str).str.zfill(6)
    filings["rcept_dt"] = pd.to_datetime(filings["rcept_dt"], format="%Y%m%d", errors="coerce")
    filings["report_type"] = filings["report_nm"].map(infer_report_detail_type)
    filings["reprt_code"] = filings["report_nm"].map(infer_report_code)
    filings = filings.loc[filings["report_type"].isin(REPORT_DETAIL_TYPES)].copy()
    filings = filings.loc[filings["reprt_code"].isin(REPORT_CODES)].copy()
    filings = filings.loc[~filings["report_nm"].astype(str).str.contains(r"\[.*정정.*\]", regex=True, na=False)].copy()
    filings = filings.sort_values(["corp_code", "reprt_code", "rcept_dt", "rcept_no"])
    filings = filings.drop_duplicates(["corp_code", "reprt_code", "rcept_dt"], keep="first")
    return filings.reset_index(drop=True)


def infer_report_code(report_name: str) -> str | None:
    text = str(report_name)
    if re.search(r"1\s*분기", text):
        return "11013"
    if re.search(r"3\s*분기", text):
        return "11014"
    if "반기" in text:
        return "11012"
    if "사업보고서" in text:
        return "11011"
    if "분기보고서" in text:
        match = re.search(r"\((\d{4})[.\-/](\d{2})\)", text)
        if match and match.group(2) == "03":
            return "11013"
        if match and match.group(2) == "09":
            return "11014"
    return None


def infer_business_year(rcept_dt: pd.Timestamp, report_code: str, report_name: str) -> int:
    match = re.search(r"\((\d{4})[.\-/]\d{2}\)", str(report_name))
    if match:
        return int(match.group(1))
    if report_code == "11011":
        return int(pd.Timestamp(rcept_dt).year) - 1
    return int(pd.Timestamp(rcept_dt).year)


def infer_report_detail_type(report_name: str) -> str | None:
    report_code = infer_report_code(report_name)
    if report_code is None:
        return None
    return REPORT_CODES[report_code][0]


def fiscal_quarter_for_report(business_year: int, report_code: str) -> str:
    if report_code not in REPORT_CODES:
        raise ValueError(f"Unsupported report code: {report_code}")
    quarter = REPORT_CODES[report_code][1]
    return f"{business_year}Q{quarter}"


def fiscal_quarter_end(fiscal_quarter: str) -> pd.Timestamp:
    year = int(fiscal_quarter[:4])
    quarter = int(fiscal_quarter[-1])
    month_day = {
        1: (3, 31),
        2: (6, 30),
        3: (9, 30),
        4: (12, 31),
    }[quarter]
    return pd.Timestamp(date(year, month_day[0], month_day[1]))


def _parse_number(value: Any) -> float:
    if value is None:
        return math.nan
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "nan", "None"}:
        return math.nan
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        number = float(text)
    except ValueError:
        return math.nan
    return -number if negative else number


def _account_key(account_name: str) -> str | None:
    normalized = re.sub(r"\s+", "", str(account_name))
    for key, names in TARGET_ACCOUNTS.items():
        for name in names:
            if re.sub(r"\s+", "", name) == normalized:
                return key
    return None


def extract_financial_metrics(financial_payload: dict[str, Any]) -> dict[str, float]:
    rows = financial_payload.get("list", []) or []
    metrics = {key: math.nan for key in TARGET_ACCOUNTS}
    for row in rows:
        key = _account_key(str(row.get("account_nm", "")))
        if key is None or not math.isnan(metrics[key]):
            continue
        value_field = "thstrm_amount"
        if key in {"revenue", "operating_income", "net_income"}:
            value_field = "thstrm_amount"
        metrics[key] = _parse_number(row.get(value_field))
    return metrics


def _fetch_metrics_with_fallback(
    client: OpendartClient,
    *,
    corp_code: str,
    business_year: int,
    report_code: str,
) -> tuple[dict[str, float], str]:
    for fs_div in ("CFS", "OFS"):
        try:
            payload = client.fetch_financials(
                corp_code=corp_code,
                business_year=business_year,
                report_code=report_code,
                fs_div=fs_div,
            )
        except Exception:
            continue
        if str(payload.get("status")) == "013":
            continue
        metrics = extract_financial_metrics(payload)
        if any(not math.isnan(value) for value in metrics.values()):
            return metrics, fs_div
    return {key: math.nan for key in TARGET_ACCOUNTS}, ""


def load_kospi_universe(
    *,
    ohlcv_path: Path = DEFAULT_V1_OHLCV_PATH,
    reference_date: date = DEFAULT_END_DATE,
) -> pd.DataFrame:
    if not ohlcv_path.exists():
        raise FileNotFoundError(ohlcv_path)
    columns = ["date", "symbol", "ticker", "market", "name", "shares_outstanding"]
    frame = pd.read_parquet(ohlcv_path, columns=[column for column in columns if column != "ticker"])
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.loc[(frame["market"].eq("KOSPI")) & (frame["date"].dt.date <= reference_date)].copy()
    frame = frame.sort_values(["symbol", "date"]).groupby("symbol", as_index=False).tail(1)
    frame["stock_code"] = frame["symbol"].astype(str).str.zfill(6)
    return frame[["stock_code", "name", "shares_outstanding"]].drop_duplicates("stock_code")


def crosscheck_kospi_universe(corp_codes: pd.DataFrame, kospi_universe: pd.DataFrame) -> pd.DataFrame:
    merged = corp_codes.merge(
        kospi_universe[["stock_code", "name", "shares_outstanding"]],
        on="stock_code",
        how="inner",
        suffixes=("", "_krx"),
    )
    return merged.drop_duplicates("stock_code").reset_index(drop=True)


def load_trading_calendar(
    *,
    ohlcv_path: Path = DEFAULT_V1_OHLCV_PATH,
    market: str = "KOSPI",
) -> list[pd.Timestamp]:
    frame = pd.read_parquet(ohlcv_path, columns=["date", "market"])
    dates = pd.to_datetime(frame.loc[frame["market"].eq(market), "date"]).dt.normalize().drop_duplicates()
    return sorted(pd.Timestamp(value) for value in dates)


def next_trading_day(value: str | date | pd.Timestamp, trading_calendar: Sequence[pd.Timestamp]) -> pd.Timestamp:
    current = pd.Timestamp(value).normalize()
    for trading_day in trading_calendar:
        trading_day = pd.Timestamp(trading_day).normalize()
        if trading_day > current:
            return trading_day
    raise ValueError(f"No trading day found after {current.date()}")


def calculate_tradable_entry_date(
    rcept_dt: str | date | pd.Timestamp,
    rcept_time: str | None,
    trading_calendar: Sequence[pd.Timestamp],
) -> pd.Timestamp:
    """Return the next KRX trading day open after a disclosure is public."""

    _ = rcept_time or MARKET_CLOSE
    return next_trading_day(rcept_dt, trading_calendar)


def add_yoy_fields(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    frame = events.copy()
    frame["fiscal_year"] = frame["fiscal_quarter"].str[:4].astype(int)
    frame["quarter_number"] = frame["fiscal_quarter"].str[-1].astype(int)
    frame = frame.sort_values(["stock_code", "quarter_number", "fiscal_year"])
    for column in ("revenue", "operating_income", "net_income"):
        previous = frame[["stock_code", "quarter_number", "fiscal_year", column]].copy()
        previous["fiscal_year"] = previous["fiscal_year"] + 1
        previous = previous.drop_duplicates(["stock_code", "quarter_number", "fiscal_year"], keep="first")
        previous = previous.rename(columns={column: f"prev_{column}"})
        frame = frame.merge(
            previous,
            on=["stock_code", "quarter_number", "fiscal_year"],
            how="left",
            validate="m:1",
        )
    return frame.drop(columns=["fiscal_year", "quarter_number"])


def compute_sue(events: pd.DataFrame) -> pd.DataFrame:
    """Compute free-data SUE using YoY EPS surprise and past 8Q EPS volatility."""

    if events.empty:
        return events.copy()
    frame = events.copy()
    frame["fiscal_year"] = frame["fiscal_quarter"].str[:4].astype(int)
    frame["quarter_number"] = frame["fiscal_quarter"].str[-1].astype(int)
    frame = frame.sort_values(["stock_code", "fiscal_year", "quarter_number"]).reset_index(drop=True)

    shares = pd.to_numeric(frame.get("shares_outstanding"), errors="coerce")
    net_income = pd.to_numeric(frame["net_income"], errors="coerce")
    frame["eps"] = net_income.where(shares.isna() | (shares <= 0), net_income / shares)
    frame["eps_basis"] = "net_income"
    frame.loc[shares.notna() & (shares > 0), "eps_basis"] = "net_income_per_share"

    prior = frame[["stock_code", "fiscal_year", "quarter_number", "eps"]].copy()
    prior["fiscal_year"] = prior["fiscal_year"] + 1
    prior = prior.drop_duplicates(["stock_code", "fiscal_year", "quarter_number"], keep="first")
    prior = prior.rename(columns={"eps": "prior_year_same_quarter_eps"})
    frame = frame.merge(
        prior,
        on=["stock_code", "fiscal_year", "quarter_number"],
        how="left",
        validate="m:1",
    )

    frame["eps_std_past_8q"] = (
        frame.groupby("stock_code")["eps"]
        .transform(lambda values: values.shift(1).rolling(8, min_periods=2).std(ddof=0))
    )
    denominator = frame["eps_std_past_8q"].replace(0, pd.NA)
    frame["sue"] = (frame["eps"] - frame["prior_year_same_quarter_eps"]) / denominator
    return frame.drop(columns=["fiscal_year", "quarter_number"])


def deduplicate_fiscal_quarter_events(events: pd.DataFrame) -> pd.DataFrame:
    """Keep the first point-in-time disclosure for each stock/fiscal quarter."""

    if events.empty:
        return events.copy()
    frame = events.copy()
    frame["rcept_dt"] = pd.to_datetime(frame["rcept_dt"])
    frame = frame.sort_values(["stock_code", "fiscal_quarter", "rcept_dt", "rcept_no"])
    return frame.drop_duplicates(["stock_code", "fiscal_quarter"], keep="first").reset_index(drop=True)


def remove_future_fiscal_quarter_events(events: pd.DataFrame) -> pd.DataFrame:
    """Drop events whose calendar fiscal-quarter end is after the receipt date."""

    if events.empty:
        return events.copy()
    frame = events.copy()
    frame["rcept_dt"] = pd.to_datetime(frame["rcept_dt"])
    fiscal_ends = frame["fiscal_quarter"].map(fiscal_quarter_end)
    return frame.loc[fiscal_ends <= frame["rcept_dt"].dt.normalize()].reset_index(drop=True)


def build_earnings_events(
    *,
    client: OpendartClient,
    start_date: date = DEFAULT_START_DATE,
    end_date: date = DEFAULT_END_DATE,
    ohlcv_path: Path = DEFAULT_V1_OHLCV_PATH,
    fetch_receipt_times: bool = False,
    checkpoint_path: Path = EARNINGS_EVENTS_PARTIAL_PATH,
    checkpoint_every: int = 100,
    max_workers: int = 4,
) -> pd.DataFrame:
    corp_codes = client.fetch_corp_codes()
    kospi = load_kospi_universe(ohlcv_path=ohlcv_path, reference_date=end_date)
    universe = crosscheck_kospi_universe(corp_codes, kospi)
    filings = fetch_periodic_filings(client, start_date=start_date, end_date=end_date)
    filings = filings.merge(
        universe[["corp_code", "stock_code", "shares_outstanding"]],
        on=["corp_code", "stock_code"],
        how="inner",
    )
    trading_calendar = load_trading_calendar(ohlcv_path=ohlcv_path)

    existing = pd.DataFrame()
    if checkpoint_path.exists():
        existing = pd.read_parquet(checkpoint_path)
    existing_keys = set(existing["rcept_no"].astype(str)) if "rcept_no" in existing.columns else set()
    filings = filings.loc[~filings["rcept_no"].astype(str).isin(existing_keys)].copy()

    rows: list[dict[str, Any]] = existing.to_dict("records") if not existing.empty else []
    processed_since_checkpoint = 0

    def process_filing(filing: Any) -> dict[str, Any]:
        report_code = str(filing.reprt_code)
        business_year = infer_business_year(
            pd.Timestamp(filing.rcept_dt),
            report_code,
            str(filing.report_nm),
        )
        metrics, fs_div = _fetch_metrics_with_fallback(
            client,
            corp_code=str(filing.corp_code),
            business_year=business_year,
            report_code=report_code,
        )
        rcept_time = client.fetch_receipt_time(str(filing.rcept_no)) if fetch_receipt_times else None
        rcept_time_source = "viewer" if rcept_time else "fallback_market_close"
        rcept_time = rcept_time or MARKET_CLOSE
        fiscal_quarter = fiscal_quarter_for_report(business_year, report_code)
        return {
            "corp_code": str(filing.corp_code),
            "stock_code": str(filing.stock_code).zfill(6),
            "report_type": str(filing.report_type),
            "reprt_code": report_code,
            "fs_div": fs_div,
            "fiscal_quarter": fiscal_quarter,
            "rcept_no": str(filing.rcept_no),
            "rcept_dt": pd.Timestamp(filing.rcept_dt).normalize(),
            "rcept_time": rcept_time,
            "rcept_time_source": rcept_time_source,
            "tradable_entry_date": calculate_tradable_entry_date(
                filing.rcept_dt,
                rcept_time,
                trading_calendar,
            ),
            "revenue": metrics["revenue"],
            "operating_income": metrics["operating_income"],
            "net_income": metrics["net_income"],
            "total_assets": metrics["total_assets"],
            "total_equity": metrics["total_equity"],
            "shares_outstanding": getattr(filing, "shares_outstanding", math.nan),
            "data_source_timestamp": pd.Timestamp(filing.rcept_dt).normalize(),
            "source_collected_at": pd.Timestamp.utcnow().tz_localize(None),
        }

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    if len(filings):
        if max_workers <= 1:
            iterator = (process_filing(filing) for filing in filings.itertuples(index=False))
            for row in iterator:
                rows.append(row)
                processed_since_checkpoint += 1
                if processed_since_checkpoint >= checkpoint_every:
                    order_earnings_columns(pd.DataFrame(rows)).to_parquet(checkpoint_path, index=False)
                    processed_since_checkpoint = 0
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                filing_iterator = iter(filings.itertuples(index=False))
                pending: set[concurrent.futures.Future] = set()
                max_pending = max(max_workers * 4, max_workers)

                def submit_next() -> None:
                    try:
                        filing = next(filing_iterator)
                    except StopIteration:
                        return
                    pending.add(executor.submit(process_filing, filing))

                for _ in range(max_pending):
                    submit_next()

                while pending:
                    done, pending = concurrent.futures.wait(
                        pending,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    for future in done:
                        rows.append(future.result())
                        processed_since_checkpoint += 1
                        submit_next()
                        if processed_since_checkpoint >= checkpoint_every:
                            order_earnings_columns(pd.DataFrame(rows)).to_parquet(checkpoint_path, index=False)
                            processed_since_checkpoint = 0
        order_earnings_columns(pd.DataFrame(rows)).to_parquet(checkpoint_path, index=False)

    events = pd.DataFrame(rows)
    if events.empty:
        return order_earnings_columns(events)
    events = events.drop_duplicates("rcept_no", keep="last")
    events = events.sort_values(["stock_code", "fiscal_quarter", "rcept_dt", "rcept_no"]).reset_index(drop=True)
    events = deduplicate_fiscal_quarter_events(events)
    events = remove_future_fiscal_quarter_events(events)
    events = add_yoy_fields(events)
    events = compute_sue(events)
    return order_earnings_columns(events)


def order_earnings_columns(events: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "corp_code",
        "stock_code",
        "report_type",
        "reprt_code",
        "fs_div",
        "fiscal_quarter",
        "rcept_no",
        "rcept_dt",
        "rcept_time",
        "rcept_time_source",
        "tradable_entry_date",
        "revenue",
        "operating_income",
        "net_income",
        "total_assets",
        "total_equity",
        "prev_revenue",
        "prev_operating_income",
        "prev_net_income",
        "shares_outstanding",
        "eps",
        "eps_basis",
        "prior_year_same_quarter_eps",
        "eps_std_past_8q",
        "sue",
        "data_source_timestamp",
        "source_collected_at",
    ]
    columns = [column for column in preferred if column in events.columns]
    extras = [column for column in events.columns if column not in columns]
    return events.loc[:, columns + extras]


def validate_earnings_point_in_time(events: pd.DataFrame) -> dict[str, list[str]]:
    violations: dict[str, list[str]] = {
        "data_source_after_receipt": [],
        "fiscal_quarter_after_receipt": [],
        "pr1_leakage": [],
    }
    if events.empty:
        return violations

    frame = events.copy()
    frame["rcept_dt"] = pd.to_datetime(frame["rcept_dt"])
    frame["data_source_timestamp"] = pd.to_datetime(frame["data_source_timestamp"])
    for row in frame.itertuples(index=False):
        label = f"{row.stock_code}|{pd.Timestamp(row.rcept_dt).date().isoformat()}|{row.fiscal_quarter}"
        if pd.Timestamp(row.data_source_timestamp).normalize() > pd.Timestamp(row.rcept_dt).normalize():
            violations["data_source_after_receipt"].append(label)
        if fiscal_quarter_end(str(row.fiscal_quarter)) > pd.Timestamp(row.rcept_dt).normalize():
            violations["fiscal_quarter_after_receipt"].append(label)

    leakage_ledger = pd.DataFrame(
        {
            "symbol": frame["stock_code"],
            "entry_date": frame["tradable_entry_date"],
            "feature_available_at": frame["data_source_timestamp"],
            "earnings_announcement_at": pd.to_datetime(
                frame["rcept_dt"].dt.strftime("%Y-%m-%d") + " " + frame["rcept_time"].fillna(MARKET_CLOSE)
            ),
            "next_trade_date": frame["tradable_entry_date"],
        }
    )
    pr1_result = check_leakage(leakage_ledger, ["earnings_yoy_sue"])
    violations["pr1_leakage"] = [
        f"{kind}:{trade}"
        for kind, trades in pr1_result.items()
        for trade in trades
    ]
    return violations


def save_earnings_events(events: pd.DataFrame, path: Path = EARNINGS_EVENTS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    events.to_parquet(path, index=False)
    return path


def load_earnings_events(path: Path = EARNINGS_EVENTS_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build MoneyGetter v2 OPENDART earnings events.")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE.isoformat())
    parser.add_argument("--end-date", default=DEFAULT_END_DATE.isoformat())
    parser.add_argument("--ohlcv-path", default=str(DEFAULT_V1_OHLCV_PATH))
    parser.add_argument("--output", default=str(EARNINGS_EVENTS_PATH))
    parser.add_argument("--raw-cache-dir", default=str(RAW_DART_DIR))
    parser.add_argument("--max-calls-per-second", type=float, default=90.0)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--checkpoint", default=str(EARNINGS_EVENTS_PARTIAL_PATH))
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument(
        "--fetch-receipt-times",
        action="store_true",
        help="Best-effort DART viewer scrape for rcept_time. Default uses conservative 15:30 fallback.",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    client = OpendartClient(
        get_api_key_from_env(),
        raw_cache_dir=Path(args.raw_cache_dir),
        rate_limiter=RateLimiter(args.max_calls_per_second),
    )
    events = build_earnings_events(
        client=client,
        start_date=pd.Timestamp(args.start_date).date(),
        end_date=pd.Timestamp(args.end_date).date(),
        ohlcv_path=Path(args.ohlcv_path),
        fetch_receipt_times=args.fetch_receipt_times,
        checkpoint_path=Path(args.checkpoint),
        checkpoint_every=args.checkpoint_every,
        max_workers=args.max_workers,
    )
    output = save_earnings_events(events, Path(args.output))
    print(f"Wrote {len(events)} earnings events to {output}")


if __name__ == "__main__":
    main()
