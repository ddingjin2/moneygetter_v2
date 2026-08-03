# QLD Buy & Hold Comparison

- Analysis date: 2026-05-31.
- Price horizon: 2020-01-02 to 2026-05-28 open-to-open forward returns, using the 2026-05-29 open as the final exit price.
- QLD source: yfinance adjusted OHLCV.
- Strategy source: current-membership Nasdaq 100 research cache, yfinance prices, 30 bps transaction costs.
- Caveat: Nasdaq 100 universe is survivorship-biased. Leveraged strategy rows are simulations, not live executable ETF returns.

## QLD Context

ProShares says QLD targets 2x the daily performance of the Nasdaq-100 Index before fees and expenses. It also warns that for holding periods longer than one day, returns may be higher or lower than the daily target and differences may be significant. The current net expense ratio shown on ProShares is 0.95%.

## Full-Period Summary

| strategy | CAGR | total_return | Sharpe | ann_vol | max_dd | excess_CAGR_vs_QLD |
|:--|--:|--:|--:|--:|--:|--:|
| Nasdaq100 A4 liquidity size, 2.0x simulated | 1.0147 | 86.5612 | 1.7534 | 0.4599 | -0.5040 | 0.6764 |
| Nasdaq100 A4 liquidity size, 1.5x simulated | 0.7247 | 31.4657 | 1.7534 | 0.3449 | -0.3876 | 0.3864 |
| Nasdaq100 A4 liquidity size, 1.25x simulated | 0.5880 | 18.1587 | 1.7534 | 0.2874 | -0.3310 | 0.2497 |
| Nasdaq100 A4 liquidity size, unlevered | 0.4573 | 10.0715 | 1.7534 | 0.2299 | -0.2711 | 0.1190 |
| QLD buy & hold | 0.3383 | 5.4277 | 0.8437 | 0.4872 | -0.6433 | 0.0000 |
| S&P 500 A4/A1 60/40 | 0.2776 | 3.7786 | 1.4304 | 0.1831 | -0.2090 | -0.0607 |
| S&P 500 conservative 4-sleeve | 0.2345 | 2.8392 | 1.4131 | 0.1580 | -0.1808 | -0.1038 |
| QQQ buy & hold | 0.2206 | 2.5710 | 0.9415 | 0.2433 | -0.3669 | -0.1177 |

## Best Unlevered Candidate vs QLD

Candidate: `US_A4_liquidity_size`, Nasdaq 100, long-only decile, 20-day rebalance, 30 bps.

Artifact: `data/cache/us/nasdaq100/strategy_compare/nasdaq100_a4_liquidity_size_20d_30bps.parquet`

| period | strategy_cagr | QLD_cagr | excess_cagr | strategy_sharpe | QLD_sharpe | strategy_mdd | QLD_mdd | strategy_total | QLD_total |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Full | 0.4573 | 0.3383 | 0.1190 | 1.7534 | 0.8437 | -0.2711 | -0.6433 | 10.0715 | 5.4277 |
| 2020-2021 | 0.7010 | 0.6995 | 0.0015 | 2.4769 | 1.2853 | -0.0899 | -0.5118 | 1.8995 | 1.8943 |
| 2022 | -0.2072 | -0.6027 | 0.3955 | -0.5574 | -1.1004 | -0.2561 | -0.6354 | -0.2065 | -0.6013 |
| 2023-2024 | 0.7414 | 0.7629 | -0.0215 | 2.7995 | 1.7593 | -0.1192 | -0.2972 | 2.0191 | 2.0938 |
| 2025-2026 YTD | 0.3975 | 0.5252 | -0.1278 | 1.9192 | 1.1446 | -0.1213 | -0.4405 | 0.5938 | 0.8004 |

Interpretation: unlevered A4 beats QLD over the full period with much lower drawdown, but QLD still wins in the strong bull subperiods 2023-2024 and 2025-2026 YTD on absolute CAGR.

## Robust Leveraged Candidate

Candidate: 1.5x simulated Nasdaq100 A4 liquidity size, long-only decile, 20-day rebalance, 30 bps. This scales strategy daily returns by 1.5x before adding any explicit financing drag.

Artifact: `data/cache/us/nasdaq100/strategy_compare/nasdaq100_a4_liquidity_size_1_5x_20d_30bps_no_financing.parquet`

| period | strategy_cagr | QLD_cagr | excess_cagr | strategy_sharpe | QLD_sharpe | strategy_mdd | QLD_mdd | strategy_total | QLD_total |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Full | 0.7247 | 0.3383 | 0.3864 | 1.7534 | 0.8437 | -0.3876 | -0.6433 | 31.4657 | 5.4277 |
| 2020-2021 | 1.1765 | 0.6995 | 0.4770 | 2.4769 | 1.2853 | -0.1331 | -0.5118 | 3.7519 | 1.8943 |
| 2022 | -0.3211 | -0.6027 | 0.2816 | -0.5574 | -1.1004 | -0.3674 | -0.6354 | -0.3201 | -0.6013 |
| 2023-2024 | 1.2619 | 0.7629 | 0.4990 | 2.7995 | 1.7593 | -0.1744 | -0.2972 | 4.0832 | 2.0938 |
| 2025-2026 YTD | 0.6311 | 0.5252 | 0.1059 | 1.9192 | 1.1446 | -0.1803 | -0.4405 | 0.9768 | 0.8004 |

Financing sensitivity: with 1.5x leverage, even if the borrowed 0.5x sleeve pays 12% annual drag, full-period CAGR is still 0.6245, max drawdown is -0.4245, and the weakest subperiod CAGR edge versus QLD remains +0.0111.

## Verdict

- Yes, there are candidates that beat QLD buy-and-hold in this research run.
- Best practical unlevered candidate: Nasdaq100 A4 liquidity size. It has higher full-period CAGR and far lower drawdown than QLD, but can lag QLD in strong uptrends.
- Best QLD-challenger candidate: 1.5x Nasdaq100 A4 liquidity size. It beats QLD in every tested subperiod on CAGR and drawdown in the simulation, with a large funding-cost cushion.
- Production caveat: the 1.5x result requires real execution modeling: financing, margin rules, tax, capacity, rebalancing slippage, and point-in-time Nasdaq 100 membership.
