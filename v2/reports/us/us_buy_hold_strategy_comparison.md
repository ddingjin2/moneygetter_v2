# US Buy & Hold Strategy Comparison

- Data refreshed through latest available US session before 2026-05-31: `2026-05-29`.
- S&P 500 cache: `798,207` OHLCV rows, `502` price files, benchmark `SPY`.
- Nasdaq 100 cache: `159,756` OHLCV rows, `102` price files including `QQQ`, benchmark `QQQ`.
- Source mode: `yfinance` prices plus current Wikipedia index constituents.
- Caveat: both universes are current-membership and survivorship-biased. Treat these as research-grade candidates, not production validation.

## Selection Rule

The comparison below uses daily net returns after transaction costs and compares each strategy with its benchmark ETF buy-and-hold on the same dates. Strategy and benchmark returns are aligned as open-to-open forward returns. The selected strategies use `30 bps` transaction costs unless noted.

## S&P 500 Candidate: A4/A1 60/40

Strategy:
- 60% `US_A4_liquidity_size`, long-only decile, 20-day rebalance, 30 bps
- 40% `US_A1_12_1_momentum`, long-only decile, 20-day rebalance, 30 bps

Daily returns artifact: `data/cache/us/strategy_compare/sp500_a4_a1_60_40_20d_30bps.parquet`

| period | strategy_cagr | SPY_cagr | excess_cagr | strategy_sharpe | SPY_sharpe | strategy_mdd | SPY_mdd | strategy_total | SPY_total |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Full | 0.2776 | 0.1584 | 0.1192 | 1.4304 | 0.8531 | -0.2090 | -0.3205 | 3.7786 | 1.5565 |
| 2020-2021 | 0.3547 | 0.2322 | 0.1225 | 1.8915 | 1.0408 | -0.0777 | -0.3205 | 0.8374 | 0.5196 |
| 2022 | 0.0041 | -0.1806 | 0.1846 | 0.1337 | -0.7050 | -0.1726 | -0.2629 | 0.0041 | -0.1799 |
| 2023-2024 | 0.3423 | 0.2568 | 0.0855 | 1.9833 | 1.8192 | -0.1092 | -0.0959 | 0.7975 | 0.5767 |
| 2025-2026 YTD | 0.2999 | 0.2080 | 0.0919 | 1.4099 | 1.1074 | -0.2090 | -0.1977 | 0.4410 | 0.3011 |

Interpretation: this is the better full-period return/Sharpe S&P 500 candidate. It beats SPY CAGR in every subperiod, but its 2025-2026 YTD subperiod drawdown is slightly worse than SPY.

## S&P 500 Conservative Variant

Strategy:
- 25% `US_A4_liquidity_size`, long-only decile, 20-day rebalance, 30 bps
- 25% `US_A4_liquidity_size`, long-only decile, 5-day rebalance, 30 bps
- 25% `US_A1_12_1_momentum`, long-only decile, 20-day rebalance, 30 bps
- 25% `US_A3_low_volatility`, long-only decile, 20-day rebalance, 30 bps

Daily returns artifact: `data/cache/us/strategy_compare/sp500_a4_a1_lowvol_four_sleeve_30bps.parquet`

| period | strategy_cagr | SPY_cagr | excess_cagr | strategy_sharpe | SPY_sharpe | strategy_mdd | SPY_mdd | strategy_total | SPY_total |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Full | 0.2345 | 0.1584 | 0.0762 | 1.4131 | 0.8531 | -0.1808 | -0.3205 | 2.8392 | 1.5565 |
| 2020-2021 | 0.3582 | 0.2322 | 0.1259 | 2.0691 | 1.0408 | -0.0683 | -0.3205 | 0.8469 | 0.5196 |
| 2022 | -0.0022 | -0.1806 | 0.1783 | 0.0895 | -0.7050 | -0.1604 | -0.2629 | -0.0022 | -0.1799 |
| 2023-2024 | 0.2633 | 0.2568 | 0.0065 | 1.8716 | 1.8192 | -0.0976 | -0.0959 | 0.5931 | 0.5767 |
| 2025-2026 YTD | 0.2125 | 0.2080 | 0.0044 | 1.2468 | 1.1074 | -0.1741 | -0.1977 | 0.3078 | 0.3011 |

Interpretation: this is the stricter S&P 500 candidate if subperiod drawdown must be no worse than SPY. The 2025-2026 YTD edge is thin, so it needs out-of-sample monitoring.

## Nasdaq 100 Candidate: A4 Liquidity Size

Strategy:
- 100% `US_A4_liquidity_size`, long-only decile, 20-day rebalance, 30 bps

Daily returns artifact: `data/cache/us/nasdaq100/strategy_compare/nasdaq100_a4_liquidity_size_20d_30bps.parquet`

| period | strategy_cagr | QQQ_cagr | excess_cagr | strategy_sharpe | QQQ_sharpe | strategy_mdd | QQQ_mdd | strategy_total | QQQ_total |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Full | 0.4573 | 0.2206 | 0.2367 | 1.7534 | 0.9415 | -0.2711 | -0.3669 | 10.0715 | 2.5710 |
| 2020-2021 | 0.7010 | 0.3706 | 0.3304 | 2.4769 | 1.3416 | -0.0899 | -0.2756 | 1.8995 | 0.8809 |
| 2022 | -0.2072 | -0.3229 | 0.1157 | -0.5574 | -1.0482 | -0.2561 | -0.3625 | -0.2065 | -0.3218 |
| 2023-2024 | 0.7414 | 0.3943 | 0.3470 | 2.7995 | 1.9446 | -0.1192 | -0.1558 | 2.0191 | 0.9391 |
| 2025-2026 YTD | 0.3975 | 0.3017 | 0.0958 | 1.9192 | 1.2606 | -0.1213 | -0.2417 | 0.5938 | 0.4437 |

Interpretation: this is the strongest Nasdaq 100 buy-and-hold challenger. It fails the existing absolute subperiod gate because 2022 Sharpe is negative, but it still outperforms QQQ in 2022 and every other subperiod on CAGR, Sharpe, and drawdown.

## Verdict

- S&P 500: buy-and-hold can be beaten in this research run. Use `A4/A1 60/40` for return focus; use the conservative 4-sleeve blend if subperiod drawdown discipline matters more.
- Nasdaq 100: `US_A4_liquidity_size` long-only decile, 20-day rebalance, 30 bps beats QQQ strongly in this run.
- Do not promote either result without point-in-time index membership, delisting-inclusive history, and corporate-action validation.
