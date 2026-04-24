from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.ohlcv import load_ohlcv  # noqa: E402


REPORT_PATH = ROOT / "v2/reports/pr7_a_1_6_mini_pilot_ic.md"
FLOW_DIR = ROOT / "v2/data/cache/investor_flow_mini_pilot"
PRICE_DIR = ROOT / "v2/data/cache/prices_mini_pilot"
CHECKPOINT_PATH = FLOW_DIR / "collection_checkpoint.json"
NAVER_URL = "https://finance.naver.com/item/frgn.naver"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

FLOW_START = pd.Timestamp("2024-01-01")
FLOW_END = pd.Timestamp("2025-12-31")
PRICE_START = pd.Timestamp("2024-01-01")
PRICE_END = pd.Timestamp("2026-01-31")
VOLUME_WARMUP_START = pd.Timestamp("2023-09-01")

REGIMES = {
    "2024": (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31")),
    "2025": (pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")),
    "2025-01~04": (pd.Timestamp("2025-01-01"), pd.Timestamp("2025-04-30")),
    "2025-05~12": (pd.Timestamp("2025-05-01"), pd.Timestamp("2025-12-31")),
}

SIGNAL_ORDER = [
    "foreign_rank_5d",
    "institutional_rank_5d",
    "combined_rank_5d",
    "divergence_5d",
]
RETURN_ORDER = ["fwd_ret_5d", "fwd_ret_20d"]

SECTOR_BIAS_WARNING = (
    "> **섹터 편향 사전 고지**: Large bucket 10 종목 중 삼성전자, SK하이닉스, "
    "SK스퀘어, LG에너지솔루션, 두산에너빌리티, 한화에어로스페이스, HD현대중공업 은 "
    "2025 하반기 AI/반도체/조선/방산/원전 랠리 수혜 섹터에 속한다. 이는 2026-04 기준 "
    "KOSPI 시총 상위 10 의 자연스러운 구성이다. 2025-05 ~ 2025-12 구간은 이 섹터 "
    "동조화의 영향을 받을 수 있으므로, 판정의 1차 근거는 2024 (정상 레짐) IC 로 한다. "
    "2025-05~12 IC 는 참고 기록만."
)


@dataclass(frozen=True)
class StockSpec:
    code: str
    name: str
    sector: str
    market_cap_bucket: str


STOCKS = [
    StockSpec("005930", "삼성전자", "반도체와반도체장비", "large_top10"),
    StockSpec("000660", "SK하이닉스", "반도체와반도체장비", "large_top10"),
    StockSpec("373220", "LG에너지솔루션", "전기제품", "large_top10"),
    StockSpec("005380", "현대차", "자동차", "large_top10"),
    StockSpec("402340", "SK스퀘어", "복합기업", "large_top10"),
    StockSpec("034020", "두산에너빌리티", "기계", "large_top10"),
    StockSpec("012450", "한화에어로스페이스", "우주항공과국방", "large_top10"),
    StockSpec("207940", "삼성바이오로직스", "제약", "large_top10"),
    StockSpec("329180", "HD현대중공업", "조선", "large_top10"),
    StockSpec("000270", "기아", "자동차", "large_top10"),
    StockSpec("015360", "INVENI", "가스유틸리티", "mid_p40_60"),
    StockSpec("001940", "KISCO홀딩스", "철강", "mid_p40_60"),
    StockSpec("001340", "PKC", "화학", "mid_p40_60"),
    StockSpec("037710", "광주신세계", "백화점과일반상점", "mid_p40_60"),
    StockSpec("108670", "LX하우시스", "건축자재", "mid_p40_60"),
    StockSpec("000390", "삼화페인트", "건축자재", "mid_p40_60"),
    StockSpec("002150", "도화엔지니어링", "건설", "mid_p40_60"),
    StockSpec("000140", "하이트진로홀딩스", "음료", "mid_p40_60"),
    StockSpec("100250", "진양홀딩스", "자동차부품", "mid_p40_60"),
    StockSpec("090350", "노루페인트", "건축자재", "mid_p40_60"),
    StockSpec("003480", "한진중공업홀딩스", "가스유틸리티", "small_p60_80"),
    StockSpec("004970", "신라교역", "식품", "small_p60_80"),
    StockSpec("123690", "한국화장품", "화장품", "small_p60_80"),
    StockSpec("013570", "디와이", "자동차부품", "small_p60_80"),
    StockSpec("015590", "DKME", "기계", "small_p60_80"),
    StockSpec("063160", "종근당바이오", "제약", "small_p60_80"),
    StockSpec("004060", "SG세계물산", "섬유,의류,신발,호화품", "small_p60_80"),
    StockSpec("109070", "주성코퍼레이션", "해운사", "small_p60_80"),
    StockSpec("010040", "한국내화", "비철금속", "small_p60_80"),
    StockSpec("000220", "유유제약", "제약", "small_p60_80"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--codes",
        default="",
        help="Comma-separated 6-digit stock codes. Empty means the approved 30-stock sample.",
    )
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--page-delay", type=float, default=0.15)
    parser.add_argument("--stock-delay", type=float, default=0.7)
    parser.add_argument("--max-pages", type=int, default=120)
    return parser.parse_args()


def flatten_column(column: object) -> str:
    if isinstance(column, tuple):
        parts = [str(part).strip() for part in column if str(part).strip() and not str(part).startswith("Unnamed")]
        return "_".join(parts)
    return str(column).strip()


def clean_number(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "nan", "None"}:
        return math.nan
    text = text.replace("상승", "").replace("하락", "").replace("보합", "").strip()
    if " " in text:
        text = text.split()[-1]
    try:
        return float(text)
    except ValueError:
        return math.nan


def normalize_flow_table(table: pd.DataFrame) -> pd.DataFrame:
    frame = table.copy()
    frame.columns = [flatten_column(column) for column in frame.columns]
    column_map = {
        "날짜_날짜": "date",
        "날짜": "date",
        "종가_종가": "close",
        "종가": "close",
        "전일비_전일비": "price_change",
        "전일비": "price_change",
        "등락률_등락률": "change_rate",
        "등락률": "change_rate",
        "거래량_거래량": "volume",
        "거래량": "volume",
        "기관_순매매량": "institutional_net_buy_shares",
        "외국인_순매매량": "foreign_net_buy_shares",
        "외국인_보유주수": "foreign_holding_shares",
        "외국인_보유율": "foreign_holding_ratio",
    }
    frame = frame.rename(columns=column_map)
    if "date" not in frame.columns:
        return pd.DataFrame()

    frame = frame.loc[frame["date"].notna()].copy()
    frame["date"] = pd.to_datetime(frame["date"], format="%Y.%m.%d", errors="coerce")
    frame = frame.loc[frame["date"].notna()].copy()
    if frame.empty:
        return frame

    numeric_columns = [
        "close",
        "volume",
        "institutional_net_buy_shares",
        "foreign_net_buy_shares",
        "foreign_holding_shares",
        "foreign_holding_ratio",
    ]
    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = frame[column].map(clean_number)

    keep_columns = [
        "date",
        "close",
        "volume",
        "institutional_net_buy_shares",
        "foreign_net_buy_shares",
        "foreign_holding_shares",
        "foreign_holding_ratio",
    ]
    existing = [column for column in keep_columns if column in frame.columns]
    return frame[existing].sort_values("date").reset_index(drop=True)


def read_naver_page(session: requests.Session, stock_code: str, page: int) -> pd.DataFrame:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = session.get(
                NAVER_URL,
                params={"code": stock_code, "page": page},
                timeout=30,
            )
            response.raise_for_status()
            html = response.content.decode("euc-kr", errors="replace")
            tables = pd.read_html(StringIO(html), flavor="lxml")
            for table in tables:
                columns = [flatten_column(column) for column in table.columns]
                if "기관_순매매량" in columns and "외국인_순매매량" in columns:
                    return normalize_flow_table(table)
            raise ValueError(f"Investor-flow table not found for {stock_code} page={page}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.6 * (attempt + 1))
    if last_error is None:
        raise RuntimeError("Unexpected empty Naver page read failure")
    raise last_error


def fetch_naver_investor_flow(
    session: requests.Session,
    stock_code: str,
    *,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    page_delay: float,
    max_pages: int,
) -> tuple[pd.DataFrame, int, list[str]]:
    frames: list[pd.DataFrame] = []
    pages_fetched = 0
    errors: list[str] = []

    for page in range(1, max_pages + 1):
        try:
            frame = read_naver_page(session, stock_code, page)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"page={page}: {type(exc).__name__}: {exc}")
            break

        if frame.empty:
            break

        pages_fetched += 1
        frames.append(frame)
        if frame["date"].min() <= start_date:
            break
        time.sleep(page_delay)

    if not frames:
        return pd.DataFrame(), pages_fetched, errors

    data = pd.concat(frames, ignore_index=True)
    data = data.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    data = data.loc[data["date"].between(start_date, end_date)].copy().reset_index(drop=True)
    return data, pages_fetched, errors


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_checkpoint() -> dict[str, Any]:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    return {}


def save_checkpoint(state: dict[str, Any]) -> None:
    ensure_directory(CHECKPOINT_PATH.parent)
    CHECKPOINT_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def longest_missing_streak(expected_days: list[pd.Timestamp], observed_dates: set[pd.Timestamp]) -> int:
    longest = 0
    streak = 0
    for day in expected_days:
        if day in observed_dates:
            streak = 0
            continue
        streak += 1
        longest = max(longest, streak)
    return longest


def summarize_flow_quality(
    spec: StockSpec,
    frame: pd.DataFrame,
    expected_days: list[pd.Timestamp],
) -> dict[str, Any]:
    data = frame.copy()
    if not data.empty:
        data["date"] = pd.to_datetime(data["date"]).dt.normalize()
    unique_days = sorted(set(data["date"])) if not data.empty else []
    observed_dates = set(unique_days)

    row_count = len(unique_days)
    expected_rows = len(expected_days)
    row_ratio = (row_count / expected_rows) if expected_rows else math.nan
    missing_streak = longest_missing_streak(expected_days, observed_dates)

    volume = data["volume"].dropna() if "volume" in data.columns else pd.Series(dtype=float)
    volume_mean = float(volume.mean()) if not volume.empty else math.nan
    volume_std = float(volume.std(ddof=0)) if not volume.empty else math.nan
    volume_cv = volume_std / volume_mean if volume_mean and not math.isnan(volume_mean) else math.nan

    flags: list[str] = []
    if not math.isnan(row_ratio) and row_ratio < 0.90:
        flags.append("row_ratio<90%")
    if missing_streak >= 5:
        flags.append("missing_streak>=5d")
    if not math.isnan(volume_cv) and volume_cv > 5.0:
        flags.append("volume_cv>5.0")

    return {
        "code": spec.code,
        "name": spec.name,
        "bucket": spec.market_cap_bucket,
        "rows": row_count,
        "expected_rows": expected_rows,
        "row_ratio": row_ratio,
        "max_missing_streak": missing_streak,
        "volume_cv": volume_cv,
        "date_min": unique_days[0].date().isoformat() if unique_days else "NA",
        "date_max": unique_days[-1].date().isoformat() if unique_days else "NA",
        "flags": ", ".join(flags) if flags else "pass",
        "is_flagged": bool(flags),
    }


def build_price_cache(
    stocks: list[StockSpec],
) -> tuple[dict[str, pd.DataFrame], list[pd.Timestamp], list[pd.Timestamp], dict[str, Any]]:
    ohlcv = load_ohlcv()
    ohlcv = ohlcv.copy()
    ohlcv["date"] = pd.to_datetime(ohlcv["date"]).dt.normalize()
    ohlcv["symbol"] = ohlcv["symbol"].astype(str).str.zfill(6)
    if "name" not in ohlcv.columns:
        ohlcv["name"] = ohlcv["symbol"]

    calendar_full = sorted(
        ohlcv.loc[ohlcv["date"].between(VOLUME_WARMUP_START, PRICE_END), "date"].drop_duplicates().tolist()
    )
    calendar_flow = sorted(ohlcv.loc[ohlcv["date"].between(FLOW_START, FLOW_END), "date"].drop_duplicates().tolist())

    ensure_directory(PRICE_DIR)
    price_frames: dict[str, pd.DataFrame] = {}
    price_rows: list[dict[str, Any]] = []

    for spec in stocks:
        frame = ohlcv.loc[
            (ohlcv["symbol"] == spec.code) & ohlcv["date"].between(VOLUME_WARMUP_START, PRICE_END),
            ["date", "symbol", "name", "close", "volume"],
        ].copy()
        frame = frame.sort_values("date").reset_index(drop=True)
        if frame.empty:
            raise ValueError(f"Price data missing for {spec.code}")
        price_frames[spec.code] = frame

        save_frame = frame.loc[frame["date"].between(PRICE_START, PRICE_END)].copy().reset_index(drop=True)
        save_frame.to_parquet(PRICE_DIR / f"{spec.code}.parquet", index=False)
        price_rows.append(
            {
                "code": spec.code,
                "rows": int(len(save_frame)),
                "date_min": save_frame["date"].min().date().isoformat(),
                "date_max": save_frame["date"].max().date().isoformat(),
            }
        )

    return (
        price_frames,
        calendar_full,
        calendar_flow,
        {
            "n_price_files": len(price_frames),
            "price_rows_min": min(row["rows"] for row in price_rows),
            "price_rows_max": max(row["rows"] for row in price_rows),
            "price_date_min": min(row["date_min"] for row in price_rows),
            "price_date_max": max(row["date_max"] for row in price_rows),
            "calendar_flow_days": len(calendar_flow),
        },
    )


def build_flow_cache(
    stocks: list[StockSpec],
    *,
    expected_days: list[pd.Timestamp],
    force_refresh: bool,
    page_delay: float,
    stock_delay: float,
    max_pages: int,
) -> tuple[dict[str, pd.DataFrame], list[dict[str, Any]], dict[str, Any]]:
    ensure_directory(FLOW_DIR)
    checkpoint = load_checkpoint()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results: dict[str, pd.DataFrame] = {}
    summaries: list[dict[str, Any]] = []

    for index, spec in enumerate(stocks, start=1):
        path = FLOW_DIR / f"{spec.code}.parquet"
        reused = path.exists() and not force_refresh

        if reused:
            frame = pd.read_parquet(path)
            pages_fetched = checkpoint.get(spec.code, {}).get("pages_fetched", 0)
            errors = checkpoint.get(spec.code, {}).get("errors", [])
            source_status = "reused"
        else:
            frame, pages_fetched, errors = fetch_naver_investor_flow(
                session,
                spec.code,
                start_date=FLOW_START,
                end_date=FLOW_END,
                page_delay=page_delay,
                max_pages=max_pages,
            )
            frame = frame.copy()
            frame["symbol"] = spec.code
            frame["name"] = spec.name
            frame.to_parquet(path, index=False)
            source_status = "fetched"
            if index < len(stocks):
                time.sleep(stock_delay)

        results[spec.code] = frame
        summary = summarize_flow_quality(spec, frame, expected_days)
        summary["pages_fetched"] = pages_fetched
        summary["source_status"] = source_status
        summary["errors"] = "; ".join(errors) if errors else ""
        summaries.append(summary)

        checkpoint[spec.code] = {
            "name": spec.name,
            "status": source_status,
            "rows": summary["rows"],
            "expected_rows": summary["expected_rows"],
            "row_ratio": summary["row_ratio"],
            "max_missing_streak": summary["max_missing_streak"],
            "volume_cv": summary["volume_cv"],
            "flags": summary["flags"],
            "pages_fetched": pages_fetched,
            "errors": errors,
            "updated_at": pd.Timestamp.now(tz="Asia/Seoul").isoformat(),
        }
        save_checkpoint(checkpoint)

    return (
        results,
        summaries,
        {
            "n_flow_files": len(results),
            "flagged_codes": [row["code"] for row in summaries if row["is_flagged"]],
            "reused_files": sum(1 for row in summaries if row["source_status"] == "reused"),
            "fetched_files": sum(1 for row in summaries if row["source_status"] == "fetched"),
        },
    )


def build_signal_panel(
    stocks: list[StockSpec],
    price_frames: dict[str, pd.DataFrame],
    flow_frames: dict[str, pd.DataFrame],
    calendar_full: list[pd.Timestamp],
) -> pd.DataFrame:
    base_calendar = pd.Index(calendar_full, name="date")
    panels: list[pd.DataFrame] = []

    for spec in stocks:
        price = price_frames[spec.code].copy()
        price["date"] = pd.to_datetime(price["date"]).dt.normalize()
        price = price.drop_duplicates("date", keep="last").set_index("date").sort_index()

        flow = flow_frames[spec.code].copy()
        if not flow.empty:
            flow["date"] = pd.to_datetime(flow["date"]).dt.normalize()
            flow = flow.drop_duplicates("date", keep="last").set_index("date").sort_index()
        else:
            flow = pd.DataFrame(index=pd.Index([], name="date"))

        panel = pd.DataFrame(index=base_calendar)
        panel["close"] = price["close"]
        panel["price_volume"] = price["volume"]
        panel["flow_volume"] = flow["volume"] if "volume" in flow.columns else math.nan
        panel["foreign_net_buy_shares"] = (
            flow["foreign_net_buy_shares"] if "foreign_net_buy_shares" in flow.columns else math.nan
        )
        panel["institutional_net_buy_shares"] = (
            flow["institutional_net_buy_shares"] if "institutional_net_buy_shares" in flow.columns else math.nan
        )

        avg_volume_60d = panel["price_volume"].rolling(60, min_periods=60).mean().shift(1)
        denom = avg_volume_60d.where(avg_volume_60d > 0)

        foreign_sum_5d = panel["foreign_net_buy_shares"].shift(1).rolling(5, min_periods=5).sum()
        institutional_sum_5d = panel["institutional_net_buy_shares"].shift(1).rolling(5, min_periods=5).sum()

        panel["foreign_rank_5d"] = foreign_sum_5d / denom
        panel["institutional_rank_5d"] = institutional_sum_5d / denom
        panel["combined_rank_5d"] = (foreign_sum_5d + institutional_sum_5d) / denom
        panel["divergence_5d"] = (foreign_sum_5d - institutional_sum_5d) / denom

        panel["fwd_ret_5d"] = panel["close"].shift(-5) / panel["close"].shift(-1) - 1.0
        panel["fwd_ret_20d"] = panel["close"].shift(-20) / panel["close"].shift(-1) - 1.0

        panel = panel.reset_index()
        panel["code"] = spec.code
        panel["name"] = spec.name
        panel["sector"] = spec.sector
        panel["market_cap_bucket"] = spec.market_cap_bucket
        panels.append(panel)

    full_panel = pd.concat(panels, ignore_index=True)
    return full_panel.loc[full_panel["date"].between(FLOW_START, FLOW_END)].copy().reset_index(drop=True)


def compute_daily_ic(panel: pd.DataFrame, include_codes: set[str]) -> pd.DataFrame:
    filtered = panel.loc[panel["code"].isin(include_codes)].copy()
    rows: list[dict[str, Any]] = []
    for date, day_frame in filtered.groupby("date", sort=True):
        for signal in SIGNAL_ORDER:
            for horizon in RETURN_ORDER:
                valid = day_frame.loc[day_frame[[signal, horizon]].notna().all(axis=1), ["code", signal, horizon]]
                cross_section_n = int(len(valid))
                ic = math.nan
                if cross_section_n >= 5 and valid[signal].nunique() >= 2 and valid[horizon].nunique() >= 2:
                    ic = float(valid[signal].rank(method="average").corr(valid[horizon].rank(method="average")))
                rows.append(
                    {
                        "date": pd.Timestamp(date),
                        "signal": signal,
                        "horizon": horizon,
                        "series": f"{signal}__{horizon}",
                        "ic": ic,
                        "cross_section_n": cross_section_n,
                    }
                )
    return pd.DataFrame(rows)


def summarize_ic(daily_ic: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for signal in SIGNAL_ORDER:
        for horizon in RETURN_ORDER:
            series = daily_ic.loc[(daily_ic["signal"] == signal) & (daily_ic["horizon"] == horizon)].copy()
            for regime_name, (start, end) in REGIMES.items():
                subset = series.loc[series["date"].between(start, end)].copy()
                valid = subset.loc[subset["ic"].notna()].copy()
                n_days = int(len(valid))
                ic_mean = float(valid["ic"].mean()) if n_days else math.nan
                ic_median = float(valid["ic"].median()) if n_days else math.nan
                ic_std = float(valid["ic"].std(ddof=1)) if n_days > 1 else math.nan
                t_stat = (
                    ic_mean / (ic_std / math.sqrt(n_days))
                    if n_days > 1 and not math.isnan(ic_std) and ic_std > 0
                    else math.nan
                )
                avg_n_stocks = float(valid["cross_section_n"].mean()) if n_days else math.nan
                stock_day_pairs = int(valid["cross_section_n"].sum()) if n_days else 0
                rows.append(
                    {
                        "signal": signal,
                        "horizon": horizon,
                        "series_label": f"{signal} x {horizon}",
                        "regime": regime_name,
                        "ic_mean": ic_mean,
                        "ic_median": ic_median,
                        "ic_std": ic_std,
                        "t_stat": t_stat,
                        "n_days": n_days,
                        "avg_n_stocks": avg_n_stocks,
                        "stock_day_pairs": stock_day_pairs,
                    }
                )
    return pd.DataFrame(rows)


def summarize_concentration(daily_ic: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for signal in SIGNAL_ORDER:
        for horizon in RETURN_ORDER:
            subset = daily_ic.loc[(daily_ic["signal"] == signal) & (daily_ic["horizon"] == horizon)].copy()
            subset = subset.loc[subset["ic"].notna()].copy()
            if subset.empty:
                rows.append(
                    {
                        "series_label": f"{signal} x {horizon}",
                        "n_days": 0,
                        "top_10pct_day_abs_ic_share": math.nan,
                        "top_month": "NA",
                        "top_month_abs_ic_share": math.nan,
                    }
                )
                continue

            subset["abs_ic"] = subset["ic"].abs()
            top_k = max(1, math.ceil(len(subset) * 0.10))
            top_share = subset["abs_ic"].nlargest(top_k).sum() / subset["abs_ic"].sum()
            subset["month"] = subset["date"].dt.to_period("M").astype(str)
            monthly = subset.groupby("month", as_index=False)["abs_ic"].sum()
            top_month_row = monthly.sort_values("abs_ic", ascending=False).iloc[0]
            top_month_share = float(top_month_row["abs_ic"] / monthly["abs_ic"].sum())
            rows.append(
                {
                    "series_label": f"{signal} x {horizon}",
                    "n_days": int(len(subset)),
                    "top_10pct_day_abs_ic_share": float(top_share),
                    "top_month": str(top_month_row["month"]),
                    "top_month_abs_ic_share": top_month_share,
                }
            )
    return pd.DataFrame(rows)


def lookup_metric(summary: pd.DataFrame, signal: str, horizon: str, regime: str, column: str) -> float:
    subset = summary.loc[
        (summary["signal"] == signal) & (summary["horizon"] == horizon) & (summary["regime"] == regime),
        column,
    ]
    if subset.empty:
        return math.nan
    value = subset.iloc[0]
    return float(value) if pd.notna(value) else math.nan


def evaluate_decision(summary: pd.DataFrame) -> dict[str, Any]:
    significant_2024: list[str] = []
    qualifying_series: list[str] = []
    sign_flip_series: list[str] = []
    edge_series: list[str] = []

    for signal in SIGNAL_ORDER:
        for horizon in RETURN_ORDER:
            label = f"{signal} x {horizon}"
            ic_2024 = lookup_metric(summary, signal, horizon, "2024", "ic_mean")
            t_2024 = lookup_metric(summary, signal, horizon, "2024", "t_stat")
            ic_pre = lookup_metric(summary, signal, horizon, "2025-01~04", "ic_mean")
            ic_extreme = lookup_metric(summary, signal, horizon, "2025-05~12", "ic_mean")

            is_significant_2024 = (
                not math.isnan(ic_2024)
                and not math.isnan(t_2024)
                and ic_2024 >= 0.03
                and t_2024 >= 2.0
            )
            if not is_significant_2024:
                continue

            significant_2024.append(label)
            same_sign = not math.isnan(ic_pre) and (ic_2024 > 0 and ic_pre > 0)
            if not math.isnan(ic_pre) and ic_2024 > 0 and ic_pre < 0:
                sign_flip_series.append(label)
                continue
            if same_sign:
                qualifying_series.append(label)
                if not math.isnan(ic_extreme) and abs(ic_extreme - ic_2024) > (2.0 * abs(ic_2024)):
                    edge_series.append(label)

    if sign_flip_series:
        verdict = "Fail"
    elif not significant_2024 or not qualifying_series:
        verdict = "Fail"
    elif edge_series:
        verdict = "Edge"
    else:
        verdict = "Pass"

    return {
        "verdict": verdict,
        "significant_2024": significant_2024,
        "qualifying_series": qualifying_series,
        "sign_flip_series": sign_flip_series,
        "edge_series": edge_series,
        "edge_rule": "|IC_2025-05~12 - IC_2024| > 2 * |IC_2024|",
    }


def format_float(value: object, digits: int = 4) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def format_ratio(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.{digits}f}%"


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def build_step1_table() -> str:
    rows = [
        {
            "code": spec.code,
            "name": spec.name,
            "sector": spec.sector,
            "market_cap_bucket": spec.market_cap_bucket,
        }
        for spec in STOCKS
    ]
    return markdown_table(rows, ["code", "name", "sector", "market_cap_bucket"])


def build_ic_matrix(summary: pd.DataFrame) -> str:
    rows: list[dict[str, Any]] = []
    for signal in SIGNAL_ORDER:
        for horizon in RETURN_ORDER:
            row = {"series": f"{signal} x {horizon}"}
            for regime in REGIMES:
                row[regime] = format_float(lookup_metric(summary, signal, horizon, regime, "ic_mean"), 4)
            rows.append(row)
    return markdown_table(rows, ["series", *REGIMES.keys()])


def build_detail_table(summary: pd.DataFrame) -> str:
    rows: list[dict[str, Any]] = []
    for signal in SIGNAL_ORDER:
        for horizon in RETURN_ORDER:
            for regime in REGIMES:
                subset = summary.loc[
                    (summary["signal"] == signal)
                    & (summary["horizon"] == horizon)
                    & (summary["regime"] == regime)
                ].iloc[0]
                rows.append(
                    {
                        "series": f"{signal} x {horizon}",
                        "regime": regime,
                        "ic_mean": format_float(subset["ic_mean"], 4),
                        "ic_median": format_float(subset["ic_median"], 4),
                        "ic_std": format_float(subset["ic_std"], 4),
                        "t_stat": format_float(subset["t_stat"], 2),
                        "n_days": int(subset["n_days"]),
                        "avg_n_stocks": format_float(subset["avg_n_stocks"], 1),
                        "stock_day_pairs": int(subset["stock_day_pairs"]),
                    }
                )
    return markdown_table(
        rows,
        [
            "series",
            "regime",
            "ic_mean",
            "ic_median",
            "ic_std",
            "t_stat",
            "n_days",
            "avg_n_stocks",
            "stock_day_pairs",
        ],
    )


def build_flow_quality_table(flow_summaries: list[dict[str, Any]]) -> str:
    rows: list[dict[str, Any]] = []
    for row in flow_summaries:
        rows.append(
            {
                "code": row["code"],
                "name": row["name"],
                "bucket": row["bucket"],
                "rows": row["rows"],
                "expected_rows": row["expected_rows"],
                "row_ratio": format_ratio(row["row_ratio"], 1),
                "max_missing_streak": row["max_missing_streak"],
                "volume_cv": format_float(row["volume_cv"], 2),
                "flags": row["flags"],
                "pages_fetched": row["pages_fetched"],
            }
        )
    return markdown_table(
        rows,
        [
            "code",
            "name",
            "bucket",
            "rows",
            "expected_rows",
            "row_ratio",
            "max_missing_streak",
            "volume_cv",
            "flags",
            "pages_fetched",
        ],
    )


def build_concentration_table(concentration: pd.DataFrame) -> str:
    rows: list[dict[str, Any]] = []
    for _, row in concentration.iterrows():
        rows.append(
            {
                "series": row["series_label"],
                "n_days": int(row["n_days"]),
                "top_10pct_day_abs_ic_share": format_ratio(row["top_10pct_day_abs_ic_share"], 1),
                "top_month": row["top_month"],
                "top_month_abs_ic_share": format_ratio(row["top_month_abs_ic_share"], 1),
            }
        )
    return markdown_table(
        rows,
        [
            "series",
            "n_days",
            "top_10pct_day_abs_ic_share",
            "top_month",
            "top_month_abs_ic_share",
        ],
    )


def build_source_table(n_flow_files: int, n_price_files: int, flagged_codes: list[str]) -> str:
    flagged_note = ", ".join(flagged_codes) if flagged_codes else "없음"
    rows = [
        {
            "path": "v2/data/cache/investor_flow_mini_pilot/*.parquet",
            "files": n_flow_files,
            "note": "Naver frgn.naver 수집 결과",
        },
        {
            "path": "v2/data/cache/prices_mini_pilot/*.parquet",
            "files": n_price_files,
            "note": "로컬 shared OHLCV price cache",
        },
        {
            "path": "v2/data/cache/investor_flow_mini_pilot/collection_checkpoint.json",
            "files": 1,
            "note": f"resume 메타데이터, 플래그 종목 {flagged_note}",
        },
    ]
    return markdown_table(rows, ["path", "files", "note"])


def write_report(
    *,
    flow_summaries: list[dict[str, Any]],
    flow_summary: dict[str, Any],
    price_summary: dict[str, Any],
    main_ic_summary: pd.DataFrame,
    ref_ic_summary: pd.DataFrame,
    concentration: pd.DataFrame,
    decision: dict[str, Any],
    reference_decision: dict[str, Any],
) -> None:
    flagged_codes = flow_summary["flagged_codes"]
    flagged_line = ", ".join(flagged_codes) if flagged_codes else "전원 통과"

    report = f"""# PR-7.A.1.6 외국인+기관 flow cross-sectional predictability mini-pilot

Updated: 2026-04-25 KST

## Step 1. 30종목 stratified 선정

### 선정 메모

- 일반주 universe 크기: `915`
- `mid_p40_60` 후보 수: `183`
- `small_p60_80` 후보 수: `183`
- 최대 sector 쏠림: `제약 3`, `건축자재 3`
- 단일 sector 15종목 이상 쏠림 없음

### 30종목 리스트

{build_step1_table()}

{SECTOR_BIAS_WARNING}

## Step 2. 투자자 flow 수집

### 수집 설정

- 소스: Naver `item/frgn.naver`
- 기간: `2024-01-01 ~ 2025-12-31`
- 대상: 승인된 30종목만
- 대기: page delay `0.15s`, stock delay `0.7s`
- checkpoint: `v2/data/cache/investor_flow_mini_pilot/collection_checkpoint.json`

### 품질 플래그 기준

- `row_ratio < 90%`
- `5거래일 이상 연속 결측`
- `일일 거래량 std/mean > 5.0`

### 각 종목 flow 완결성

{build_flow_quality_table(flow_summaries)}

### Step 2 요약

- flow parquet 생성: `{flow_summary["n_flow_files"]}`개
- 품질 플래그 종목: `{flagged_line}`
- reused cache: `{flow_summary["reused_files"]}`
- fetched this run: `{flow_summary["fetched_files"]}`
- 플래그 3종목은 모두 `volume_cv > 5.0` 단독 플래그다.

### IC 계산 시 플래그 종목 처리 방침

- 기본(main): **포함**
- 참고(reference): **제외** (`{", ".join(flagged_codes) if flagged_codes else "없음"}`)

## Step 3. 가격 데이터 수집

- 소스: 로컬 shared OHLCV `C:\\dev\\moneygetter\\data\\processed\\market_ohlcv.parquet`
- 저장 기간: `2024-01-01 ~ 2026-01-31`
- 내부 warmup: `2023-09-01 ~ 2023-12-31` 거래량 60일 평균 계산용
- price parquet 생성: `{price_summary["n_price_files"]}`개
- 저장 행수 범위: `{price_summary["price_rows_min"]} ~ {price_summary["price_rows_max"]}`
- 저장 데이터 날짜 범위: `{price_summary["price_date_min"]} ~ {price_summary["price_date_max"]}`
- 2024~2025 평가용 거래일 수: `{price_summary["calendar_flow_days"]}`

## Step 4. 4개 신호 계산

- `foreign_rank_5d`: `sum(foreign_net_buy_shares[t-5:t-1]) / avg(volume[t-60:t-1])`
- `institutional_rank_5d`: `sum(institutional_net_buy_shares[t-5:t-1]) / avg(volume[t-60:t-1])`
- `combined_rank_5d`: `sum(foreign + institutional net shares[t-5:t-1]) / avg(volume[t-60:t-1])`
- `divergence_5d`: `sum(foreign - institutional net shares[t-5:t-1]) / avg(volume[t-60:t-1])`
- point-in-time: `t` 신호는 `t-1`까지의 flow만 사용

## Step 5. Forward return 계산

- `fwd_ret_5d = close[t+5] / close[t+1] - 1`
- `fwd_ret_20d = close[t+20] / close[t+1] - 1`
- 시작점은 모두 `t+1`

## Step 6. IC 측정

### 32셀 IC_mean 테이블 (main: 플래그 포함)

{build_ic_matrix(main_ic_summary)}

### 상세 통계 (main: 플래그 포함)

{build_detail_table(main_ic_summary)}

- `n_days`가 `2024`에서 `184`로 줄어든 이유: `60거래일 평균 거래량` 정상화와 `5거래일` 신호 window 때문에 2024 초반 warmup 구간은 IC 계산에서 제외됐다.

### 32셀 IC_mean 테이블 (reference: 플래그 제외)

{build_ic_matrix(ref_ic_summary)}

### IC 집중도 체크

`IC_sum`은 부호 상쇄를 피하기 위해 `abs(IC)` 합으로 계산했다.

{build_concentration_table(concentration)}

## Step 7. 판정

### 적용 판정 규칙

- 통과 조건:
  - 1차 게이트: 최소 1개 신호가 `2024` 기간에 `IC_mean >= 0.03` and `t-stat >= 2.0`
  - 부호 consistency: 해당 신호의 `2025-01~04` IC 도 부호 동일
  - `2025-05~12` IC 는 정보 기록만
- 탈락 조건:
  - 4개 신호 모두 `2024` IC_mean < 0.03 또는 t-stat < 2.0
  - 또는 2024 유의 신호가 `2025-01~04` 에 부호 반전
- 경계 조건:
  - 2024 유의 + `2025-01~04` 부호 일치 + `2025-05~12` 극단적 차이
  - 운영 정의: `{decision["edge_rule"]}`

### 판정 결과

- **판정: {decision["verdict"]}**
- 2024 1차 게이트 통과 series: `{", ".join(decision["significant_2024"]) if decision["significant_2024"] else "없음"}`
- 2025-01~04 부호 일치 series: `{", ".join(decision["qualifying_series"]) if decision["qualifying_series"] else "없음"}`
- 2025-01~04 부호 반전 series: `{", ".join(decision["sign_flip_series"]) if decision["sign_flip_series"] else "없음"}`
- 2025-05~12 extreme-difference series: `{", ".join(decision["edge_series"]) if decision["edge_series"] else "없음"}`
- reference(플래그 제외) 판정: `{reference_decision["verdict"]}`

## Step 8. 결과 메모

- 본 mini-pilot 은 IC 측정만 수행했다.
- 백테스트, 포트폴리오 구성, PnL 계산은 수행하지 않았다.
- 2025-05~12 구간은 시총 상위 랠리 섹터 동조화 가능성을 고려해 참고 기록으로만 남긴다.

## 산출물

{build_source_table(flow_summary["n_flow_files"], price_summary["n_price_files"], flagged_codes)}
"""

    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    args = parse_args()
    selected = STOCKS
    if args.codes:
        requested = {code.strip() for code in args.codes.split(",") if code.strip()}
        selected = [spec for spec in STOCKS if spec.code in requested]
        if len(selected) != len(requested):
            missing = sorted(requested - {spec.code for spec in selected})
            raise ValueError(f"Unknown codes requested: {missing}")
    if not selected:
        raise ValueError("No stocks selected")

    price_frames, calendar_full, calendar_flow, price_summary = build_price_cache(selected)
    flow_frames, flow_summaries, flow_summary = build_flow_cache(
        selected,
        expected_days=calendar_flow,
        force_refresh=args.force_refresh,
        page_delay=args.page_delay,
        stock_delay=args.stock_delay,
        max_pages=args.max_pages,
    )

    panel = build_signal_panel(selected, price_frames, flow_frames, calendar_full)
    included_codes = {spec.code for spec in selected}
    flagged_codes = {row["code"] for row in flow_summaries if row["is_flagged"]}
    reference_codes = included_codes - flagged_codes if flagged_codes else included_codes

    main_ic_daily = compute_daily_ic(panel, included_codes)
    ref_ic_daily = compute_daily_ic(panel, reference_codes)
    main_ic_summary = summarize_ic(main_ic_daily)
    ref_ic_summary = summarize_ic(ref_ic_daily)
    concentration = summarize_concentration(main_ic_daily)
    decision = evaluate_decision(main_ic_summary)
    reference_decision = evaluate_decision(ref_ic_summary)

    write_report(
        flow_summaries=flow_summaries,
        flow_summary=flow_summary,
        price_summary=price_summary,
        main_ic_summary=main_ic_summary,
        ref_ic_summary=ref_ic_summary,
        concentration=concentration,
        decision=decision,
        reference_decision=reference_decision,
    )


if __name__ == "__main__":
    main()
