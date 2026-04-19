# PR-4.7 Regime Reevaluation

Diagnostic-only report. Inputs are PR-4.6 trade-level ledgers and cached KOSPI daily data.

## Step 1. KOSPI Daily Data
- Cache path: `v2\data\cache\kospi_daily.parquet`
- Loader preference: pykrx/KRX first; Naver Finance fallback if pykrx/KRX returns empty or fails.
- Rows: 1545
- Date range: 2020-01-02 ~ 2026-04-17
- Missing values by column: {'date': 0, 'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0, 'returns': 1}
- Calendar gaps greater than 1 day: 353; max calendar gap: 8 days. Exchange holiday validation is skipped.
- 2025-05-01 to 2026-04-17 KOSPI return: 141.89%

## Step 2. Monthly Market Regimes
### 2.1 Monthly KOSPI Returns
| Month | Start Close | End Close | Return % | Vol % | MDD % | Regime |
| --- | --- | --- | --- | --- | --- | --- |
| 2020-01 | 2175.17 | 2119.01 | -2.58 | 5.40 | -6.54 | Bear Normal |
| 2020-02 | 2118.88 | 1987.01 | -6.22 | 7.05 | -11.44 | Bear Extreme |
| 2020-03 | 2002.51 | 1754.64 | -12.38 | 18.84 | -30.10 | Bear Extreme |
| 2020-04 | 1685.46 | 1947.56 | 15.55 | 8.18 | -1.88 | Bull Extreme |
| 2020-05 | 1895.37 | 2029.60 | 7.08 | 5.24 | -1.41 | Bull Extreme |
| 2020-06 | 2065.08 | 2108.33 | 2.09 | 8.88 | -7.51 | Bull Normal |
| 2020-07 | 2106.70 | 2249.37 | 6.77 | 3.99 | -1.72 | Bull Extreme |
| 2020-08 | 2251.04 | 2326.17 | 3.34 | 6.37 | -6.70 | Bull Normal |
| 2020-09 | 2349.55 | 2327.89 | -0.92 | 5.19 | -6.99 | Bear Normal |
| 2020-10 | 2358.00 | 2267.15 | -3.85 | 3.96 | -5.68 | Bear Normal |
| 2020-11 | 2300.16 | 2591.34 | 12.66 | 4.39 | -1.60 | Bull Extreme |
| 2020-12 | 2634.25 | 2873.47 | 9.08 | 4.56 | -1.62 | Bull Extreme |
| 2021-01 | 2944.45 | 2976.21 | 1.08 | 8.64 | -7.25 | Bull Normal |
| 2021-02 | 3056.53 | 3012.95 | -1.43 | 7.42 | -5.32 | Bear Normal |
| 2021-03 | 3043.87 | 3061.42 | 0.58 | 4.10 | -4.05 | Bull Normal |
| 2021-04 | 3087.40 | 3147.86 | 1.96 | 2.87 | -2.26 | Bull Normal |
| 2021-05 | 3127.20 | 3203.92 | 2.45 | 4.02 | -3.91 | Bull Normal |
| 2021-06 | 3221.87 | 3296.68 | 2.32 | 2.16 | -1.16 | Bull Normal |
| 2021-07 | 3282.06 | 3202.32 | -2.43 | 3.01 | -3.11 | Bear Normal |
| 2021-08 | 3223.04 | 3199.27 | -0.74 | 4.24 | -6.70 | Bear Normal |
| 2021-09 | 3207.02 | 3068.82 | -4.31 | 3.02 | -4.58 | Bear Normal |
| 2021-10 | 3019.18 | 2970.68 | -1.61 | 4.98 | -3.67 | Bear Normal |
| 2021-11 | 2978.94 | 2839.01 | -4.70 | 4.44 | -5.79 | Bear Normal |
| 2021-12 | 2899.72 | 2977.65 | 2.69 | 3.77 | -2.20 | Bull Normal |
| 2022-01 | 2988.77 | 2663.34 | -10.89 | 5.81 | -12.54 | Bear Extreme |
| 2022-02 | 2707.82 | 2699.18 | -0.32 | 5.40 | -4.44 | Bear Normal |
| 2022-03 | 2703.52 | 2757.65 | 2.00 | 4.86 | -4.57 | Bull Normal |
| 2022-04 | 2739.85 | 2695.05 | -1.64 | 4.13 | -4.35 | Bear Normal |
| 2022-05 | 2687.45 | 2685.90 | -0.06 | 4.71 | -5.11 | Bear Normal |
| 2022-06 | 2658.99 | 2332.64 | -12.27 | 6.52 | -13.34 | Bear Extreme |
| 2022-07 | 2305.42 | 2451.50 | 6.34 | 4.50 | -2.13 | Bull Extreme |
| 2022-08 | 2452.25 | 2472.05 | 0.81 | 4.11 | -4.21 | Bull Normal |
| 2022-09 | 2415.61 | 2155.49 | -10.77 | 5.68 | -12.00 | Bear Extreme |
| 2022-10 | 2209.38 | 2293.61 | 3.81 | 5.46 | -3.35 | Bull Normal |
| 2022-11 | 2335.22 | 2472.53 | 5.88 | 5.07 | -3.14 | Bull Extreme |
| 2022-12 | 2479.84 | 2236.40 | -9.82 | 4.52 | -9.82 | Bear Extreme |
| 2023-01 | 2225.67 | 2425.08 | 8.96 | 4.46 | -2.37 | Bull Extreme |
| 2023-02 | 2449.80 | 2412.85 | -1.51 | 4.57 | -3.26 | Bear Normal |
| 2023-03 | 2427.85 | 2476.86 | 2.02 | 4.21 | -4.64 | Bull Normal |
| 2023-04 | 2472.34 | 2501.53 | 1.18 | 3.39 | -3.54 | Bull Normal |
| 2023-05 | 2524.39 | 2577.12 | 2.09 | 2.56 | -1.94 | Bull Normal |
| 2023-06 | 2569.17 | 2564.28 | -0.19 | 2.86 | -3.45 | Bear Normal |
| 2023-07 | 2602.47 | 2632.58 | 1.16 | 3.87 | -3.14 | Bull Normal |
| 2023-08 | 2667.07 | 2556.27 | -4.15 | 3.83 | -6.10 | Bear Normal |
| 2023-09 | 2563.71 | 2465.07 | -3.85 | 3.60 | -5.32 | Bear Normal |
| 2023-10 | 2405.69 | 2277.99 | -5.31 | 5.68 | -8.14 | Bear Extreme |
| 2023-11 | 2301.56 | 2535.29 | 10.16 | 6.85 | -3.94 | Bull Extreme |
| 2023-12 | 2505.01 | 2655.28 | 6.00 | 3.64 | -0.97 | Bull Extreme |
| 2024-01 | 2669.81 | 2497.09 | -6.47 | 3.99 | -8.76 | Bear Extreme |
| 2024-02 | 2542.46 | 2642.36 | 3.93 | 4.93 | -2.06 | Bull Normal |
| 2024-03 | 2674.27 | 2746.63 | 2.71 | 4.49 | -2.30 | Bull Normal |
| 2024-04 | 2747.86 | 2692.06 | -2.03 | 5.58 | -6.14 | Bear Normal |
| 2024-05 | 2683.65 | 2636.52 | -1.76 | 4.31 | -4.27 | Bear Normal |
| 2024-06 | 2682.52 | 2797.82 | 4.30 | 3.50 | -1.53 | Bull Normal |
| 2024-07 | 2804.31 | 2770.69 | -1.20 | 4.01 | -6.25 | Bear Normal |
| 2024-08 | 2777.68 | 2674.31 | -3.72 | 10.72 | -12.10 | Bear Normal |
| 2024-09 | 2681.00 | 2593.27 | -3.27 | 6.34 | -6.25 | Bear Normal |
| 2024-10 | 2561.69 | 2556.15 | -0.22 | 3.92 | -2.94 | Bear Normal |
| 2024-11 | 2542.36 | 2455.91 | -3.40 | 5.23 | -6.65 | Bear Normal |
| 2024-12 | 2454.48 | 2399.49 | -2.24 | 6.17 | -5.58 | Bear Normal |
| 2025-01 | 2398.94 | 2517.37 | 4.94 | 4.03 | -1.28 | Bull Normal |
| 2025-02 | 2453.95 | 2532.78 | 3.21 | 5.60 | -5.19 | Bull Normal |
| 2025-03 | 2528.92 | 2481.12 | -1.89 | 5.19 | -6.16 | Bear Normal |
| 2025-04 | 2521.39 | 2556.61 | 1.40 | 9.26 | -9.03 | Bull Normal |
| 2025-05 | 2559.79 | 2697.67 | 5.39 | 4.12 | -1.84 | Bull Extreme |
| 2025-06 | 2698.97 | 3071.70 | 13.81 | 4.93 | -1.68 | Bull Extreme |
| 2025-07 | 3089.65 | 3245.44 | 5.04 | 3.88 | -1.99 | Bull Extreme |
| 2025-08 | 3119.41 | 3186.01 | 2.14 | 5.42 | -3.02 | Bull Normal |
| 2025-09 | 3142.93 | 3424.60 | 8.96 | 4.59 | -2.87 | Bull Extreme |
| 2025-10 | 3455.83 | 4107.50 | 18.86 | 5.92 | -1.35 | Bull Extreme |
| 2025-11 | 4221.87 | 3926.59 | -6.99 | 9.89 | -8.90 | Bear Extreme |
| 2025-12 | 3920.37 | 4214.17 | 7.49 | 5.70 | -4.14 | Bull Extreme |
| 2026-01 | 4309.63 | 5224.36 | 21.23 | 4.44 | -0.81 | Bull Extreme |
| 2026-02 | 4949.67 | 6244.13 | 26.15 | 13.11 | -5.25 | Bull Extreme |
| 2026-03 | 5791.91 | 5052.46 | -12.77 | 21.68 | -14.73 | Bear Extreme |
| 2026-04 | 5478.70 | 6191.92 | 13.02 | 14.83 | -4.47 | Bull Extreme |

### 2.2 Regime Distribution
| Regime | Month Count |
| --- | --- |
| Bear Extreme | 10 |
| Bear Normal | 25 |
| Bull Extreme | 19 |
| Bull Normal | 22 |

### 2.3 Abnormal Period Check
| Metric | Value |
| --- | --- |
| 2025-05 to 2026-04 Bull Extreme months | 9 |
| 2025-05 to 2026-04 KOSPI return % | 141.89 |
| 2020-03 to 2025-04 Bull Extreme months | 10 |
| Prior period annualized Bull Extreme count | 1.94 |
| Recent / prior annualized ratio | 4.65 |
| Criterion result | abnormal by 3x Bull Extreme criterion |

## Step 3. Fold-Level KOSPI Mapping
### 3.1 Fold Periods And KOSPI Performance
| Fold | Test Start | Test End | KOSPI Return % | KOSPI Vol % | Bull Extreme Months |
| --- | --- | --- | --- | --- | --- |
| 1 | 2023-03-27 | 2024-03-26 | 14.44 | 15.45 | 2 |
| 2 | 2024-03-27 | 2025-03-26 | -4.04 | 19.56 | 0 |
| 3 | 2025-03-27 | 2026-03-26 | 109.44 | 32.80 | 8 |

### 3.2 Strategy Vs KOSPI
| Variant | Fold | Strategy Net PF | KOSPI Return % | Strategy Raw Return Avg % | KOSPI Daily Return Avg % |
| --- | --- | --- | --- | --- | --- |
| A | 1 | 1.3883 | 14.44 | 1.77 | 0.0586 |
| A | 2 | 0.8414 | -4.04 | -0.14 | -0.0097 |
| A | 3 | 3.1521 | 109.44 | 6.91 | 0.3205 |
| B | 1 | 0.2966 | 14.44 | -4.05 | 0.0586 |
| B | 2 | 0.7586 | -4.04 | -0.51 | -0.0097 |
| B | 3 | 6.5985 | 109.44 | 10.98 | 0.3205 |

## Step 4. Regime-Conditional Recheck
### 4.1 Fold 1/2 And Bull Extreme Exclusion
| Variant | Scope | Trades | PF | Win Rate % | Avg Win % | Avg Loss % |
| --- | --- | --- | --- | --- | --- | --- |
| A | Fold 1/2 pooled | 140 | 1.0024 | 47.14 | 9.31 | -8.17 |
| A | Full WF excluding Bull Extreme entry months | 162 | 1.1407 | 45.68 | 10.15 | -7.47 |
| A | Bull Extreme entry months only | 43 | 3.6510 | 74.42 | 13.23 | -9.70 |
| B | Fold 1/2 pooled | 41 | 0.4804 | 24.39 | 11.70 | -7.86 |
| B | Full WF excluding Bull Extreme entry months | 52 | 0.7323 | 30.77 | 10.88 | -6.85 |
| B | Bull Extreme entry months only | 23 | 6.8333 | 78.26 | 19.17 | -10.42 |

A Fold 1/2 criterion bucket: normal-regime edge weak

## Step 5. Alpha Decomposition
Scatter plot: `v2\reports\pr4_7_a_kospi_scatter.png`

| Variant | N | Alpha | Beta | R2 |
| --- | --- | --- | --- | --- |
| A | 205 | 0.0103 | 0.9216 | 0.0845 |

## Step 6. Final Summary
### 6.1 Facts Only
| Question | Fact |
| --- | --- |
| 2025-05 to 2026-04 abnormal rise status | abnormal by 3x Bull Extreme criterion; KOSPI return 141.89%, Bull Extreme months 9 |
| Fold_3 overlap with abnormal window | 90.41% calendar-day overlap |
| A Fold_1/2 pooled PF | 1.0024 |
| A full WF excluding Bull Extreme entry months PF | 1.1407 |
| B Fold_1/2 pooled PF / Bull Extreme excluded PF | 0.4804 / 0.7323 |
| A alpha, beta, R2 | 0.0103, 0.9216, 0.0845 |

### 6.2 User Decision Scenarios
| Scenario | Condition |
| --- | --- |
| Scenario A | A Fold_1/2 pooled PF >= 1.3 and Bull Extreme excluded PF >= 1.3 |
| Scenario B | At least one of the two PF values is between 1.0 and 1.3, and neither is below 1.0 |
| Scenario C | At least one of the two PF values is below 1.0 |
| Scenario D | Data limitation prevents classification |
| Current result | Scenario B: A Fold_1/2 PF 1.0024, A Bull Extreme excluded PF 1.1407 |
