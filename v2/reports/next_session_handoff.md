# Moneygetter v2 next-session handoff

Last updated: 2026-07-15 KST

## Current operating decision

The user wants Moneygetter A4 paper trading to be handled as autonomously as possible by Hermes. Keep communication practical and direct in Korean.

## Active project paths

- v1 project: `/mnt/c/dev/moneygetter`
- v2 project: `/mnt/c/dev/moneygetter_v2/v2`
- v1 processed OHLCV: `/mnt/c/dev/moneygetter/data/processed/market_ohlcv.parquet`
- v2 per-symbol price cache: `/mnt/c/dev/moneygetter_v2/v2/data/cache/price_market_cap_full`
- A4 paper account dir: `/mnt/c/dev/moneygetter_v2/v2/data/cache/paper_trading/a4_20d_top10`

## Current paper-trading setup

- Strategy/account: A4 20d top10 / `A4_60_20d_top10`
- Initial paper capital: 100,000,000 KRW
- Buy fee: 0.1%
- Sell fee: 0.1%
- Current cached latest price date: 2026-07-14
- Current positions: 77
- Current cash: about 657,511.075 KRW
- Current equity: about 101,413,601.075 KRW
- Current cumulative return: +1.4136%
- Rebalance interval: 20 trading days
- Last rebalance/fill date: 2026-07-01
- Current rebalance due: false, elapsed trading days: 9 as of cached 2026-07-14
- Rebalance target notional: current account equity, not fixed initial capital
- SK hynix (000660) was not selected by A4 on any replay date; this was not a share-rounding failure.

## Automation already set up

Hermes cron job:

- Name: `moneygetter-a4-after-close`
- Job ID: `b78bbd32acf7`
- Schedule: `30 16 * * 1-5` = weekdays 16:30 KST
- Script: `moneygetter_a4_after_close.sh`
- Actual script path: `/home/mjin1115/.hermes/scripts/moneygetter_a4_after_close.sh`
- Last known next run: 2026-05-06 16:30 KST

Script behavior:

1. `cd /mnt/c/dev/moneygetter_v2/v2`
2. Run `python3 scripts/run_after_close_a4.py`
3. Write latest run log to:
   `/mnt/c/dev/moneygetter_v2/v2/data/cache/paper_trading/a4_20d_top10/cron_after_close_latest.log`

`run_after_close_a4.py` behavior:

1. Unless `--skip-data-update`, run v1 update:
   `python3 scripts/update_dataset.py --config config/data_pipeline.yaml` under `/mnt/c/dev/moneygetter`
2. Rebuild v2 per-symbol cache from v1 parquet:
   `python3 scripts/prepare_price_market_cap_full.py` under `/mnt/c/dev/moneygetter_v2/v2`
3. Determine latest price date and rebalance due state
4. Process verified delistings, then run paper mark:
   - `python3 scripts/paper_account_a4.py process-delistings --asof <latest>`
   - `python3 scripts/paper_account_a4.py mark`
5. If due, size targets from current equity and run:
   - `python3 scripts/paper_quality_gate_a4.py --strict`
   - `python3 scripts/paper_account_a4.py rebalance --asof <latest>`
   - `python3 scripts/paper_account_a4.py fill --asof <latest>` unless `--no-fill`
6. Unless `--skip-audit`, run:
   `python3 scripts/audit_daily_a4.py`

Useful options:

```bash
cd /mnt/c/dev/moneygetter_v2/v2
python3 scripts/run_after_close_a4.py --dry-run
python3 scripts/run_after_close_a4.py --skip-v1-update
python3 scripts/run_after_close_a4.py --skip-data-update
python3 scripts/run_after_close_a4.py --skip-audit
python3 scripts/run_after_close_a4.py --force-rebalance --no-fill
```

## Daily audit harness

Implemented file:

- `/mnt/c/dev/moneygetter_v2/v2/scripts/audit_daily_a4.py`

Outputs:

- JSON: `/mnt/c/dev/moneygetter_v2/v2/data/cache/paper_trading/a4_20d_top10/daily_audit.json`
- Markdown: `/mnt/c/dev/moneygetter_v2/v2/reports/daily_a4_audit.md`

Audit checks include:

- v1 market_ohlcv exists and nonempty
- v1 latest date
- v2 per-symbol cache file count and read health
- v1/v2 latest date match
- open positions exist
- account cash reconciles against trades cash_flow
- latest equity curve reconciles against current prices
- all open positions have latest prices
- cron log exists and has no obvious error words
- rebalance due calculation

Last verified audit result:

```json
{
  "status": "pass",
  "summary": {
    "errors": 0,
    "warnings": 0,
    "checks": 11,
    "v1_max_date": "2026-04-17",
    "v2_latest_date": "2026-04-17",
    "positions": 75,
    "equity_recomputed": 9990565.845999997,
    "rebalance_due": false,
    "elapsed_trading_days": 0
  }
}
```

Run manually:

```bash
cd /mnt/c/dev/moneygetter_v2/v2
python3 scripts/audit_daily_a4.py
```

## Verification commands already run

```bash
cd /mnt/c/dev/moneygetter_v2/v2
python3 -m py_compile scripts/audit_daily_a4.py scripts/run_after_close_a4.py
python3 scripts/audit_daily_a4.py
python3 scripts/run_after_close_a4.py --dry-run --skip-data-update
```

All passed.

## Hermes config change made

Compression threshold was changed from 50% to 80%:

```yaml
compression:
  enabled: true
  threshold: 0.8
  target_ratio: 0.2
  protect_last_n: 20
  hygiene_hard_message_limit: 400
```

Config path:

- `/home/mjin1115/.hermes/config.yaml`

This applies reliably from new Hermes sessions.

## Migration discussion

The user has a spare laptop and may want to migrate the always-on setup there. Recommended approach:

1. Install Ubuntu 24.04 LTS on the laptop if possible.
2. Disable sleep/lid suspend.
3. Backup/copy `~/.hermes` from current machine.
4. Backup/copy `/mnt/c/dev/moneygetter` and `/mnt/c/dev/moneygetter_v2`.
5. On Ubuntu laptop, restore projects under `~/dev` and create `/mnt/c/dev -> ~/dev` symlink for path compatibility.
6. Install Python deps: pandas, pyarrow, numpy, pyyaml, pykrx, requests.
7. Run `python3 scripts/run_after_close_a4.py --dry-run` under v2.
8. Register OS cron or Hermes cron on the laptop.
9. Pause/remove the old machine's cron job to avoid duplicate automation.

## Important caveats

- This is paper trading only. No real broker orders are sent.
- KIS integration skeleton exists, but real order submission is intentionally not implemented yet.
- pykrx/KRX data can fail or be delayed; use the cron log and daily audit report first when troubleshooting.
- If the user asks for status in a new session, first inspect:
  - `cron_after_close_latest.log`
  - `daily_audit.json`
  - `daily_a4_audit.md`
  - `paper_account_a4.py status`

## Suggested first command in next session

```bash
cd /mnt/c/dev/moneygetter_v2/v2
python3 scripts/audit_daily_a4.py && python3 scripts/paper_account_a4.py status
```

Then summarize the audit status, latest date, cash/equity, positions, and rebalance due state in Korean.
