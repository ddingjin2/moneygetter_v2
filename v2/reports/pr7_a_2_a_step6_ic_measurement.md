# PR-7.A.2.a Step 6 IC Measurement

## 1. Universe & Data Summary
- Universe stocks: `808`
- Date range: `2020-03-27 ~ 2026-04-17`
- Total (code, date) pairs: `1157935`
- Signal valid ratio: `99.7%`
- Return valid ratios: `1d=99.9%`, `5d=99.7%`, `20d=98.6%`
- Valid signal-return pairs: `1d=1153895`, `5d=1150663`, `20d=1138543`
- Trading halt rows: `0` across `0` stocks and `0` dates

### Trading Halt Date Distribution Top 20
(none)

## 2. Size Bucket Distribution

Market-cap was unavailable; size buckets use average daily trading value proxy `mean(close * volume)` excluding rows where `volume == 0 and open == 0`.

### Boundaries
| size_bucket | rank_min | rank_max | avg_daily_value_min | avg_daily_value_max |
| --- | --- | --- | --- | --- |
| large | 1 | 270 | 7811994498 | 1456761391929 |
| mid | 271 | 539 | 2007592230 | 7806077421 |
| small | 540 | 808 | 30608329 | 2007100547 |

### Bucket Summary
| size_bucket | count | avg_daily_value_mean | avg_daily_value_min | avg_daily_value_max |
| --- | --- | --- | --- | --- |
| large | 270 | 46574349257 | 7811994498 | 1456761391929 |
| mid | 269 | 4119647363 | 2007592230 | 7806077421 |
| small | 269 | 996050880 | 30608329 | 2007100547 |

## 3. Full Universe IC Results
| horizon | mean_ic | std_ic | t_stat | p_value | positive_ratio | n_days | avg_n_valid |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1d | -0.0100 | 0.0630 | -6.09 | 0.0000 | 42.2% | 1481 | 779.1 |
| 5d | -0.0094 | 0.0578 | -6.24 | 0.0000 | 44.1% | 1477 | 779.1 |
| 20d | -0.0083 | 0.0553 | -5.74 | 0.0000 | 44.4% | 1462 | 778.8 |

- Option A 5d sign check: `negative` mean IC for `divergence_5d = institutional_5d_mean - foreign_5d_mean`.
- Because the signal is institutional minus foreign flow, positive IC means higher institutional-relative flow predicts higher forward return; negative IC means the opposite.

### Largest Absolute Daily IC Observations
| horizon | date | ic | n_valid |
| --- | --- | --- | --- |
| 1d | 2022-06-24 | -0.3196 | 772 |
| 1d | 2024-12-13 | -0.2283 | 798 |
| 1d | 2026-01-20 | 0.2231 | 807 |
| 1d | 2021-10-06 | -0.2133 | 768 |
| 1d | 2024-12-10 | -0.2073 | 798 |
| 5d | 2022-06-27 | 0.2064 | 772 |
| 5d | 2022-02-17 | 0.1732 | 772 |
| 5d | 2021-05-31 | -0.1696 | 759 |
| 5d | 2023-04-03 | 0.1685 | 776 |
| 5d | 2024-04-17 | -0.1681 | 791 |
| 20d | 2022-06-24 | -0.2270 | 772 |
| 20d | 2023-04-28 | 0.2161 | 778 |
| 20d | 2022-06-23 | -0.1999 | 772 |
| 20d | 2021-05-31 | -0.1982 | 759 |
| 20d | 2026-01-23 | -0.1664 | 807 |

## 4. Size-stratified IC
| size_bucket | 1d | 5d | 20d |
| --- | --- | --- | --- |
| large | -0.0054 | -0.0049 | -0.0085 |
| mid | -0.0107 | -0.0081 | -0.0028 |
| small | -0.0172 | -0.0144 | -0.0132 |

- Judgment: `small bucket has the largest absolute 5d IC`.

## 5. Mini-pilot In/Out IC
| split | 1d | 5d | 20d |
| --- | --- | --- | --- |
| mini_pilot_in_30 | -0.0105 | -0.0090 | -0.0038 |
| mini_pilot_out_778 | -0.0098 | -0.0092 | -0.0081 |

- 5d in/out judgment: `same sign`.

## 6. Trading Halt / Illiquid Impact
### Valid Stock Count Distribution
| horizon | min | p05 | median | p95 | max | days_lt_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 1d | 745 | 747.0 | 776.0 | 806.0 | 808 | 0 |
| 5d | 745 | 747.0 | 776.0 | 806.0 | 807 | 0 |
| 20d | 745 | 747.0 | 776.0 | 806.0 | 807 | 0 |

### Excluding Days With Fewer Than 100 Valid Stocks
| horizon | all_mean_ic | n_ge_100_mean_ic | diff |
| --- | --- | --- | --- |
| 1d | -0.0100 | -0.0100 | 0.0000 |
| 5d | -0.0094 | -0.0094 | 0.0000 |
| 20d | -0.0083 | -0.0083 | 0.0000 |

## 7. Caveats For Backtest Gate
- Alive-only universe caveat remains: roughly 30-80 delisted names may be missing from the universe reconstruction.
- market_cap is unavailable. Size buckets use trading-value proxy, so large/mid/small definitions are weaker than market-cap buckets.
- Market-cap-weighted backtest is not possible from current sources; only equal-weight or trading-value proxy variants are feasible.
- Trading halt mask is consistently defined as `volume == 0 and open == 0`; halt rows are excluded from signal rolling inputs and returns are invalid when current or forward endpoint is halted.
- 2020-2021 investor-flow data was actually collected at full expected KOSPI trading-day coverage in Step 2; Step 2 report recorded 100% yearly average coverage.

## 8. Artifacts
- Size buckets: `v2\data\cache\price_market_cap_full\_size_buckets.parquet`
- Trading status: `v2\data\cache\price_market_cap_full\_trading_status.parquet`
- Signals: `v2\data\cache\signals\option_a_divergence_5d.parquet`
- Forward returns: `v2\data\cache\returns\forward_returns.parquet`
- Full universe IC: `v2\data\cache\ic\ic_full_universe.parquet`
- Size bucket IC: `v2\data\cache\ic\ic_by_size_bucket.parquet`
- Mini-pilot split IC: `v2\data\cache\ic\ic_minipilot_split.parquet`

## Gate
Step 6 IC measurement complete. Stop here; do not enter Step 7 backtest without user approval.
