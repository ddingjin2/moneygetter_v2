# Literature-inspired factor exploration

Scope: KOSPI cached universe, long-only equal-weight, signal at t -> next open-to-open return, 30bp one-way cost charged on turnover, 5d/20d rebalance, top 10/15/20%. IS=2020-03-27..2024-12-31, OOS=2025-01-01..2026-04-17. This is exploratory and data-snooping-prone.

## Paper themes used
- Low-volatility / betting-against-beta anomaly: Frazzini & Pedersen BAB; Blitz & van Vliet volatility effect. Impl: low realized vol, low beta.
- Idiosyncratic volatility puzzle: Ang, Hodrick, Xing & Zhang; Bali & Cakici. Impl: low residual volatility after market beta.
- Lottery demand / MAX anomaly: Bali, Cakici & Whitelaw, Maxing out. Impl: avoid stocks with high max daily return over recent month.
- Residual momentum: Blitz, Huij & Martens. Impl: momentum after removing market exposure.
- Liquidity/illiquidity: Amihud-style illiquidity and turnover/liquidity literature. Impl: illiquidity and low-traded-value variants.

## Top by OOS Sharpe
| strategy | rebalance | q | sharpe_IS | sharpe_OOS | ann_return_OOS | ann_vol_OOS | max_dd_OOS | avg_turnover_OOS | min_sub_sharpe | OOS_monthly_spread | OOS_spread_win |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q_A4_LV_MAX | 20d | 0.1000 | 1.4217 | 3.2872 | 0.3416 | 0.1039 | -0.0775 | 0.0077 | -0.2085 | -0.0398 | 0.3750 |
| Q_A4_A3_MAX | 20d | 0.1000 | 1.4504 | 3.2794 | 0.3411 | 0.1040 | -0.0775 | 0.0078 | -0.2069 | -0.0399 | 0.3750 |
| A4_60 | 20d | 0.1000 | 1.4500 | 3.2647 | 0.3406 | 0.1043 | -0.0775 | 0.0077 | -0.1950 | -0.0399 | 0.3750 |
| Q_A4_A3_MAX | 5d | 0.1000 | 1.4247 | 3.1255 | 0.3032 | 0.0970 | -0.0697 | 0.0109 | -0.1462 | -0.0429 | 0.3750 |
| A4_60 | 5d | 0.1000 | 1.4373 | 3.1150 | 0.3033 | 0.0974 | -0.0698 | 0.0105 | -0.1276 | -0.0428 | 0.3750 |
| Q_A4_LV_MAX | 20d | 0.1500 | 1.3797 | 3.1046 | 0.3271 | 0.1054 | -0.0841 | 0.0076 | -0.0845 | -0.0410 | 0.3125 |
| Q_A4_LV_MAX | 5d | 0.1000 | 1.4390 | 3.0919 | 0.3006 | 0.0972 | -0.0697 | 0.0107 | -0.1415 | -0.0431 | 0.3750 |
| Q_A4_A3_MAX | 20d | 0.1500 | 1.4184 | 3.0744 | 0.3257 | 0.1059 | -0.0841 | 0.0076 | -0.0705 | -0.0411 | 0.3125 |
| A4_60 | 20d | 0.1500 | 1.4229 | 3.0057 | 0.3215 | 0.1070 | -0.0837 | 0.0074 | -0.0785 | -0.0415 | 0.3750 |
| Q_A4_A3_MAX | 5d | 0.1500 | 1.3428 | 2.9306 | 0.3028 | 0.1033 | -0.0849 | 0.0095 | -0.1199 | -0.0429 | 0.4375 |
| Q_A4_A3_MAX | 20d | 0.2000 | 1.2742 | 2.9198 | 0.3223 | 0.1104 | -0.0918 | 0.0070 | -0.2329 | -0.0415 | 0.3750 |
| Q_A4_LV_MAX | 5d | 0.1500 | 1.3520 | 2.9184 | 0.3021 | 0.1035 | -0.0849 | 0.0094 | -0.1227 | -0.0430 | 0.4375 |
| A4_60 | 5d | 0.1500 | 1.3584 | 2.9156 | 0.3051 | 0.1047 | -0.0850 | 0.0094 | -0.0923 | -0.0428 | 0.4375 |
| Q_A4_LV_MAX | 5d | 0.2000 | 1.3009 | 2.9082 | 0.3137 | 0.1079 | -0.0895 | 0.0085 | -0.1808 | -0.0422 | 0.4375 |
| Q_A4_LV_MAX | 20d | 0.2000 | 1.2222 | 2.9055 | 0.3206 | 0.1103 | -0.0919 | 0.0070 | -0.2499 | -0.0416 | 0.3750 |
| Q_A4_A3_MAX | 5d | 0.2000 | 1.3043 | 2.8987 | 0.3129 | 0.1079 | -0.0895 | 0.0088 | -0.1892 | -0.0422 | 0.4375 |
| A4_60 | 20d | 0.2000 | 1.2639 | 2.8957 | 0.3209 | 0.1108 | -0.0923 | 0.0069 | -0.2239 | -0.0416 | 0.3750 |
| ILLIQ_60 | 5d | 0.1500 | 1.2348 | 2.8205 | 0.3919 | 0.1389 | -0.0986 | 0.0062 | 0.0055 | -0.0362 | 0.3125 |
| ILLIQ_60 | 20d | 0.1500 | 1.2652 | 2.8196 | 0.3904 | 0.1385 | -0.0998 | 0.0043 | 0.1192 | -0.0363 | 0.3125 |
| A4_60 | 5d | 0.2000 | 1.2932 | 2.8180 | 0.3069 | 0.1089 | -0.0907 | 0.0086 | -0.2130 | -0.0427 | 0.4375 |
| ILLIQ_60 | 20d | 0.1000 | 1.3771 | 2.7552 | 0.4412 | 0.1602 | -0.1037 | 0.0053 | 0.2096 | NA | NA |
| ILLIQ_60 | 5d | 0.1000 | 1.3644 | 2.7279 | 0.4355 | 0.1596 | -0.1032 | 0.0070 | 0.1954 | NA | NA |
| LV_126 | 20d | 0.2000 | 0.8454 | 2.6860 | 0.2636 | 0.0981 | -0.0853 | 0.0064 | -0.6722 | NA | NA |
| ILLIQ_60 | 20d | 0.2000 | 1.2020 | 2.6715 | 0.3555 | 0.1331 | -0.1045 | 0.0039 | -0.0415 | NA | NA |
| ILLIQ_60 | 5d | 0.2000 | 1.1869 | 2.6477 | 0.3477 | 0.1313 | -0.1053 | 0.0051 | -0.0631 | NA | NA |
| MAXRET_21 | 20d | 0.1500 | 0.5638 | 2.5427 | 0.2230 | 0.0877 | -0.0653 | 0.0268 | -1.1752 | NA | NA |
| MAXRET_21 | 20d | 0.2000 | 0.6451 | 2.5354 | 0.2369 | 0.0934 | -0.0703 | 0.0249 | -1.0320 | NA | NA |
| LV_126 | 20d | 0.1000 | 0.7717 | 2.5170 | 0.2131 | 0.0847 | -0.0816 | 0.0076 | -0.8041 | NA | NA |
| LV_126 | 5d | 0.2000 | 0.8769 | 2.4933 | 0.2374 | 0.0952 | -0.0856 | 0.0084 | -0.7031 | NA | NA |
| LV_126 | 20d | 0.1500 | 0.9542 | 2.4514 | 0.2251 | 0.0918 | -0.0924 | 0.0070 | -0.6735 | NA | NA |

## Baselines and directly comparable new composites
| strategy | rebalance | q | sharpe_IS | sharpe_OOS | ann_return_OOS | ann_vol_OOS | max_dd_OOS | avg_turnover_OOS | min_sub_sharpe | OOS_monthly_spread | OOS_spread_win |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A4_60 | 20d | 0.1000 | 1.4500 | 3.2647 | 0.3406 | 0.1043 | -0.0775 | 0.0077 | -0.1950 | -0.0399 | 0.3750 |
| A4_60 | 20d | 0.1500 | 1.4229 | 3.0057 | 0.3215 | 0.1070 | -0.0837 | 0.0074 | -0.0785 | -0.0415 | 0.3750 |
| A4_60 | 20d | 0.2000 | 1.2639 | 2.8957 | 0.3209 | 0.1108 | -0.0923 | 0.0069 | -0.2239 | -0.0416 | 0.3750 |
| A4_60 | 5d | 0.1000 | 1.4373 | 3.1150 | 0.3033 | 0.0974 | -0.0698 | 0.0105 | -0.1276 | -0.0428 | 0.3750 |
| A4_60 | 5d | 0.1500 | 1.3584 | 2.9156 | 0.3051 | 0.1047 | -0.0850 | 0.0094 | -0.0923 | -0.0428 | 0.4375 |
| A4_60 | 5d | 0.2000 | 1.2932 | 2.8180 | 0.3069 | 0.1089 | -0.0907 | 0.0086 | -0.2130 | -0.0427 | 0.4375 |
| Q_A4_A3_MAX | 20d | 0.1000 | 1.4504 | 3.2794 | 0.3411 | 0.1040 | -0.0775 | 0.0078 | -0.2069 | -0.0399 | 0.3750 |
| Q_A4_A3_MAX | 20d | 0.1500 | 1.4184 | 3.0744 | 0.3257 | 0.1059 | -0.0841 | 0.0076 | -0.0705 | -0.0411 | 0.3125 |
| Q_A4_A3_MAX | 20d | 0.2000 | 1.2742 | 2.9198 | 0.3223 | 0.1104 | -0.0918 | 0.0070 | -0.2329 | -0.0415 | 0.3750 |
| Q_A4_A3_MAX | 5d | 0.1000 | 1.4247 | 3.1255 | 0.3032 | 0.0970 | -0.0697 | 0.0109 | -0.1462 | -0.0429 | 0.3750 |
| Q_A4_A3_MAX | 5d | 0.1500 | 1.3428 | 2.9306 | 0.3028 | 0.1033 | -0.0849 | 0.0095 | -0.1199 | -0.0429 | 0.4375 |
| Q_A4_A3_MAX | 5d | 0.2000 | 1.3043 | 2.8987 | 0.3129 | 0.1079 | -0.0895 | 0.0088 | -0.1892 | -0.0422 | 0.4375 |

## Robust rows: IS>1, OOS>3, min_sub>-0.3
| strategy | rebalance | q | sharpe_IS | sharpe_OOS | ann_return_OOS | ann_vol_OOS | max_dd_OOS | avg_turnover_OOS | min_sub_sharpe | OOS_monthly_spread | OOS_spread_win |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q_A4_LV_MAX | 20d | 0.1000 | 1.4217 | 3.2872 | 0.3416 | 0.1039 | -0.0775 | 0.0077 | -0.2085 | -0.0398 | 0.3750 |
| Q_A4_A3_MAX | 20d | 0.1000 | 1.4504 | 3.2794 | 0.3411 | 0.1040 | -0.0775 | 0.0078 | -0.2069 | -0.0399 | 0.3750 |
| A4_60 | 20d | 0.1000 | 1.4500 | 3.2647 | 0.3406 | 0.1043 | -0.0775 | 0.0077 | -0.1950 | -0.0399 | 0.3750 |
| Q_A4_A3_MAX | 5d | 0.1000 | 1.4247 | 3.1255 | 0.3032 | 0.0970 | -0.0697 | 0.0109 | -0.1462 | -0.0429 | 0.3750 |
| A4_60 | 5d | 0.1000 | 1.4373 | 3.1150 | 0.3033 | 0.0974 | -0.0698 | 0.0105 | -0.1276 | -0.0428 | 0.3750 |
| Q_A4_LV_MAX | 20d | 0.1500 | 1.3797 | 3.1046 | 0.3271 | 0.1054 | -0.0841 | 0.0076 | -0.0845 | -0.0410 | 0.3125 |
| Q_A4_LV_MAX | 5d | 0.1000 | 1.4390 | 3.0919 | 0.3006 | 0.0972 | -0.0697 | 0.0107 | -0.1415 | -0.0431 | 0.3750 |
| Q_A4_A3_MAX | 20d | 0.1500 | 1.4184 | 3.0744 | 0.3257 | 0.1059 | -0.0841 | 0.0076 | -0.0705 | -0.0411 | 0.3125 |
| A4_60 | 20d | 0.1500 | 1.4229 | 3.0057 | 0.3215 | 0.1070 | -0.0837 | 0.0074 | -0.0785 | -0.0415 | 0.3750 |

## Benchmark and OOS excess check
KOSPI OOS was extremely strong, so absolute Sharpe is not enough. OOS strategy returns still underperformed KOSPI on cumulative/excess basis.

| name | ann_return | ann_vol | sharpe | max_dd | cum_return |
| --- | --- | --- | --- | --- | --- |
| KOSPI_IS | 0.0925 | 0.1823 | 0.5075 | -0.3479 | 0.4230 |
| KOSPI_OOS | 0.8138 | 0.3215 | 2.5314 | -0.1989 | 1.5805 |

| strategy | rebalance | q | OOS_cum_strategy | OOS_cum_kospi | OOS_excess_ann | OOS_IR | OOS_excess_mdd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q_A4_LV_MAX | 20d | 0.1000 | 0.5200 | 1.5805 | -0.4721 | -1.6335 | -0.5107 |
| Q_A4_A3_MAX | 20d | 0.1000 | 0.5189 | 1.5805 | -0.4727 | -1.6358 | -0.5113 |
| A4_60 | 20d | 0.1000 | 0.5179 | 1.5805 | -0.4732 | -1.6387 | -0.5106 |
| ILLIQ_60 | 20d | 0.1000 | 0.7054 | 1.5805 | -0.3725 | -1.2879 | -0.5040 |

## Interpretation
- Best new row by OOS Sharpe is Q_A4_LV_MAX 20d top10: OOS Sharpe 3.2872, OOS ann_return 34.16%, MDD -7.75%. It beats A4_60 20d top10 only marginally: +0.0225 Sharpe and +0.10%p annual return.
- Q_A4_A3_MAX 20d top10 is essentially tied with A4_60 20d top10: OOS Sharpe 3.2794 vs 3.2647, same drawdown.
- Pure literature factors (low vol, MAX, illiquidity, residual momentum) did not clearly dominate A4. Illiquidity has high OOS return but much higher vol/drawdown; low-vol/MAX alone have weak IS or bad subperiods.
- Therefore the practical candidate remains A4 20d top10; Q_A4_LV_MAX can be watched as a tiny literature-confirmed tweak, but the improvement is too small to call a new alpha.
- Existing A3+A4 from prior run remains the lower-vol/lower-drawdown comfort candidate, but it sacrifices return and had weaker subperiod robustness.

## Caveats
- Universe is cached/alive-biased unless the upstream cache already includes delistings.
- No true market-cap weighting/cap constraints here; A4 is traded-value/liquidity-like, not actual size.
- 30bp one-way cost is a simple model; market impact, limits, halts, borrow, and exact Korean-market execution constraints are not fully modeled.
- OOS underperformed KOSPI in the 2025 bull regime; this is a defensive/low-liquidity absolute-return candidate, not confirmed benchmark-relative alpha.

Artifacts:
- data/cache/lit_factor_explore/metrics.parquet
- data/cache/lit_factor_explore/summary_wide.parquet
- data/cache/lit_factor_explore/pnl_daily.parquet
- data/cache/lit_factor_explore/monthly_spread_summary.parquet
