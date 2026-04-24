# PR-7.A.1.6 외국인+기관 flow cross-sectional predictability mini-pilot

Updated: 2026-04-25 KST

## Step 1. 30종목 stratified 선정

### 선정 메모

- 일반주 universe 크기: `915`
- `mid_p40_60` 후보 수: `183`
- `small_p60_80` 후보 수: `183`
- 최대 sector 쏠림: `제약 3`, `건축자재 3`
- 단일 sector 15종목 이상 쏠림 없음

### 30종목 리스트

| code | name | sector | market_cap_bucket |
| --- | --- | --- | --- |
| 005930 | 삼성전자 | 반도체와반도체장비 | large_top10 |
| 000660 | SK하이닉스 | 반도체와반도체장비 | large_top10 |
| 373220 | LG에너지솔루션 | 전기제품 | large_top10 |
| 005380 | 현대차 | 자동차 | large_top10 |
| 402340 | SK스퀘어 | 복합기업 | large_top10 |
| 034020 | 두산에너빌리티 | 기계 | large_top10 |
| 012450 | 한화에어로스페이스 | 우주항공과국방 | large_top10 |
| 207940 | 삼성바이오로직스 | 제약 | large_top10 |
| 329180 | HD현대중공업 | 조선 | large_top10 |
| 000270 | 기아 | 자동차 | large_top10 |
| 015360 | INVENI | 가스유틸리티 | mid_p40_60 |
| 001940 | KISCO홀딩스 | 철강 | mid_p40_60 |
| 001340 | PKC | 화학 | mid_p40_60 |
| 037710 | 광주신세계 | 백화점과일반상점 | mid_p40_60 |
| 108670 | LX하우시스 | 건축자재 | mid_p40_60 |
| 000390 | 삼화페인트 | 건축자재 | mid_p40_60 |
| 002150 | 도화엔지니어링 | 건설 | mid_p40_60 |
| 000140 | 하이트진로홀딩스 | 음료 | mid_p40_60 |
| 100250 | 진양홀딩스 | 자동차부품 | mid_p40_60 |
| 090350 | 노루페인트 | 건축자재 | mid_p40_60 |
| 003480 | 한진중공업홀딩스 | 가스유틸리티 | small_p60_80 |
| 004970 | 신라교역 | 식품 | small_p60_80 |
| 123690 | 한국화장품 | 화장품 | small_p60_80 |
| 013570 | 디와이 | 자동차부품 | small_p60_80 |
| 015590 | DKME | 기계 | small_p60_80 |
| 063160 | 종근당바이오 | 제약 | small_p60_80 |
| 004060 | SG세계물산 | 섬유,의류,신발,호화품 | small_p60_80 |
| 109070 | 주성코퍼레이션 | 해운사 | small_p60_80 |
| 010040 | 한국내화 | 비철금속 | small_p60_80 |
| 000220 | 유유제약 | 제약 | small_p60_80 |

> **섹터 편향 사전 고지**: Large bucket 10 종목 중 삼성전자, SK하이닉스, SK스퀘어, LG에너지솔루션, 두산에너빌리티, 한화에어로스페이스, HD현대중공업 은 2025 하반기 AI/반도체/조선/방산/원전 랠리 수혜 섹터에 속한다. 이는 2026-04 기준 KOSPI 시총 상위 10 의 자연스러운 구성이다. 2025-05 ~ 2025-12 구간은 이 섹터 동조화의 영향을 받을 수 있으므로, 판정의 1차 근거는 2024 (정상 레짐) IC 로 한다. 2025-05~12 IC 는 참고 기록만.

## Step 2. 투자자 flow 수집

### 수집 설정

- 소스: Naver `item/frgn.naver`
- 기간: `2024-01-01 ~ 2025-12-31`
- 대상: 승인된 30종목만
- 대기: page delay `0.15s`, stock delay `0.7s`
- checkpoint: `v2/data/cache/investor_flow_mini_pilot/collection_checkpoint.json`

### 품질 플래그 기준

- `row_ratio < 90%`
- `5거래일 이상 연속 결측`
- `일일 거래량 std/mean > 5.0`

### 각 종목 flow 완결성

| code | name | bucket | rows | expected_rows | row_ratio | max_missing_streak | volume_cv | flags | pages_fetched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 005930 | 삼성전자 | large_top10 | 486 | 486 | 100.0% | 0 | 0.42 | pass | 29 |
| 000660 | SK하이닉스 | large_top10 | 486 | 486 | 100.0% | 0 | 0.44 | pass | 29 |
| 373220 | LG에너지솔루션 | large_top10 | 486 | 486 | 100.0% | 0 | 0.59 | pass | 29 |
| 005380 | 현대차 | large_top10 | 486 | 486 | 100.0% | 0 | 0.70 | pass | 29 |
| 402340 | SK스퀘어 | large_top10 | 486 | 486 | 100.0% | 0 | 0.67 | pass | 29 |
| 034020 | 두산에너빌리티 | large_top10 | 486 | 486 | 100.0% | 0 | 0.95 | pass | 29 |
| 012450 | 한화에어로스페이스 | large_top10 | 486 | 486 | 100.0% | 0 | 0.96 | pass | 29 |
| 207940 | 삼성바이오로직스 | large_top10 | 486 | 486 | 100.0% | 0 | 0.69 | pass | 29 |
| 329180 | HD현대중공업 | large_top10 | 486 | 486 | 100.0% | 0 | 0.86 | pass | 29 |
| 000270 | 기아 | large_top10 | 486 | 486 | 100.0% | 0 | 0.64 | pass | 29 |
| 015360 | INVENI | mid_p40_60 | 486 | 486 | 100.0% | 0 | 0.91 | pass | 29 |
| 001940 | KISCO홀딩스 | mid_p40_60 | 486 | 486 | 100.0% | 0 | 0.88 | pass | 29 |
| 001340 | PKC | mid_p40_60 | 486 | 486 | 100.0% | 0 | 2.10 | pass | 29 |
| 037710 | 광주신세계 | mid_p40_60 | 486 | 486 | 100.0% | 0 | 1.07 | pass | 29 |
| 108670 | LX하우시스 | mid_p40_60 | 486 | 486 | 100.0% | 0 | 0.81 | pass | 29 |
| 000390 | 삼화페인트 | mid_p40_60 | 486 | 486 | 100.0% | 0 | 4.92 | pass | 29 |
| 002150 | 도화엔지니어링 | mid_p40_60 | 486 | 486 | 100.0% | 0 | 7.18 | volume_cv>5.0 | 29 |
| 000140 | 하이트진로홀딩스 | mid_p40_60 | 486 | 486 | 100.0% | 0 | 2.57 | pass | 29 |
| 100250 | 진양홀딩스 | mid_p40_60 | 486 | 486 | 100.0% | 0 | 2.37 | pass | 29 |
| 090350 | 노루페인트 | mid_p40_60 | 486 | 486 | 100.0% | 0 | 4.27 | pass | 29 |
| 003480 | 한진중공업홀딩스 | small_p60_80 | 486 | 486 | 100.0% | 0 | 5.44 | volume_cv>5.0 | 29 |
| 004970 | 신라교역 | small_p60_80 | 486 | 486 | 100.0% | 0 | 1.24 | pass | 29 |
| 123690 | 한국화장품 | small_p60_80 | 486 | 486 | 100.0% | 0 | 3.19 | pass | 29 |
| 013570 | 디와이 | small_p60_80 | 486 | 486 | 100.0% | 0 | 2.84 | pass | 29 |
| 015590 | DKME | small_p60_80 | 486 | 486 | 100.0% | 0 | 3.25 | pass | 29 |
| 063160 | 종근당바이오 | small_p60_80 | 486 | 486 | 100.0% | 0 | 2.21 | pass | 29 |
| 004060 | SG세계물산 | small_p60_80 | 486 | 486 | 100.0% | 0 | 3.15 | pass | 29 |
| 109070 | 주성코퍼레이션 | small_p60_80 | 486 | 486 | 100.0% | 0 | 6.90 | volume_cv>5.0 | 29 |
| 010040 | 한국내화 | small_p60_80 | 486 | 486 | 100.0% | 0 | 4.50 | pass | 29 |
| 000220 | 유유제약 | small_p60_80 | 486 | 486 | 100.0% | 0 | 4.62 | pass | 29 |

### Step 2 요약

- flow parquet 생성: `30`개
- 품질 플래그 종목: `002150, 003480, 109070`
- reused cache: `30`
- fetched this run: `0`
- 플래그 3종목은 모두 `volume_cv > 5.0` 단독 플래그다.

### IC 계산 시 플래그 종목 처리 방침

- 기본(main): **포함**
- 참고(reference): **제외** (`002150, 003480, 109070`)

## Step 3. 가격 데이터 수집

- 소스: 로컬 shared OHLCV `C:\dev\moneygetter\data\processed\market_ohlcv.parquet`
- 저장 기간: `2024-01-01 ~ 2026-01-31`
- 내부 warmup: `2023-09-01 ~ 2023-12-31` 거래량 60일 평균 계산용
- price parquet 생성: `30`개
- 저장 행수 범위: `507 ~ 507`
- 저장 데이터 날짜 범위: `2024-01-02 ~ 2026-01-30`
- 2024~2025 평가용 거래일 수: `486`

## Step 4. 4개 신호 계산

- `foreign_rank_5d`: `sum(foreign_net_buy_shares[t-5:t-1]) / avg(volume[t-60:t-1])`
- `institutional_rank_5d`: `sum(institutional_net_buy_shares[t-5:t-1]) / avg(volume[t-60:t-1])`
- `combined_rank_5d`: `sum(foreign + institutional net shares[t-5:t-1]) / avg(volume[t-60:t-1])`
- `divergence_5d`: `sum(foreign - institutional net shares[t-5:t-1]) / avg(volume[t-60:t-1])`
- point-in-time: `t` 신호는 `t-1`까지의 flow만 사용

## Step 5. Forward return 계산

- `fwd_ret_5d = close[t+5] / close[t+1] - 1`
- `fwd_ret_20d = close[t+20] / close[t+1] - 1`
- 시작점은 모두 `t+1`

## Step 6. IC 측정

### 32셀 IC_mean 테이블 (main: 플래그 포함)

| series | 2024 | 2025 | 2025-01~04 | 2025-05~12 |
| --- | --- | --- | --- | --- |
| foreign_rank_5d x fwd_ret_5d | 0.0137 | -0.0082 | 0.0307 | -0.0275 |
| foreign_rank_5d x fwd_ret_20d | 0.0222 | 0.0061 | 0.0494 | -0.0153 |
| institutional_rank_5d x fwd_ret_5d | -0.0275 | -0.0037 | -0.0016 | -0.0047 |
| institutional_rank_5d x fwd_ret_20d | -0.0477 | -0.0205 | -0.0262 | -0.0177 |
| combined_rank_5d x fwd_ret_5d | -0.0128 | -0.0005 | 0.0293 | -0.0152 |
| combined_rank_5d x fwd_ret_20d | -0.0219 | -0.0077 | 0.0200 | -0.0213 |
| divergence_5d x fwd_ret_5d | 0.0307 | -0.0030 | 0.0222 | -0.0154 |
| divergence_5d x fwd_ret_20d | 0.0535 | 0.0122 | 0.0314 | 0.0027 |

### 상세 통계 (main: 플래그 포함)

| series | regime | ic_mean | ic_median | ic_std | t_stat | n_days | avg_n_stocks | stock_day_pairs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| foreign_rank_5d x fwd_ret_5d | 2024 | 0.0137 | 0.0000 | 0.2151 | 0.99 | 239 | 28.7 | 6860 |
| foreign_rank_5d x fwd_ret_5d | 2025 | -0.0082 | -0.0190 | 0.2133 | -0.60 | 242 | 28.9 | 7000 |
| foreign_rank_5d x fwd_ret_5d | 2025-01~04 | 0.0307 | 0.0153 | 0.1973 | 1.39 | 80 | 28.8 | 2302 |
| foreign_rank_5d x fwd_ret_5d | 2025-05~12 | -0.0275 | -0.0418 | 0.2189 | -1.60 | 162 | 29.0 | 4698 |
| foreign_rank_5d x fwd_ret_20d | 2024 | 0.0222 | 0.0172 | 0.1994 | 1.72 | 239 | 28.7 | 6860 |
| foreign_rank_5d x fwd_ret_20d | 2025 | 0.0061 | 0.0000 | 0.1902 | 0.50 | 242 | 28.9 | 7000 |
| foreign_rank_5d x fwd_ret_20d | 2025-01~04 | 0.0494 | 0.0416 | 0.1832 | 2.41 | 80 | 28.8 | 2302 |
| foreign_rank_5d x fwd_ret_20d | 2025-05~12 | -0.0153 | -0.0446 | 0.1906 | -1.02 | 162 | 29.0 | 4698 |
| institutional_rank_5d x fwd_ret_5d | 2024 | -0.0275 | -0.0325 | 0.2086 | -2.04 | 239 | 28.7 | 6860 |
| institutional_rank_5d x fwd_ret_5d | 2025 | -0.0037 | -0.0099 | 0.2325 | -0.25 | 242 | 28.9 | 7000 |
| institutional_rank_5d x fwd_ret_5d | 2025-01~04 | -0.0016 | 0.0054 | 0.2473 | -0.06 | 80 | 28.8 | 2302 |
| institutional_rank_5d x fwd_ret_5d | 2025-05~12 | -0.0047 | -0.0170 | 0.2256 | -0.27 | 162 | 29.0 | 4698 |
| institutional_rank_5d x fwd_ret_20d | 2024 | -0.0477 | -0.0650 | 0.1864 | -3.96 | 239 | 28.7 | 6860 |
| institutional_rank_5d x fwd_ret_20d | 2025 | -0.0205 | -0.0342 | 0.2327 | -1.37 | 242 | 28.9 | 7000 |
| institutional_rank_5d x fwd_ret_20d | 2025-01~04 | -0.0262 | -0.0493 | 0.2302 | -1.02 | 80 | 28.8 | 2302 |
| institutional_rank_5d x fwd_ret_20d | 2025-05~12 | -0.0177 | -0.0254 | 0.2346 | -0.96 | 162 | 29.0 | 4698 |
| combined_rank_5d x fwd_ret_5d | 2024 | -0.0128 | -0.0158 | 0.2168 | -0.91 | 239 | 28.7 | 6860 |
| combined_rank_5d x fwd_ret_5d | 2025 | -0.0005 | -0.0049 | 0.2294 | -0.03 | 242 | 28.9 | 7000 |
| combined_rank_5d x fwd_ret_5d | 2025-01~04 | 0.0293 | 0.0643 | 0.2444 | 1.07 | 80 | 28.8 | 2302 |
| combined_rank_5d x fwd_ret_5d | 2025-05~12 | -0.0152 | -0.0148 | 0.2209 | -0.87 | 162 | 29.0 | 4698 |
| combined_rank_5d x fwd_ret_20d | 2024 | -0.0219 | -0.0448 | 0.2011 | -1.68 | 239 | 28.7 | 6860 |
| combined_rank_5d x fwd_ret_20d | 2025 | -0.0077 | -0.0219 | 0.2186 | -0.55 | 242 | 28.9 | 7000 |
| combined_rank_5d x fwd_ret_20d | 2025-01~04 | 0.0200 | 0.0076 | 0.2300 | 0.78 | 80 | 28.8 | 2302 |
| combined_rank_5d x fwd_ret_20d | 2025-05~12 | -0.0213 | -0.0236 | 0.2121 | -1.28 | 162 | 29.0 | 4698 |
| divergence_5d x fwd_ret_5d | 2024 | 0.0307 | 0.0274 | 0.2225 | 2.13 | 239 | 28.7 | 6860 |
| divergence_5d x fwd_ret_5d | 2025 | -0.0030 | -0.0252 | 0.2043 | -0.23 | 242 | 28.9 | 7000 |
| divergence_5d x fwd_ret_5d | 2025-01~04 | 0.0222 | 0.0209 | 0.1861 | 1.06 | 80 | 28.8 | 2302 |
| divergence_5d x fwd_ret_5d | 2025-05~12 | -0.0154 | -0.0450 | 0.2121 | -0.92 | 162 | 29.0 | 4698 |
| divergence_5d x fwd_ret_20d | 2024 | 0.0535 | 0.0650 | 0.1917 | 4.31 | 239 | 28.7 | 6860 |
| divergence_5d x fwd_ret_20d | 2025 | 0.0122 | 0.0057 | 0.1929 | 0.98 | 242 | 28.9 | 7000 |
| divergence_5d x fwd_ret_20d | 2025-01~04 | 0.0314 | 0.0393 | 0.1828 | 1.54 | 80 | 28.8 | 2302 |
| divergence_5d x fwd_ret_20d | 2025-05~12 | 0.0027 | -0.0126 | 0.1976 | 0.17 | 162 | 29.0 | 4698 |

- `n_days`가 `2024`에서 `184`로 줄어든 이유: `60거래일 평균 거래량` 정상화와 `5거래일` 신호 window 때문에 2024 초반 warmup 구간은 IC 계산에서 제외됐다.

### 32셀 IC_mean 테이블 (reference: 플래그 제외)

| series | 2024 | 2025 | 2025-01~04 | 2025-05~12 |
| --- | --- | --- | --- | --- |
| foreign_rank_5d x fwd_ret_5d | 0.0167 | -0.0087 | 0.0359 | -0.0308 |
| foreign_rank_5d x fwd_ret_20d | 0.0248 | -0.0003 | 0.0266 | -0.0135 |
| institutional_rank_5d x fwd_ret_5d | -0.0274 | -0.0063 | 0.0032 | -0.0110 |
| institutional_rank_5d x fwd_ret_20d | -0.0537 | -0.0228 | -0.0305 | -0.0190 |
| combined_rank_5d x fwd_ret_5d | -0.0111 | -0.0004 | 0.0367 | -0.0186 |
| combined_rank_5d x fwd_ret_20d | -0.0223 | -0.0156 | -0.0010 | -0.0228 |
| divergence_5d x fwd_ret_5d | 0.0347 | -0.0029 | 0.0192 | -0.0139 |
| divergence_5d x fwd_ret_20d | 0.0610 | 0.0123 | 0.0222 | 0.0075 |

### IC 집중도 체크

`IC_sum`은 부호 상쇄를 피하기 위해 `abs(IC)` 합으로 계산했다.

| series | n_days | top_10pct_day_abs_ic_share | top_month | top_month_abs_ic_share |
| --- | --- | --- | --- | --- |
| foreign_rank_5d x fwd_ret_5d | 481 | 25.1% | 2024-07 | 6.9% |
| foreign_rank_5d x fwd_ret_20d | 481 | 26.1% | 2024-05 | 7.3% |
| institutional_rank_5d x fwd_ret_5d | 481 | 26.8% | 2025-12 | 6.8% |
| institutional_rank_5d x fwd_ret_20d | 481 | 25.0% | 2025-12 | 7.3% |
| combined_rank_5d x fwd_ret_5d | 481 | 23.9% | 2025-12 | 5.8% |
| combined_rank_5d x fwd_ret_20d | 481 | 26.2% | 2025-04 | 6.1% |
| divergence_5d x fwd_ret_5d | 481 | 24.5% | 2024-07 | 6.7% |
| divergence_5d x fwd_ret_20d | 481 | 23.3% | 2024-02 | 6.3% |

## Step 7. 판정

### 적용 판정 규칙

- 통과 조건:
  - 1차 게이트: 최소 1개 신호가 `2024` 기간에 `IC_mean >= 0.03` and `t-stat >= 2.0`
  - 부호 consistency: 해당 신호의 `2025-01~04` IC 도 부호 동일
  - `2025-05~12` IC 는 정보 기록만
- 탈락 조건:
  - 4개 신호 모두 `2024` IC_mean < 0.03 또는 t-stat < 2.0
  - 또는 2024 유의 신호가 `2025-01~04` 에 부호 반전
- 경계 조건:
  - 2024 유의 + `2025-01~04` 부호 일치 + `2025-05~12` 극단적 차이
  - 운영 정의: `|IC_2025-05~12 - IC_2024| > 2 * |IC_2024|`

### 판정 결과

- **판정: Pass**
- 2024 1차 게이트 통과 series: `divergence_5d x fwd_ret_5d, divergence_5d x fwd_ret_20d`
- 2025-01~04 부호 일치 series: `divergence_5d x fwd_ret_5d, divergence_5d x fwd_ret_20d`
- 2025-01~04 부호 반전 series: `없음`
- 2025-05~12 extreme-difference series: `없음`
- reference(플래그 제외) 판정: `Pass`

## Step 8. 결과 메모

- 본 mini-pilot 은 IC 측정만 수행했다.
- 백테스트, 포트폴리오 구성, PnL 계산은 수행하지 않았다.
- 2025-05~12 구간은 시총 상위 랠리 섹터 동조화 가능성을 고려해 참고 기록으로만 남긴다.

## 산출물

| path | files | note |
| --- | --- | --- |
| v2/data/cache/investor_flow_mini_pilot/*.parquet | 30 | Naver frgn.naver 수집 결과 |
| v2/data/cache/prices_mini_pilot/*.parquet | 30 | 로컬 shared OHLCV price cache |
| v2/data/cache/investor_flow_mini_pilot/collection_checkpoint.json | 1 | resume 메타데이터, 플래그 종목 002150, 003480, 109070 |
