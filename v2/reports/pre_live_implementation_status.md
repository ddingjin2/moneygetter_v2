# Pre-live implementation status

Completed in this pass:

1. Incremental after-close OHLCV updater
- Script: `scripts/update_after_close_ohlcv.py`
- Uses `pykrx` when installed.
- Updates `data/cache/price_market_cap_full/*.parquet` by date range.
- Current environment does not have pykrx installed, so live download requires:
  ```bash
  python3 -m pip install pykrx
  ```

2. Data quality gate
- Script: `scripts/paper_quality_gate_a4.py`
- Checks latest date, universe count, bad price ratio, zero volume count, paper account existence.
- Latest verification:
  - latest_price_date: 2026-04-17
  - universe_count: 806
  - bad_price_count: 0
  - zero_volume_count: 40
  - pass: true

3. Liquidity guard
- Script updated: `scripts/paper_trade_a4.py`
- Adds per-order fields:
  - `a4_avg_dvol_krw`
  - `order_to_avg_dvol`
  - `liquidity_warning`
- Default warning threshold: order amount > 5% of 60d average traded value.

4. Performance report
- Script: `scripts/report_paper_performance_a4.py`
- Report: `reports/paper_trading_performance.md`
- Summarizes cash, market value, equity, cumulative return, drawdown, trades, top positions.

5. KIS order preview skeleton
- Script updated: `scripts/kis_client.py`
- Added `preview-orders` command.
- Default preview reads current `latest_state.json` -> orders CSV and summarizes without sending orders.
- Optional `--use-live-quotes` fetches KIS quotes if credentials are configured.
- Real order submission remains intentionally unimplemented.

6. After-close runner integrated with quality gate
- Script updated: `scripts/run_after_close_a4.py`
- On rebalance due, it now runs `paper_quality_gate_a4.py --strict` before generating/filling orders.

## Verification commands run

```bash
python3 -m py_compile \
  scripts/update_after_close_ohlcv.py \
  scripts/paper_quality_gate_a4.py \
  scripts/report_paper_performance_a4.py \
  scripts/paper_trade_a4.py \
  scripts/run_after_close_a4.py \
  scripts/kis_client.py

python3 scripts/paper_quality_gate_a4.py --strict
python3 scripts/report_paper_performance_a4.py
python3 scripts/paper_account_a4.py rebalance
python3 scripts/kis_client.py preview-orders
python3 scripts/run_after_close_a4.py --dry-run --skip-data-update
```

All passed.

## Current state

- Paper account exists and is marked.
- Current latest cached date: 2026-04-17
- Current rebalance due: false because elapsed trading days since 2026-04-17 is 0.
- Current generated orders after already being in target portfolio: 0 rows.

## Remaining blocker before true live operation

1. Install and test pykrx or choose KIS as data source.
2. Configure KIS credentials and verify:
   ```bash
   python3 scripts/kis_client.py check-env
   python3 scripts/kis_client.py quote 005930
   python3 scripts/kis_client.py balance
   ```
3. Run at least a few after-close cycles with fresh data.
4. Implement actual order submit only after quote/balance/preview are verified.

## Safe daily command once pykrx/data is ready

```bash
cd /mnt/c/dev/moneygetter_v2/v2
python3 scripts/run_after_close_a4.py
python3 scripts/report_paper_performance_a4.py
```

## Safe preview command before any real broker order code is added

```bash
python3 scripts/kis_client.py preview-orders
# later, with KIS credentials:
python3 scripts/kis_client.py preview-orders --use-live-quotes
```
