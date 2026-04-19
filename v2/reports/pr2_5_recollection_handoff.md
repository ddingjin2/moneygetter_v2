# PR-2.5 OPENDART Recollection Handoff

Updated: 2026-04-19 KST

## Current State

- Working repo: `C:\dev\moneygetter_v2`
- The shell initially opened in `C:\WINDOWS\System32`; use `C:\dev\moneygetter_v2` as the working directory.
- No git repository is detected at `C:\dev\moneygetter_v2`.
- No background collection process is currently running. `v2/data/cache/pr2_5_collection_meta.json` and `v2/data/cache/pr2_5_collection.pid` were not created.

## Step 0 Result

- `OPENDART_API_KEY` was visible in the process environment.
- Live OPENDART key validation passed:
  - Samsung Electronics 2024 Q1 list query returned status `000`.
  - Test query returned `55` filings.
- `v2/data/cache/earnings_events.parquet` exists with `22,441` events.

## Baseline Before PR-2.5 Recollection

These values are now persisted in `v2/data/cache/collection_checkpoint.json` under `baseline_stats`.

| Metric | Value |
| --- | ---: |
| raw_dart files | 2,036 |
| financial payload files | 1,108 |
| events with all revenue/operating_income/net_income missing | 21,481 |
| SUE non-null events | 680 |
| revenue non-null ratio | 4.18% |
| YoY revenue pair ratio | 3.58% |

## Changes Made

- Added `v2/scripts/collect_earnings_payload.py`.
- The script:
  - reads the API key only from `OPENDART_API_KEY`;
  - validates the key with a live OPENDART request;
  - uses a minute-window rate limiter, default `80` calls/minute;
  - retries transient request/API failures up to 5 attempts;
  - tries `CFS` first, then `OFS`;
  - writes raw payloads to `v2/data/cache/raw_dart/`;
  - updates `v2/data/cache/earnings_events.parquet` every 100 processed events;
  - writes `v2/data/cache/collection_checkpoint.json`;
  - rebuilds YoY fields and SUE after each checkpoint;
  - writes `v2/reports/pr2_5_recollection_report.md`.

## Partial Run Completed

A first 100-event run was completed successfully:

| Metric | Value |
| --- | ---: |
| checkpoint completed events | 100 |
| metric events | 60 |
| OPENDART 013/no-data events | 40 |
| parser metrics-missing events | 0 |
| hard failures | 0 |
| API calls made | 58 |

Current post-partial-run state:

| Metric | Value |
| --- | ---: |
| raw_dart files | 2,094 |
| financial payload files | 1,166 |
| events with all revenue/operating_income/net_income missing | 21,434 |
| SUE non-null events | 680 |
| revenue non-null count | 983 |

Backup created before the first write:

- `v2/data/cache/earnings_events.pr2_5_backup_20260419_040708.parquet`

## Current Resume Plan

From `C:\dev\moneygetter_v2`:

```powershell
echo $env:OPENDART_API_KEY
python v2\scripts\collect_earnings_payload.py --dry-run
```

Expected dry-run after the partial run:

| Item | Value |
| --- | ---: |
| checkpoint completed | 100 |
| cached reparse remaining | 0 |
| new fetch required | 21,381 |
| max expected API calls | 42,762 |
| max expected time at 80/min | 534.5 minutes |

For a full unattended run:

```powershell
python v2\scripts\collect_earnings_payload.py
```

For safer Codex/session-sized chunks:

```powershell
python v2\scripts\collect_earnings_payload.py --max-runtime-minutes 60 --no-start-delay
```

The script resumes from `v2/data/cache/collection_checkpoint.json`; do not delete that file unless intentionally restarting the recollection.

## Post-Collection Commands

After collection finishes:

```powershell
python v2\scripts\validate_earnings_data.py
pytest -q v2/tests
```

Then run the v1 regression tests from the v1 project location expected by the original PR-2.5 prompt.

## Notes For Next Session

- The current report `v2/reports/pr2_5_recollection_report.md` is only a partial-run report and will be overwritten by the collection script.
- PowerShell may render Korean UTF-8 report text as mojibake depending on the active code page; the generated files are written as UTF-8.
- If OPENDART status `020` appears repeatedly, stop and inspect whether it is a minute-rate or daily quota issue before continuing.
