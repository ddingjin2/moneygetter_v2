from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRICE_DIR = ROOT / "data/cache/price_market_cap_full"
UNIVERSE_PATH = ROOT / "data/cache/universe/kospi_universe.parquet"
REPORT_PATH = ROOT / "reports/after_close_data_update.md"
META_PATH = PRICE_DIR / "_incremental_update_meta.json"


def atomic_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def atomic_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_universe_codes() -> list[str]:
    u = pd.read_parquet(UNIVERSE_PATH)
    return sorted(u["code"].astype(str).str.zfill(6).unique())


def fetch_pykrx_date(date: pd.Timestamp) -> pd.DataFrame:
    try:
        from pykrx import stock  # type: ignore
    except Exception as exc:
        raise SystemExit("pykrx is not installed. Install with: python3 -m pip install pykrx") from exc
    ymd = date.strftime("%Y%m%d")
    ohlcv = stock.get_market_ohlcv_by_ticker(ymd, market="KOSPI")
    if ohlcv is None or ohlcv.empty:
        return pd.DataFrame()
    cap = pd.DataFrame()
    try:
        cap = stock.get_market_cap_by_ticker(ymd, market="KOSPI")
    except Exception:
        cap = pd.DataFrame()
    name_map = {}
    for code in ohlcv.index.astype(str).str.zfill(6):
        try:
            name_map[code] = stock.get_market_ticker_name(code)
        except Exception:
            name_map[code] = code
    out = pd.DataFrame({
        "date": date.normalize(),
        "symbol": ohlcv.index.astype(str).str.zfill(6),
        "open": pd.to_numeric(ohlcv.get("시가"), errors="coerce"),
        "high": pd.to_numeric(ohlcv.get("고가"), errors="coerce"),
        "low": pd.to_numeric(ohlcv.get("저가"), errors="coerce"),
        "close": pd.to_numeric(ohlcv.get("종가"), errors="coerce"),
        "volume": pd.to_numeric(ohlcv.get("거래량"), errors="coerce"),
        "trading_value": pd.to_numeric(ohlcv.get("거래대금"), errors="coerce"),
    })
    out["name"] = out["symbol"].map(name_map).fillna(out["symbol"])
    out["turnover"] = out["trading_value"]
    if not cap.empty:
        cap = cap.copy()
        cap.index = cap.index.astype(str).str.zfill(6)
        out["market_cap"] = out["symbol"].map(pd.to_numeric(cap.get("시가총액"), errors="coerce"))
        out["shares_outstanding"] = out["symbol"].map(pd.to_numeric(cap.get("상장주식수"), errors="coerce"))
    else:
        out["market_cap"] = pd.NA
        out["shares_outstanding"] = pd.NA
    out["source"] = "pykrx"
    return out[["date", "symbol", "name", "open", "high", "low", "close", "volume", "trading_value", "turnover", "market_cap", "shares_outstanding", "source"]]


def update_cache_for_dates(dates: list[pd.Timestamp], dry_run: bool) -> dict:
    codes = set(load_universe_codes())
    rows_written = 0
    dates_done = []
    missing_dates = []
    for date in dates:
        daily = fetch_pykrx_date(date)
        if daily.empty:
            missing_dates.append(date.strftime("%Y-%m-%d"))
            continue
        daily = daily[daily["symbol"].isin(codes)].copy()
        for code, row in daily.groupby("symbol"):
            path = PRICE_DIR / f"{code}.parquet"
            old = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=daily.columns)
            merged = pd.concat([old, row], ignore_index=True)
            merged["date"] = pd.to_datetime(merged["date"]).dt.normalize()
            merged = merged.drop_duplicates(["date", "symbol"], keep="last").sort_values("date")
            if not dry_run:
                atomic_parquet(merged, path)
            rows_written += len(row)
        dates_done.append(date.strftime("%Y-%m-%d"))
    meta = {"dates_requested": [d.strftime("%Y-%m-%d") for d in dates], "dates_updated": dates_done, "missing_dates": missing_dates, "rows_seen": rows_written, "dry_run": dry_run, "updated_at": pd.Timestamp.now().isoformat()}
    if not dry_run:
        atomic_text(json.dumps(meta, ensure_ascii=False, indent=2), META_PATH)
    return meta


def infer_dates(start: str | None, end: str | None) -> list[pd.Timestamp]:
    if start is None and end is None:
        # Conservative default: try today. pykrx returns empty before market data is published.
        return [pd.Timestamp.now(tz="Asia/Seoul").normalize().tz_localize(None)]
    s = pd.Timestamp(start).normalize()
    e = pd.Timestamp(end or start).normalize()
    return [pd.Timestamp(d) for d in pd.date_range(s, e, freq="B")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally update KOSPI OHLCV cache from pykrx after close.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dates = infer_dates(args.start, args.end)
    meta = update_cache_for_dates(dates, args.dry_run)
    report = ["# After-close OHLCV update", "", "```json", json.dumps(meta, ensure_ascii=False, indent=2), "```", ""]
    if not args.dry_run:
        atomic_text("\n".join(report), REPORT_PATH)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
