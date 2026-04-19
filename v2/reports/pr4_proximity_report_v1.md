# PR-4 52-Week High Proximity Report

Thresholds are fixed before evaluation: near-high proximity >= 0.95, far-from-high proximity <= 0.60.
No OPENDART calls are made; this report reuses the existing earnings_events.parquet.

## Section 1. Variant Comparison Matrix
| Variant | Train PF | Test PF | WF Median PF | Common PF | MDD | Trades | WF Trades | Common Trades | Leakage Violations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. SUE Only | 1.7470 | 1.2241 | 1.3883 | 1.5033 | -0.1737 | 199 | 205 | 139 | 0 |
| B. SUE + Near High | 1.3510 | 2.4353 | 0.7586 | 3.0427 | -0.0670 | 81 | 75 | 53 | 0 |
| C. SUE + Far from High | 1.0981 | 0.9499 | 1.0972 | 1.3504 | -0.1723 | 139 | 147 | 92 | 0 |
| D. Proximity Only | 1.3323 | 1.1329 | 0.7143 | 1.9757 | -0.2168 | 184 | 185 | 124 | 0 |

## Section 2. Goh & Jeon Directionality Test
| Relation | Left WF Median PF | Right WF Median PF | Passes |
| --- | --- | --- | --- |
| B > A | 0.7586 | 1.3883 | False |
| B > C | 0.7586 | 1.0972 | False |
| B > D | 0.7586 | 0.7143 | True |

Directionality reproduced: False

## Section 3. Fold Regime Analysis
KOSPI context uses an equal-weight KOSPI-stock proxy from local OHLCV because the dataset has no official index row.
| variant | fold_id | test_period | kospi_proxy_return | kospi_proxy_mdd | kospi_proxy_volatility | strategy_pf | strategy_trades | strategy_total_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. SUE Only | fold_1 | 2023-03-27 ~ 2024-03-26 | 0.1023 | -0.0903 | 0.0908 | 1.3883 | 67 | 0.0356 |
| A. SUE Only | fold_2 | 2024-03-27 ~ 2025-03-26 | 0.0290 | -0.0994 | 0.1181 | 0.8414 | 73 | -0.0348 |
| A. SUE Only | fold_3 | 2025-03-27 ~ 2026-03-26 | 0.3702 | -0.0901 | 0.1560 | 3.1521 | 65 | 0.2042 |
| B. SUE + Near High | fold_1 | 2023-03-27 ~ 2024-03-26 | 0.1023 | -0.0903 | 0.0908 | 0.2966 | 22 | -0.0509 |
| B. SUE + Near High | fold_2 | 2024-03-27 ~ 2025-03-26 | 0.0290 | -0.0994 | 0.1181 | 0.7586 | 19 | -0.0115 |
| B. SUE + Near High | fold_3 | 2025-03-27 ~ 2026-03-26 | 0.3702 | -0.0901 | 0.1560 | 6.5985 | 34 | 0.1764 |
| C. SUE + Far from High | fold_1 | 2023-03-27 ~ 2024-03-26 | 0.1023 | -0.0903 | 0.0908 | 1.0972 | 55 | 0.0094 |
| C. SUE + Far from High | fold_2 | 2024-03-27 ~ 2025-03-26 | 0.0290 | -0.0994 | 0.1181 | 1.0035 | 65 | 0.0006 |
| C. SUE + Far from High | fold_3 | 2025-03-27 ~ 2026-03-26 | 0.3702 | -0.0901 | 0.1560 | 3.3019 | 27 | 0.0719 |
| D. Proximity Only | fold_1 | 2023-03-27 ~ 2024-03-26 | 0.1023 | -0.0903 | 0.0908 | 0.4272 | 61 | -0.0776 |
| D. Proximity Only | fold_2 | 2024-03-27 ~ 2025-03-26 | 0.0290 | -0.0994 | 0.1181 | 0.7143 | 62 | -0.0259 |
| D. Proximity Only | fold_3 | 2025-03-27 ~ 2026-03-26 | 0.3702 | -0.0901 | 0.1560 | 4.2262 | 62 | 0.1853 |

Strategy B fold distribution:
| fold_id | start | end | trades | PF | total_return |
| --- | --- | --- | --- | --- | --- |
| fold_1 | 2023-03-27 | 2024-03-26 | 22 | 0.2966 | -0.0509 |
| fold_2 | 2024-03-27 | 2025-03-26 | 19 | 0.7586 | -0.0115 |
| fold_3 | 2025-03-27 | 2026-03-26 | 34 | 6.5985 | 0.1764 |

## Section 4. PnL Concentration
Strategy B uses the fixed Train/Test test ledger at 70bps.
| frequency | top_3_periods_share | top_period_share | positive_periods_ratio | period_pnl_std |
| --- | --- | --- | --- | --- |
| monthly | 1.2060 | 0.8768 | 0.6364 | 4873200.6841 |
| quarterly | 1.2041 | 0.8749 | 0.6667 | 5358211.0302 |

Monthly PnL:
| period | pnl |
| --- | --- |
| 2024-03 | 340032.9565 |
| 2024-05 | 44232.2417 |
| 2024-07 | 110742.2070 |
| 2024-08 | -1902123.4171 |
| 2024-11 | 588662.3581 |
| 2025-03 | -1348311.3281 |
| 2025-04 | -33770.6320 |
| 2025-05 | 15517522.6673 |
| 2025-08 | 3219873.7941 |
| 2025-11 | -1444943.3252 |
| 2026-03 | 2606671.2794 |

Quarterly PnL:
| period | pnl |
| --- | --- |
| 2024Q1 | 340032.9565 |
| 2024Q2 | 44232.2417 |
| 2024Q3 | -1791381.2101 |
| 2024Q4 | 588662.3581 |
| 2025Q1 | -1348311.3281 |
| 2025Q2 | 15483752.0353 |
| 2025Q3 | 3219873.7941 |
| 2025Q4 | -1444943.3252 |
| 2026Q1 | 2606671.2794 |

## Section 5. Commercialization Gates
| Gate | Value | Threshold | Passes |
| --- | --- | --- | --- |
| WF median PF >= 1.3 | 0.7586 | >= 1.3 | False |
| Common trade PF >= 1.0 | 3.0427 | >= 1.0 | True |
| MDD >= -20% | -0.0670 | >= -0.20 | True |
| Minimum fold PF >= 0.9 | 0.2966 | >= 0.9 | False |
| Top 3 months share < 150% | 1.2060 | < 1.5 | True |

All commercial gates passed: False

Leakage checks by variant:
| Variant | trade_ledger_violations |
| --- | --- |
| A. SUE Only | 0 |
| B. SUE + Near High | 0 |
| C. SUE + Far from High | 0 |
| D. Proximity Only | 0 |

Earnings dataset point-in-time checks:
| violation_type | count | examples |
| --- | --- | --- |
| data_source_after_receipt | 0 |  |
| fiscal_quarter_after_receipt | 0 |  |
| pr1_leakage | 0 |  |

## Section 6. Final Verdict
FAIL: Goh & Jeon directionality was not reproduced. Re-evaluate Option B before PR-5.

## Section 7. Uncertainty And Constraints
- Goh & Jeon reported long-short monthly returns on 2004-2015 data; this is a 2020-2026 long-only test after 70bps round-trip costs.
- The local OHLCV file has all-zero market_cap and no official KOSPI index row, so regime context uses an equal-weight KOSPI-stock proxy.
- The 2020-2026 period includes unusual Korean-market regimes, including the 2023-2024 short-sale ban period.
- The proximity threshold is fixed at 0.95. No threshold sensitivity search was run in this PR.
- Directionality, not numeric equality with the paper, is the reproduction target.
