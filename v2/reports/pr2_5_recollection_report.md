# PR-2.5 OPENDART 재무 Payload 재수집 리포트

Generated at: 2026-04-19T18:51:57

## 1. 수집 전후 비교
| 지표 | 수집 전 | 수집 후 | 변화 |
| --- | --- | --- | --- |
| raw_dart 캐시 파일 수 | 2,036 | 27,194 | 25,158 |
| 재무 payload 파일 수 | 1,108 | 26,266 | 25,158 |
| SUE 계산 가능 이벤트 수 | 680 | 15,323 | 14,643 |
| revenue non-null 비율 | 4.18% | 92.01% | 87.83% |
| YoY pair 가능 비율 | 3.58% | 78.08% | 74.50% |

## 2. 수집 실패 분석
- 계획상 신규 수집 필요 이벤트: 978
- 캐시 재파싱 대상 이벤트: 0
- hard failure 이벤트 수: 0
- OPENDART 013/no data 이벤트 수: 918
- status 000이나 parser metric 미검출 이벤트 수: 1

### Reason Distribution
| reason | count |
| --- | --- |
| metrics | 20562 |
| CFS:metrics | 17715 |
| OFS:metrics | 2847 |
| CFS:no_data;OFS:no_data | 918 |
| no_data | 918 |
| CFS:metrics_missing;OFS:metrics_missing | 1 |
| metrics_missing | 1 |

### Hard Failure Distribution
(empty)

### Remaining Missing Concentration
| stock_code | remaining_missing_events |
| --- | --- |
| 001270 | 29 |
| 003470 | 29 |
| 030210 | 29 |
| 092220 | 25 |
| 006220 | 23 |
| 082640 | 21 |
| 003460 | 21 |
| 323410 | 21 |
| 000650 | 20 |
| 001290 | 20 |

## 3. PR-3 재실행 타당성
- 전체 SUE 계산 가능 이벤트 수: 15,323
- 2019-2025 연평균 SUE 샘플 수: 2,432.8
- 2019-2025 연최소 SUE 샘플 수: 2,408
- SUE 샘플 수가 연 500건 이상 달성했는가: yes
- PR-3 재실행 권고: yes

### Yearly SUE Availability
| year | sue_non_null |
| --- | --- |
| 2020 | 2408 |
| 2021 | 2421 |
| 2022 | 2449 |
| 2023 | 2450 |
| 2024 | 2415 |
| 2025 | 2454 |
| 2026 | 726 |

## 4. 남은 리스크
- 재무 3필드가 모두 결측인 잔여 이벤트 수: 1,088
- OPENDART 013은 해당 API의 재무제표 payload 부재로 간주했다.
- status 000이지만 metric이 미검출된 이벤트는 계정명 매핑 보강 여지가 있다.
- 연평균 SUE 샘플이 500건 미만이면 FnGuide 등 유료 데이터 보완을 재검토해야 한다.
