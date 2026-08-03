# PR-7.A.X Step 8.1 Signal Catalog

## Scope
- Step 8.1 only: common signal infrastructure and batch signal calculation.
- No hypothesis evaluation, ranking, backtest, or Step 8.2 batch IC measurement.
- C2 uses proxy coding: +1 if `ret_1d >= 0.27`, -1 if `ret_1d <= -0.27`, else 0.
- Trading halt masking reuses `v2/data/cache/price_market_cap_full/_trading_status.parquet`.

## Signal Catalog
| signal_id | name | requires_flow | requires_kospi | min_history_days | expected_horizons | formula_text |
| --- | --- | --- | --- | --- | --- | --- |
| A0_baseline | Option A divergence_5d baseline | True | False | 5 | 5 | divergence_5d = institutional_5d_mean - foreign_5d_mean |
| A1 | 12-1개월 가격 모멘텀 | False | False | 252 | 5,21 | signal_A1(code,t) = cs_z_t(close_{t-21} / close_{t-252} - 1) |
| A2 | 1개월 단기 reversal | False | False | 21 | 1,5 | signal_A2(code,t) = -cs_z_t(close_t / close_{t-21} - 1) |
| A3 | 저변동성 anomaly | False | False | 60 | 21 | signal_A3(code,t) = -cs_z_t(std(ret_1d(code,t-59:t))) |
| A4 | 거래대금 size proxy | False | False | 60 | 21 | signal_A4(code,t) = -cs_z_t(log(mean(dvol(code,t-59:t)))) |
| A5 | Amihud illiquidity | False | False | 60 | 21 | signal_A5(code,t) = cs_z_t(mean(abs(ret_1d(code,s)) / max(dvol(code,s), eps), s=t-59:t)) |
| A6 | 거래량 충격 reversal | False | False | 60 | 1,5 | signal_A6(code,t) = -cs_z_t(ret_5d(code,t) * log(volume_t / mean(volume_{t-60:t-6}))) |
| A7 | 가격-거래량 divergence | False | False | 25 | 5,21 | signal_A7(code,t) = -cs_z_t(ret_20d(code,t) * (-cs_z_t(log(mean(volume_{t-4:t}) / mean(volume_{t-24:t-5}))))) |
| A8 | overnight gap reversal proxy | False | False | 1 | 1 | signal_A8(code,t) = -cs_z_t((open_t / close_{t-1} - 1) - (close_t / open_t - 1)) |
| A9 | 52주 고점 proximity | False | False | 252 | 21 | signal_A9(code,t) = cs_z_t(close_t / max(high_{t-251:t})) |
| A10 | 시장 beta residual reversal | False | True | 60 | 5 | signal_A10(code,t) = -cs_z_t(resid_5d) |
| B1 | 외국인 순매수 가격 비동조 | True | False | 5 | 5,21 | signal_B1(code,t) = cs_z_t(foreign_flow_5d) - cs_z_t(ret_5d(code,t)) |
| B2 | 기관 순매수 consistency | True | False | 20 | 5,21 | signal_B2(code,t) = cs_z_t(mean(1[institutional_net_buy_shares_s > 0], s=t-19:t)) |
| B3 | 수급 충격 대비 평소 수급 변동성 | True | False | 60 | 1,5 | signal_B3(code,t) = cs_z_t(flow_total_t / max(std(flow_total_{t-60:t-1}), eps)) |
| B4 | 수급 불확실성 penalty | True | False | 20 | 5,21 | signal_B4(code,t) = -cs_z_t(flip_rate_20) |
| B5 | 쌍방 순매수 concentration | True | False | 10 | 5,21 | signal_B5(code,t) = cs_z_t(co_buy_10) + cs_z_t(flow_intensity_10) |
| C1 | 무수급 침묵 후 가격 drift | True | False | 20 | 5,21 | signal_C1(code,t) = -cs_z_t(mean(silent_day_s, s=t-19:t)) |
| C2 | 가격제한폭 근접 후 후유증 | False | False | 1 | 1,5 | signal_C2(code,t) = 1[ret_1d >= 0.27] - 1[ret_1d <= -0.27] |
| C3 | KOSPI 급락일 저항력 | False | True | 60 | 5,21 | signal_C3(code,t) = cs_z_t(ret_1d(code,t) - beta_60(code,t) * mkt_ret_1d(t)) on stress days |
| C4 | 거래대금 regime jump | False | False | 125 | 5,21 | signal_C4(code,t) = cs_z_t(dvol_jump) + cs_z_t(low_base) |
| C5 | 유니버스 내부 동조 붕괴 | False | True | 60 | 1,5 | signal_C5(code,t) = cs_z_t(anti_mkt) where anti_mkt = -sign(ret_1d * mkt_ret_1d) * abs(ret_1d), defined only on days where abs(mkt_ret_1d(t)) >= expanding_median(abs(mkt_ret_1d), min_periods=60).shift(1); else NaN |

## Sanity Check
| signal_id | total_pairs | non_nan_ratio | cs_z_mean | cs_z_std | cs_z_min | cs_z_p01 | cs_z_p99 | cs_z_max | mean_cross_section_dispersion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0_baseline | 1164383 | 0.991687 | -0.000000 | 1.000000 | -27.626142 | -2.304720 | 2.291998 | 27.902699 | 126951.941429 |
| A1 | 1164383 | 0.825627 | -0.000000 | 1.000000 | -2.702047 | -1.387512 | 3.912051 | 23.390589 | 0.524746 |
| A2 | 1164383 | 0.985427 | -0.000000 | 1.000000 | -28.017688 | -3.590812 | 1.859968 | 8.734815 | 0.149967 |
| A3 | 1164383 | 0.958381 | 0.000000 | 1.000000 | -26.201570 | -3.450523 | 1.598493 | 2.412083 | 0.016135 |
| A4 | 1197418 | 0.905728 | -0.000000 | 1.000000 | -4.319120 | -2.311607 | 2.067515 | 4.628568 | 1.977738 |
| A5 | 1164383 | 0.930747 | 0.000000 | 1.000000 | -0.541882 | -0.460676 | 3.232925 | 27.178664 | 0.000000 |
| A6 | 1164383 | 0.944895 | 0.000000 | 1.000000 | -27.747724 | -3.421989 | 1.202754 | 27.599547 | 0.144465 |
| A7 | 1164383 | 0.970274 | 0.000000 | 1.000000 | -27.520884 | -1.851968 | 3.710786 | 27.924936 | 0.193259 |
| A8 | 1164383 | 0.999306 | -0.000000 | 1.000000 | -28.104019 | -2.654305 | 2.789424 | 18.524898 | 0.032501 |
| A9 | 1164383 | 0.826317 | 0.000000 | 1.000000 | -4.473979 | -2.811126 | 1.837109 | 2.789063 | 0.154168 |
| A10 | 1164383 | 0.958381 | 0.000000 | 1.000000 | -27.975681 | -3.549005 | 2.115348 | 14.061353 | 0.068672 |
| B1 | 1164383 | 0.978190 | -0.000000 | 1.000000 | -26.982228 | -2.649920 | 2.251589 | 26.998228 | 0.138874 |
| B2 | 1164383 | 0.981278 | 0.000000 | 1.000000 | -3.212236 | -2.410389 | 2.366870 | 3.741894 | 0.194384 |
| B3 | 1164383 | 0.942935 | -0.000000 | 1.000000 | -27.885733 | -2.723721 | 2.767201 | 27.978989 | 1.664840 |
| B4 | 1164383 | 0.981278 | 0.000000 | 1.000000 | -3.735544 | -2.072587 | 2.842128 | 3.337914 | 0.150278 |
| B5 | 1164383 | 0.976026 | 0.000000 | 1.000000 | -1.991388 | -1.534087 | 2.892735 | 26.761016 | 0.213013 |
| C1 | 1164383 | 0.981278 | -0.000000 | 1.000000 | -10.178367 | -5.843656 | 0.759868 | 0.885187 | 0.133313 |
| C2 | 1164383 | 0.999306 | 0.000000 | 1.000000 | -28.354894 | -0.096738 | 0.036322 | 28.407745 | 0.031510 |
| C3 | 1164383 | 0.105796 | -0.000000 | 1.000000 | -11.560972 | -2.306231 | 3.133885 | 15.178890 | 0.024422 |
| C4 | 1164383 | 0.879656 | 0.000000 | 1.000000 | -5.970874 | -2.162711 | 2.417035 | 7.501495 | 2.318233 |
| C5 | 1164383 | 0.518548 | 0.000000 | 1.000000 | -27.864289 | -2.860999 | 2.538095 | 14.006102 | 0.027982 |

## A0_baseline Regression Check
- Status: RED
- Step 6 prompt 5d IC: -0.009400
- Step 6 cache 5d IC: -0.009385
- Current 5d IC: -0.029052
- Absolute diff vs prompt: 0.019652
- IC dates: 1482
- GREEN rule: absolute diff vs prompt < 0.000100

## Step 8.2 Readiness
- Signals written: 20 raw parquet files and 20 cross-sectional z-score parquet files under `v2/data/cache/signals_batch/`.
- Sanity abnormal items: None
- If A0_baseline status is RED, stop before Step 8.2 and inspect baseline regression mismatch.
