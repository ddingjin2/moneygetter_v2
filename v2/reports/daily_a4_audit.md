# Daily A4 audit

- generated_at: 2026-09-17T21:04:45.900062+09:00
- status: **warning**
- processed_max_date: 2026-09-17
- v2_latest_date: 2026-09-17
- positions: 77
- equity_recomputed: 115388579.721
- rebalance_due: False
- elapsed_trading_days: 12

## Checks

| status | severity | code | message |
| --- | --- | --- | --- |
| OK | error | `processed_ohlcv_exists` | v2 processed market_ohlcv parquet exists |
| OK | error | `processed_ohlcv_nonempty` | v2 processed market_ohlcv has rows |
| OK | error | `v2_cache_file_count` | v2 per-symbol price cache has expected file count |
| OK | error | `v2_cache_readable` | v2 price cache files are readable |
| OK | warning | `processed_cache_latest_date_match` | v2 processed and per-symbol cache latest dates match |
| OK | error | `positions_nonempty` | paper account has open positions |
| OK | error | `cash_reconciles` | account cash reconciles with trade cash flows |
| OK | warning | `equity_curve_reconciles` | latest equity curve row reconciles with current prices |
| OK | error | `all_positions_priced` | all open positions have latest prices |
| OK | warning | `cron_log_exists` | latest after-close cron log exists |
| FAIL | warning | `cron_log_clean` | latest cron log tail has no obvious error words |

## Key reconciliation

- cash: 510071.721
- expected_cash_from_trades: 510071.721
- cash_diff_vs_trades: -0.000000
- market_value_recomputed: 114878508.000
- equity_diff_vs_curve: 0.000000

