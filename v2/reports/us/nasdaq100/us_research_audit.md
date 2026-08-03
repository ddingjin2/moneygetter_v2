# US Research Data Audit

- Status: `warning`
- Summary: `{'universe_key': 'nasdaq100', 'errors': 0, 'warnings': 1, 'processed_max_date': '2026-05-29', 'returns_max_date': '2026-05-29', 'benchmark_max_date': '2026-05-29', 'price_files': 102, 'universe_symbols': 101}`

## Checks
| ok    | severity   | code                    | message                                                                                                | details                                                                                                  |
|:------|:-----------|:------------------------|:-------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------|
| True  | error      | processed_exists        | US processed OHLCV exists                                                                              | {'path': 'C:\\dev\\moneygetter_v2\\v2\\data\\processed\\us_nasdaq100_ohlcv.parquet'}                     |
| True  | error      | universe_exists         | US universe exists                                                                                     | {'path': 'C:\\dev\\moneygetter_v2\\v2\\data\\cache\\us\\nasdaq100\\universe\\us_universe.parquet'}       |
| True  | error      | price_cache_exists      | US per-symbol price cache exists                                                                       | {'file_count': 102}                                                                                      |
| True  | error      | input_dates_match       | processed, returns, and status latest dates match                                                      | {'processed': '2026-05-29', 'returns': '2026-05-29', 'status': '2026-05-29'}                             |
| True  | warning    | benchmark_date_matches  | benchmark latest date matches processed latest date                                                    | {'benchmark': '2026-05-29', 'processed': '2026-05-29'}                                                   |
| True  | error      | signals_exist           | US signal z-score files exist                                                                          | {}                                                                                                       |
| True  | error      | ic_exists               | US IC summary exists                                                                                   | {'path': 'C:\\dev\\moneygetter_v2\\v2\\data\\cache\\us\\nasdaq100\\ic\\ic_batch_summary.parquet'}        |
| True  | error      | backtest_exists         | US backtest metrics exist                                                                              | {'path': 'C:\\dev\\moneygetter_v2\\v2\\data\\cache\\us\\nasdaq100\\backtest_batch\\all_metrics.parquet'} |
| False | warning    | survivorship_bias       | Current nasdaq100 universe is survivorship-biased and is not production-grade point-in-time membership | {'symbols': 101}                                                                                         |
| True  | warning    | adjusted_open_available | Adjusted open is available for all rows                                                                | {'raw_open_only_rows': 0}                                                                                |
