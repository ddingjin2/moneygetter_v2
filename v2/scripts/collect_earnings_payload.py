from __future__ import annotations

import argparse
import gc
import json
import math
import os
import re
import shutil
import sys
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.earnings import (  # noqa: E402
    EARNINGS_EVENTS_PATH,
    RAW_DART_DIR,
    add_yoy_fields,
    compute_sue,
    extract_financial_metrics,
    order_earnings_columns,
)


OPENDART_BASE_URL = "https://opendart.fss.or.kr/api"
FINANCIAL_ENDPOINT = f"{OPENDART_BASE_URL}/fnlttSinglAcntAll.json"
LIST_ENDPOINT = f"{OPENDART_BASE_URL}/list.json"
CHECKPOINT_PATH = Path("v2/data/cache/collection_checkpoint.json")
REPORT_PATH = Path("v2/reports/pr2_5_recollection_report.md")
FINANCIAL_CACHE_RE = re.compile(
    r"^fnlttSinglAcntAll_(?P<corp_code>\d+)_(?P<business_year>\d{4})_"
    r"(?P<reprt_code>110\d{2})_(?P<fs_div>CFS|OFS)\.json$"
)
VALUE_COLUMNS = ["revenue", "operating_income", "net_income", "total_assets", "total_equity"]
PRIMARY_VALUE_COLUMNS = ["revenue", "operating_income", "net_income"]
DERIVED_COLUMNS = [
    "prev_revenue",
    "prev_operating_income",
    "prev_net_income",
    "eps",
    "eps_basis",
    "prior_year_same_quarter_eps",
    "eps_std_past_8q",
    "sue",
]


class RateLimiter:
    def __init__(self, max_per_minute: int = 80) -> None:
        self.max_per_minute = max_per_minute
        self.calls: deque[float] = deque()

    def acquire(self) -> None:
        while True:
            now = monotonic()
            while self.calls and now - self.calls[0] > 60:
                self.calls.popleft()
            if len(self.calls) < self.max_per_minute:
                self.calls.append(monotonic())
                return
            sleep_for = 60 - (now - self.calls[0]) + 0.1
            sleep(max(sleep_for, 0.1))


@dataclass(frozen=True)
class CollectionPlan:
    total_events: int
    raw_dart_files: int
    financial_payload_files: int
    cached_events: int
    cached_parse_needed: int
    cached_normal: int
    missing_events: int
    checkpoint_completed: int
    cached_remaining: int
    new_fetch_required: int
    expected_api_calls: int
    expected_minutes: float


@dataclass(frozen=True)
class EventResult:
    rcept_no: str
    result_type: str
    metrics: dict[str, float]
    fs_div: str
    source: str
    api_calls: int
    reason: str


def require_env_api_key() -> str:
    api_key = os.environ.get("OPENDART_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENDART_API_KEY is not set in the process environment.")
    return api_key


def mask_api_key(message: object) -> str:
    return re.sub(r"(crtfc_key=)[^&\s]+", r"\1<redacted>", str(message))


def validate_api_key(api_key: str) -> None:
    params = {
        "crtfc_key": api_key,
        "corp_code": "00126380",
        "bgn_de": "20240101",
        "end_de": "20240331",
    }
    try:
        response = requests.get(LIST_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        raise RuntimeError(f"API key validation request failed: {mask_api_key(exc)}") from None
    if str(data.get("status")) != "000":
        raise RuntimeError(f"API key invalid: {data}")
    print(f"API OK. Test query returned {data['total_count']} filings.", flush=True)


def financial_cache_path(raw_dir: Path, corp_code: str, business_year: int, reprt_code: str, fs_div: str) -> Path:
    return raw_dir / f"fnlttSinglAcntAll_{corp_code}_{business_year}_{reprt_code}_{fs_div}.json"


def event_cache_key(row: Any) -> tuple[str, int, str]:
    return (str(row.corp_code), int(str(row.fiscal_quarter)[:4]), str(row.reprt_code))


def collect_cached_financial_keys(raw_dir: Path) -> tuple[set[tuple[str, int, str]], int]:
    keys: set[tuple[str, int, str]] = set()
    payload_files = 0
    if not raw_dir.exists():
        return keys, payload_files
    for path in raw_dir.iterdir():
        if not path.is_file():
            continue
        match = FINANCIAL_CACHE_RE.match(path.name)
        if match is None:
            continue
        payload_files += 1
        keys.add(
            (
                match.group("corp_code"),
                int(match.group("business_year")),
                match.group("reprt_code"),
            )
        )
    return keys, payload_files


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_checkpoint(
    *,
    path: Path,
    baseline_stats: dict[str, Any],
    completed_rcept_nos: set[str],
    metric_rcept_nos: set[str],
    no_data_rcept_nos: set[str],
    metrics_missing_rcept_nos: set[str],
    failed_events: list[dict[str, Any]],
    counters: Counter[str],
    api_calls: int,
) -> None:
    checkpoint = {
        "baseline_stats": baseline_stats,
        "collected_rcept_nos": sorted(completed_rcept_nos),
        "completed_rcept_nos": sorted(completed_rcept_nos),
        "financial_metric_rcept_nos": sorted(metric_rcept_nos),
        "no_data_rcept_nos": sorted(no_data_rcept_nos),
        "metrics_missing_rcept_nos": sorted(metrics_missing_rcept_nos),
        "failed_rcept_nos": [item["rcept_no"] for item in failed_events],
        "failed_events": failed_events,
        "reason_counts": dict(counters),
        "api_calls": api_calls,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(checkpoint, handle, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def raw_file_count(raw_dir: Path) -> int:
    if not raw_dir.exists():
        return 0
    return sum(1 for path in raw_dir.iterdir() if path.is_file())


def all_primary_values_missing(events: pd.DataFrame) -> pd.Series:
    return events[PRIMARY_VALUE_COLUMNS].isna().all(axis=1)


def build_plan(
    events: pd.DataFrame,
    *,
    raw_dir: Path,
    completed_rcept_nos: set[str],
    max_per_minute: int,
) -> CollectionPlan:
    cached_keys, financial_payload_files = collect_cached_financial_keys(raw_dir)
    event_keys = events.apply(lambda row: (str(row["corp_code"]), int(str(row["fiscal_quarter"])[:4]), str(row["reprt_code"])), axis=1)
    has_cached_payload = event_keys.isin(cached_keys)
    missing = all_primary_values_missing(events)
    completed = events["rcept_no"].astype(str).isin(completed_rcept_nos)

    cached_events = int(has_cached_payload.sum())
    cached_parse_needed = int((has_cached_payload & missing).sum())
    cached_normal = cached_events - cached_parse_needed
    cached_remaining = int((missing & has_cached_payload & ~completed).sum())
    new_fetch_required = int((missing & ~has_cached_payload & ~completed).sum())
    expected_api_calls = new_fetch_required * 2
    expected_minutes = expected_api_calls / max_per_minute if max_per_minute else math.nan
    return CollectionPlan(
        total_events=int(len(events)),
        raw_dart_files=raw_file_count(raw_dir),
        financial_payload_files=financial_payload_files,
        cached_events=cached_events,
        cached_parse_needed=cached_parse_needed,
        cached_normal=cached_normal,
        missing_events=int(missing.sum()),
        checkpoint_completed=int(completed.sum()),
        cached_remaining=cached_remaining,
        new_fetch_required=new_fetch_required,
        expected_api_calls=expected_api_calls,
        expected_minutes=expected_minutes,
    )


def print_plan(plan: CollectionPlan, *, max_per_minute: int) -> None:
    print("[수집 계획]", flush=True)
    print(f"전체 이벤트: {plan.total_events:,}", flush=True)
    print(f"raw_dart 파일 수: {plan.raw_dart_files:,}", flush=True)
    print(f"재무 payload 파일 수: {plan.financial_payload_files:,}", flush=True)
    print(
        "이미 캐시됨: "
        f"{plan.cached_events:,} 이벤트 "
        f"(파싱 필요: {plan.cached_parse_needed:,}, 정상: {plan.cached_normal:,})",
        flush=True,
    )
    print(f"재무 3필드 모두 결측: {plan.missing_events:,} 이벤트", flush=True)
    print(f"체크포인트로 이미 처리됨: {plan.checkpoint_completed:,} 이벤트", flush=True)
    print(f"캐시 재파싱 필요: {plan.cached_remaining:,} 이벤트", flush=True)
    print(f"신규 수집 필요: {plan.new_fetch_required:,} 이벤트", flush=True)
    print(
        "예상 API 호출 수: "
        f"최대 {plan.expected_api_calls:,} "
        "(공시 리스트 재조회 없음, 재무 CFS/OFS fallback 기준)",
        flush=True,
    )
    print(
        f"예상 소요 시간: {plan.expected_minutes:,.1f}분 "
        f"(rate limit 분당 {max_per_minute} 호출 가정)",
        flush=True,
    )


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    tmp_path.replace(path)


def fetch_with_retry(
    url: str,
    params: dict[str, Any],
    *,
    rate_limiter: RateLimiter,
    max_attempts: int = 5,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            rate_limiter.acquire()
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            status = str(data.get("status", "000"))
            if status == "013":
                return data
            if status == "020":
                sleep(60)
                continue
            if status != "000":
                raise ValueError(f"API error: {data}")
            return data
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == max_attempts - 1:
                raise RuntimeError(f"OPENDART request failed: {mask_api_key(exc)}") from None
            sleep(2**attempt)
    raise RuntimeError(f"OPENDART request failed after {max_attempts} attempts: {mask_api_key(last_error)}")


def load_or_fetch_payload(
    *,
    api_key: str,
    raw_dir: Path,
    corp_code: str,
    business_year: int,
    reprt_code: str,
    fs_div: str,
    rate_limiter: RateLimiter,
) -> tuple[dict[str, Any], str]:
    cache_path = financial_cache_path(raw_dir, corp_code, business_year, reprt_code, fs_div)
    if cache_path.exists():
        return read_json(cache_path), "cache"

    payload = fetch_with_retry(
        FINANCIAL_ENDPOINT,
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": str(business_year),
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        },
        rate_limiter=rate_limiter,
    )
    write_json_atomic(cache_path, payload)
    return payload, "api"


def empty_metrics() -> dict[str, float]:
    return {column: math.nan for column in VALUE_COLUMNS}


def has_any_metric(metrics: dict[str, float]) -> bool:
    return any(not math.isnan(float(value)) for value in metrics.values())


def process_event(
    *,
    row: Any,
    api_key: str,
    raw_dir: Path,
    rate_limiter: RateLimiter,
) -> EventResult:
    corp_code = str(row.corp_code)
    business_year = int(str(row.fiscal_quarter)[:4])
    reprt_code = str(row.reprt_code)
    total_api_calls = 0
    reasons: list[str] = []
    last_source = "cache"

    for fs_div in ("CFS", "OFS"):
        payload, source = load_or_fetch_payload(
            api_key=api_key,
            raw_dir=raw_dir,
            corp_code=corp_code,
            business_year=business_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
            rate_limiter=rate_limiter,
        )
        last_source = source
        total_api_calls += int(source == "api")
        status = str(payload.get("status", "000"))
        if status == "013":
            reasons.append(f"{fs_div}:no_data")
            continue
        if status != "000":
            reasons.append(f"{fs_div}:status_{status}")
            continue

        metrics = extract_financial_metrics(payload)
        if has_any_metric(metrics):
            return EventResult(
                rcept_no=str(row.rcept_no),
                result_type="metrics",
                metrics=metrics,
                fs_div=fs_div,
                source=source,
                api_calls=total_api_calls,
                reason=f"{fs_div}:metrics",
            )
        reasons.append(f"{fs_div}:metrics_missing")

    result_type = "no_data" if reasons and all(reason.endswith("no_data") for reason in reasons) else "metrics_missing"
    return EventResult(
        rcept_no=str(row.rcept_no),
        result_type=result_type,
        metrics=empty_metrics(),
        fs_div="",
        source=last_source,
        api_calls=total_api_calls,
        reason=";".join(reasons) if reasons else "not_attempted",
    )


def apply_result(events: pd.DataFrame, index: int, result: EventResult) -> None:
    if result.result_type != "metrics":
        return
    for column in VALUE_COLUMNS:
        events.at[index, column] = result.metrics[column]
    events.at[index, "fs_div"] = result.fs_div
    events.at[index, "source_collected_at"] = pd.Timestamp.utcnow().tz_localize(None)


def rebuild_derived(events: pd.DataFrame) -> pd.DataFrame:
    base = events.drop(columns=[column for column in DERIVED_COLUMNS if column in events.columns]).copy()
    rebuilt = add_yoy_fields(base)
    rebuilt = compute_sue(rebuilt)
    return order_earnings_columns(rebuilt)


def write_events_atomic(events: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp.parquet")
    events.to_parquet(tmp_path, index=False)
    tmp_path.replace(path)


def ensure_backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.stem}.pr2_5_backup_{timestamp}{path.suffix}")
    shutil.copy2(path, backup_path)
    return backup_path


def recover_baseline_stats(events: pd.DataFrame, raw_dir: Path, earnings_path: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
    baseline = checkpoint.get("baseline_stats")
    if isinstance(baseline, dict):
        return baseline

    backup_paths = sorted(earnings_path.parent.glob(f"{earnings_path.stem}.pr2_5_backup_*{earnings_path.suffix}"))
    if not backup_paths:
        return frame_stats(events, raw_dir)

    backup_events = pd.read_parquet(backup_paths[0])
    stats = frame_stats(backup_events, raw_dir)
    api_calls = int(checkpoint.get("api_calls") or 0)
    stats["raw_dart_files"] = max(0, raw_file_count(raw_dir) - api_calls)
    stats["financial_payload_files"] = max(0, collect_cached_financial_keys(raw_dir)[1] - api_calls)
    return stats


def frame_stats(events: pd.DataFrame, raw_dir: Path) -> dict[str, Any]:
    revenue_pair = events["revenue"].notna() & events["prev_revenue"].notna()
    return {
        "raw_dart_files": raw_file_count(raw_dir),
        "financial_payload_files": collect_cached_financial_keys(raw_dir)[1],
        "sue_non_null": int(events["sue"].notna().sum()) if "sue" in events else 0,
        "revenue_non_null_ratio": float(events["revenue"].notna().mean()) if len(events) else math.nan,
        "yoy_pair_ratio": float(revenue_pair.mean()) if len(events) else math.nan,
    }


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "(empty)"
    lines = ["| " + " | ".join(columns) + " |"]
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def format_int(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return f"{int(value):,}"


def format_ratio(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:.2%}"


def build_recollection_report(
    *,
    before_stats: dict[str, Any],
    after_events: pd.DataFrame,
    after_stats: dict[str, Any],
    counters: Counter[str],
    failed_events: list[dict[str, Any]],
    plan: CollectionPlan,
    report_path: Path,
) -> None:
    after = after_events.copy()
    after["year"] = pd.to_datetime(after["rcept_dt"]).dt.year
    sue_by_year = (
        after.loc[after["sue"].notna()]
        .groupby("year")
        .size()
        .reset_index(name="sue_non_null")
        .sort_values("year")
    )
    full_years = sue_by_year.loc[sue_by_year["year"].between(2019, 2025)]
    annual_mean = float(full_years["sue_non_null"].mean()) if len(full_years) else 0.0
    annual_min = int(full_years["sue_non_null"].min()) if len(full_years) else 0
    rerun_recommended = annual_mean >= 500

    unresolved = after.loc[all_primary_values_missing(after)].copy()
    concentration = (
        unresolved.groupby(["stock_code"], dropna=False)
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="remaining_missing_events")
    )

    comparison_rows = [
        {
            "지표": "raw_dart 캐시 파일 수",
            "수집 전": format_int(before_stats["raw_dart_files"]),
            "수집 후": format_int(after_stats["raw_dart_files"]),
            "변화": format_int(after_stats["raw_dart_files"] - before_stats["raw_dart_files"]),
        },
        {
            "지표": "재무 payload 파일 수",
            "수집 전": format_int(before_stats["financial_payload_files"]),
            "수집 후": format_int(after_stats["financial_payload_files"]),
            "변화": format_int(after_stats["financial_payload_files"] - before_stats["financial_payload_files"]),
        },
        {
            "지표": "SUE 계산 가능 이벤트 수",
            "수집 전": format_int(before_stats["sue_non_null"]),
            "수집 후": format_int(after_stats["sue_non_null"]),
            "변화": format_int(after_stats["sue_non_null"] - before_stats["sue_non_null"]),
        },
        {
            "지표": "revenue non-null 비율",
            "수집 전": format_ratio(before_stats["revenue_non_null_ratio"]),
            "수집 후": format_ratio(after_stats["revenue_non_null_ratio"]),
            "변화": format_ratio(after_stats["revenue_non_null_ratio"] - before_stats["revenue_non_null_ratio"]),
        },
        {
            "지표": "YoY pair 가능 비율",
            "수집 전": format_ratio(before_stats["yoy_pair_ratio"]),
            "수집 후": format_ratio(after_stats["yoy_pair_ratio"]),
            "변화": format_ratio(after_stats["yoy_pair_ratio"] - before_stats["yoy_pair_ratio"]),
        },
    ]

    reason_rows = [
        {"reason": reason, "count": count}
        for reason, count in sorted(counters.items(), key=lambda item: (-item[1], item[0]))
    ]
    hard_failure_rows = pd.DataFrame(failed_events)
    if not hard_failure_rows.empty:
        hard_failure_summary = (
            hard_failure_rows.groupby("reason", dropna=False)
            .size()
            .sort_values(ascending=False)
            .reset_index(name="count")
            .to_dict("records")
        )
    else:
        hard_failure_summary = []

    sue_year_rows = sue_by_year.to_dict("records")
    concentration_rows = concentration.to_dict("records")

    lines = [
        "# PR-2.5 OPENDART 재무 Payload 재수집 리포트",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 1. 수집 전후 비교",
        markdown_table(comparison_rows, ["지표", "수집 전", "수집 후", "변화"]),
        "",
        "## 2. 수집 실패 분석",
        f"- 계획상 신규 수집 필요 이벤트: {plan.new_fetch_required:,}",
        f"- 캐시 재파싱 대상 이벤트: {plan.cached_remaining:,}",
        f"- hard failure 이벤트 수: {len(failed_events):,}",
        f"- OPENDART 013/no data 이벤트 수: {counters.get('no_data', 0):,}",
        f"- status 000이나 parser metric 미검출 이벤트 수: {counters.get('metrics_missing', 0):,}",
        "",
        "### Reason Distribution",
        markdown_table(reason_rows, ["reason", "count"]),
        "",
        "### Hard Failure Distribution",
        markdown_table(hard_failure_summary, ["reason", "count"]),
        "",
        "### Remaining Missing Concentration",
        markdown_table(concentration_rows, ["stock_code", "remaining_missing_events"]),
        "",
        "## 3. PR-3 재실행 타당성",
        f"- 전체 SUE 계산 가능 이벤트 수: {after_stats['sue_non_null']:,}",
        f"- 2019-2025 연평균 SUE 샘플 수: {annual_mean:,.1f}",
        f"- 2019-2025 연최소 SUE 샘플 수: {annual_min:,}",
        f"- SUE 샘플 수가 연 500건 이상 달성했는가: {'yes' if annual_mean >= 500 else 'no'}",
        f"- PR-3 재실행 권고: {'yes' if rerun_recommended else 'no'}",
        "",
        "### Yearly SUE Availability",
        markdown_table(sue_year_rows, ["year", "sue_non_null"]),
        "",
        "## 4. 남은 리스크",
        f"- 재무 3필드가 모두 결측인 잔여 이벤트 수: {int(all_primary_values_missing(after).sum()):,}",
        "- OPENDART 013은 해당 API의 재무제표 payload 부재로 간주했다.",
        "- status 000이지만 metric이 미검출된 이벤트는 계정명 매핑 보강 여지가 있다.",
        "- 연평균 SUE 샘플이 500건 미만이면 FnGuide 등 유료 데이터 보완을 재검토해야 한다.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def select_remaining_events(events: pd.DataFrame, completed_rcept_nos: set[str], raw_dir: Path) -> pd.DataFrame:
    cached_keys, _ = collect_cached_financial_keys(raw_dir)
    missing = events.loc[all_primary_values_missing(events)].copy()
    missing = missing.loc[~missing["rcept_no"].astype(str).isin(completed_rcept_nos)].copy()
    if missing.empty:
        return missing
    missing["_has_cached_payload"] = missing.apply(
        lambda row: (str(row["corp_code"]), int(str(row["fiscal_quarter"])[:4]), str(row["reprt_code"])) in cached_keys,
        axis=1,
    )
    missing = missing.sort_values(["_has_cached_payload", "rcept_dt", "stock_code"], ascending=[False, True, True])
    return missing.drop(columns=["_has_cached_payload"])


def collect_payloads(
    *,
    events: pd.DataFrame,
    api_key: str,
    raw_dir: Path,
    output_path: Path,
    checkpoint_path: Path,
    checkpoint_interval: int,
    max_per_minute: int,
    max_events: int | None,
    max_runtime_minutes: float | None,
    baseline_stats: dict[str, Any],
    plan: CollectionPlan,
    report_path: Path,
) -> None:
    checkpoint = load_checkpoint(checkpoint_path)
    completed_rcept_nos = set(map(str, checkpoint.get("completed_rcept_nos") or checkpoint.get("collected_rcept_nos") or []))
    metric_rcept_nos = set(map(str, checkpoint.get("financial_metric_rcept_nos") or []))
    no_data_rcept_nos = set(map(str, checkpoint.get("no_data_rcept_nos") or []))
    metrics_missing_rcept_nos = set(map(str, checkpoint.get("metrics_missing_rcept_nos") or []))
    failed_events = list(checkpoint.get("failed_events") or [])
    counters = Counter(checkpoint.get("reason_counts") or {})
    api_calls = int(checkpoint.get("api_calls") or 0)

    remaining = select_remaining_events(events, completed_rcept_nos, raw_dir)
    if max_events is not None:
        remaining = remaining.head(max_events)

    total = len(remaining)
    rate_limiter = RateLimiter(max_per_minute=max_per_minute)
    start = monotonic()
    last_progress = start
    processed = 0
    consecutive_failures = 0

    def persist() -> None:
        rebuilt = rebuild_derived(events)
        write_events_atomic(rebuilt, output_path)
        save_checkpoint(
            path=checkpoint_path,
            baseline_stats=baseline_stats,
            completed_rcept_nos=completed_rcept_nos,
            metric_rcept_nos=metric_rcept_nos,
            no_data_rcept_nos=no_data_rcept_nos,
            metrics_missing_rcept_nos=metrics_missing_rcept_nos,
            failed_events=failed_events,
            counters=counters,
            api_calls=api_calls,
        )
        after_stats = frame_stats(rebuilt, raw_dir)
        build_recollection_report(
            before_stats=baseline_stats,
            after_events=rebuilt,
            after_stats=after_stats,
            counters=counters,
            failed_events=failed_events,
            plan=plan,
            report_path=report_path,
        )
        gc.collect()

    for index, row in remaining.iterrows():
        elapsed_minutes = (monotonic() - start) / 60
        if max_runtime_minutes is not None and elapsed_minutes >= max_runtime_minutes:
            print(f"[중단] max runtime {max_runtime_minutes}분 도달. 체크포인트 저장 후 종료합니다.", flush=True)
            break

        try:
            result = process_event(row=row, api_key=api_key, raw_dir=raw_dir, rate_limiter=rate_limiter)
            api_calls += result.api_calls
            apply_result(events, int(index), result)
            completed_rcept_nos.add(result.rcept_no)
            counters[result.result_type] += 1
            counters[result.reason] += 1
            if result.result_type == "metrics":
                metric_rcept_nos.add(result.rcept_no)
            elif result.result_type == "no_data":
                no_data_rcept_nos.add(result.rcept_no)
            elif result.result_type == "metrics_missing":
                metrics_missing_rcept_nos.add(result.rcept_no)
            consecutive_failures = 0
        except Exception as exc:  # noqa: BLE001 - persist and continue by design.
            reason = f"{type(exc).__name__}: {exc}"
            failed_events.append(
                {
                    "rcept_no": str(row.rcept_no),
                    "corp_code": str(row.corp_code),
                    "stock_code": str(row.stock_code),
                    "fiscal_quarter": str(row.fiscal_quarter),
                    "reprt_code": str(row.reprt_code),
                    "reason": reason[:500],
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
            )
            counters["hard_failure"] += 1
            counters[reason[:120]] += 1
            consecutive_failures += 1
            if consecutive_failures >= 30:
                persist()
                raise RuntimeError("30 consecutive collection failures. Stopping for API/network inspection.") from exc
            if consecutive_failures >= 10:
                print("[경고] 연속 10건 실패. 60초 대기 후 계속합니다.", flush=True)
                sleep(60)

        processed += 1
        now = monotonic()
        if processed % checkpoint_interval == 0:
            persist()
            print(
                f"[체크포인트] {processed:,}/{total:,} 처리 | "
                f"metrics: {counters.get('metrics', 0):,} | "
                f"no_data: {counters.get('no_data', 0):,} | "
                f"failed: {counters.get('hard_failure', 0):,}",
                flush=True,
            )
        if now - last_progress >= 600:
            rate = processed / max((now - start) / 60, 0.001)
            eta = (total - processed) / rate if rate else math.nan
            print(
                f"[진행] 진행률: {processed:,}/{total:,} ({processed / total:.1%}) | "
                f"수집 성공: {counters.get('metrics', 0):,} | "
                f"실패: {counters.get('hard_failure', 0):,} | "
                f"ETA: {eta:,.1f}분",
                flush=True,
            )
            last_progress = now

    persist()
    print(
        f"[완료/저장] 처리: {processed:,}/{total:,} | "
        f"metrics: {counters.get('metrics', 0):,} | "
        f"no_data: {counters.get('no_data', 0):,} | "
        f"metrics_missing: {counters.get('metrics_missing', 0):,} | "
        f"hard_failure: {counters.get('hard_failure', 0):,} | "
        f"api_calls: {api_calls:,}",
        flush=True,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect missing OPENDART financial payloads for PR-2.5.")
    parser.add_argument("--earnings-path", default=str(EARNINGS_EVENTS_PATH))
    parser.add_argument("--raw-cache-dir", default=str(RAW_DART_DIR))
    parser.add_argument("--checkpoint-path", default=str(CHECKPOINT_PATH))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--max-per-minute", type=int, default=80)
    parser.add_argument("--checkpoint-interval", type=int, default=100)
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--max-runtime-minutes", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-start-delay", action="store_true")
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    earnings_path = Path(args.earnings_path)
    raw_dir = Path(args.raw_cache_dir)
    checkpoint_path = Path(args.checkpoint_path)
    report_path = Path(args.report_path)

    api_key = require_env_api_key()
    validate_api_key(api_key)

    if not earnings_path.exists():
        raise FileNotFoundError(earnings_path)
    events = pd.read_parquet(earnings_path)
    checkpoint = load_checkpoint(checkpoint_path)
    completed_rcept_nos = set(map(str, checkpoint.get("completed_rcept_nos") or checkpoint.get("collected_rcept_nos") or []))
    baseline_stats = recover_baseline_stats(events, raw_dir, earnings_path, checkpoint)
    plan = build_plan(
        events,
        raw_dir=raw_dir,
        completed_rcept_nos=completed_rcept_nos,
        max_per_minute=args.max_per_minute,
    )
    print_plan(plan, max_per_minute=args.max_per_minute)
    if args.dry_run:
        return

    if not completed_rcept_nos:
        backup_path = ensure_backup(earnings_path)
        if backup_path is not None:
            print(f"[백업] {backup_path}", flush=True)
    else:
        print(f"[재개] checkpoint completed={len(completed_rcept_nos):,}; 추가 백업은 생략합니다.", flush=True)

    delay_message = "5초 대기 후 " if not args.no_start_delay else ""
    print(f"시작합니다. {delay_message}수집을 진행합니다.", flush=True)
    if not args.no_start_delay:
        sleep(5)

    collect_payloads(
        events=events,
        api_key=api_key,
        raw_dir=raw_dir,
        output_path=earnings_path,
        checkpoint_path=checkpoint_path,
        checkpoint_interval=args.checkpoint_interval,
        max_per_minute=args.max_per_minute,
        max_events=args.max_events,
        max_runtime_minutes=args.max_runtime_minutes,
        baseline_stats=baseline_stats,
        plan=plan,
        report_path=report_path,
    )


if __name__ == "__main__":
    main()
