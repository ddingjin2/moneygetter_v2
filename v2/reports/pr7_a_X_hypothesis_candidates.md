# PR-7.A.X Hypothesis Candidates (D Generation)

## Generation Notes
- 본 단계는 generation only. 평가/선택 금지.
- 카테고리 비율 강제: mainstream 10, option_a_variant 5, non_consensus 5
- 데이터 제약: 시가총액 미확보, alive-only universe, KOSPI only, intraday 없음, KOSDAQ 없음, 펀더멘털/공시/뉴스/파생/외환 데이터 없음.
- 가용 데이터: KOSPI 808종목 일별 investor flow, 일별 OHLCV, KOSPI 지수 일별. 기간은 2020-03-27 ~ 2026-04-17.
- 수식에서 `ret_kd(code,t)`는 `close_t / close_{t-k} - 1`, `dvol(code,t)`은 `close_t * volume_t`, `mkt_ret_kd(t)`는 KOSPI 지수 k일 수익률, `cs_z_t(.)`는 t일 cross-sectional z-score를 의미한다.
- 아래 검증 비용은 데이터 로딩 및 IC 산출까지의 rough estimate이며, backtest/turnover/cost 검증은 포함하지 않는다.

## Category A: Mainstream Extension (10)

### A1. 12-1개월 가격 모멘텀: 과거 12개월 상승 후 최근 1개월을 제외한 강한 종목이 다음 기간에도 상대 강세
1. 가설: `ret_252d_ex_21d`가 높은 종목일수록 다음 5~21거래일 cross-sectional return이 높다.
2. 신호 정의: `signal_A1(code,t) = cs_z_t(close_{t-21} / close_{t-252} - 1)`, 단 252거래일 이력 필요.
3. 옵션 A와의 차별점: investor flow divergence가 아니라 장기 가격 추세 continuation만 사용한다.
4. 학술/업계 prior: Jegadeesh and Titman (1993) 가격 모멘텀, Asness/Moskowitz/Pedersen (2013) value and momentum everywhere가 대표 prior다. 한국 주식시장 모멘텀 검증은 기간/표본/리밸런싱에 따라 혼재되어 보고된다. 대표 IC/Sharpe는 시장과 비용 가정별 차이가 커서 단일 range를 명시하기 어렵다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 1
7. 검증 비용 추정: 1.0시간
8. 한 줄 요약: 전통적인 중기 가격 모멘텀을 KOSPI alive-only universe에 적용한다.

### A2. 1개월 단기 reversal: 최근 21거래일 하락 종목이 다음 기간에 상대 반등
1. 가설: 최근 21거래일 수익률이 낮은 종목일수록 다음 1~5거래일 cross-sectional return이 높다.
2. 신호 정의: `signal_A2(code,t) = -cs_z_t(close_t / close_{t-21} - 1)`.
3. 옵션 A와의 차별점: 수급 주체 차이가 아니라 단기 가격 과잉반응/유동성 회복을 사용한다.
4. 학술/업계 prior: Jegadeesh (1990), Lehmann (1990), Lo and MacKinlay (1990)의 단기 reversal prior가 있다. 한국 시장에서도 단기 reversal은 거래비용과 체결가 가정에 민감한 것으로 알려져 있다. daily IC는 보통 낮은 절대값에서 논의된다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 1
7. 검증 비용 추정: 0.8시간
8. 한 줄 요약: 최근 낙폭이 큰 종목의 짧은 반등 가능성을 본다.

### A3. 저변동성 anomaly: 최근 실현변동성이 낮은 종목이 다음 기간에 상대 강세
1. 가설: 최근 60거래일 일간 수익률 변동성이 낮은 종목일수록 다음 21거래일 cross-sectional return이 높다.
2. 신호 정의: `signal_A3(code,t) = -cs_z_t(std(ret_1d(code,t-59:t)))`.
3. 옵션 A와의 차별점: 외국인/기관 수급이 아니라 가격 경로의 risk 특성만 사용한다.
4. 학술/업계 prior: Haugen and Heins (1975), Blitz and van Vliet (2007), Frazzini and Pedersen (2014)의 low volatility / betting-against-beta prior가 있다. 한국 시장 적용 사례는 ETF/팩터 리서치에서 반복적으로 다뤄졌으나, 구현 universe와 비용에 따라 결과가 달라진다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 1
7. 검증 비용 추정: 1.0시간
8. 한 줄 요약: 변동성이 낮은 종목의 상대 성과를 확인하는 표준 방어형 팩터다.

### A4. 거래대금 size proxy: 평균 거래대금이 작은 종목이 다음 기간에 상대 강세
1. 가설: 최근 평균 거래대금이 낮은 종목일수록 다음 21거래일 cross-sectional return이 높다.
2. 신호 정의: `signal_A4(code,t) = -cs_z_t(log(mean(dvol(code,t-59:t))))`.
3. 옵션 A와의 차별점: investor flow 대신 거래대금을 시가총액 부재 시 size/liquidity proxy로 사용한다.
4. 학술/업계 prior: Banz (1981)의 size effect, Amihud (2002)의 illiquidity prior와 연결된다. 단, 거래대금은 시가총액과 유동성이 섞인 proxy라서 순수 size effect와 동일하지 않다. 한국 검증은 소형주/저유동성 premium 논의가 있으나 survivorship와 거래비용 영향이 크다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 2
7. 검증 비용 추정: 0.8시간
8. 한 줄 요약: 시총이 없으므로 평균 거래대금을 size/liquidity 대체 변수로 사용한다.

### A5. Amihud illiquidity: 가격 충격 대비 거래대금이 작은 종목이 다음 기간에 상대 강세
1. 가설: 최근 Amihud illiquidity가 높은 종목일수록 다음 21거래일 cross-sectional return이 높다.
2. 신호 정의: `signal_A5(code,t) = cs_z_t(mean(abs(ret_1d(code,s)) / max(dvol(code,s), eps), s=t-59:t))`.
3. 옵션 A와의 차별점: 수급 주체의 방향이 아니라 가격 변화 대비 거래대금이라는 liquidity compensation을 사용한다.
4. 학술/업계 prior: Amihud (2002)는 illiquidity premium의 대표 prior다. 한국 시장에서도 유동성 premium 연구가 있으나 microcap, 거래정지, 비용 처리에 민감하다. 대표 IC/Sharpe는 표본과 필터에 따라 폭이 크다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 2
7. 검증 비용 추정: 1.2시간
8. 한 줄 요약: 거래대금 대비 가격 충격이 큰 종목의 보상 가능성을 본다.

### A6. 거래량 충격 reversal: 비정상적 거래량과 동반된 급등 종목이 단기 되돌림
1. 가설: 최근 5거래일 수익률이 높고 거래량이 평균 대비 급증한 종목일수록 다음 1~5거래일 cross-sectional return이 낮다.
2. 신호 정의: `signal_A6(code,t) = -cs_z_t(ret_5d(code,t) * log(volume_t / mean(volume_{t-60:t-6})))`.
3. 옵션 A와의 차별점: 기관-외국인 괴리가 아니라 price-volume overreaction 조합을 사용한다.
4. 학술/업계 prior: Lee and Swaminathan (2000)의 price momentum and trading volume, short-term reversal 문헌과 연결된다. 한국에서는 거래대금 급증/테마주 단기 반전 형태의 실무적 논의가 있으나 정식 IC range는 일관되게 인용하기 어렵다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 2
7. 검증 비용 추정: 1.0시간
8. 한 줄 요약: 거래량 급증을 동반한 단기 급등의 과열성 되돌림을 본다.

### A7. 가격-거래량 divergence: 가격 상승에도 거래량이 감소한 종목은 다음 기간 상대 약세
1. 가설: 최근 가격은 상승했지만 거래량 추세가 약한 종목일수록 다음 5~21거래일 cross-sectional return이 낮다.
2. 신호 정의: `signal_A7(code,t) = -cs_z_t(ret_20d(code,t) * (-cs_z_t(log(mean(volume_{t-4:t}) / mean(volume_{t-24:t-5})))))`.
3. 옵션 A와의 차별점: investor flow가 아니라 가격 추세와 거래 참여 강도의 불일치를 사용한다.
4. 학술/업계 prior: volume-confirmed momentum과 technical analysis literature, Lee and Swaminathan (2000)의 거래량 conditioning prior와 관련된다. 한국 정량 검증 사례는 많지만 공개된 대표 IC range는 표준화되어 있지 않다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 2
7. 검증 비용 추정: 1.2시간
8. 한 줄 요약: 상승이 거래량 확인 없이 진행된 경우의 후속 상대 약세를 본다.

### A8. overnight gap reversal proxy: 전일 대비 갭 상승 후 종가가 약한 종목은 다음날 상대 약세
1. 가설: 당일 시가가 전일 종가보다 높게 출발했으나 당일 종가가 시가보다 약한 종목일수록 다음 1거래일 cross-sectional return이 낮다.
2. 신호 정의: `signal_A8(code,t) = -cs_z_t((open_t / close_{t-1} - 1) - (close_t / open_t - 1))`.
3. 옵션 A와의 차별점: 수급 누적치가 아니라 open-close 구조에서 나타나는 intraday proxy를 사용한다.
4. 학술/업계 prior: overnight/intraday return decomposition은 Lou, Polk, and Skouras (2019) 등에서 논의된다. 한국 일별 OHLC만으로는 진짜 intraday order flow를 볼 수 없고, 공개 KOSPI IC range는 제한적이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 3
7. 검증 비용 추정: 1.0시간
8. 한 줄 요약: 갭 상승 뒤 장중 약세라는 일별 OHLC 패턴을 단기 신호로 본다.

### A9. 52주 고점 proximity: 52주 고점에 가까운 종목이 다음 기간 상대 강세
1. 가설: 현재 종가가 최근 252거래일 최고가에 가까운 종목일수록 다음 21거래일 cross-sectional return이 높다.
2. 신호 정의: `signal_A9(code,t) = cs_z_t(close_t / max(high_{t-251:t}))`.
3. 옵션 A와의 차별점: investor flow와 무관하게 anchoring 및 trend persistence proxy를 사용한다.
4. 학술/업계 prior: George and Hwang (2004)의 52-week high momentum prior가 있다. 한국 시장 검증 사례는 존재하나 공개적으로 합의된 대표 IC/Sharpe range는 없다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 2
7. 검증 비용 추정: 1.0시간
8. 한 줄 요약: 신고가 근접도를 momentum/anchoring 변수로 사용한다.

### A10. 시장 beta residual reversal: KOSPI beta-adjusted 단기 잔차 하락 종목이 다음 기간 상대 반등
1. 가설: 최근 5거래일 KOSPI 지수로 설명되지 않는 잔차 수익률이 낮은 종목일수록 다음 5거래일 cross-sectional return이 높다.
2. 신호 정의: `beta_60(code,t) = cov(ret_1d(code,t-59:t), mkt_ret_1d(t-59:t)) / var(mkt_ret_1d(t-59:t))`; `resid_5d = ret_5d(code,t) - beta_60(code,t) * mkt_ret_5d(t)`; `signal_A10(code,t) = -cs_z_t(resid_5d)`.
3. 옵션 A와의 차별점: 기관/외국인 divergence가 아니라 시장 공통 움직임을 제거한 가격 잔차를 사용한다.
4. 학술/업계 prior: residual reversal은 short-term reversal과 statistical arbitrage literature에서 흔한 변형이다. 한국 KOSPI에서 지수 beta 보정 후 cross-sectional reversal을 공개 range로 제시한 자료는 제한적이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 2
7. 검증 비용 추정: 1.5시간
8. 한 줄 요약: 시장 움직임을 뺀 단기 과잉 하락의 반등 여부를 본다.

## Category B: Option A Variant (5)

### B1. 외국인 순매수 가격 비동조: 외국인이 샀는데 가격이 하락한 종목이 다음 기간 상대 강세
1. 가설: 최근 외국인 순매수 강도가 높지만 가격 수익률이 낮은 종목일수록 다음 5~21거래일 cross-sectional return이 높다.
2. 신호 정의: `foreign_flow_5d = sum(foreign_net_buy_shares_{t-4:t}) / max(sum(volume_{t-4:t}), eps)`; `signal_B1(code,t) = cs_z_t(foreign_flow_5d) - cs_z_t(ret_5d(code,t))`.
3. 옵션 A와의 차별점: 기관-외국인 차이가 아니라 외국인 flow와 contemporaneous price impact의 불일치를 사용한다.
4. 학술/업계 prior: order flow predictability와 informed trading literature prior가 있으며, Kaniel/Saar/Titman (2008)는 개인 투자자 flow와 단기 return을 다뤘다. 한국에서는 외국인 수급을 보는 실무 자료가 많지만 이 특정 비동조 형태의 공개 IC range는 제한적이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 3
7. 검증 비용 추정: 1.2시간
8. 한 줄 요약: 외국인 매수에도 가격이 눌린 종목의 후행 반응을 본다.

### B2. 기관 순매수 consistency: 기관이 여러 날 연속 순매수한 종목이 다음 기간 상대 강세
1. 가설: 최근 기관 순매수 일수 비율이 높은 종목일수록 다음 5~21거래일 cross-sectional return이 높다.
2. 신호 정의: `signal_B2(code,t) = cs_z_t(mean(1[institutional_net_buy_shares_s > 0], s=t-19:t))`.
3. 옵션 A와의 차별점: 순매수 금액/주식수 평균의 크기가 아니라 순매수 방향의 지속성과 breadth를 사용한다.
4. 학술/업계 prior: institutional herding과 flow persistence literature prior가 있다. Lakonishok/Shleifer/Vishny (1992)는 institutional trading herding을 다뤘다. 한국 기관 수급 persistence의 공개 대표 IC/Sharpe range는 표준화되어 있지 않다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 3
7. 검증 비용 추정: 1.0시간
8. 한 줄 요약: 기관이 며칠이나 같은 방향으로 샀는지를 크기 대신 사용한다.

### B3. 수급 충격 대비 평소 수급 변동성: 평소 대비 비정상적으로 큰 외국인/기관 순매수 종목이 다음 기간 상대 이동
1. 가설: 최근 1거래일 investor flow가 자기 과거 변동성 대비 큰 양수인 종목일수록 다음 1~5거래일 cross-sectional return이 높다.
2. 신호 정의: `flow_total_t = foreign_net_buy_shares_t + institutional_net_buy_shares_t`; `flow_z_own = flow_total_t / max(std(flow_total_{t-60:t-1}), eps)`; `signal_B3(code,t) = cs_z_t(flow_z_own)`.
3. 옵션 A와의 차별점: 기관과 외국인의 상대 차이가 아니라 해당 종목 자신의 평소 수급 noise 대비 abnormal shock을 사용한다.
4. 학술/업계 prior: order imbalance와 flow shock의 가격 영향 literature prior가 있다. Chordia/Roll/Subrahmanyam 계열의 order imbalance 연구와 연결된다. 현재 데이터는 실제 호가 imbalance가 아니라 투자자별 순매수 주식수라 proxy 한계가 있다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 3
7. 검증 비용 추정: 1.2시간
8. 한 줄 요약: 절대 수급보다 평소 대비 얼마나 이례적인 수급인지 본다.

### B4. 수급 불확실성 penalty: 외국인과 기관 flow 부호가 자주 뒤집히는 종목이 다음 기간 상대 약세
1. 가설: 최근 외국인+기관 합산 flow의 부호 전환 빈도가 높은 종목일수록 다음 5~21거래일 cross-sectional return이 낮다.
2. 신호 정의: `flow_total_s = foreign_net_buy_shares_s + institutional_net_buy_shares_s`; `flip_rate_20 = mean(1[sign(flow_total_s) != sign(flow_total_{s-1})], s=t-18:t)`; `signal_B4(code,t) = -cs_z_t(flip_rate_20)`.
3. 옵션 A와의 차별점: 한 시점의 기관-외국인 divergence level이 아니라 수급 방향 안정성/불안정성의 time-series pattern을 사용한다.
4. 학술/업계 prior: 직접적인 표준 factor는 아니지만 flow persistence, investor disagreement, liquidity provision literature와 관련된다. 한국에서 공개된 대표 IC range는 알려진 표준값이 없다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 4
7. 검증 비용 추정: 1.2시간
8. 한 줄 요약: 수급 방향이 자주 바뀌는 종목의 후속 상대 성과를 본다.

### B5. 쌍방 순매수 concentration: 외국인과 기관이 동시에 순매수하고 거래량 대비 비중도 큰 종목이 다음 기간 상대 강세
1. 가설: 최근 외국인과 기관이 같은 날 동시에 순매수한 비율과 거래량 대비 순매수 강도가 모두 높은 종목일수록 다음 5~21거래일 cross-sectional return이 높다.
2. 신호 정의: `co_buy_10 = mean(1[foreign_net_buy_shares_s > 0 and institutional_net_buy_shares_s > 0], s=t-9:t)`; `flow_intensity_10 = sum(max(foreign_net_buy_shares_s,0) + max(institutional_net_buy_shares_s,0), s=t-9:t) / max(sum(volume_s, s=t-9:t), eps)`; `signal_B5(code,t) = cs_z_t(co_buy_10) + cs_z_t(flow_intensity_10)`.
3. 옵션 A와의 차별점: 기관-외국인 괴리를 사는 것이 아니라 두 주체의 동시 매수 concurrence와 intensity를 사용한다.
4. 학술/업계 prior: institutional herding, common demand shocks, flow co-movement literature와 연결된다. 한국에서는 외국인/기관 동반 순매수 화면형 지표는 흔하나 정량 IC 공개 range는 제한적이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 3
7. 검증 비용 추정: 1.2시간
8. 한 줄 요약: 외국인과 기관이 서로 반대가 아니라 같은 방향으로 산 날의 밀도를 본다.

## Category C: Non-consensus / Less Explored (5)

### C1. 무수급 침묵 후 가격 drift: 외국인/기관 순매수 기록이 거의 0인 날이 누적된 종목은 다음 기간 상대 약세
1. 가설: 최근 외국인과 기관 순매수 주식수가 모두 0 또는 극소인 날의 비율이 높은 종목일수록 다음 5~21거래일 cross-sectional return이 낮다.
2. 신호 정의: `silent_day_s = 1[abs(foreign_net_buy_shares_s) + abs(institutional_net_buy_shares_s) <= q_small(code)]`; `signal_C1(code,t) = -cs_z_t(mean(silent_day_s, s=t-19:t))`, `q_small(code)`은 해당 종목 flow absolute sum의 과거 5% 분위수 또는 0.
3. 옵션 A와의 차별점: 수급 divergence의 방향이 아니라 관측 가능한 외국인/기관 참여 부재 자체를 사용한다.
4. 학술/업계 prior: no-trade, attention, liquidity neglect literature와 느슨하게 관련된다. KOSPI 투자자별 flow에서 `no flow days`를 직접 cross-sectional alpha로 쓰는 공개 사례는 제한적이다. 학술계가 덜 다룰 수 있는 이유는 0이 실제 무거래인지 reporting/rounding인지 구분이 어렵기 때문이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 5
7. 검증 비용 추정: 1.5시간
8. 한 줄 요약: 수급 신호의 방향이 아니라 수급 관측 부재를 정보로 취급한다.

### C2. 가격제한폭 근접 후 후유증: 상한가/하한가 근접 다음날의 cross-sectional continuation 또는 reversal
1. 가설: 전일 수익률이 한국 가격제한폭에 근접한 종목은 다음 1~5거래일에 일반 종목과 다른 상대 수익률 패턴을 보인다.
2. 신호 정의: `limit_up_proxy = 1[ret_1d(code,t) >= 0.27]`; `limit_down_proxy = 1[ret_1d(code,t) <= -0.27]`; `signal_C2(code,t) = limit_up_proxy - limit_down_proxy` 또는 별도 long/short dummy로 분리.
3. 옵션 A와의 차별점: investor flow가 아니라 한국 시장의 일일 가격제한 제도에서 생기는 discrete price event를 사용한다.
4. 학술/업계 prior: price limit, delayed price discovery, magnet effect literature가 있다. 한국/중국/대만 등 가격제한 시장 연구는 있으나, KOSPI 2020~2026 daily OHLCV만으로는 정확한 상하한가 여부를 완벽히 식별하지 못한다. 학술계가 덜 표준 factor화한 이유는 제도/종목별 예외 처리와 event sparsity 때문이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능하나 proxy 검증이다. 정확한 상하한가 플래그 수집 시 추가 수집 필요, 예상 2~4시간.
6. Mainstream 정도: 4
7. 검증 비용 추정: proxy IC 1.0시간, 정확 플래그 포함 3~5시간
8. 한 줄 요약: 한국 가격제한폭 근접 이벤트 이후의 단기 상대 패턴을 본다.

### C3. KOSPI 급락일 저항력: 시장 급락일에 덜 빠진 종목이 다음 기간 상대 강세
1. 가설: KOSPI가 큰 폭으로 하락한 날에 상대적으로 덜 하락한 종목일수록 다음 5~21거래일 cross-sectional return이 높다.
2. 신호 정의: `stress_day_t = 1[mkt_ret_1d(t) <= quantile(mkt_ret_1d, 10% rolling or full-sample pre-t)]`; `signal_C3(code,t) = cs_z_t(ret_1d(code,t) - beta_60(code,t) * mkt_ret_1d(t))` only when `stress_day_t=1`, otherwise missing or carry no signal.
3. 옵션 A와의 차별점: 수급 divergence가 아니라 시장 스트레스 조건에서의 상대 가격 탄력성을 사용한다.
4. 학술/업계 prior: downside beta, crash resilience, quality/defensive behavior literature와 관련된다. 일반 low beta와 겹치지만 급락일 conditional cross-section이라는 점이 다르다. 한국에서 이 조건부 신호만의 공개 대표 IC range는 제한적이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 4
7. 검증 비용 추정: 1.5시간
8. 한 줄 요약: 평상시가 아니라 KOSPI 급락일의 상대 저항력을 따로 측정한다.

### C4. 거래대금 regime jump: 장기 저거래 종목의 갑작스러운 거래대금 체제 전환 후 후속 drift
1. 가설: 장기적으로 거래대금이 낮던 종목에서 최근 거래대금이 구조적으로 상승한 경우 다음 5~21거래일 cross-sectional return이 높다.
2. 신호 정의: `dvol_jump = log(mean(dvol_{t-4:t}) / mean(dvol_{t-124:t-25}))`; `low_base = -cs_z_t(log(mean(dvol_{t-124:t-25})))`; `signal_C4(code,t) = cs_z_t(dvol_jump) + cs_z_t(low_base)`.
3. 옵션 A와의 차별점: investor flow의 매수/매도가 아니라 관심도/거래 가능성의 regime change를 사용한다.
4. 학술/업계 prior: attention, liquidity shocks, volume breakout literature와 관련되지만 전통 factor로 정착된 형태는 아니다. 학술계가 덜 다룰 수 있는 이유는 news/event 미관측 confounding과 microcap 처리 때문이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 4
7. 검증 비용 추정: 1.2시간
8. 한 줄 요약: 조용하던 종목의 거래대금 체제 전환을 관심도 변화 proxy로 본다.

### C5. 유니버스 내부 동조 붕괴: 같은 날 시장과 반대로 움직인 종목의 후속 상대 성과
1. 가설: KOSPI 상승일에 하락하거나 KOSPI 하락일에 상승한 종목은 다음 1~5거래일에 별도 cross-sectional reversal 또는 continuation 패턴을 보인다.
2. 신호 정의: `anti_mkt = -sign(ret_1d(code,t) * mkt_ret_1d(t)) * abs(ret_1d(code,t))`; `signal_C5(code,t) = cs_z_t(anti_mkt)`, 단 `abs(mkt_ret_1d(t))`가 일정 임계값 이상인 날만 사용 가능.
3. 옵션 A와의 차별점: 투자자별 flow가 아니라 시장 공통 방향과 개별 종목 방향의 sign disagreement를 사용한다.
4. 학술/업계 prior: residual return, dispersion, idiosyncratic shock literature와 관련되지만 이산적인 sign-disagreement 신호는 덜 표준화되어 있다. 학술계가 덜 다룰 수 있는 이유는 일반 residual reversal과 겹치고, 명확한 경제적 라벨링이 어렵기 때문이다.
5. 가용 데이터로 검증 가능 여부: 본 PR 데이터로 즉시 가능.
6. Mainstream 정도: 5
7. 검증 비용 추정: 1.2시간
8. 한 줄 요약: 시장 방향과 반대로 움직인 개별 종목의 단기 후속 패턴을 본다.

## Cross-cutting Notes
- 같은 데이터 의존성을 공유하는 그룹:
  - OHLCV만 사용: A1, A2, A3, A4, A5, A6, A7, A8, A9, C2, C4
  - OHLCV + KOSPI 지수 사용: A10, C3, C5
  - investor flow + OHLCV 사용: B1, B3, B5
  - investor flow만 또는 거의 flow 중심: B2, B4, C1
- 추가 수집이 필요한 가설들의 의존성:
  - C2는 proxy 검증은 즉시 가능하지만 정확한 상한가/하한가 플래그 또는 종목별 기준가/가격제한 예외를 쓰려면 추가 수집이 필요할 수 있다.
  - 본 20개 중 펀더멘털, 뉴스, 공시, 시가총액, 산업분류, intraday, 파생/외환 데이터가 필수인 가설은 포함하지 않았다.
- 사용자 후속 평가 시 참고할 만한 비교축:
  - 예상 turnover: A2, A6, A8, B3, C2, C5는 짧은 horizon 후보라 turnover가 높을 수 있다. A1, A3, A4, A5, A9는 상대적으로 느린 후보로 분류 가능하다.
  - capacity proxy: A4, A5, C4는 저거래대금/비유동성 노출이 직접 포함되어 capacity와 비용 검토가 별도로 필요하다.
  - 데이터 해석 risk: C1은 0 flow가 실제 참여 부재인지 reporting artifact인지 확인 축이 필요하다. C2는 가격제한폭 event proxy 정확도 확인 축이 필요하다.
  - Option A와의 거리: A군은 대부분 가격/거래량 anomaly이고, B군은 investor flow를 쓰되 divergence_5d 평균 차이와 다른 정보 구조를 사용한다. C군은 제도, 침묵, regime, stress condition, market sign disagreement처럼 비표준 조건을 사용한다.

## Gate
Generation only complete. 다음 단계 (사람 평가 + 별도 세션 steel-man 검토) 사용자 결정.
