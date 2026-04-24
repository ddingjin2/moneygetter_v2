# PR-7.A.1 Handoff

Updated: 2026-04-19 KST

## Current State

- Repository path: `C:\dev\moneygetter_v2`.
- Git branch: `option_a_investor_flow`.
- Initial snapshot commit exists: `2d079b5f v2 옵션 B 종결 시점 스냅샷 (PR-6 완료)`.
- Remote: `https://github.com/ddingjin2/moneygetter_v2.git`.
- Branch `option_a_investor_flow` has been pushed to origin.
- PR-7.A.1 has completed Step 1 only and is intentionally stopped at the Step 1.5 user gate.
- Do not run Step 2 full-universe collection unless the user explicitly approves continuing after reviewing the pilot result.

## Files Added In PR-7.A.1 Step 1

- `v2/scripts/explore_naver_investor_flow.py`
- `v2/reports/pr7_a_1_data_exploration.md`
- `v2/data/cache/investor_flow_pilot/005930.parquet`
- This handoff: `v2/reports/pr7_a_1_handoff.md`

These files are currently uncommitted unless a later session commits them.

## Environment Checks Already Passed

- `pwd`: `C:\dev\moneygetter_v2`
- `git status -sb`: branch was `option_a_investor_flow...origin/option_a_investor_flow`
- Required prior cache files existed:
  - `v2/data/cache/earnings_events.parquet`
  - `v2/data/cache/kospi_daily.parquet`
  - `v2/data/cache/trades/`

## Step 1 Source Probe

User instruction for source priority:

1. Naver Finance first.
2. FinanceDataReader fallback only if Naver fails.
3. Do not retry pykrx. pykrx/KRX was already observed failing in prior work.

Naver URL pattern tested:

```text
https://finance.naver.com/item/frgn.naver?code=005930&page=1
```

The useful table contains these fields:

- date
- close
- volume
- foreign net buy shares
- institutional net buy shares
- foreign holding shares
- foreign holding ratio

## Samsung Electronics Pilot Result

Source: `v2/reports/pr7_a_1_data_exploration.md`

- Pilot stock: Samsung Electronics `005930`
- Requested date range: `2020-01-01` to `2026-04-17`
- Source used: Naver Finance
- Pages fetched: `78`
- Rows collected: `1,545`
- Date range collected: `2020-01-02` to `2026-04-17`
- Simple Mon-Fri business-day row ratio: `0.9403530127814973`
- Missing vs simple Mon-Fri business days: `98`
- Errors: none
- Fallback: not attempted because Naver succeeded

Pilot parquet:

```text
v2/data/cache/investor_flow_pilot/005930.parquet
```

Schema:

| column | dtype |
| --- | --- |
| date | datetime64[ns] |
| close | Int64 |
| volume | Int64 |
| foreign_net_buy_shares | Int64 |
| institutional_net_buy_shares | Int64 |
| foreign_holding_shares | Int64 |
| foreign_holding_ratio | float64 |

Required column completeness:

| column | exists | non_null_ratio |
| --- | --- | --- |
| foreign_net_buy_shares | True | 1.0000 |
| institutional_net_buy_shares | True | 1.0000 |

## Known Problems From Pilot

1. Individual net buy is not available from Naver `frgn.naver`.
2. Individual net buy cannot be derived as `volume - foreign - institutional`; volume is total traded volume, not total net buy.
3. Net buy value columns are not available. Value can only be approximated later, e.g. shares times close, and that is not true traded value.
4. Naver is HTML scraping, not an official API. Full collection must use one request at a time, at least one second delay, retries, checkpointing, and transparent failure reporting.
5. Point-in-time timing remains unknown. Conservative assumption for later signal work: T-day flow is usable no earlier than T+1 open.
6. Samsung Electronics is a best-case large-cap pilot. Do not assume the same coverage for all earnings-event stocks.

## Validation Already Run

Only the new pilot script was linted:

```powershell
uv run ruff check v2/scripts/explore_naver_investor_flow.py
```

Result: all checks passed.

Full test suite was not rerun after Step 1 because this stage intentionally stopped at the user gate.

## Resume Instructions For A New Session

If the user pastes the original PR-7.A.1 prompt again:

1. Verify `pwd`, git branch, and required caches.
2. Read `v2/reports/pr7_a_1_data_exploration.md` and this handoff first.
3. Do not rerun the Samsung pilot unless the user explicitly requests it.
4. State that Step 1 is complete and ask/confirm whether to proceed past Step 1.5.
5. Only after explicit approval, implement Step 2 onward:
   - `v2/data/investor_flow_loader.py`
   - checkpointed per-stock collection under `v2/data/cache/investor_flow/`
   - `v2/data/cache/investor_flow_checkpoint.json`
   - `v2/data/cache/investor_flow_failed_stocks.json`
   - `v2/tests/test_investor_flow_loader.py`
   - `v2/reports/pr7_a_1_data_collection_report.md`

Restrictions still active for PR-7.A.1:

- No signal definitions.
- No backtests.
- No investment ideas.
- No pykrx retry.
- No Step 2 full collection without user approval.
- Naver scraping must remain serial and rate-limited.
