# Earnings Data Quality

Records: 22441
Date range: 2019-02-14 to 2026-03-31

## KOSPI Coverage
| reference_year | kospi_symbols_expected | covered_symbols | coverage | passes_70pct_gate |
| --- | --- | --- | --- | --- |
| 2026 | 2199 | 804 | 0.3656 | False |

## Annual Filing Counts
| year | covered_symbols | mean | median | min | max |
| --- | --- | --- | --- | --- | --- |
| 2019 | 747 | 3.9639 | 4.0000 | 1 | 4 |
| 2020 | 761 | 3.9409 | 4.0000 | 1 | 4 |
| 2021 | 780 | 3.9256 | 4.0000 | 1 | 4 |
| 2022 | 787 | 3.9390 | 4.0000 | 1 | 4 |
| 2023 | 797 | 3.9260 | 4.0000 | 1 | 4 |
| 2024 | 807 | 3.9281 | 4.0000 | 1 | 4 |
| 2025 | 815 | 3.9460 | 4.0000 | 1 | 4 |
| 2026 | 804 | 1.0000 | 1.0000 | 1 | 1 |

## Missing Rates By Receipt Year
| year | records | revenue_missing_rate | operating_income_missing_rate | net_income_missing_rate | total_assets_missing_rate | total_equity_missing_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | 2961 | 0.0892 | 0.0854 | 0.1354 | 0.0665 | 0.1006 |
| 2020 | 2999 | 0.0880 | 0.0867 | 0.1551 | 0.0647 | 0.0960 |
| 2021 | 3062 | 0.0879 | 0.0865 | 0.1561 | 0.0627 | 0.1058 |
| 2022 | 3100 | 0.0884 | 0.0887 | 0.1690 | 0.0635 | 0.1100 |
| 2023 | 3129 | 0.0837 | 0.0729 | 0.1585 | 0.0451 | 0.0802 |
| 2024 | 3170 | 0.0634 | 0.0432 | 0.1435 | 0.0013 | 0.0047 |
| 2025 | 3216 | 0.0650 | 0.0501 | 0.1704 | 0.0096 | 0.0103 |
| 2026 | 804 | 0.0622 | 0.0435 | 0.0560 | 0.0137 | 0.0100 |

## Receipt Time Distribution
| bucket | records | share |
| --- | --- | --- |
| before_15_30 | 0 | 0.0000 |
| after_or_at_15_30 | 22441 | 1.0000 |
| missing_time | 0 | 0.0000 |

## Leakage Precheck
| violation_type | count | examples |
| --- | --- | --- |
| data_source_after_receipt | 0 |  |
| fiscal_quarter_after_receipt | 0 |  |
| pr1_leakage | 0 |  |
