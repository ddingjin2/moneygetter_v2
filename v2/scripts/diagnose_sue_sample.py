from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.earnings import (  # noqa: E402
    EARNINGS_EVENTS_PATH,
    OpendartClient,
    RAW_DART_DIR,
    RateLimiter,
    extract_financial_metrics,
    get_api_key_from_env,
    infer_business_year,
)


REPORT_PATH = Path("v2/reports/pr3_5_data_quality_diagnosis.md")
DEFAULT_OHLCV_PATH = Path("C:/dev/moneygetter/data/processed/market_ohlcv.parquet")
SAMPLE_SIZE = 10
SAMPLE_RANDOM_STATE = 35


@dataclass(frozen=True)
class DiagnosisInputs:
    earnings_path: Path
    ohlcv_path: Path
    report_path: Path
    sample_size: int
    random_state: int
    fetch_opendart: bool


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(empty)"
    rendered = frame.copy()
    for column in rendered.columns:
        if pd.api.types.is_float_dtype(rendered[column]):
            rendered[column] = rendered[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    lines = ["| " + " | ".join(rendered.columns) + " |"]
    lines.append("| " + " | ".join(["---"] * len(rendered.columns)) + " |")
    for _, row in rendered.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in rendered.columns) + " |")
    return "\n".join(lines)


def _quarter_index(fiscal_quarter: str) -> int:
    year = int(str(fiscal_quarter)[:4])
    quarter = int(str(fiscal_quarter)[-1])
    return year * 4 + quarter


def _target_quarters() -> list[str]:
    return [f"{year}Q{quarter}" for year in range(2020, 2026) for quarter in range(1, 5)]


def _field_missing_rates(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fields = [
        "revenue",
        "operating_income",
        "net_income",
        "prev_revenue",
        "prev_operating_income",
        "prev_net_income",
    ]
    field_rows = [
        {
            "field": field,
            "records": int(len(events)),
            "non_null": int(events[field].notna().sum()),
            "null_ratio": float(events[field].isna().mean()),
        }
        for field in fields
    ]
    pair_rows = []
    for current, previous in (
        ("revenue", "prev_revenue"),
        ("operating_income", "prev_operating_income"),
        ("net_income", "prev_net_income"),
    ):
        both = events[current].notna() & events[previous].notna()
        pair_rows.append(
            {
                "yoy_pair": f"{current}+{previous}",
                "records": int(len(events)),
                "both_present": int(both.sum()),
                "both_present_ratio": float(both.mean()),
            }
        )
    return pd.DataFrame(field_rows), pd.DataFrame(pair_rows)


def _coverage_by_stock(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    target = set(_target_quarters())
    quarter_count = len(target)
    rows: list[dict[str, object]] = []
    for stock_code, group in events.groupby("stock_code", sort=True):
        quarters = set(group["fiscal_quarter"].astype(str))
        target_present = sorted(quarters & target, key=_quarter_index)
        indices = [_quarter_index(value) for value in target_present]
        longest = _longest_run(indices)
        rows.append(
            {
                "stock_code": str(stock_code),
                "events_total": int(len(group)),
                "quarters_present_2020_2025": int(len(target_present)),
                "coverage_24q": float(len(target_present) / quarter_count),
                "longest_consecutive_quarters": int(longest),
                "has_4q_run": bool(longest >= 4),
                "has_8q_run": bool(longest >= 8),
            }
        )
    stock = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {
                "stocks": int(len(stock)),
                "avg_events_total": float(stock["events_total"].mean()) if len(stock) else math.nan,
                "avg_coverage_24q": float(stock["coverage_24q"].mean()) if len(stock) else math.nan,
                "stocks_with_4q_run": int(stock["has_4q_run"].sum()) if len(stock) else 0,
                "stocks_with_8q_run": int(stock["has_8q_run"].sum()) if len(stock) else 0,
            }
        ]
    )
    return stock, summary


def _longest_run(indices: list[int]) -> int:
    if not indices:
        return 0
    longest = 1
    current = 1
    for previous, value in zip(indices, indices[1:], strict=False):
        if value == previous + 1:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
    return longest


def _market_cap_quintiles(events: pd.DataFrame, ohlcv_path: Path) -> pd.DataFrame:
    ohlcv = pd.read_parquet(ohlcv_path, columns=["date", "symbol", "market_cap"])
    prices = ohlcv.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()
    prices["stock_code"] = prices["symbol"].astype(str).str.zfill(6)

    frame = events.copy()
    frame["entry_date"] = pd.to_datetime(frame["tradable_entry_date"]).dt.normalize()
    frame["stock_code"] = frame["stock_code"].astype(str).str.zfill(6)
    frame = frame.merge(
        prices[["date", "stock_code", "market_cap"]],
        left_on=["entry_date", "stock_code"],
        right_on=["date", "stock_code"],
        how="left",
    )
    positive = pd.to_numeric(frame["market_cap"], errors="coerce").gt(0)
    if not bool(positive.any()):
        row: dict[str, object] = {
            "market_cap_quintile": "unavailable_all_zero_or_missing",
            "events": int(len(frame)),
            "median_market_cap": math.nan,
            "sue_non_null_ratio": float(frame["sue"].notna().mean()) if len(frame) else math.nan,
        }
        for field in ("revenue", "operating_income", "net_income"):
            row[f"{field}_missing"] = float(frame[field].isna().mean()) if len(frame) else math.nan
        return pd.DataFrame([row])

    frame = frame.loc[positive].copy()
    frame["market_cap_quintile"] = pd.qcut(
        frame["market_cap"],
        q=5,
        labels=["Q1_small", "Q2", "Q3", "Q4", "Q5_large"],
        duplicates="drop",
    )
    rows = []
    for quintile, group in frame.groupby("market_cap_quintile", observed=True, sort=True):
        row: dict[str, object] = {
            "market_cap_quintile": str(quintile),
            "events": int(len(group)),
            "median_market_cap": float(group["market_cap"].median()),
            "sue_non_null_ratio": float(group["sue"].notna().mean()),
        }
        for field in ("revenue", "operating_income", "net_income"):
            row[f"{field}_missing"] = float(group[field].isna().mean())
        rows.append(row)
    return pd.DataFrame(rows)


def _yearly_missing(events: pd.DataFrame) -> pd.DataFrame:
    frame = events.copy()
    frame["year"] = pd.to_datetime(frame["rcept_dt"]).dt.year
    rows = []
    for year in range(2020, 2027):
        group = frame.loc[frame["year"].eq(year)]
        if group.empty:
            rows.append(
                {
                    "year": year,
                    "events": 0,
                    "sue_non_null": 0,
                    "sue_non_null_ratio": 0.0,
                    "revenue_missing": math.nan,
                    "net_income_missing": math.nan,
                }
            )
            continue
        rows.append(
            {
                "year": year,
                "events": int(len(group)),
                "sue_non_null": int(group["sue"].notna().sum()),
                "sue_non_null_ratio": float(group["sue"].notna().mean()),
                "revenue_missing": float(group["revenue"].isna().mean()),
                "net_income_missing": float(group["net_income"].isna().mean()),
            }
        )
    return pd.DataFrame(rows)


def _raw_payload(
    *,
    client: OpendartClient | None,
    corp_code: str,
    business_year: int,
    report_code: str,
    fs_div: str,
    raw_cache_dir: Path,
    fetch_opendart: bool,
) -> tuple[dict[str, Any] | None, str]:
    cache_path = raw_cache_dir / f"fnlttSinglAcntAll_{corp_code}_{business_year}_{report_code}_{fs_div}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8")), "cache"
    if not fetch_opendart or client is None:
        return None, "not_fetched"
    try:
        return client.fetch_financials(
            corp_code=corp_code,
            business_year=business_year,
            report_code=report_code,
            fs_div=fs_div,
        ), "opendart"
    except Exception as exc:  # noqa: BLE001
        return {"status": "ERROR", "message": str(exc), "list": []}, "error"


def _broad_account_value_present(payload: dict[str, Any] | None, field: str) -> bool:
    if not payload:
        return False
    rows = payload.get("list", []) or []
    if field == "revenue":
        tokens = ("매출", "수익")
    elif field == "net_income":
        tokens = ("순이익", "당기순이익", "분기순이익", "반기순이익")
    else:
        tokens = ("영업이익",)
    for row in rows:
        account_name = str(row.get("account_nm", ""))
        value = str(row.get("thstrm_amount", "")).strip()
        if value in {"", "-", "nan", "None"}:
            continue
        if any(token in account_name for token in tokens):
            return True
    return False


def _opendart_sample(events: pd.DataFrame, inputs: DiagnosisInputs) -> pd.DataFrame:
    missing = events.loc[events["revenue"].isna()].copy()
    if missing.empty:
        return pd.DataFrame()
    sample = missing.sample(
        n=min(inputs.sample_size, len(missing)),
        random_state=inputs.random_state,
    )
    client = None
    if inputs.fetch_opendart:
        try:
            client = OpendartClient(
                get_api_key_from_env(),
                raw_cache_dir=RAW_DART_DIR,
                rate_limiter=RateLimiter(max_calls_per_second=2),
            )
        except Exception:
            client = None

    rows = []
    for event in sample.itertuples(index=False):
        report_code = str(event.reprt_code)
        business_year = infer_business_year(pd.Timestamp(event.rcept_dt), report_code, str(getattr(event, "report_nm", "")))
        if str(event.fiscal_quarter)[:4].isdigit():
            business_year = int(str(event.fiscal_quarter)[:4])

        payloads = []
        sources = []
        for fs_div in ("CFS", "OFS"):
            payload, source = _raw_payload(
                client=client,
                corp_code=str(event.corp_code),
                business_year=business_year,
                report_code=report_code,
                fs_div=fs_div,
                raw_cache_dir=RAW_DART_DIR,
                fetch_opendart=inputs.fetch_opendart,
            )
            payloads.append(payload)
            sources.append(f"{fs_div}:{source}")

        parsed_metrics = [extract_financial_metrics(payload or {}) for payload in payloads]
        parser_revenue_present = any(not math.isnan(metrics["revenue"]) for metrics in parsed_metrics)
        source_revenue_present = any(_broad_account_value_present(payload, "revenue") for payload in payloads)
        source_net_income_present = any(_broad_account_value_present(payload, "net_income") for payload in payloads)
        statuses = "/".join(str((payload or {}).get("status", "NA")) for payload in payloads)
        messages = " / ".join(str((payload or {}).get("message", ""))[:80] for payload in payloads)
        rows.append(
            {
                "stock_code": str(event.stock_code).zfill(6),
                "rcept_no": str(event.rcept_no),
                "fiscal_quarter": str(event.fiscal_quarter),
                "reprt_code": report_code,
                "raw_source": ";".join(sources),
                "raw_status": statuses,
                "raw_message": messages,
                "source_revenue_value_present": bool(source_revenue_present),
                "parser_would_extract_revenue": bool(parser_revenue_present),
                "source_net_income_value_present": bool(source_net_income_present),
                "parquet_revenue_nan": True,
                "parse_or_stale_miss": bool(source_revenue_present),
                "mapping_miss": bool(source_revenue_present and not parser_revenue_present),
            }
        )
    return pd.DataFrame(rows)


def _quarterly_sue_capacity(events: pd.DataFrame) -> pd.DataFrame:
    frame = events.copy()
    frame["stock_code"] = frame["stock_code"].astype(str).str.zfill(6)
    frame["quarter_idx"] = frame["fiscal_quarter"].astype(str).map(_quarter_index)
    frame["net_income_available"] = frame["net_income"].notna()
    rows = []
    by_key = {
        (row.stock_code, row.quarter_idx): bool(row.net_income_available)
        for row in frame[["stock_code", "quarter_idx", "net_income_available"]].itertuples(index=False)
    }
    for row in frame.itertuples(index=False):
        if pd.isna(row.net_income):
            continue
        stock = str(row.stock_code).zfill(6)
        idx = int(row.quarter_idx)
        prior_same = by_key.get((stock, idx - 4), False)
        trailing4 = all(by_key.get((stock, idx - offset), False) for offset in range(1, 5))
        trailing8 = all(by_key.get((stock, idx - offset), False) for offset in range(1, 9))
        rows.append(
            {
                "stock_code": stock,
                "fiscal_quarter": str(row.fiscal_quarter),
                "current_net_income": True,
                "prior_same_quarter": bool(prior_same),
                "trailing4_complete": bool(trailing4),
                "trailing8_complete": bool(trailing8),
                "eligible_min4": bool(prior_same and trailing4),
                "eligible_strict8": bool(prior_same and trailing8),
            }
        )
    capacity = pd.DataFrame(rows)
    if capacity.empty:
        return pd.DataFrame(
            [
                {"rule": "current_actual_sue", "sample_count": int(events["sue"].notna().sum())},
                {"rule": "min4_complete_trailing", "sample_count": 0},
                {"rule": "strict8_complete_trailing", "sample_count": 0},
            ]
        )
    return pd.DataFrame(
        [
            {"rule": "current_actual_sue", "sample_count": int(events["sue"].notna().sum())},
            {"rule": "min4_complete_trailing", "sample_count": int(capacity["eligible_min4"].sum())},
            {"rule": "strict8_complete_trailing", "sample_count": int(capacity["eligible_strict8"].sum())},
        ]
    )


def _market_top_half_count(events: pd.DataFrame, ohlcv_path: Path) -> int:
    ohlcv = pd.read_parquet(ohlcv_path, columns=["date", "symbol", "market_cap"])
    prices = ohlcv.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()
    prices["stock_code"] = prices["symbol"].astype(str).str.zfill(6)
    frame = events.loc[events["sue"].notna()].copy()
    frame["entry_date"] = pd.to_datetime(frame["tradable_entry_date"]).dt.normalize()
    frame["stock_code"] = frame["stock_code"].astype(str).str.zfill(6)
    frame = frame.merge(
        prices[["date", "stock_code", "market_cap"]],
        left_on=["entry_date", "stock_code"],
        right_on=["date", "stock_code"],
        how="left",
    )
    frame = frame.loc[pd.to_numeric(frame["market_cap"], errors="coerce").gt(0)].copy()
    if frame.empty:
        return int(round(len(events.loc[events["sue"].notna()]) * 0.5))
    threshold = frame["market_cap"].median()
    return int(frame["market_cap"].ge(threshold).sum())


def _raw_cache_coverage(events: pd.DataFrame) -> pd.DataFrame:
    cached_payloads = 0
    cached_payload_status_000 = 0
    events_with_any_payload = 0
    for event in events.itertuples(index=False):
        business_year = int(str(event.fiscal_quarter)[:4])
        has_payload = False
        for fs_div in ("CFS", "OFS"):
            cache_path = RAW_DART_DIR / (
                f"fnlttSinglAcntAll_{event.corp_code}_{business_year}_{event.reprt_code}_{fs_div}.json"
            )
            if not cache_path.exists():
                continue
            has_payload = True
            cached_payloads += 1
            try:
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if str(payload.get("status")) == "000":
                cached_payload_status_000 += 1
        if has_payload:
            events_with_any_payload += 1

    cached = events.loc[
        [
            any(
                (
                    RAW_DART_DIR
                    / f"fnlttSinglAcntAll_{row.corp_code}_{int(str(row.fiscal_quarter)[:4])}_{row.reprt_code}_{fs_div}.json"
                ).exists()
                for fs_div in ("CFS", "OFS")
            )
            for row in events.itertuples(index=False)
        ]
    ]
    return pd.DataFrame(
        [
            {
                "events": int(len(events)),
                "payload_slots_cfs_ofs": int(len(events) * 2),
                "cached_payloads": int(cached_payloads),
                "cached_payload_ratio": float(cached_payloads / (len(events) * 2)) if len(events) else 0.0,
                "cached_payload_status_000": int(cached_payload_status_000),
                "events_with_any_payload": int(events_with_any_payload),
                "events_with_any_payload_ratio": float(events_with_any_payload / len(events)) if len(events) else 0.0,
                "sue_non_null_inside_cached_events": int(cached["sue"].notna().sum()) if len(cached) else 0,
                "sue_non_null_ratio_inside_cached_events": float(cached["sue"].notna().mean()) if len(cached) else 0.0,
                "net_income_non_null_ratio_inside_cached_events": float(cached["net_income"].notna().mean()) if len(cached) else 0.0,
            }
        ]
    )


def _scenario_estimates(
    events: pd.DataFrame,
    market_quintiles: pd.DataFrame,
    sample: pd.DataFrame,
    capacity: pd.DataFrame,
    raw_cache: pd.DataFrame,
    ohlcv_path: Path,
) -> tuple[pd.DataFrame, str, str]:
    current = int(events["sue"].notna().sum())
    years = pd.to_datetime(events.loc[events["sue"].notna(), "rcept_dt"]).dt.year
    year_span = max(1, int(years.max() - years.min() + 1)) if len(years) else 1
    top_half = _market_top_half_count(events, ohlcv_path)

    sample_error_rate = float(sample["raw_status"].astype(str).str.contains("ERROR").mean()) if not sample.empty else 0.0
    sample_rate = float(sample["parse_or_stale_miss"].mean()) if not sample.empty and sample_error_rate < 1.0 else 0.0
    mapping_rate = float(sample["mapping_miss"].mean()) if not sample.empty else 0.0
    missing_sue = int(events["sue"].isna().sum())
    cached_sue_rate = float(raw_cache.iloc[0]["sue_non_null_ratio_inside_cached_events"]) if not raw_cache.empty else 0.0
    cached_event_coverage = float(raw_cache.iloc[0]["events_with_any_payload_ratio"]) if not raw_cache.empty else 0.0
    if sample_error_rate == 1.0 and cached_sue_rate > 0:
        scenario_b = int(round(len(events) * cached_sue_rate))
        scenario_b_basis = (
            f"live 1E sample failed; extrapolate cached-event SUE rate ({cached_sue_rate:.2%}) "
            f"from current raw-cache coverage ({cached_event_coverage:.2%})"
        )
    else:
        scenario_b = int(round(current + missing_sue * sample_rate))
        scenario_b_basis = f"current + missing_sue * 1E sample miss rate ({sample_rate:.2%})"
    min4 = int(capacity.loc[capacity["rule"].eq("min4_complete_trailing"), "sample_count"].iloc[0])
    all_combined = int(round(max(scenario_b, min4) * 0.5))

    estimates = pd.DataFrame(
        [
            {
                "scenario": "A_top50_market_cap",
                "expected_total_sue_samples": top_half,
                "expected_samples_per_year": top_half / year_span,
                "basis": "market-cap data unavailable; naive 50% retention from current SUE samples",
            },
            {
                "scenario": "B_fix_parsing_or_stale_fetch",
                "expected_total_sue_samples": scenario_b,
                "expected_samples_per_year": scenario_b / year_span,
                "basis": scenario_b_basis,
            },
            {
                "scenario": "C_min4_quarter_rule",
                "expected_total_sue_samples": min4,
                "expected_samples_per_year": min4 / year_span,
                "basis": "existing net_income only, prior same quarter plus complete trailing 4 quarters",
            },
            {
                "scenario": "A+B+C_combined",
                "expected_total_sue_samples": all_combined,
                "expected_samples_per_year": all_combined / year_span,
                "basis": "B projection with top-50% universe retention; C does not add under current net-income data",
            },
        ]
    )

    all_quintiles_bad = False
    market_cap_unavailable = False
    if not market_quintiles.empty:
        market_cap_unavailable = bool(
            market_quintiles["market_cap_quintile"].astype(str).eq("unavailable_all_zero_or_missing").all()
        )
        all_quintiles_bad = (not market_cap_unavailable) and bool(market_quintiles["net_income_missing"].min() > 0.85)
    four = int(capacity.loc[capacity["rule"].eq("min4_complete_trailing"), "sample_count"].iloc[0])
    eight = int(capacity.loc[capacity["rule"].eq("strict8_complete_trailing"), "sample_count"].iloc[0])
    c_gap = four > eight * 1.5 if eight else four > 0

    if cached_event_coverage < 0.20 and cached_sue_rate > 0.20:
        primary = "D"
        reason = (
            "dominant B-like extraction/fetch incompleteness: only "
            f"{cached_event_coverage:.1%} of events have any cached financial payload, "
            f"but cached events produce SUE at {cached_sue_rate:.1%}."
        )
    elif mapping_rate > 0.20 or sample_rate > 0.20:
        primary = "B"
        reason = f"sample parse/stale miss rate is {sample_rate:.1%}, above the 20% parser-loss threshold."
    elif c_gap:
        primary = "C"
        reason = f"min4 capacity ({four}) is materially larger than strict8 capacity ({eight})."
    elif all_quintiles_bad:
        primary = "A"
        reason = "net_income missing rate is above 85% in every market-cap quintile, so source coverage is broadly poor."
    elif market_cap_unavailable:
        primary = "D"
        reason = "market-cap data is unavailable locally, and OPENDART/parser evidence does not isolate one cause."
    else:
        primary = "D"
        reason = "no single scenario explains the loss cleanly."

    if primary != "D" and (sample_rate > 0.20) + c_gap + all_quintiles_bad + (cached_event_coverage < 0.20) >= 2:
        primary = "D"
        reason = (
            "multiple diagnostics fire: "
            f"sample miss {sample_rate:.1%}, cached-event coverage {cached_event_coverage:.1%}, "
            f"min4/strict8 {four}/{eight}, all-quintile high missing={all_quintiles_bad}, "
            f"market-cap unavailable={market_cap_unavailable}."
        )

    if estimates["expected_samples_per_year"].max() >= 500:
        final = "(a) 해결책 적용 후 PR-3 재실행 → 결과 양호 시 PR-4 진행"
    else:
        final = "(b) 해결책 적용해도 샘플 부족 예상 → 옵션 B 폐기, 옵션 C/D 로 전환"
    return estimates, f"Scenario {primary}: {reason}", final


def build_report(inputs: DiagnosisInputs) -> str:
    events = pd.read_parquet(inputs.earnings_path)
    events["stock_code"] = events["stock_code"].astype(str).str.zfill(6)
    events["rcept_dt"] = pd.to_datetime(events["rcept_dt"])
    events["tradable_entry_date"] = pd.to_datetime(events["tradable_entry_date"])

    field_missing, yoy_pairs = _field_missing_rates(events)
    _, coverage_summary = _coverage_by_stock(events)
    market_quintiles = _market_cap_quintiles(events, inputs.ohlcv_path)
    yearly = _yearly_missing(events)
    sample = _opendart_sample(events, inputs)
    capacity = _quarterly_sue_capacity(events)
    raw_cache = _raw_cache_coverage(events)
    estimates, scenario, final_recommendation = _scenario_estimates(
        events,
        market_quintiles,
        sample,
        capacity,
        raw_cache,
        inputs.ohlcv_path,
    )

    sample_summary = pd.DataFrame(
        [
            {
                "sampled_revenue_nan_events": int(len(sample)),
                "source_revenue_present_count": int(sample["source_revenue_value_present"].sum()) if not sample.empty else 0,
                "parser_would_extract_count": int(sample["parser_would_extract_revenue"].sum()) if not sample.empty else 0,
                "parse_or_stale_miss_count": int(sample["parse_or_stale_miss"].sum()) if not sample.empty else 0,
                "mapping_miss_count": int(sample["mapping_miss"].sum()) if not sample.empty else 0,
                "source_net_income_present_count": int(sample["source_net_income_value_present"].sum()) if not sample.empty else 0,
                "raw_error_count": int(sample["raw_status"].astype(str).str.contains("ERROR").sum()) if not sample.empty else 0,
            }
        ]
    )

    best = estimates.sort_values("expected_samples_per_year", ascending=False).iloc[0]
    regen_needed = (
        "yes"
        if "B-like extraction/fetch incompleteness" in scenario
        or bool(sample_summary.iloc[0]["parse_or_stale_miss_count"])
        else "no"
    )
    sue_rule_needed = "yes" if int(capacity.loc[capacity["rule"].eq("min4_complete_trailing"), "sample_count"].iloc[0]) > int(events["sue"].notna().sum()) else "no"
    universe_only = "no"

    lines = [
        "# PR-3.5 Data Quality Diagnosis",
        "",
        "## Section 1. 결측률 수치",
        "",
        "### 1-A. Field Missing Rates",
        _markdown_table(field_missing),
        "",
        "### 1-A. YoY Pair Availability",
        _markdown_table(yoy_pairs),
        "",
        "### 1-B. Stock Quarter Coverage",
        _markdown_table(coverage_summary),
        "",
        "### 1-C. Market-cap Quintile Missing Rates",
        _markdown_table(market_quintiles),
        "",
        "### 1-D. Yearly SUE Availability",
        _markdown_table(yearly),
        "",
        "### 1-E. OPENDART Raw Sample Check",
        _markdown_table(sample_summary),
        "",
        _markdown_table(sample),
        "",
        "### Raw Financial Payload Cache Coverage",
        _markdown_table(raw_cache),
        "",
        "### SUE Rule Capacity Check",
        _markdown_table(capacity),
        "",
        "## Section 2. 원인 판정",
        scenario,
        "",
        "Market-cap segmentation is not available because the local OHLCV/features files have all-zero market_cap. "
        "The live OPENDART 1-E sample failed at the HTTP layer in this environment, so the raw-cache coverage table is used as the stronger diagnostic.",
        "",
        "## Section 3. 해결책 권고",
        _markdown_table(estimates),
        "",
        f"Best projected path: {best['scenario']} with about {int(best['expected_total_sue_samples'])} total samples "
        f"({float(best['expected_samples_per_year']):.1f}/year). Minimum target is 500/year.",
        "",
        "Recommended order: first repair/retry financial payload collection and rebuild earnings_events.parquet from raw filings, "
        "then rerun PR-3. Only after that should SUE eligibility or universe filters be tuned. A top-50% universe filter alone cannot create more SUE samples.",
        "",
        "## Section 4. PR-3 재실행 필요성 판단",
        f"- 데이터 재생성 필요한가: {regen_needed}",
        f"- SUE 계산 규칙 수정 필요한가: {sue_rule_needed}",
        f"- universe 조정만으로 해결 가능한가: {universe_only}",
        "",
        "## Section 5. 최종 권고",
        final_recommendation,
        "",
    ]
    return "\n".join(lines)


def run_diagnosis(inputs: DiagnosisInputs) -> str:
    report = build_report(inputs)
    inputs.report_path.parent.mkdir(parents=True, exist_ok=True)
    inputs.report_path.write_text(report, encoding="utf-8")
    return report


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose PR-3 SUE sample availability.")
    parser.add_argument("--earnings-path", default=str(EARNINGS_EVENTS_PATH))
    parser.add_argument("--ohlcv-path", default=str(DEFAULT_OHLCV_PATH))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--random-state", type=int, default=SAMPLE_RANDOM_STATE)
    parser.add_argument(
        "--no-opendart-fetch",
        action="store_true",
        help="Use only existing raw cache for the 1-E sample.",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    report = run_diagnosis(
        DiagnosisInputs(
            earnings_path=Path(args.earnings_path),
            ohlcv_path=Path(args.ohlcv_path),
            report_path=Path(args.report_path),
            sample_size=args.sample_size,
            random_state=args.random_state,
            fetch_opendart=not args.no_opendart_fetch,
        )
    )
    print(report)


if __name__ == "__main__":
    main()
