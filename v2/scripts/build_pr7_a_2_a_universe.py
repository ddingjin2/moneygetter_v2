from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.ohlcv import load_ohlcv  # noqa: E402


REFERENCE_DATE = pd.Timestamp("2026-04-17")
START_DATE = pd.Timestamp("2020-03-27")
UNIVERSE_PATH = ROOT / "v2/data/cache/universe/kospi_universe.parquet"
REPORT_PATH = ROOT / "v2/reports/pr7_a_2_a_full_universe_ic.md"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SECTOR_REGEX = re.compile(r'업종명\s*:\s*<a href="/sise/sise_group_detail\.naver\?type=upjong&no=\d+">([^<]+)<')
CODE_REGEX = re.compile(r"code=(\d{6})")

PRODUCT_PREFIXES = [
    "KODEX",
    "TIGER",
    "KOSEF",
    "HANARO",
    "KBSTAR",
    "ARIRANG",
    "SOL",
    "ACE",
    "TIMEFOLIO",
    "PLUS",
    "RISE",
    "TREX",
    "1Q",
    "KIWOOM",
    "WON",
    "FOCUS",
    "TRUSTON",
    "UNICORN",
    "KoAct",
    "TIME ",
    "MIDAS ",
    "VITA ",
    "에셋플러스 ",
    "ITF ",
    "KCGI ",
    "파워",
    "마이티",
    "HK",
    "BNK",
    "N2",
    "메리츠 ",
    "한투 ",
    "미래에셋 ",
    "하나 ",
    "키움 ",
    "신한 ",
    "KB ",
    "삼성 ",
    "대신 ",
    "QV ",
    "TRUE ",
    "DAISHIN",
]
PRODUCT_KEYWORDS = ["ETF", "ETN", "SPAC", "REIT", "스팩", "리츠"]
PRODUCT_NAME_CONTAINS = ["액티브", "인프라", "리얼티", "유전"]
PREFERRED_SUFFIXES = [
    "우",
    "우B",
    "우C",
    "1우",
    "2우",
    "3우",
    "1우B",
    "2우B",
    "3우B",
    "1우C",
    "2우C",
    "3우C",
]


@dataclass(frozen=True)
class UniverseStats:
    raw_latest_kospi_rows: int
    active_common_rows: int
    delisted_common_rows: int
    total_universe_rows: int
    sector_non_null_rows: int
    sector_missing_rows: int


def is_preferred_share(code: str, name: str) -> bool:
    if code[-1] in {"5", "7", "9"}:
        return True
    return any(name.endswith(suffix) for suffix in PREFERRED_SUFFIXES)


def is_excluded_product(name: str) -> bool:
    lowered = name.lower()
    if any(keyword.lower() in lowered for keyword in PRODUCT_KEYWORDS):
        return True
    if any(keyword in name for keyword in PRODUCT_NAME_CONTAINS):
        return True
    return any(name.startswith(prefix) for prefix in PRODUCT_PREFIXES)


def normalize_name(value: object) -> str:
    text = " ".join(str(value).split())
    if text.startswith("Empty DataFrame"):
        return ""
    return text


def load_local_kospi_history() -> pd.DataFrame:
    frame = load_ohlcv().copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
    frame["name"] = frame["name"].map(normalize_name)
    return frame.loc[frame["market"].eq("KOSPI")].copy()


def fetch_naver_active_common_snapshot() -> pd.DataFrame:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    rows: list[dict[str, str]] = []

    for page in range(1, 60):
        response = session.get(
            "https://finance.naver.com/sise/sise_market_sum.naver",
            params={"sosok": "0", "page": page},
            timeout=30,
        )
        response.raise_for_status()
        html = response.content.decode("euc-kr", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        page_rows = 0
        for anchor in soup.select("table.type_2 a.tltle"):
            match = CODE_REGEX.search(anchor.get("href", ""))
            if not match:
                continue
            rows.append(
                {
                    "code": match.group(1),
                    "name": " ".join(anchor.get_text(" ", strip=True).split()),
                }
            )
            page_rows += 1

        if page_rows == 0:
            break

    frame = pd.DataFrame(rows).drop_duplicates("code", keep="first")
    frame["preferred"] = [is_preferred_share(code, name) for code, name in zip(frame["code"], frame["name"])]
    frame["excluded_product"] = frame["name"].map(is_excluded_product)
    frame = frame.loc[~frame["preferred"] & ~frame["excluded_product"]].copy()
    return frame[["code", "name"]].sort_values("code").reset_index(drop=True)


def build_symbol_history_summary(history: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for code, group in history.groupby("symbol", sort=True):
        group = group.sort_values("date")
        names = [normalize_name(value) for value in group["name"].tolist()]
        non_empty_names = [value for value in names if value]
        name = non_empty_names[-1] if non_empty_names else ""
        records.append(
            {
                "code": code,
                "name": name,
                "listed_date": group["date"].min(),
                "last_seen_date": group["date"].max(),
            }
        )
    return pd.DataFrame(records)


def build_delisted_common(summary: pd.DataFrame, active_codes: set[str]) -> pd.DataFrame:
    frame = summary.loc[
        (summary["last_seen_date"] >= START_DATE)
        & (summary["last_seen_date"] < REFERENCE_DATE)
        & (~summary["code"].isin(active_codes))
    ].copy()
    frame["preferred"] = [is_preferred_share(code, name) for code, name in zip(frame["code"], frame["name"])]
    frame["excluded_product"] = frame["name"].map(is_excluded_product)
    frame = frame.loc[(frame["name"] != "") & ~frame["preferred"] & ~frame["excluded_product"]].copy()
    frame["delisted_date"] = frame["last_seen_date"]
    return frame[["code", "name", "listed_date", "delisted_date"]].sort_values("code").reset_index(drop=True)


def fetch_sector_map(codes: list[str], *, delay_seconds: float = 0.10) -> dict[str, str | None]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    sectors: dict[str, str | None] = {}

    for index, code in enumerate(codes, start=1):
        sector: str | None = None
        try:
            response = session.get(
                "https://finance.naver.com/item/main.naver",
                params={"code": code},
                timeout=30,
            )
            response.raise_for_status()
            if "item/main.naver" in str(response.url):
                match = SECTOR_REGEX.search(response.text)
                if match:
                    sector = match.group(1).strip()
        except Exception:  # noqa: BLE001
            sector = None

        sectors[code] = sector
        if index < len(codes):
            time.sleep(delay_seconds)
    return sectors


def build_universe_frame() -> tuple[pd.DataFrame, UniverseStats]:
    history = load_local_kospi_history()
    summary = build_symbol_history_summary(history)
    latest_active = fetch_naver_active_common_snapshot().merge(
        summary[["code", "listed_date"]],
        on="code",
        how="left",
        validate="1:1",
    )
    latest_active = latest_active.loc[
        latest_active["listed_date"].notna() & (latest_active["listed_date"] <= REFERENCE_DATE)
    ].copy()

    active_codes = set(latest_active["code"])
    delisted_common = build_delisted_common(summary, active_codes)

    active_frame = latest_active.copy()
    active_frame["delisted_date"] = pd.NaT

    universe = pd.concat(
        [
            active_frame[["code", "name", "listed_date", "delisted_date"]],
            delisted_common[["code", "name", "listed_date", "delisted_date"]],
        ],
        ignore_index=True,
    ).drop_duplicates("code", keep="first")

    sector_map = fetch_sector_map(universe["code"].tolist())
    universe["sector"] = universe["code"].map(sector_map)
    universe = universe.sort_values("code").reset_index(drop=True)

    stats = UniverseStats(
        raw_latest_kospi_rows=int(history.loc[history["date"].eq(REFERENCE_DATE), "symbol"].nunique()),
        active_common_rows=int(len(active_frame)),
        delisted_common_rows=int(len(delisted_common)),
        total_universe_rows=int(len(universe)),
        sector_non_null_rows=int(universe["sector"].notna().sum()),
        sector_missing_rows=int(universe["sector"].isna().sum()),
    )
    return universe, stats


def listing_bucket(value: pd.Timestamp) -> str:
    if pd.isna(value) or value <= START_DATE:
        return "listed_on_or_before_2020-03-27"
    if value.year <= 2021:
        return "listed_2020-03-28_to_2021-12-31"
    return f"listed_{value.year}"


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def write_report(universe: pd.DataFrame, stats: UniverseStats) -> None:
    active = universe.loc[universe["delisted_date"].isna()].copy()
    delisted = universe.loc[universe["delisted_date"].notna()].copy()

    bucket_rows = (
        universe.assign(listing_bucket=universe["listed_date"].map(listing_bucket))
        .groupby("listing_bucket", as_index=False)
        .agg(count=("code", "count"))
        .sort_values("listing_bucket")
    )
    sector_rows = (
        active.assign(sector=active["sector"].fillna("unknown"))
        .groupby("sector", as_index=False)
        .agg(count=("code", "count"))
        .sort_values(["count", "sector"], ascending=[False, True])
        .head(15)
    )
    sample_rows = universe.head(20).copy()

    report = f"""# PR-7.A.2.a 전체 universe 투자자 flow 수집 + IC 재측정

Updated: 2026-04-25 KST

## 상태

- 현재 문서는 **Step 1 완료 상태**까지만 반영한다.
- Step 2 전체 flow 수집은 사용자 승인 전 시작하지 않는다.

## Step 1. Universe 정의

### 기준

- 기준일: `2026-04-17`
- active universe 소스:
  - Naver `sise_market_sum.naver` current KOSPI snapshot
  - 로컬 shared OHLCV `C:\\dev\\moneygetter\\data\\processed\\market_ohlcv.parquet`
- active common-stock 필터:
  - Naver KOSPI 종목 리스트 기준
  - 보통주만
  - ETF / ETN / SPAC / 리츠 및 상장지수상품 계열 이름 제외
- delisted 처리:
  - `2020-03-27 ~ 2026-04-17` 사이에 이력이 있고 `last_seen_date < 2026-04-17` 인 종목 후보 확인
  - 같은 보통주 / 상품 제외 필터 적용 후 universe 에 포함
- sector 소스:
  - Naver `item/main.naver` 현재 페이지의 업종 링크
  - delisted 종목은 페이지 redirect 시 sector 를 `NA` 로 둠

### 주의 메모

- `listed_date` 는 **로컬 OHLCV first_seen_date proxy** 다.
- 2020-03-27 이전 상장 종목은 대부분 `2020-01-02` 로 기록된다.
- active common-stock 기준면은 `2026-04-25` Naver current snapshot 을 관측한 뒤, 로컬 OHLCV `listed_date <= 2026-04-17` 조건으로 정렬했다.
- `2026-04-17` 과 `2026-04-25` 사이 신규 상장 종목은 자동 제외된다.

### Universe 요약

- raw latest KOSPI rows: `{stats.raw_latest_kospi_rows}`
- active common rows: `{stats.active_common_rows}`
- period-delisted common rows: `{stats.delisted_common_rows}`
- total universe rows: `{stats.total_universe_rows}`
- sector resolved rows: `{stats.sector_non_null_rows}`
- sector missing rows: `{stats.sector_missing_rows}`

### 상태 bucket 분포

{markdown_table(
    [
        {"bucket": "active_on_2026-04-17", "count": int(len(active))},
        {"bucket": "delisted_during_2020-03-27_to_2026-04-17", "count": int(len(delisted))},
    ],
    ["bucket", "count"],
)}

### listing bucket 분포

{markdown_table(bucket_rows.to_dict("records"), ["listing_bucket", "count"])}

### active sector 상위 15개

{markdown_table(sector_rows.to_dict("records"), ["sector", "count"])}

### universe 샘플 20행

{markdown_table(sample_rows.to_dict("records"), ["code", "name", "listed_date", "delisted_date", "sector"])}

### 산출물

- universe parquet: `v2/data/cache/universe/kospi_universe.parquet`
- active universe helper: `v2/data/universe.py:get_active_universe`

### 중단 게이트

- Step 1 완료
- 사용자 승인 전 Step 2 전체 flow 수집 금지
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    universe, stats = build_universe_frame()
    UNIVERSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    universe.to_parquet(UNIVERSE_PATH, index=False)
    write_report(universe, stats)


if __name__ == "__main__":
    main()
