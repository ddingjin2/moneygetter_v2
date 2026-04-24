# PR-7.A.2.a Handoff

Updated: 2026-04-25 KST

## Current State

- Repository path: `C:\dev\moneygetter_v2`
- Working directory used for recent work: `C:\dev\moneygetter_v2\v2`
- Git branch: `option_a_investor_flow`
- The worktree is **not clean**.
- PR-7.A.1.5, PR-7.A.1.6, and PR-7.A.2.a Step 1 files are already staged.
- PR-7.A.2.a has completed **Step 1 only** and is intentionally stopped at the user approval gate before Step 2 full collection.

## Files Added Or Updated For PR-7.A.2.a Step 1

- `v2/scripts/build_pr7_a_2_a_universe.py`
- `v2/data/universe.py`
- `v2/data/cache/universe/kospi_universe.parquet`
- `v2/reports/pr7_a_2_a_full_universe_ic.md`
- This handoff: `v2/reports/pr7_a_2_a_handoff.md`
- Session memory: `v2/reports/pr7_session_memory.md`

## What Step 1 Actually Did

- Active universe source:
  - Naver `sise_market_sum.naver` current KOSPI snapshot
  - local shared OHLCV `C:\dev\moneygetter\data\processed\market_ohlcv.parquet`
- Active universe filter:
  - KOSPI only
  - common stock only
  - ETF / ETN / SPAC / REIT / product-like names excluded
- Delisted handling:
  - local OHLCV history was scanned for names with `last_seen_date < 2026-04-17`
  - only period-delisted common stocks were retained
- Sector source:
  - Naver `item/main.naver`
  - if page redirected or no sector was exposed, sector stayed `NA`

## Universe Result

- Raw latest KOSPI rows from local OHLCV on `2026-04-17`: `2188`
- Active common rows on `2026-04-17`: `806`
- Period-delisted common rows: `2`
- Total universe rows: `808`
- Sector resolved rows: `805`
- Sector missing rows: `3`

Period-delisted names included:

- `008110` `대동전자` until `2026-03-17`
- `138490` `코오롱ENP` until `2026-03-17`

Remaining sector-missing names:

- `008110` `대동전자`
- `071840` `롯데하이마트`
- `138490` `코오롱ENP`

Point-in-time active universe counts already verified through `get_active_universe(date)`:

- `2020-03-27`: `745`
- `2022-01-03`: `771`
- `2026-03-17`: `808`
- `2026-04-17`: `806`

## Reusable Helper

`v2/data/universe.py` now contains:

- `load_kospi_universe(path=...)`
- `get_active_universe(date, universe=None, path=...)`
- existing `filter_nonmicrocap(...)`

Important caveat:

- `listed_date` is a **local OHLCV first-seen proxy**, not a verified exchange listing date.
- For pre-2020-03-27 names, many rows naturally show `2020-01-02`.

## Important Discrepancy To Remember

The user prompt for PR-7.A.2.a states mini-pilot background numbers:

- `divergence_5d x fwd_ret_20d`: `2024 IC_mean 0.0535`, `t-stat 4.31`
- `divergence_5d x fwd_ret_5d`: `2024 IC_mean 0.0307`, `t-stat 2.13`

But the currently staged PR-7.A.1.6 report in this repo shows:

- `divergence_5d x fwd_ret_20d`: `2024 IC_mean 0.0358`, `t-stat 2.66`
- `divergence_5d x fwd_ret_5d`: `2024 IC_mean 0.0353`, `t-stat 2.33`

Do not silently ignore this mismatch in a new session. Call it out if the user asks about consistency.

## Do Not Do Yet

- Do not start Step 2 full-universe flow collection without explicit user approval.
- Do not run IC measurement for PR-7.A.2.a before Step 2 gate approval.
- Do not backtest, build portfolios, or compute PnL.
- Do not tune signal windows.

## Resume Instructions For A New Session

1. Read:
   - `v2/reports/pr7_session_memory.md`
   - `v2/reports/pr7_a_2_a_handoff.md`
   - `v2/reports/pr7_a_2_a_full_universe_ic.md`
2. Confirm the user still wants to proceed to PR-7.A.2.a Step 2.
3. Reuse:
   - `v2/data/cache/universe/kospi_universe.parquet`
   - `v2/data/universe.py:get_active_universe`
4. Implement Step 2 with:
   - serial Naver scraping
   - `0.8s` stock delay
   - `0.2s` page delay
   - checkpoint/resume
   - batch progress reporting every 100 names
5. Stop again after Step 2 and wait for approval before Step 3 onward.

## Validation Already Run

Lint passed for the Step 1 files:

```powershell
uv run ruff check v2/scripts/build_pr7_a_2_a_universe.py v2/data/universe.py
```
