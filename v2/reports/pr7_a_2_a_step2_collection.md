# PR-7.A.2.a Step 2 Investor Flow Collection

## Summary
- Attempted stocks in log: `808` / universe `808`
- Success: `808`
- Partial: `0`
- Failed: `0`
- Total rows: `1157935`
- Last run elapsed: `6h 13m`
- Last run attempted: `408`

## Coverage Distribution
| bucket | count |
| --- | --- |
| 00-10% | 0 |
| 10-20% | 0 |
| 20-30% | 0 |
| 30-40% | 0 |
| 40-50% | 0 |
| 50-60% | 0 |
| 60-70% | 0 |
| 70-80% | 0 |
| 80-90% | 0 |
| 90-100% | 0 |
| 100% | 808 |

## Coverage Threshold Counts
| range | count |
| --- | --- |
| 95%+ | 808 |
| 80-95% | 0 |
| 50-80% | 0 |
| <50% | 0 |

## Yearly Availability
| year | stock_count | avg_coverage_ratio |
| --- | --- | --- |
| 2020 | 752 | 100.0% |
| 2021 | 771 | 100.0% |
| 2022 | 776 | 100.0% |
| 2023 | 789 | 100.0% |
| 2024 | 800 | 100.0% |
| 2025 | 807 | 100.0% |
| 2026 | 808 | 100.0% |

## Failed / Partial Pattern Analysis
### Code-size bucket fallback
(none)

### Listing bucket
(none)

### Sector top 5
(none)

### Delisted stocks
| code | name | delisted_date | status | rows_collected | coverage_ratio |
| --- | --- | --- | --- | --- | --- |
| 008110 | 대동전자 | 2026-03-17 00:00:00 | ok | 1463 | 1.0 |
| 138490 | 코오롱ENP | 2026-03-17 00:00:00 | ok | 1463 | 1.0 |

## Mini-pilot 30-stock Recollection Comparison
- Exact date/value match: `0/30`
- Matched rows: `0`
| code | mini_rows | full_rows | date_match | value_match | pattern |
| --- | --- | --- | --- | --- | --- |
| 000140 | 486 | 1486 | False | False | full_more_dates |
| 000220 | 486 | 1486 | False | False | full_more_dates |
| 000270 | 486 | 1486 | False | False | full_more_dates |
| 000390 | 486 | 1486 | False | False | full_more_dates |
| 000660 | 486 | 1486 | False | False | full_more_dates |
| 001340 | 486 | 1486 | False | False | full_more_dates |
| 001940 | 486 | 1486 | False | False | full_more_dates |
| 002150 | 486 | 1486 | False | False | full_more_dates |
| 003480 | 486 | 1486 | False | False | full_more_dates |
| 004060 | 486 | 1486 | False | False | full_more_dates |
| 004970 | 486 | 1486 | False | False | full_more_dates |
| 005380 | 486 | 1486 | False | False | full_more_dates |
| 005930 | 486 | 1486 | False | False | full_more_dates |
| 010040 | 486 | 1486 | False | False | full_more_dates |
| 012450 | 486 | 1486 | False | False | full_more_dates |
| 013570 | 486 | 1486 | False | False | full_more_dates |
| 015360 | 486 | 1486 | False | False | full_more_dates |
| 015590 | 486 | 1486 | False | False | full_more_dates |
| 034020 | 486 | 1486 | False | False | full_more_dates |
| 037710 | 486 | 1486 | False | False | full_more_dates |
| 063160 | 486 | 1486 | False | False | full_more_dates |
| 090350 | 486 | 1486 | False | False | full_more_dates |
| 100250 | 486 | 1486 | False | False | full_more_dates |
| 108670 | 486 | 1486 | False | False | full_more_dates |
| 109070 | 486 | 1486 | False | False | full_more_dates |
| 123690 | 486 | 1486 | False | False | full_more_dates |
| 207940 | 486 | 1486 | False | False | full_more_dates |
| 329180 | 486 | 1119 | False | False | full_more_dates |
| 373220 | 486 | 1031 | False | False | full_more_dates |
| 402340 | 486 | 1073 | False | False | full_more_dates |

## Sample Validation
| bucket | code | name | date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- | --- | --- | --- |
| large | 000020 | 동화약품 | 2020-03-27 | 17 | -27414 |
| large | 000020 | 동화약품 | 2020-03-30 | 27076 | -6954 |
| large | 000020 | 동화약품 | 2020-03-31 | -3278 | 331 |
| large | 000020 | 동화약품 | 2020-04-01 | 4496 | 28251 |
| large | 000020 | 동화약품 | 2020-04-02 | 15443 | -7567 |
| large | 000020 | 동화약품 | 2026-04-13 | 4834 | 311 |
| large | 000020 | 동화약품 | 2026-04-14 | 6571 | -867 |
| large | 000020 | 동화약품 | 2026-04-15 | 4968 | -2363 |
| large | 000020 | 동화약품 | 2026-04-16 | 20632 | 58 |
| large | 000020 | 동화약품 | 2026-04-17 | 5774 | 2767 |
| mid | 100090 | SK오션플랜트 | 2020-03-27 | 11918 | -2322 |
| mid | 100090 | SK오션플랜트 | 2020-03-30 | 13430 | -20825 |
| mid | 100090 | SK오션플랜트 | 2020-03-31 | 13492 | 7673 |
| mid | 100090 | SK오션플랜트 | 2020-04-01 | 2528 | -32399 |
| mid | 100090 | SK오션플랜트 | 2020-04-02 | -326 | -35803 |
| mid | 100090 | SK오션플랜트 | 2026-04-13 | -5060 | -95503 |
| mid | 100090 | SK오션플랜트 | 2026-04-14 | 40641 | -183565 |
| mid | 100090 | SK오션플랜트 | 2026-04-15 | 65941 | -63029 |
| mid | 100090 | SK오션플랜트 | 2026-04-16 | -105683 | -102929 |
| mid | 100090 | SK오션플랜트 | 2026-04-17 | 26390 | -402103 |
| mid | 100220 | 비상교육 | 2020-03-27 | 6456 | 14318 |
| mid | 100220 | 비상교육 | 2020-03-30 | -11478 | -4009 |
| mid | 100220 | 비상교육 | 2020-03-31 | 17616 | 9773 |
| mid | 100220 | 비상교육 | 2020-04-01 | 37482 | 15 |
| mid | 100220 | 비상교육 | 2020-04-02 | 231 | -11094 |
| mid | 100220 | 비상교육 | 2026-04-13 | 7818 | 2 |
| mid | 100220 | 비상교육 | 2026-04-14 | -11821 | -77 |
| mid | 100220 | 비상교육 | 2026-04-15 | 9574 | 1701 |
| mid | 100220 | 비상교육 | 2026-04-16 | 10094 | 3258 |
| mid | 100220 | 비상교육 | 2026-04-17 | -3066 | 4695 |
| small | 300720 | 한일시멘트 | 2020-03-27 | -275 | -3072 |
| small | 300720 | 한일시멘트 | 2020-03-30 | 1044 | -4562 |
| small | 300720 | 한일시멘트 | 2020-03-31 | 344 | 141 |
| small | 300720 | 한일시멘트 | 2020-04-01 | 0 | -1421 |
| small | 300720 | 한일시멘트 | 2020-04-02 | 311 | -1324 |
| small | 300720 | 한일시멘트 | 2026-04-13 | -22516 | -15965 |
| small | 300720 | 한일시멘트 | 2026-04-14 | -1148 | -7784 |
| small | 300720 | 한일시멘트 | 2026-04-15 | -95338 | -87889 |
| small | 300720 | 한일시멘트 | 2026-04-16 | -14925 | -36937 |
| small | 300720 | 한일시멘트 | 2026-04-17 | -16721 | 15220 |
| small | 302440 | SK바이오사이언스 | 2021-03-18 | -79508 | -81994 |
| small | 302440 | SK바이오사이언스 | 2021-03-19 | -680647 | -160200 |
| small | 302440 | SK바이오사이언스 | 2021-03-22 | -166678 | -8034 |
| small | 302440 | SK바이오사이언스 | 2021-03-23 | -66847 | 7321 |
| small | 302440 | SK바이오사이언스 | 2021-03-24 | -9530 | 35280 |
| small | 302440 | SK바이오사이언스 | 2026-04-13 | 6286 | -11640 |
| small | 302440 | SK바이오사이언스 | 2026-04-14 | 3077 | 8351 |
| small | 302440 | SK바이오사이언스 | 2026-04-15 | 35000 | 16832 |
| small | 302440 | SK바이오사이언스 | 2026-04-16 | 5139 | 25787 |
| small | 302440 | SK바이오사이언스 | 2026-04-17 | -67245 | 1812 |

## Suspicious Quiet Stocks
(none found)

## Artifacts
- Parquet directory: `v2\data\cache\investor_flow_full`
- Collection log: `v2\data\cache\investor_flow_full\_collection_log.parquet`
- Report: `v2\reports\pr7_a_2_a_step2_collection.md`

## Gate
Step 2 collection and validation only. Signal calculation, IC measurement, backtest, and Step 3 are not included.
