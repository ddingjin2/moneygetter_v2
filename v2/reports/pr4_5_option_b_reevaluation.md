# PR-4.5 Option B Reevaluation

## Step 0.1 Ledger Schema Confirmation
| file | total_rows | fold_distribution | variant_values | entry_date_min | entry_date_max |
| --- | --- | --- | --- | --- | --- |
| pr3_a_sue_only_latest.parquet | 404 | {0: 199, 1: 67, 2: 73, 3: 65} | ['a_sue_only'] | 2023-03-27 | 2026-03-20 |
| pr4_a_sue_only_latest.parquet | 404 | {0: 199, 1: 67, 2: 73, 3: 65} | ['a_sue_only'] | 2023-03-27 | 2026-03-20 |
| pr4_b_sue_near_high_latest.parquet | 156 | {0: 81, 1: 22, 2: 19, 3: 34} | ['b_sue_near_high'] | 2023-05-03 | 2026-03-23 |
| pr4_c_sue_far_from_high_latest.parquet | 286 | {0: 139, 1: 55, 2: 65, 3: 27} | ['c_sue_far_from_high'] | 2023-03-28 | 2026-03-20 |
| pr4_d_proximity_only_latest.parquet | 369 | {0: 184, 1: 61, 2: 62, 3: 62} | ['d_proximity_only'] | 2023-05-03 | 2026-03-20 |

Fold meaning confirmed from PR-4.6 runner code: `fold=0` is the fixed full test ledger (`stage1_test_ledger_70`); `fold=1..3` are Stage 6 walk-forward test ledgers.

## Step 0.2 Analysis Scope
All primary diagnostics use WF fold 1/2/3 test trades only. The full fixed test ledger (`fold=0`) is excluded except where Step 4.1 explicitly uses it as a final-entry reference.
| variant | wf_test_rows |
| --- | --- |
| A | 205 |
| B | 75 |
| C | 147 |
| D | 185 |

## Step 1. A Baseline Recheck
### 1.1 Fold Mapping Table
KOSPI index data status: no KOSPI/index-like daily file was found under `v2/data/cache`, so KOSPI return/volatility/correlation fields are left blank.
| Variant | Fold | Train period | Test period | Test Trades | Test PF (70bps) | KOSPI Test Return | KOSPI Vol Annualized |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 2020-03-27 ~ 2023-03-26 | 2023-03-27 ~ 2024-03-26 | 67 | 1.3883 |  |  |
| A | 2 | 2021-03-27 ~ 2024-03-26 | 2024-03-27 ~ 2025-03-26 | 73 | 0.8414 |  |  |
| A | 3 | 2022-03-27 ~ 2025-03-26 | 2025-03-27 ~ 2026-03-26 | 65 | 3.1521 |  |  |
| B | 1 | 2020-03-27 ~ 2023-03-26 | 2023-03-27 ~ 2024-03-26 | 22 | 0.2966 |  |  |
| B | 2 | 2021-03-27 ~ 2024-03-26 | 2024-03-27 ~ 2025-03-26 | 19 | 0.7586 |  |  |
| B | 3 | 2022-03-27 ~ 2025-03-26 | 2025-03-27 ~ 2026-03-26 | 34 | 6.5985 |  |  |

### 1.2 Fold PF And KOSPI Correlation
| Variant | PF vs KOSPI return Pearson | PF vs KOSPI volatility Pearson | Note |
| --- | --- | --- | --- |
| A |  |  | KOSPI index data unavailable; n=3 correlation would be reference-only |
| B |  |  | KOSPI index data unavailable; n=3 correlation would be reference-only |

### 1.3 A Baseline Fold_2 Details
| fold | trade_count | win_rate | avg_win_pct | avg_loss_pct | PF |
| --- | --- | --- | --- | --- | --- |
| 2 | 73 | 0.4521 | 11.0600 | -10.6445 | 0.8414 |

A Fold_2 top 10 loss trades:
| stock_code | entry_date | exit_date | holding_days | entry_price | exit_price | raw_return | net_return | sue_value | exit_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 003570 | 2024-11-08 | 2024-12-05 | 20 | 25050.0000 | 18380.0000 | -0.2663 | -0.2714 | 0.2620 | fixed_20d |
| 012450 | 2024-11-14 | 2024-12-11 | 20 | 397328.0000 | 293442.0000 | -0.2615 | -0.2666 | 1.0224 | fixed_20d |
| 001570 | 2024-03-28 | 2024-04-25 | 20 | 120000.0000 | 91200.0000 | -0.2400 | -0.2453 | -2.0654 | fixed_20d |
| 092790 | 2024-11-29 | 2024-12-27 | 20 | 9880.0000 | 7680.0000 | -0.2227 | -0.2281 | 0.1200 | fixed_20d |
| 006340 | 2024-11-11 | 2024-12-06 | 20 | 3055.0000 | 2420.0000 | -0.2079 | -0.2134 | 0.5625 | fixed_20d |
| 103590 | 2024-08-14 | 2024-09-11 | 20 | 23700.0000 | 19180.0000 | -0.1907 | -0.1964 | 1.2990 | fixed_20d |
| 025560 | 2024-10-31 | 2024-11-27 | 20 | 20635.0000 | 16870.0000 | -0.1825 | -0.1882 | 0.6357 | fixed_20d |
| 003010 | 2024-11-12 | 2024-12-09 | 20 | 5160.0000 | 4220.0000 | -0.1822 | -0.1879 | 0.1285 | fixed_20d |
| 023960 | 2024-11-14 | 2024-12-11 | 20 | 1684.0000 | 1390.0000 | -0.1746 | -0.1803 | 1.3924 | fixed_20d |
| 074610 | 2024-08-13 | 2024-09-10 | 20 | 19750.0000 | 16370.0000 | -0.1711 | -0.1769 | 2.2791 | fixed_20d |

A Fold_2 top 10 profit trades:
| stock_code | entry_date | exit_date | holding_days | entry_price | exit_price | raw_return | net_return | sue_value | exit_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 008970 | 2024-05-16 | 2024-06-13 | 20 | 1334.0000 | 2105.0000 | 0.5780 | 0.5670 | 1.7362 | fixed_20d |
| 004310 | 2024-07-15 | 2024-08-09 | 20 | 3530.0000 | 5500.0000 | 0.5581 | 0.5472 | -0.6435 | fixed_20d |
| 071970 | 2024-04-02 | 2024-04-30 | 20 | 11950.0000 | 16110.0000 | 0.3481 | 0.3387 | 2.5247 | fixed_20d |
| 339770 | 2024-05-13 | 2024-06-11 | 20 | 4057.0000 | 5164.0000 | 0.2729 | 0.2640 | 0.9374 | fixed_20d |
| 003570 | 2025-02-21 | 2025-03-21 | 20 | 29000.0000 | 34100.0000 | 0.1759 | 0.1677 | 3.0659 | fixed_20d |
| 020150 | 2024-05-16 | 2024-06-13 | 20 | 47000.0000 | 55000.0000 | 0.1702 | 0.1620 | 1.3086 | fixed_20d |
| 001080 | 2025-02-17 | 2025-03-17 | 20 | 2180.0000 | 2545.0000 | 0.1674 | 0.1593 | 1.9677 | fixed_20d |
| 012800 | 2024-11-14 | 2024-12-11 | 20 | 1108.0000 | 1280.0000 | 0.1552 | 0.1472 | 0.8643 | fixed_20d |
| 009470 | 2024-05-13 | 2024-06-11 | 20 | 72600.0000 | 83000.0000 | 0.1433 | 0.1353 | 1.2640 | fixed_20d |
| 073240 | 2024-11-14 | 2024-12-11 | 20 | 4225.0000 | 4795.0000 | 0.1349 | 0.1270 | 0.8162 | fixed_20d |

## Step 2. B Variant Fold_3 Concentration
### 2.1 B Monthly PnL
| Month | Trade Count | Net Return Sum | PnL KRW Sum | Share of Net PnL (%) | Share of Absolute Returns (%) | Cumulative Absolute Share (%) |
| --- | --- | --- | --- | --- | --- | --- |
| 2023-05 | 8 | -0.5823 | -2904737.1644 | -26.4414 | 10.4993 | 10.4993 |
| 2023-08 | 9 | -0.2301 | -1103424.8257 | -10.4489 | 4.1490 | 14.6484 |
| 2023-11 | 5 | -0.2256 | -1083021.4547 | -10.2468 | 4.0688 | 18.7172 |
| 2024-05 | 7 | 0.0087 | 44082.3472 | 0.3928 | 0.1560 | 18.8731 |
| 2024-07 | 1 | 0.0221 | 110366.9231 | 1.0019 | 0.3978 | 19.2710 |
| 2024-08 | 7 | -0.3789 | -1895677.4889 | -17.2057 | 6.8320 | 26.1030 |
| 2024-11 | 4 | 0.1194 | 586667.4953 | 5.4226 | 2.1532 | 28.2562 |
| 2025-04 | 1 | -0.0070 | -34877.9273 | -0.3168 | 0.1258 | 28.3820 |
| 2025-05 | 18 | 3.1549 | 15861140.5231 | 143.2636 | 56.8870 | 85.2690 |
| 2025-08 | 7 | 0.5690 | 3291174.2299 | 25.8384 | 10.2599 | 95.5289 |
| 2025-11 | 8 | -0.2480 | -1476939.9484 | -11.2599 | 4.4711 | 100.0000 |

| top1_net_pnl_share_pct | top3_net_pnl_share_pct | top1_abs_return_share_pct | top3_abs_return_share_pct | top_positive_month |
| --- | --- | --- | --- | --- |
| 139.1969 | 173.2287 | 56.8870 | 77.6463 | 2025-05 |

### 2.2 B 2025-05 Trade Details
| stock_code | entry_date | exit_date | holding_days | entry_price | exit_price | net_return | sue_value | proximity_value | exit_reason | fold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 071320 | 2025-05-14 | 2025-06-12 | 20 | 58700.0000 | 80300.0000 | 0.3584 | 0.7709 | 0.9503 | fixed_20d | 3 |
| 003540 | 2025-05-15 | 2025-06-13 | 20 | 19870.0000 | 24650.0000 | 0.2319 | 0.4075 | 0.9861 | fixed_20d | 3 |
| 044820 | 2025-05-15 | 2025-06-13 | 20 | 12800.0000 | 16840.0000 | 0.3064 | 0.6603 | 0.9860 | fixed_20d | 3 |
| 003200 | 2025-05-16 | 2025-06-16 | 20 | 9430.0000 | 10890.0000 | 0.1468 | 1.4804 | 0.9937 | fixed_20d | 3 |
| 003230 | 2025-05-16 | 2025-06-16 | 20 | 1121000.0000 | 1279000.0000 | 0.1330 | 0.4269 | 0.9812 | fixed_20d | 3 |
| 003240 | 2025-05-16 | 2025-06-16 | 20 | 867000.0000 | 1061000.0000 | 0.2152 | 0.4987 | 0.9687 | fixed_20d | 3 |
| 003830 | 2025-05-16 | 2025-06-16 | 20 | 122600.0000 | 147400.0000 | 0.1939 | 0.6351 | 0.9838 | fixed_20d | 3 |
| 003920 | 2025-05-16 | 2025-06-16 | 20 | 79500.0000 | 69200.0000 | -0.1356 | 0.3094 | 0.9785 | fixed_20d | 3 |
| 004960 | 2025-05-16 | 2025-06-16 | 20 | 7580.0000 | 8830.0000 | 0.1568 | 0.3586 | 0.9523 | fixed_20d | 3 |
| 012630 | 2025-05-16 | 2025-06-16 | 20 | 19800.0000 | 22600.0000 | 0.1335 | 0.8630 | 0.9924 | fixed_20d | 3 |
| 017960 | 2025-05-16 | 2025-06-16 | 20 | 21850.0000 | 23950.0000 | 0.0885 | 2.2608 | 0.9861 | fixed_20d | 3 |
| 030610 | 2025-05-16 | 2025-06-16 | 20 | 7210.0000 | 8380.0000 | 0.1542 | 0.5724 | 0.9710 | fixed_20d | 3 |
| 034830 | 2025-05-16 | 2025-06-16 | 20 | 1077.0000 | 1253.0000 | 0.1553 | 1.0589 | 0.9607 | fixed_20d | 3 |
| 071050 | 2025-05-16 | 2025-06-16 | 20 | 93000.0000 | 125800.0000 | 0.3433 | 0.3920 | 0.9926 | fixed_20d | 3 |
| 139130 | 2025-05-16 | 2025-06-16 | 20 | 10530.0000 | 11820.0000 | 0.1147 | 0.3747 | 0.9897 | fixed_20d | 3 |
| 278470 | 2025-05-16 | 2025-06-16 | 20 | 112200.0000 | 132600.0000 | 0.1736 | 0.7851 | 0.9779 | fixed_20d | 3 |
| 352820 | 2025-05-16 | 2025-06-16 | 20 | 274000.0000 | 299000.0000 | 0.0836 | 0.6676 | 0.9856 | fixed_20d | 3 |
| 383800 | 2025-05-16 | 2025-06-16 | 20 | 7210.0000 | 9450.0000 | 0.3015 | 0.5311 | 0.9660 | fixed_20d | 3 |

### 2.3 B Fold_3 Excluding 2025-05
| Variant | Fold | Original Fold_3 PF | Original Trade Count | Excluded 2025-05 Trade Count | Remaining Trade Count | Recalculated PF | Bucket |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | 3 | 6.5985 | 34 | 18 | 16 | 1.7209 | 1.5 or higher: Fold_3 PF has support outside 2025-05 |

### 2.4 A Fold_3 Top Month Check
A Fold_3 monthly PnL:
| Month | Trade Count | Net Return Sum | PnL KRW Sum | Share of Net PnL (%) | Share of Absolute Returns (%) | Cumulative Absolute Share (%) |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-04 | 2 | -0.0074 | -37018.0392 | -0.1849 | 0.1556 | 0.1556 |
| 2025-05 | 20 | 3.6121 | 18166617.8572 | 90.1924 | 75.9008 | 76.0563 |
| 2025-07 | 1 | 0.0765 | 451679.4185 | 1.9095 | 1.6069 | 77.6632 |
| 2025-08 | 20 | -0.0556 | -328176.9300 | -1.3875 | 1.1676 | 78.8308 |
| 2025-11 | 20 | 0.6934 | 4085898.2242 | 17.3128 | 14.5695 | 93.4003 |
| 2026-02 | 2 | -0.3141 | -1922382.0555 | -7.8424 | 6.5997 | 100.0000 |

| Variant | Fold | Original Fold_3 PF | Top Positive Month | Top Month Share of Net PnL (%) | Excluded Trade Count | Remaining Trade Count | Recalculated PF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 3 | 3.1521 | 2025-05 | 88.9796 | 20 | 45 | 1.2372 |

## Step 3. Stock/Sector Concentration
### 3.1 Stock Concentration Summary
| Variant | WF test trades | unique stock count | top10 trade count share (%) | top10 abs PnL share (%) | top1 abs PnL share (%) |
| --- | --- | --- | --- | --- | --- |
| A | 205 | 140 | 9.7561 | 25.2138 | 3.8031 |
| B | 75 | 65 | 14.6667 | 38.1973 | 7.1056 |

A top 10 stocks by absolute PnL:
| Rank | stock_code | trade count | gross PnL | PnL share (%) |
| --- | --- | --- | --- | --- |
| 1 | 008970 | 1 | 2843347.9065 | 3.8031 |
| 2 | 249420 | 1 | 2290566.0725 | 3.0637 |
| 3 | 105840 | 1 | 2100238.5783 | 2.8092 |
| 4 | 136490 | 4 | 2077723.9783 | 2.7790 |
| 5 | 071320 | 1 | 1808884.9362 | 2.4195 |
| 6 | 071970 | 1 | 1687720.1703 | 2.2574 |
| 7 | 044820 | 1 | 1559547.3103 | 2.0860 |
| 8 | 003570 | 3 | -1535988.7921 | 2.0544 |
| 9 | 042700 | 1 | 1524269.0258 | 2.0388 |
| 10 | 900140 | 6 | 1422609.2944 | 1.9028 |

B top 10 stocks by absolute PnL:
| Rank | stock_code | trade count | gross PnL | PnL share (%) |
| --- | --- | --- | --- | --- |
| 1 | 003230 | 2 | 2856089.4830 | 7.1056 |
| 2 | 071320 | 1 | 1791526.5946 | 4.4571 |
| 3 | 077970 | 1 | 1778782.0723 | 4.4254 |
| 4 | 071050 | 1 | 1728071.5271 | 4.2992 |
| 5 | 044820 | 1 | 1537777.5836 | 3.8258 |
| 6 | 383800 | 1 | 1518058.6705 | 3.7767 |
| 7 | 003540 | 1 | 1163741.6622 | 2.8952 |
| 8 | 003240 | 1 | 1083523.0334 | 2.6957 |
| 9 | 003830 | 1 | 976157.1307 | 2.4285 |
| 10 | 005960 | 1 | 919737.8063 | 2.2882 |

### 3.2 Sector Concentration
Sector fields were not found in `earnings_events.parquet`; skipped.

### 3.3 Market Cap Buckets
Local OHLCV has a `market_cap` column, but no positive usable values were found; skipped.

## Step 4. SUE Pipeline Recheck
### 4.1 Pipeline Sample Counts
| Stage | Count | Pass rate vs previous |
| --- | --- | --- |
| Raw earnings events | 22441 |  |
| Revenue YoY pair available | 17522 | 0.7808 |
| Net income YoY pair available | 15383 | 0.8779 |
| SUE calculable | 15323 | 0.9961 |
| Positive SUE daily top 20% | 1736 | 0.1133 |
| Price data matched | 1729 | 0.9960 |
| Tradable day after filters | 1664 | 0.9624 |
| Final entry: A baseline fold=0 completed trades | 199 | 0.1196 |
| Final entry: B variant fold=0 completed trades | 81 | 0.0487 |

### 4.2 SUE Distribution And Extreme Values
| min | p25 | median | p75 | p95 | p99 | max | SUE > 10 count | SUE > 20 count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0033 | 1.3995 | 2.2960 | 4.0714 | 9.2275 | 22.6976 | 285.6251 | 73 | 21 |

| Variant | total_pnl_krw | SUE>10 trades | SUE>10 pnl_krw | SUE>10 pnl share (%) | SUE>20 trades | SUE>20 pnl_krw | SUE>20 pnl share (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 20492623.6464 | 1 | 95010.7234 | 0.4636 | 0 | 0.0000 | 0.0000 |
| B | 11394752.7092 | 0 | 0.0000 | 0.0000 | 0 | 0.0000 | 0.0000 |

## Step 5. Final Summary
### 5.1 Facts Only
| Question | Fact |
| --- | --- |
| A baseline minimum fold PF / 0.9 gate | 0.8414; below the 0.9 gate |
| A baseline fold_3 top-month exclusion | Top positive month was 2025-05; PF after excluding it was 1.2372 |
| A/B fold PF and KOSPI return correlation | KOSPI index data was unavailable, so correlation was not computed |
| B Fold_3 PF after excluding 2025-05 | 1.7209 |
| A/B top 10 stock absolute PnL share | A 25.21%, B 38.20% |
| Extreme SUE PnL share | A SUE>10 0.46%, B SUE>10 0.00% |

### 5.2 User Decision Options
| Option | Condition only |
| --- | --- |
| Option I: go directly to PR-5 (low attention filter) | Appropriate only if A baseline fold-level behavior and concentration are judged acceptable |
| Option II: expand to Option C (investor flow) | Appropriate only if A baseline has signal but fold/month/stock concentration requires an additional orthogonal filter |
| Option III: retire Option B (Option E weekly bars or Option D image CNN) | Appropriate only if A and B both show structural dependence by fold/month/stock |
| Option IV: consider paid data expansion | Appropriate only if current OPENDART/price data is judged insufficient to resolve SUE signal quality |
