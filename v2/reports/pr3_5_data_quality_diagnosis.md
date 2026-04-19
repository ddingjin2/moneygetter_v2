# PR-3.5 Data Quality Diagnosis

## Section 1. 결측률 수치

### 1-A. Field Missing Rates
| field | records | non_null | null_ratio |
| --- | --- | --- | --- |
| revenue | 22441 | 20648 | 0.0799 |
| operating_income | 22441 | 20827 | 0.0719 |
| net_income | 22441 | 19029 | 0.1520 |
| prev_revenue | 22441 | 17623 | 0.2147 |
| prev_operating_income | 22441 | 17750 | 0.2090 |
| prev_net_income | 22441 | 16339 | 0.2719 |

### 1-A. YoY Pair Availability
| yoy_pair | records | both_present | both_present_ratio |
| --- | --- | --- | --- |
| revenue+prev_revenue | 22441 | 17522 | 0.7808 |
| operating_income+prev_operating_income | 22441 | 17551 | 0.7821 |
| net_income+prev_net_income | 22441 | 15383 | 0.6855 |

### 1-B. Stock Quarter Coverage
| stocks | avg_events_total | avg_coverage_24q | stocks_with_4q_run | stocks_with_8q_run |
| --- | --- | --- | --- | --- |
| 827 | 27.1354 | 0.9437 | 797 | 785 |

### 1-C. Market-cap Quintile Missing Rates
| market_cap_quintile | events | median_market_cap | sue_non_null_ratio | revenue_missing | operating_income_missing | net_income_missing |
| --- | --- | --- | --- | --- | --- | --- |
| unavailable_all_zero_or_missing | 22441 |  | 0.6828 | 0.0799 | 0.0719 | 0.1520 |

### 1-D. Yearly SUE Availability
| year | events | sue_non_null | sue_non_null_ratio | revenue_missing | net_income_missing |
| --- | --- | --- | --- | --- | --- |
| 2020 | 2999 | 2408 | 0.8029 | 0.0880 | 0.1551 |
| 2021 | 3062 | 2421 | 0.7907 | 0.0879 | 0.1561 |
| 2022 | 3100 | 2449 | 0.7900 | 0.0884 | 0.1690 |
| 2023 | 3129 | 2450 | 0.7830 | 0.0837 | 0.1585 |
| 2024 | 3170 | 2415 | 0.7618 | 0.0634 | 0.1435 |
| 2025 | 3216 | 2454 | 0.7631 | 0.0650 | 0.1704 |
| 2026 | 804 | 726 | 0.9030 | 0.0622 | 0.0560 |

### 1-E. OPENDART Raw Sample Check
| sampled_revenue_nan_events | source_revenue_present_count | parser_would_extract_count | parse_or_stale_miss_count | mapping_miss_count | source_net_income_present_count | raw_error_count |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 3 | 0 | 3 | 3 | 3 | 0 |

| stock_code | rcept_no | fiscal_quarter | reprt_code | raw_source | raw_status | raw_message | source_revenue_value_present | parser_would_extract_revenue | source_net_income_value_present | parquet_revenue_nan | parse_or_stale_miss | mapping_miss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 032830 | 20210310001045 | 2020Q4 | 11011 | CFS:cache;OFS:cache | 013/013 | 조회된 데이타가 없습니다. / 조회된 데이타가 없습니다. | False | False | False | True | False | False |
| 089860 | 20210517002086 | 2021Q1 | 11013 | CFS:cache;OFS:cache | 013/013 | 조회된 데이타가 없습니다. / 조회된 데이타가 없습니다. | False | False | False | True | False | False |
| 088350 | 20250312000939 | 2024Q4 | 11011 | CFS:cache;OFS:not_fetched | 000/NA | 정상 /  | True | False | True | True | True | True |
| 030210 | 20240307000697 | 2023Q4 | 11011 | CFS:cache;OFS:not_fetched | 000/NA | 정상 /  | True | False | True | True | True | True |
| 377740 | 20220331002923 | 2021Q4 | 11011 | CFS:cache;OFS:cache | 013/013 | 조회된 데이타가 없습니다. / 조회된 데이타가 없습니다. | False | False | False | True | False | False |
| 001270 | 20190814001830 | 2019Q2 | 11012 | CFS:cache;OFS:cache | 013/013 | 조회된 데이타가 없습니다. / 조회된 데이타가 없습니다. | False | False | False | True | False | False |
| 016360 | 20201113000758 | 2020Q3 | 11014 | CFS:cache;OFS:cache | 013/013 | 조회된 데이타가 없습니다. / 조회된 데이타가 없습니다. | False | False | False | True | False | False |
| 005740 | 20210817002158 | 2021Q2 | 11012 | CFS:cache;OFS:not_fetched | 000/NA | 정상 /  | True | False | True | True | True | True |
| 006220 | 20190401004790 | 2018Q4 | 11011 | CFS:cache;OFS:cache | 013/013 | 조회된 데이타가 없습니다. / 조회된 데이타가 없습니다. | False | False | False | True | False | False |
| 005940 | 20191114001070 | 2019Q3 | 11014 | CFS:cache;OFS:cache | 013/013 | 조회된 데이타가 없습니다. / 조회된 데이타가 없습니다. | False | False | False | True | False | False |

### Raw Financial Payload Cache Coverage
| events | payload_slots_cfs_ofs | cached_payloads | cached_payload_ratio | cached_payload_status_000 | events_with_any_payload | events_with_any_payload_ratio | sue_non_null_inside_cached_events | sue_non_null_ratio_inside_cached_events | net_income_non_null_ratio_inside_cached_events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 22441 | 44882 | 26266 | 0.5852 | 21524 | 22441 | 1.0000 | 15323 | 0.6828 | 0.8480 |

### SUE Rule Capacity Check
| rule | sample_count |
| --- | --- |
| current_actual_sue | 15323 |
| min4_complete_trailing | 13907 |
| strict8_complete_trailing | 10649 |

## Section 2. 원인 판정
Scenario B: sample parse/stale miss rate is 30.0%, above the 20% parser-loss threshold.

Market-cap segmentation is not available because the local OHLCV/features files have all-zero market_cap. The live OPENDART 1-E sample failed at the HTTP layer in this environment, so the raw-cache coverage table is used as the stronger diagnostic.

## Section 3. 해결책 권고
| scenario | expected_total_sue_samples | expected_samples_per_year | basis |
| --- | --- | --- | --- |
| A_top50_market_cap | 7662 | 1094.5714 | market-cap data unavailable; naive 50% retention from current SUE samples |
| B_fix_parsing_or_stale_fetch | 17458 | 2494.0000 | current + missing_sue * 1E sample miss rate (30.00%) |
| C_min4_quarter_rule | 13907 | 1986.7143 | existing net_income only, prior same quarter plus complete trailing 4 quarters |
| A+B+C_combined | 8729 | 1247.0000 | B projection with top-50% universe retention; C does not add under current net-income data |

Best projected path: B_fix_parsing_or_stale_fetch with about 17458 total samples (2494.0/year). Minimum target is 500/year.

Recommended order: first repair/retry financial payload collection and rebuild earnings_events.parquet from raw filings, then rerun PR-3. Only after that should SUE eligibility or universe filters be tuned. A top-50% universe filter alone cannot create more SUE samples.

## Section 4. PR-3 재실행 필요성 판단
- 데이터 재생성 필요한가: yes
- SUE 계산 규칙 수정 필요한가: no
- universe 조정만으로 해결 가능한가: no

## Section 5. 최종 권고
(a) 해결책 적용 후 PR-3 재실행 → 결과 양호 시 PR-4 진행
