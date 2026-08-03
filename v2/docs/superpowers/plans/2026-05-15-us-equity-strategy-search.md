# US Equity Strategy Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a US equity research pipeline that mirrors the current KOSPI workflow: collect a point-in-time-ish tradable universe and daily OHLCV data, generate factor signals, run IC and cost-aware backtests, and produce PASS/FAIL strategy verdict reports.

**Architecture:** Add a US-specific pipeline beside the existing KOSPI pipeline instead of rewriting the current scripts. Keep raw vendor ingestion, normalized market cache, signal generation, IC measurement, and backtest output separated so the data source can be swapped without changing research logic. Use config-driven paths under `v2/data/cache/us/` and reports under `v2/reports/us/` to avoid polluting existing Korean-market artifacts.

**Tech Stack:** Python 3.12, pandas, pyarrow parquet, pytest, existing `v2.data.market_dataset` normalization patterns, new provider adapters for US market data, optional paid data source credentials via `.env` or environment variables.

---

## Scope And Assumptions

- This plan searches US equity strategies using the same research discipline as the current KOSPI flow: validation before promotion, explicit costs, benchmark alpha, subperiod checks, and automatic verdicts.
- The first target universe is liquid US common stocks, preferably Russell 3000-like or NYSE/Nasdaq/NYSE American common shares with liquidity filters.
- The first implementation must support at least one free or low-friction smoke-test provider and one production-grade paid/provider adapter. Free data is acceptable for plumbing tests, not for final strategy claims.
- US corporate actions matter. Daily OHLCV must store adjusted close and raw open/high/low/close when available. Backtests should default to adjusted open-to-open returns only if the provider supplies adjustment factors; otherwise mark the run as research-only.
- Survivorship bias is a first-class risk. The pipeline may start with a current universe for smoke testing, but every report must label that mode as `survivorship_biased_current_universe`.
- Fundamental/investor-flow analogs are not required in Phase 1. Phase 1 should test price/liquidity/volatility/reversal/momentum style signals that can be computed from daily OHLCV and benchmark returns.

## Recommended Approach

Use a staged adapter architecture.

1. **Provider interface first:** implement a normalized schema and provider abstraction before picking one permanent vendor. This keeps the codebase from becoming tied to a single API.
2. **Free smoke test, paid-quality gate:** allow a small symbol smoke test with free data, but require a survivorship/corporate-action warning in reports. For serious evaluation, plug in a provider with delisting history and corporate action data.
3. **Reuse research logic:** port the current Step 8 style signal catalog and backtest framework, but make it market-agnostic enough to run on both KOSPI and US later.

Avoid starting by copying one giant script. The current scripts are useful references, but the US pipeline should have smaller modules because provider complexity will grow.

## File Structure

- Create: `v2/config/us_market_data.example.json`
  - Provider settings, universe filters, date range, paths, benchmark ticker, cost assumptions.
- Create: `v2/data/us_schema.py`
  - Canonical column definitions and validators for US universe, daily bars, benchmark bars, trading status, returns, and factor outputs.
- Create: `v2/data/us_providers.py`
  - Provider protocol plus adapters for `csv_local` and one API-backed provider.
- Create: `v2/data/us_market_dataset.py`
  - Normalize, merge, validate, and save US OHLCV/universe parquet files.
- Create: `v2/scripts/us_build_universe.py`
  - Build US universe cache.
- Create: `v2/scripts/us_update_market_dataset.py`
  - Incrementally collect and merge daily bars.
- Create: `v2/scripts/us_prepare_backtest_inputs.py`
  - Build per-symbol price cache, forward returns, trading status, size/liquidity buckets, and benchmark returns.
- Create: `v2/scripts/us_signal_catalog.py`
  - Compute US factor signals and cross-sectional z-scores.
- Create: `v2/scripts/us_run_ic_batch.py`
  - Measure daily IC by horizon, bucket, and subperiod.
- Create: `v2/scripts/us_run_backtest_batch.py`
  - Run long-only and long-short strategy backtests with US cost assumptions.
- Create: `v2/scripts/us_audit_research_data.py`
  - Verify cache freshness, schema, missingness, and report warnings.
- Create: `v2/reports/us/README.md`
  - Explain artifacts and research caveats.
- Create tests:
  - `v2/tests/test_us_schema.py`
  - `v2/tests/test_us_market_dataset.py`
  - `v2/tests/test_us_prepare_backtest_inputs.py`
  - `v2/tests/test_us_signal_catalog.py`
  - `v2/tests/test_us_backtest_batch.py`

## Canonical Schemas

US universe parquet: `v2/data/cache/us/universe/us_universe.parquet`

Columns:
- `symbol`: provider-normalized ticker, string
- `name`: company name, string
- `exchange`: primary exchange, string
- `security_type`: common stock, ADR, ETF, etc.
- `currency`: usually USD
- `country`: issuer/listing country if available
- `active_start_date`: earliest tradable date in this cache
- `active_end_date`: delisting/end date or null
- `is_current_member`: bool
- `source`: provider id
- `collected_at`: timestamp

US OHLCV parquet: `v2/data/processed/us_market_ohlcv.parquet`

Columns:
- `date`
- `symbol`
- `exchange`
- `name`
- `open`
- `high`
- `low`
- `close`
- `adj_open`
- `adj_high`
- `adj_low`
- `adj_close`
- `volume`
- `dollar_volume`
- `split_factor`
- `dividend`
- `source`
- `collected_at`

Backtest price cache: `v2/data/cache/us/price_full/{symbol}.parquet`

Columns:
- `date`, `symbol`, `name`, `open`, `adj_open`, `close`, `adj_close`, `volume`, `dollar_volume`, `source`

Forward returns: `v2/data/cache/us/returns/forward_returns.parquet`

Columns:
- `symbol`, `date`, `forward_return_1d`, `forward_return_5d`, `forward_return_20d`, `ret_valid_1d`, `ret_valid_5d`, `ret_valid_20d`

Signals: `v2/data/cache/us/signals_batch/{signal_id}.parquet` and `{signal_id}_cs_zscore.parquet`

Columns:
- raw: `symbol`, `date`, `signal_value`
- z-score: `symbol`, `date`, `signal_cs_z`

## Strategy Candidates For Phase 1

Implement these OHLCV-only signals first:

- `US_A1_12_1_momentum`: `adj_close.shift(21) / adj_close.shift(252) - 1`
- `US_A2_1m_reversal`: `-(adj_close / adj_close.shift(21) - 1)`
- `US_A3_low_volatility`: negative 60-day return volatility
- `US_A4_liquidity_size`: negative log 60-day average dollar volume; treat as a size/liquidity factor, not pure alpha
- `US_A5_illiquidity`: negative Amihud-style `abs(ret_1d) / dollar_volume`
- `US_A6_volume_shock`: current 5-day volume versus prior 60-day volume baseline
- `US_A7_near_high`: `adj_close / rolling_252d_high`
- `US_A8_overnight_gap_reversal`: negative open-versus-prior-close gap
- `US_A9_beta_residual`: negative 60-day beta-adjusted residual return versus SPY or broad-market benchmark

Do not add fundamental or earnings factors until Phase 1 has clean data, IC, and backtest gates.

## Evaluation Gates

Use these gates before calling a candidate viable:

- Data gate: no schema errors, benchmark present, price cache latest date matches processed OHLCV latest date, and at least 95% of selected symbols have valid prices for the target range.
- IC gate: sign-stable mean IC over 1d/5d/20d horizons, with subperiod direction not flipping in more than one subperiod.
- Backtest gate: after realistic costs, preferred portfolio has full-period Sharpe >= 0.8, max drawdown no worse than -35%, and all subperiod Sharpes >= 0.0.
- Benchmark gate: long-only portfolio must have positive annualized alpha versus benchmark and information ratio >= 0.3 after costs.
- Robustness gate: result remains directionally similar under top decile/top quintile, 5d/20d rebalance, and 15/30/50 bps cost assumptions.

Initial US cost assumptions:

- Long-only: 5, 10, 20, 30 bps one-way scenarios.
- Long-short: 10, 20, 30, 50 bps one-way scenarios. Add a `borrow_cost_bps` column with value `0.0` and label reports as `borrow_cost_not_modeled` until a real borrow data source exists.
- Use t+1 adjusted open-to-open returns when adjusted open exists. If only adjusted close exists, mark the run as `close_adjusted_proxy` and do not promote it.

---

### Task 1: Add US Config And Schemas

**Files:**
- Create: `v2/config/us_market_data.example.json`
- Create: `v2/data/us_schema.py`
- Test: `v2/tests/test_us_schema.py`

- [ ] **Step 1: Write schema tests**

Create `v2/tests/test_us_schema.py`:

```python
from __future__ import annotations

import pandas as pd
import pytest

from v2.data.us_schema import normalize_us_ohlcv, normalize_us_universe


def test_normalize_us_universe_standardizes_symbols_and_dates() -> None:
    frame = pd.DataFrame(
        {
            "symbol": [" aapl ", "MSFT"],
            "name": ["Apple Inc.", "Microsoft Corp."],
            "exchange": ["nasdaq", "NASDAQ"],
            "security_type": ["common_stock", "common_stock"],
            "active_start_date": ["2020-01-01", "2020-01-02"],
            "active_end_date": [None, ""],
        }
    )

    out = normalize_us_universe(frame)

    assert out["symbol"].tolist() == ["AAPL", "MSFT"]
    assert out["exchange"].tolist() == ["NASDAQ", "NASDAQ"]
    assert str(out["active_start_date"].min().date()) == "2020-01-01"
    assert out["active_end_date"].isna().all()


def test_normalize_us_ohlcv_requires_adjusted_open_for_promotable_data() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2024-01-02"],
            "symbol": ["aapl"],
            "open": [100],
            "high": [110],
            "low": [99],
            "close": [105],
            "adj_open": [98],
            "adj_close": [103],
            "volume": [1000],
        }
    )

    out = normalize_us_ohlcv(frame)

    assert out.loc[0, "symbol"] == "AAPL"
    assert out.loc[0, "dollar_volume"] == 105000
    assert out.loc[0, "adjustment_quality"] == "adjusted_open_available"


def test_normalize_us_ohlcv_rejects_missing_required_columns() -> None:
    with pytest.raises(ValueError, match="missing required"):
        normalize_us_ohlcv(pd.DataFrame({"symbol": ["AAPL"]}))
```

- [ ] **Step 2: Run the failing schema tests**

Run:

```powershell
python -m pytest v2/tests/test_us_schema.py -q
```

Expected: tests fail because `v2.data.us_schema` does not exist.

- [ ] **Step 3: Implement schema normalization**

Create `v2/data/us_schema.py`:

```python
from __future__ import annotations

from typing import Iterable

import pandas as pd


US_UNIVERSE_COLUMNS = [
    "symbol",
    "name",
    "exchange",
    "security_type",
    "currency",
    "country",
    "active_start_date",
    "active_end_date",
    "is_current_member",
    "source",
    "collected_at",
]

US_OHLCV_COLUMNS = [
    "date",
    "symbol",
    "exchange",
    "name",
    "open",
    "high",
    "low",
    "close",
    "adj_open",
    "adj_high",
    "adj_low",
    "adj_close",
    "volume",
    "dollar_volume",
    "split_factor",
    "dividend",
    "source",
    "collected_at",
    "adjustment_quality",
]


def _require(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"US frame is missing required columns: {missing}")


def normalize_symbol(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().str.replace(".", "-", regex=False)


def normalize_us_universe(frame: pd.DataFrame) -> pd.DataFrame:
    _require(frame, ["symbol", "name", "exchange", "security_type", "active_start_date"])
    out = frame.copy()
    out["symbol"] = normalize_symbol(out["symbol"])
    out["exchange"] = out["exchange"].astype(str).str.strip().str.upper()
    out["name"] = out["name"].astype(str).str.strip()
    out["security_type"] = out["security_type"].astype(str).str.strip().str.lower()
    out["active_start_date"] = pd.to_datetime(out["active_start_date"], errors="coerce").dt.normalize()
    if "active_end_date" not in out.columns:
        out["active_end_date"] = pd.NaT
    out["active_end_date"] = pd.to_datetime(out["active_end_date"].replace("", pd.NA), errors="coerce").dt.normalize()
    if "currency" not in out.columns:
        out["currency"] = "USD"
    if "country" not in out.columns:
        out["country"] = "US"
    if "is_current_member" not in out.columns:
        out["is_current_member"] = out["active_end_date"].isna()
    if "source" not in out.columns:
        out["source"] = "unknown"
    if "collected_at" not in out.columns:
        out["collected_at"] = pd.Timestamp.now(tz="UTC")
    ordered = [column for column in US_UNIVERSE_COLUMNS if column in out.columns]
    return out[ordered].drop_duplicates("symbol", keep="last").sort_values("symbol").reset_index(drop=True)


def normalize_us_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    _require(frame, ["date", "symbol", "open", "high", "low", "close", "volume"])
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.normalize()
    out["symbol"] = normalize_symbol(out["symbol"])
    for column in ["open", "high", "low", "close", "adj_open", "adj_high", "adj_low", "adj_close", "volume", "split_factor", "dividend"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    if "adj_close" not in out.columns:
        out["adj_close"] = pd.NA
    if "adj_open" not in out.columns:
        out["adj_open"] = pd.NA
    if "adj_high" not in out.columns:
        out["adj_high"] = pd.NA
    if "adj_low" not in out.columns:
        out["adj_low"] = pd.NA
    if "exchange" not in out.columns:
        out["exchange"] = "UNKNOWN"
    if "name" not in out.columns:
        out["name"] = out["symbol"]
    if "split_factor" not in out.columns:
        out["split_factor"] = pd.NA
    if "dividend" not in out.columns:
        out["dividend"] = pd.NA
    if "source" not in out.columns:
        out["source"] = "unknown"
    if "collected_at" not in out.columns:
        out["collected_at"] = pd.Timestamp.now(tz="UTC")
    out["dollar_volume"] = pd.to_numeric(out["close"], errors="coerce") * pd.to_numeric(out["volume"], errors="coerce")
    out["adjustment_quality"] = out["adj_open"].notna().map({True: "adjusted_open_available", False: "raw_open_only"})
    ordered = [column for column in US_OHLCV_COLUMNS if column in out.columns]
    return out[ordered].dropna(subset=["date", "symbol"]).drop_duplicates(["date", "symbol"], keep="last").sort_values(["symbol", "date"]).reset_index(drop=True)
```

- [ ] **Step 4: Add example config**

Create `v2/config/us_market_data.example.json`:

```json
{
  "market": "US",
  "start": "2010-01-01",
  "end": null,
  "provider": "csv_local",
  "provider_settings": {
    "raw_universe_csv": "v2/data/raw/us/universe.csv",
    "raw_ohlcv_dir": "v2/data/raw/us/ohlcv"
  },
  "universe": {
    "security_types": ["common_stock"],
    "exchanges": ["NYSE", "NASDAQ", "NYSEAMERICAN"],
    "min_median_dollar_volume_60d": 1000000,
    "min_price": 2.0
  },
  "benchmark": {
    "symbol": "SPY"
  },
  "costs": {
    "long_only_bps": [5, 10, 20, 30],
    "long_short_bps": [10, 20, 30, 50]
  }
}
```

- [ ] **Step 5: Run schema tests**

Run:

```powershell
python -m pytest v2/tests/test_us_schema.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add v2/config/us_market_data.example.json v2/data/us_schema.py v2/tests/test_us_schema.py
git commit -m "feat: add US market data schemas"
```

### Task 2: Build Provider Interface And Local CSV Adapter

**Files:**
- Create: `v2/data/us_providers.py`
- Test: `v2/tests/test_us_market_dataset.py`

- [ ] **Step 1: Write provider tests**

Create `v2/tests/test_us_market_dataset.py` with local CSV fixture coverage:

```python
from __future__ import annotations

import pandas as pd

from v2.data.us_providers import CsvLocalUsProvider


def test_csv_local_provider_loads_universe_and_daily_bars(tmp_path) -> None:
    universe_csv = tmp_path / "universe.csv"
    bars_dir = tmp_path / "bars"
    bars_dir.mkdir()
    universe_csv.write_text(
        "symbol,name,exchange,security_type,active_start_date\nAAPL,Apple Inc.,NASDAQ,common_stock,2020-01-01\n",
        encoding="utf-8",
    )
    (bars_dir / "AAPL.csv").write_text(
        "date,symbol,open,high,low,close,adj_open,adj_close,volume\n2024-01-02,AAPL,100,101,99,100,98,98,1000\n",
        encoding="utf-8",
    )

    provider = CsvLocalUsProvider(raw_universe_csv=universe_csv, raw_ohlcv_dir=bars_dir)

    universe = provider.fetch_universe()
    bars = provider.fetch_daily_bars(["AAPL"], "2024-01-01", "2024-01-31")

    assert universe["symbol"].tolist() == ["AAPL"]
    assert bars.loc[0, "symbol"] == "AAPL"
    assert pd.Timestamp(bars.loc[0, "date"]).date().isoformat() == "2024-01-02"
```

- [ ] **Step 2: Run provider tests and see failure**

Run:

```powershell
python -m pytest v2/tests/test_us_market_dataset.py -q
```

Expected: fail because `v2.data.us_providers` does not exist.

- [ ] **Step 3: Implement provider interface**

Create `v2/data/us_providers.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd

from v2.data.us_schema import normalize_us_ohlcv, normalize_us_universe


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
        for symbol in symbols:
            path = base / f"{symbol.upper()}.csv"
            if not path.exists():
                continue
            frame = pd.read_csv(path)
            frame["symbol"] = symbol.upper()
            frame = normalize_us_ohlcv(frame)
            frame = frame.loc[pd.to_datetime(frame["date"]).between(start_ts, end_ts)]
            frames.append(frame)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
```

- [ ] **Step 4: Run provider tests**

Run:

```powershell
python -m pytest v2/tests/test_us_market_dataset.py -q
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```powershell
git add v2/data/us_providers.py v2/tests/test_us_market_dataset.py
git commit -m "feat: add local US data provider"
```

### Task 3: Build US Dataset Scripts

**Files:**
- Create: `v2/data/us_market_dataset.py`
- Create: `v2/scripts/us_build_universe.py`
- Create: `v2/scripts/us_update_market_dataset.py`
- Modify: `v2/tests/test_us_market_dataset.py`

- [ ] **Step 1: Add dataset merge tests**

Append to `v2/tests/test_us_market_dataset.py`:

```python
from v2.data.us_market_dataset import merge_us_ohlcv


def test_merge_us_ohlcv_keeps_latest_duplicate() -> None:
    old = pd.DataFrame(
        {
            "date": ["2024-01-02"],
            "symbol": ["AAPL"],
            "open": [100],
            "high": [101],
            "low": [99],
            "close": [100],
            "adj_open": [98],
            "adj_close": [98],
            "volume": [1000],
            "source": ["old"],
        }
    )
    new = old.copy()
    new["close"] = [101]
    new["source"] = ["new"]

    merged = merge_us_ohlcv(old, new)

    assert len(merged) == 1
    assert merged.loc[0, "close"] == 101
    assert merged.loc[0, "source"] == "new"
```

- [ ] **Step 2: Run failing merge test**

Run:

```powershell
python -m pytest v2/tests/test_us_market_dataset.py::test_merge_us_ohlcv_keeps_latest_duplicate -q
```

Expected: fail because `v2.data.us_market_dataset` does not exist.

- [ ] **Step 3: Implement dataset helpers**

Create `v2/data/us_market_dataset.py`:

```python
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd

from v2.data.us_schema import normalize_us_ohlcv, normalize_us_universe

ROOT = Path(__file__).resolve().parents[1]
US_OHLCV_PATH = ROOT / "data/processed/us_market_ohlcv.parquet"
US_UNIVERSE_PATH = ROOT / "data/cache/us/universe/us_universe.parquet"


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def save_us_universe(frame: pd.DataFrame, path: Path = US_UNIVERSE_PATH) -> Path:
    atomic_write_parquet(normalize_us_universe(frame), path)
    return path


def load_us_universe(path: Path = US_UNIVERSE_PATH) -> pd.DataFrame:
    return normalize_us_universe(pd.read_parquet(path))


def merge_us_ohlcv(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        return normalize_us_ohlcv(incoming)
    if incoming.empty:
        return normalize_us_ohlcv(existing)
    return normalize_us_ohlcv(pd.concat([existing, incoming], ignore_index=True))


def save_us_ohlcv(frame: pd.DataFrame, path: Path = US_OHLCV_PATH) -> Path:
    atomic_write_parquet(normalize_us_ohlcv(frame), path)
    return path


def load_us_ohlcv(path: Path = US_OHLCV_PATH) -> pd.DataFrame:
    return normalize_us_ohlcv(pd.read_parquet(path))


def latest_us_ohlcv_date(path: Path = US_OHLCV_PATH) -> pd.Timestamp | None:
    if not path.exists():
        return None
    frame = pd.read_parquet(path, columns=["date"])
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
    return pd.Timestamp(dates.max()).normalize() if not dates.empty else None
```

- [ ] **Step 4: Implement universe script**

Create `v2/scripts/us_build_universe.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from v2.data.us_market_dataset import save_us_universe
from v2.data.us_providers import CsvLocalUsProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Build US universe cache.")
    parser.add_argument("--config", default="v2/config/us_market_data.example.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    settings = config["provider_settings"]
    provider = CsvLocalUsProvider(settings["raw_universe_csv"], settings["raw_ohlcv_dir"])
    universe = provider.fetch_universe()
    path = save_us_universe(universe)
    print(json.dumps({"path": str(path), "symbols": int(len(universe))}, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Implement market update script**

Create `v2/scripts/us_update_market_dataset.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from v2.data.us_market_dataset import US_OHLCV_PATH, latest_us_ohlcv_date, load_us_ohlcv, load_us_universe, merge_us_ohlcv, save_us_ohlcv
from v2.data.us_providers import CsvLocalUsProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally update US OHLCV dataset.")
    parser.add_argument("--config", default="v2/config/us_market_data.example.json")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--limit-symbols", type=int, default=None)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    latest = latest_us_ohlcv_date()
    start = args.start or ((latest + pd.Timedelta(days=1)).date().isoformat() if latest is not None else config["start"])
    end = args.end
    settings = config["provider_settings"]
    provider = CsvLocalUsProvider(settings["raw_universe_csv"], settings["raw_ohlcv_dir"])
    universe = load_us_universe()
    symbols = universe["symbol"].astype(str).tolist()
    if args.limit_symbols:
        symbols = symbols[: args.limit_symbols]
    incoming = provider.fetch_daily_bars(symbols, start, end)
    existing = load_us_ohlcv() if US_OHLCV_PATH.exists() else pd.DataFrame()
    merged = merge_us_ohlcv(existing, incoming)
    path = save_us_ohlcv(merged)
    print(json.dumps({"path": str(path), "rows_new": int(len(incoming)), "rows_total": int(len(merged)), "max_date": str(pd.to_datetime(merged["date"]).max().date())}, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run dataset tests**

Run:

```powershell
python -m pytest v2/tests/test_us_market_dataset.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add v2/data/us_market_dataset.py v2/scripts/us_build_universe.py v2/scripts/us_update_market_dataset.py v2/tests/test_us_market_dataset.py
git commit -m "feat: add US market dataset pipeline"
```

### Task 4: Prepare US Backtest Inputs

**Files:**
- Create: `v2/scripts/us_prepare_backtest_inputs.py`
- Test: `v2/tests/test_us_prepare_backtest_inputs.py`

- [ ] **Step 1: Write backtest input tests**

Create `v2/tests/test_us_prepare_backtest_inputs.py`:

```python
from __future__ import annotations

import pandas as pd

from v2.scripts.us_prepare_backtest_inputs import build_forward_returns


def test_build_forward_returns_uses_adjusted_open() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAPL", "AAPL", "AAPL"],
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "adj_open": [100.0, 110.0, 121.0],
            "open": [10.0, 11.0, 12.0],
            "volume": [1000, 1000, 1000],
        }
    )

    out = build_forward_returns(frame, horizons=[1])

    assert round(float(out.loc[0, "forward_return_1d"]), 6) == 0.1
    assert bool(out.loc[0, "ret_valid_1d"]) is True
    assert bool(out.loc[2, "ret_valid_1d"]) is False
```

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m pytest v2/tests/test_us_prepare_backtest_inputs.py -q
```

Expected: fail because script does not exist.

- [ ] **Step 3: Implement input preparation script**

Create `v2/scripts/us_prepare_backtest_inputs.py`:

```python
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd

from v2.data.us_market_dataset import load_us_ohlcv

ROOT = Path(__file__).resolve().parents[1]
US_CACHE = ROOT / "data/cache/us"
PRICE_DIR = US_CACHE / "price_full"
RETURNS_PATH = US_CACHE / "returns/forward_returns.parquet"
STATUS_PATH = PRICE_DIR / "_trading_status.parquet"
BUCKETS_PATH = PRICE_DIR / "_liquidity_buckets.parquet"
BENCHMARK_PATH = US_CACHE / "benchmarks/us_benchmark_daily_returns.parquet"


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def build_forward_returns(frame: pd.DataFrame, horizons: list[int] = [1, 5, 20]) -> pd.DataFrame:
    data = frame.copy().sort_values(["symbol", "date"]).reset_index(drop=True)
    data["price_for_return"] = pd.to_numeric(data["adj_open"], errors="coerce").fillna(pd.to_numeric(data["open"], errors="coerce"))
    out = data[["symbol", "date"]].copy()
    for horizon in horizons:
        future = data.groupby("symbol")["price_for_return"].shift(-horizon)
        current = data["price_for_return"]
        ret = future / current - 1.0
        valid = current.gt(0) & future.gt(0) & ret.notna()
        out[f"forward_return_{horizon}d"] = ret.where(valid)
        out[f"ret_valid_{horizon}d"] = valid.astype(bool)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare US backtest input caches.")
    parser.add_argument("--benchmark-symbol", default="SPY")
    args = parser.parse_args()
    ohlcv = load_us_ohlcv()
    ohlcv["date"] = pd.to_datetime(ohlcv["date"]).dt.normalize()
    for symbol, frame in ohlcv.groupby("symbol"):
        atomic_write_parquet(frame.sort_values("date"), PRICE_DIR / f"{symbol}.parquet")
    returns = build_forward_returns(ohlcv)
    atomic_write_parquet(returns, RETURNS_PATH)
    status = ohlcv[["symbol", "date", "open", "adj_open", "close", "adj_close", "volume", "dollar_volume", "adjustment_quality"]].copy()
    status["trading_halt"] = pd.to_numeric(status["volume"], errors="coerce").fillna(0).eq(0)
    atomic_write_parquet(status, STATUS_PATH)
    buckets = (
        ohlcv.assign(dollar_volume=pd.to_numeric(ohlcv["dollar_volume"], errors="coerce"))
        .groupby("symbol", as_index=False)
        .agg(avg_dollar_volume=("dollar_volume", "mean"), nonhalt_days=("volume", lambda s: int(pd.to_numeric(s, errors="coerce").gt(0).sum())))
        .sort_values("avg_dollar_volume", ascending=False)
        .reset_index(drop=True)
    )
    buckets["liquidity_rank"] = range(1, len(buckets) + 1)
    buckets["liquidity_bucket"] = pd.qcut(buckets["liquidity_rank"], q=[0, 1 / 3, 2 / 3, 1], labels=["large_liquid", "mid", "small_illiquid"]).astype(str)
    atomic_write_parquet(buckets, BUCKETS_PATH)
    benchmark = ohlcv.loc[ohlcv["symbol"].eq(args.benchmark_symbol.upper())].sort_values("date")
    if not benchmark.empty:
        px = pd.to_numeric(benchmark["adj_close"], errors="coerce").fillna(pd.to_numeric(benchmark["close"], errors="coerce"))
        bench = benchmark[["date"]].copy()
        bench["close"] = px
        bench["daily_return"] = px.pct_change()
        atomic_write_parquet(bench, BENCHMARK_PATH)
    print(json.dumps({"symbols": int(ohlcv["symbol"].nunique()), "rows": int(len(ohlcv)), "max_date": str(ohlcv["date"].max().date())}, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run backtest input tests**

Run:

```powershell
python -m pytest v2/tests/test_us_prepare_backtest_inputs.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add v2/scripts/us_prepare_backtest_inputs.py v2/tests/test_us_prepare_backtest_inputs.py
git commit -m "feat: prepare US backtest inputs"
```

### Task 5: Implement US Signal Catalog

**Files:**
- Create: `v2/scripts/us_signal_catalog.py`
- Test: `v2/tests/test_us_signal_catalog.py`

- [ ] **Step 1: Write signal tests**

Create `v2/tests/test_us_signal_catalog.py`:

```python
from __future__ import annotations

import pandas as pd

from v2.scripts.us_signal_catalog import cs_zscore, signal_1m_reversal


def test_cs_zscore_is_cross_sectional_by_date() -> None:
    frame = pd.DataFrame({"date": ["2024-01-02"] * 3, "symbol": ["A", "B", "C"], "signal_value": [1.0, 2.0, 3.0]})
    out = cs_zscore(frame)
    assert round(float(out["signal_cs_z"].mean()), 12) == 0.0


def test_signal_1m_reversal_is_negative_lookback_return() -> None:
    close = pd.Series([100.0] * 21 + [110.0])
    frame = pd.DataFrame({"adj_close": close})
    out = signal_1m_reversal(frame)
    assert round(float(out.iloc[-1]), 6) == -0.1
```

- [ ] **Step 2: Run failing signal tests**

Run:

```powershell
python -m pytest v2/tests/test_us_signal_catalog.py -q
```

Expected: fail because script does not exist.

- [ ] **Step 3: Implement signal catalog**

Create `v2/scripts/us_signal_catalog.py` with functions for `US_A1` through `US_A9`, `cs_zscore`, and a `--run` CLI that writes raw and z-score parquet files under `v2/data/cache/us/signals_batch/`. Use `adj_close` for price signals and `dollar_volume` for liquidity signals. Mask rows where return inputs are missing or `volume <= 0`.

Required function signatures:

```python
def cs_zscore(frame: pd.DataFrame) -> pd.DataFrame: ...
def signal_12_1_momentum(frame: pd.DataFrame) -> pd.Series: ...
def signal_1m_reversal(frame: pd.DataFrame) -> pd.Series: ...
def signal_low_volatility(frame: pd.DataFrame) -> pd.Series: ...
def signal_liquidity_size(frame: pd.DataFrame) -> pd.Series: ...
def signal_illiquidity(frame: pd.DataFrame) -> pd.Series: ...
def signal_volume_shock(frame: pd.DataFrame) -> pd.Series: ...
def signal_near_high(frame: pd.DataFrame) -> pd.Series: ...
def signal_overnight_gap_reversal(frame: pd.DataFrame) -> pd.Series: ...
def signal_beta_residual(frame: pd.DataFrame, benchmark: pd.DataFrame) -> pd.Series: ...
```

Implementation rule for `cs_zscore`:

```python
def cs_zscore(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    grouped = out.groupby("date")["signal_value"]
    mean = grouped.transform("mean")
    std = grouped.transform(lambda s: s.std(ddof=0))
    out["signal_cs_z"] = (out["signal_value"] - mean) / std.replace(0, pd.NA)
    return out[["symbol", "date", "signal_cs_z"]]
```

- [ ] **Step 4: Run signal tests**

Run:

```powershell
python -m pytest v2/tests/test_us_signal_catalog.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add v2/scripts/us_signal_catalog.py v2/tests/test_us_signal_catalog.py
git commit -m "feat: add US signal catalog"
```

### Task 6: Implement IC Batch Measurement

**Files:**
- Create: `v2/scripts/us_run_ic_batch.py`
- Create report output: `v2/reports/us/us_ic_batch.md`

- [ ] **Step 1: Implement IC script**

Create `v2/scripts/us_run_ic_batch.py` that:

- Loads `v2/data/cache/us/signals_batch/*_cs_zscore.parquet`.
- Loads `v2/data/cache/us/returns/forward_returns.parquet`.
- Computes daily Spearman IC for 1d, 5d, and 20d horizons.
- Writes full daily IC to `v2/data/cache/us/ic/ic_batch_full.parquet`.
- Writes summary to `v2/data/cache/us/ic/ic_batch_summary.parquet`.
- Writes markdown report to `v2/reports/us/us_ic_batch.md`.

Core IC implementation:

```python
def daily_ic(merged: pd.DataFrame, signal_col: str, return_col: str) -> pd.DataFrame:
    rows = []
    for date, group in merged.dropna(subset=[signal_col, return_col]).groupby("date"):
        if len(group) < 30:
            continue
        rows.append({"date": date, "ic": group[signal_col].corr(group[return_col], method="spearman"), "n_valid": len(group)})
    return pd.DataFrame(rows)
```

- [ ] **Step 2: Run IC script**

Run:

```powershell
python v2/scripts/us_run_ic_batch.py --run
```

Expected: report prints a summary with each signal and horizon. If no data exists, it must exit with a clear message naming the missing cache.

- [ ] **Step 3: Commit**

```powershell
git add v2/scripts/us_run_ic_batch.py v2/reports/us/us_ic_batch.md v2/data/cache/us/ic
git commit -m "feat: add US IC batch measurement"
```

### Task 7: Implement US Backtest Batch

**Files:**
- Create: `v2/scripts/us_run_backtest_batch.py`
- Test: `v2/tests/test_us_backtest_batch.py`
- Create report output: `v2/reports/us/us_backtest_batch.md`

- [ ] **Step 1: Write backtest unit tests**

Create `v2/tests/test_us_backtest_batch.py`:

```python
from __future__ import annotations

import pandas as pd

from v2.scripts.us_run_backtest_batch import weights_from_signal


def test_weights_from_signal_long_only_decile_uses_top_names() -> None:
    values = pd.Series(range(100), index=[f"S{i:03d}" for i in range(100)], dtype="float64")
    weights = weights_from_signal(values, "LO_decile")

    assert weights.gt(0).sum() == 10
    assert weights.loc["S099"] == 0.1
    assert weights.loc["S000"] == 0.0


def test_weights_from_signal_long_short_decile_is_dollar_neutral() -> None:
    values = pd.Series(range(100), index=[f"S{i:03d}" for i in range(100)], dtype="float64")
    weights = weights_from_signal(values, "LS_decile")

    assert round(float(weights.sum()), 12) == 0.0
    assert weights.gt(0).sum() == 10
    assert weights.lt(0).sum() == 10
```

- [ ] **Step 2: Implement backtest script**

Create `v2/scripts/us_run_backtest_batch.py` by adapting the current Step 8.4 framework:

- Inputs:
  - `v2/data/cache/us/signals_batch/{signal_id}_cs_zscore.parquet`
  - `v2/data/cache/us/returns/forward_returns.parquet`
  - `v2/data/cache/us/benchmarks/us_benchmark_daily_returns.parquet`
- Portfolios:
  - `LO_decile`
  - `LO_quintile`
  - `LS_decile`
  - `LS_quintile`
- Rebalances:
  - 5d and 20d first; add 1d only for diagnostics because US turnover can dominate.
- Costs:
  - Long-only: 5, 10, 20, 30 bps.
  - Long-short: 10, 20, 30, 50 bps.
- Outputs:
  - `v2/data/cache/us/backtest_batch/all_metrics.parquet`
  - `v2/data/cache/us/backtest_batch/option_{signal_id}_metrics.parquet`
  - `v2/data/cache/us/backtest_batch/option_{signal_id}_pnl_daily.parquet`
  - `v2/reports/us/us_backtest_batch.md`

The verdict table must include:

```text
gate_a_full_sharpe
gate_b_subperiod
gate_c_benchmark_alpha
gate_d_drawdown
verdict
```

- [ ] **Step 3: Run backtest tests**

Run:

```powershell
python -m pytest v2/tests/test_us_backtest_batch.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Run backtest batch**

Run:

```powershell
python v2/scripts/us_run_backtest_batch.py --run
```

Expected: script writes metrics and report. If benchmark is missing, the report must mark benchmark gates as failed, not silently pass.

- [ ] **Step 5: Commit**

```powershell
git add v2/scripts/us_run_backtest_batch.py v2/tests/test_us_backtest_batch.py v2/reports/us/us_backtest_batch.md v2/data/cache/us/backtest_batch
git commit -m "feat: add US backtest batch"
```

### Task 8: Add US Research Audit

**Files:**
- Create: `v2/scripts/us_audit_research_data.py`
- Create report output: `v2/reports/us/us_research_audit.md`

- [ ] **Step 1: Implement audit checks**

Create `v2/scripts/us_audit_research_data.py` that verifies:

- `us_market_ohlcv.parquet` exists and is non-empty.
- universe exists and is non-empty.
- price cache symbol count matches universe count after filters.
- latest processed OHLCV date matches price cache latest date.
- forward returns, trading status, benchmark, signals, IC, and backtest metrics exist.
- reports clearly label `survivorship_biased_current_universe` when the universe has no delisted symbols or no `active_end_date` values.
- reports clearly label `raw_open_only` when adjusted open is unavailable.

Output JSON:

```json
{
  "status": "ok_or_warning_or_error",
  "summary": {
    "errors": 0,
    "warnings": 0,
    "processed_max_date": "YYYY-MM-DD",
    "price_cache_latest_date": "YYYY-MM-DD",
    "universe_symbols": 0
  },
  "checks": []
}
```

- [ ] **Step 2: Run audit**

Run:

```powershell
python v2/scripts/us_audit_research_data.py
```

Expected: status is `warning` for smoke-test/free data unless a production provider with delisting/corporate-action coverage is configured.

- [ ] **Step 3: Commit**

```powershell
git add v2/scripts/us_audit_research_data.py v2/reports/us/us_research_audit.md
git commit -m "feat: add US research audit"
```

### Task 9: End-To-End Smoke Test With Tiny Local Dataset

**Files:**
- Create: `v2/data/raw/us/universe.csv`
- Create: `v2/data/raw/us/ohlcv/AAPL.csv`
- Create: `v2/data/raw/us/ohlcv/MSFT.csv`
- Create: `v2/data/raw/us/ohlcv/SPY.csv`
- Modify: reports generated by scripts

- [ ] **Step 1: Create a tiny local fixture dataset**

Create three CSVs with at least 300 trading rows each so 252-day momentum can produce non-null values. Use deterministic synthetic data if real CSVs are not available. Synthetic data is only for pipeline validation and must be labeled as such in reports.

- [ ] **Step 2: Run the full pipeline**

Run:

```powershell
python v2/scripts/us_build_universe.py --config v2/config/us_market_data.example.json
python v2/scripts/us_update_market_dataset.py --config v2/config/us_market_data.example.json
python v2/scripts/us_prepare_backtest_inputs.py --benchmark-symbol SPY
python v2/scripts/us_signal_catalog.py --run
python v2/scripts/us_run_ic_batch.py --run
python v2/scripts/us_run_backtest_batch.py --run
python v2/scripts/us_audit_research_data.py
```

Expected: every command exits 0. Audit status should be `warning`, not `error`, because fixture data is not production-grade.

- [ ] **Step 3: Run relevant tests**

Run:

```powershell
python -m pytest v2/tests/test_us_schema.py v2/tests/test_us_market_dataset.py v2/tests/test_us_prepare_backtest_inputs.py v2/tests/test_us_signal_catalog.py v2/tests/test_us_backtest_batch.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit smoke-test support**

```powershell
git add v2/data/raw/us v2/data/cache/us v2/reports/us
git commit -m "test: add US pipeline smoke artifacts"
```

### Task 10: Production Data Provider Integration

**Files:**
- Modify: `v2/data/us_providers.py`
- Modify: `v2/config/us_market_data.example.json`
- Create: `v2/reports/us/us_data_source_decision.md`

- [ ] **Step 1: Choose production provider**

Write `v2/reports/us/us_data_source_decision.md` with:

- selected provider
- whether it includes delisted securities
- whether it includes split/dividend adjustment factors
- whether adjusted open is available or constructible
- rate limits and expected full-universe collection time
- license restrictions for local caching
- failure/retry behavior

- [ ] **Step 2: Implement adapter behind `UsMarketDataProvider`**

Add a provider class such as `PolygonUsProvider`, `TiingoUsProvider`, `SharadarUsProvider`, or `NasdaqDataLinkUsProvider`. Keep its public methods identical:

```python
def fetch_universe(self) -> pd.DataFrame: ...
def fetch_daily_bars(self, symbols: list[str], start: str, end: str | None) -> pd.DataFrame: ...
```

The adapter must return frames accepted by `normalize_us_universe` and `normalize_us_ohlcv`.

- [ ] **Step 3: Add provider-specific tests using mocked HTTP responses**

Do not hit the real provider in unit tests. Use fixed JSON/CSV response strings and assert normalized output.

- [ ] **Step 4: Run full collection on limited symbols**

Run:

```powershell
python v2/scripts/us_build_universe.py --config v2/config/us_market_data.local.json
python v2/scripts/us_update_market_dataset.py --config v2/config/us_market_data.local.json --limit-symbols 25
python v2/scripts/us_prepare_backtest_inputs.py --benchmark-symbol SPY
python v2/scripts/us_audit_research_data.py
```

Expected: no schema errors; warnings only for known provider limitations.

- [ ] **Step 5: Commit provider integration**

```powershell
git add v2/data/us_providers.py v2/config/us_market_data.example.json v2/reports/us/us_data_source_decision.md
git commit -m "feat: add production US data provider"
```

## Final Verification Checklist

- [ ] Unit tests pass:

```powershell
python -m pytest v2/tests/test_us_schema.py v2/tests/test_us_market_dataset.py v2/tests/test_us_prepare_backtest_inputs.py v2/tests/test_us_signal_catalog.py v2/tests/test_us_backtest_batch.py -q
```

- [ ] End-to-end scripts exit 0:

```powershell
python v2/scripts/us_build_universe.py --config v2/config/us_market_data.local.json
python v2/scripts/us_update_market_dataset.py --config v2/config/us_market_data.local.json
python v2/scripts/us_prepare_backtest_inputs.py --benchmark-symbol SPY
python v2/scripts/us_signal_catalog.py --run
python v2/scripts/us_run_ic_batch.py --run
python v2/scripts/us_run_backtest_batch.py --run
python v2/scripts/us_audit_research_data.py
```

- [ ] Reports exist:
  - `v2/reports/us/us_ic_batch.md`
  - `v2/reports/us/us_backtest_batch.md`
  - `v2/reports/us/us_research_audit.md`
  - `v2/reports/us/us_data_source_decision.md`

- [ ] The final strategy verdict remains conservative. A signal is not called viable unless it passes all gates after costs and benchmark alpha checks.

## New Session Prompt

Use this prompt to start the next session:

```text
We are in C:\dev\moneygetter_v2\v2. Please implement the plan in docs/superpowers/plans/2026-05-15-us-equity-strategy-search.md task by task. Use the existing KOSPI pipeline only as reference. Keep US artifacts under v2/data/cache/us, v2/data/processed/us_market_ohlcv.parquet, and v2/reports/us. Use TDD for each task, do not claim a strategy is valid without the gates in the plan, and preserve existing user changes in the worktree.
```
