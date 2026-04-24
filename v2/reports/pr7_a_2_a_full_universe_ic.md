# PR-7.A.2.a 전체 universe 투자자 flow 수집 + IC 재측정

Updated: 2026-04-25 KST

## 상태

- 현재 문서는 **Step 1 완료 상태**까지만 반영한다.
- Step 2 전체 flow 수집은 사용자 승인 전 시작하지 않는다.

## Step 1. Universe 정의

### 기준

- 기준일: `2026-04-17`
- active universe 소스:
  - Naver `sise_market_sum.naver` current KOSPI snapshot
  - 로컬 shared OHLCV `C:\dev\moneygetter\data\processed\market_ohlcv.parquet`
- active common-stock 필터:
  - Naver KOSPI 종목 리스트 기준
  - 보통주만
  - ETF / ETN / SPAC / 리츠 및 상장지수상품 계열 이름 제외
- delisted 처리:
  - `2020-03-27 ~ 2026-04-17` 사이에 이력이 있고 `last_seen_date < 2026-04-17` 인 종목 후보 확인
  - 같은 보통주 / 상품 제외 필터 적용 후 universe 에 포함
- sector 소스:
  - Naver `item/main.naver` 현재 페이지의 업종 링크
  - delisted 종목은 페이지 redirect 시 sector 를 `NA` 로 둠

### 주의 메모

- `listed_date` 는 **로컬 OHLCV first_seen_date proxy** 다.
- 2020-03-27 이전 상장 종목은 대부분 `2020-01-02` 로 기록된다.
- active common-stock 기준면은 `2026-04-25` Naver current snapshot 을 관측한 뒤, 로컬 OHLCV `listed_date <= 2026-04-17` 조건으로 정렬했다.
- `2026-04-17` 과 `2026-04-25` 사이 신규 상장 종목은 자동 제외된다.

### Universe 요약

- raw latest KOSPI rows: `2188`
- active common rows: `806`
- period-delisted common rows: `2`
- total universe rows: `808`
- sector resolved rows: `805`
- sector missing rows: `3`

### 상태 bucket 분포

| bucket | count |
| --- | --- |
| active_on_2026-04-17 | 806 |
| delisted_during_2020-03-27_to_2026-04-17 | 2 |

### listing bucket 분포

| listing_bucket | count |
| --- | --- |
| listed_2020-03-28_to_2021-12-31 | 26 |
| listed_2022 | 5 |
| listed_2023 | 13 |
| listed_2024 | 11 |
| listed_2025 | 7 |
| listed_2026 | 1 |
| listed_on_or_before_2020-03-27 | 745 |

### active sector 상위 15개

| sector | count |
| --- | --- |
| 자동차부품 | 69 |
| 화학 | 68 |
| 제약 | 54 |
| 섬유,의류,신발,호화품 | 45 |
| 식품 | 43 |
| 철강 | 36 |
| 건설 | 32 |
| 건축자재 | 25 |
| 비철금속 | 25 |
| 기계 | 22 |
| 증권 | 21 |
| 전자장비와기기 | 19 |
| 화장품 | 16 |
| IT서비스 | 14 |
| 조선 | 14 |

### universe 샘플 20행

| code | name | listed_date | delisted_date | sector |
| --- | --- | --- | --- | --- |
| 000020 | 동화약품 | 2020-01-02 00:00:00 | NaT | 제약 |
| 000040 | KR모터스 | 2020-01-02 00:00:00 | NaT | 자동차 |
| 000050 | 경방 | 2020-01-02 00:00:00 | NaT | 섬유,의류,신발,호화품 |
| 000070 | 삼양홀딩스 | 2020-01-02 00:00:00 | NaT | 화학 |
| 000080 | 하이트진로 | 2020-01-02 00:00:00 | NaT | 음료 |
| 000100 | 유한양행 | 2020-01-02 00:00:00 | NaT | 제약 |
| 000120 | CJ대한통운 | 2020-01-02 00:00:00 | NaT | 항공화물운송과물류 |
| 000140 | 하이트진로홀딩스 | 2020-01-02 00:00:00 | NaT | 음료 |
| 000150 | 두산 | 2020-01-02 00:00:00 | NaT | 복합기업 |
| 000180 | 성창기업지주 | 2020-01-02 00:00:00 | NaT | 종이와목재 |
| 000210 | DL | 2020-01-02 00:00:00 | NaT | 화학 |
| 000220 | 유유제약 | 2020-01-02 00:00:00 | NaT | 제약 |
| 000230 | 일동홀딩스 | 2020-01-02 00:00:00 | NaT | 제약 |
| 000240 | 한국앤컴퍼니 | 2020-01-02 00:00:00 | NaT | 자동차부품 |
| 000270 | 기아 | 2020-01-02 00:00:00 | NaT | 자동차 |
| 000300 | DH오토넥스 | 2020-01-02 00:00:00 | NaT | 자동차부품 |
| 000320 | 노루홀딩스 | 2020-01-02 00:00:00 | NaT | 건축자재 |
| 000370 | 한화손해보험 | 2020-01-02 00:00:00 | NaT | 손해보험 |
| 000390 | 삼화페인트 | 2020-01-02 00:00:00 | NaT | 건축자재 |
| 000400 | 롯데손해보험 | 2020-01-02 00:00:00 | NaT | 손해보험 |

### 산출물

- universe parquet: `v2/data/cache/universe/kospi_universe.parquet`
- active universe helper: `v2/data/universe.py:get_active_universe`

### 중단 게이트

- Step 1 완료
- 사용자 승인 전 Step 2 전체 flow 수집 금지
