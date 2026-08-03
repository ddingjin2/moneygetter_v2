# QLD Realistic Refit

- Analysis date: 2026-05-31.
- Price horizon: 2020-01-02 to 2026-05-28 open-to-open forward returns, using 2026-05-29 open as the final exit price.
- Benchmark: QLD buy-and-hold, yfinance adjusted OHLCV.
- Strategy universe: Nasdaq 100 PIT-lite expanded universe from current constituents plus Wikipedia constituent-change history.
- Data fetched: 277 requested tickers, 201 with yfinance price history, 76 unavailable mostly due delisting, acquisition, or ticker retirement.
- Realism model for final grid: 30 bps base trading cost, additional 10 bps slippage, financing at 13-week T-bill proxy plus 2% spread, 4% annual tax/implementation drag, leverage grid from 1.0x to 2.5x.
- Caveat: this is still not production-grade PIT. Missing delisted/acquired price histories remain a survivorship/data-availability hole.

## Why The Previous QLD Challenger Changed

The previous best candidate used the current Nasdaq 100 universe only. That allowed stocks that were not yet Nasdaq 100 members to appear in earlier historical ranks. After applying a PIT-lite membership mask and adding available historical removed constituents, the same A4 liquidity-size effect no longer beats QLD.

## Refit Result

No candidate beat QLD buy-and-hold after adding the realism layer.

The best full-period realistic candidate across 9 OHLCV signals, long-only decile/quintile portfolios, 5-day/20-day rebalances, and 1.0x-2.5x leverage was:

- `US_A5_illiquidity`, long-only decile, 20-day rebalance, 30 bps base cost, 2.05x leverage
- Financing: 13-week T-bill proxy + 2% spread
- Additional slippage: 10 bps
- Tax/implementation drag: 4% annually

Artifact: `data/cache/us/nasdaq100_pitlite/strategy_compare/nasdaq100_pitlite_expanded_realistic_best_refit.parquet`

| period | strategy_cagr | QLD_cagr | excess_cagr | strategy_sharpe | QLD_sharpe | strategy_mdd | QLD_mdd | strategy_total | QLD_total |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Full | 0.1880 | 0.3383 | -0.1503 | 0.5900 | 0.8437 | -0.8083 | -0.6433 | 2.0034 | 5.4277 |
| 2020-2021 | 0.5823 | 0.6995 | -0.1172 | 1.0728 | 1.2853 | -0.5496 | -0.5118 | 1.5081 | 1.8943 |
| 2022 | -0.7770 | -0.6027 | -0.1743 | -1.5897 | -1.1004 | -0.7948 | -0.6354 | -0.7757 | -0.6013 |
| 2023-2024 | 0.7537 | 0.7629 | -0.0092 | 1.4846 | 1.7593 | -0.3355 | -0.2972 | 2.0616 | 2.0938 |
| 2025-2026 YTD | 0.4907 | 0.5252 | -0.0345 | 1.0334 | 1.1446 | -0.4797 | -0.4405 | 0.7439 | 0.8004 |

## A4 After Realism

The former A4 candidate is no longer a QLD challenger after PIT-lite expansion.

Best realistic A4 configuration:

- `US_A4_liquidity_size`, long-only decile, 20-day rebalance, 30 bps base cost
- 2.5x leverage
- Financing: 13-week T-bill proxy + 2% spread
- Additional slippage: 10 bps
- Tax/implementation drag: 4% annually

| period | strategy_cagr | QLD_cagr | excess_cagr | strategy_sharpe | QLD_sharpe | strategy_mdd | QLD_mdd | strategy_total | QLD_total |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Full | 0.1627 | 0.3383 | -0.1756 | 0.5553 | 0.8437 | -0.4791 | -0.6433 | 1.6184 | 5.4277 |
| 2020-2021 | 0.6396 | 0.6995 | -0.0599 | 1.2848 | 1.2853 | -0.2852 | -0.5118 | 1.6934 | 1.8943 |
| 2022 | -0.2346 | -0.6027 | 0.3682 | -0.1953 | -1.1004 | -0.4084 | -0.6354 | -0.2338 | -0.6013 |
| 2023-2024 | 0.3081 | 0.7629 | -0.4548 | 0.8412 | 1.7593 | -0.2816 | -0.2972 | 0.7074 | 2.0938 |
| 2025-2026 YTD | -0.1920 | 0.5252 | -0.7172 | -0.2534 | 1.1446 | -0.4118 | -0.4405 | -0.2569 | 0.8004 |

## Capacity Check

Capacity estimate uses A4 rebalance trades and 60-day average dollar volume. It answers: how much strategy capital can trade while each rebalance trade stays under a given ADV participation rate.

| participation | min_capacity_usd | p05_capacity_usd | median_capacity_usd |
|:--|--:|--:|--:|
| 1% ADV | 3,306,785 | 11,395,825 | 18,794,562 |
| 2% ADV | 6,613,570 | 22,791,651 | 37,589,123 |
| 5% ADV | 16,533,925 | 56,979,126 | 93,972,808 |
| 10% ADV | 33,067,849 | 113,958,253 | 187,945,616 |

Interpretation: capacity is not the main reason the QLD challenge fails. The main issue is that the alpha weakens materially once the universe is made closer to point-in-time.

## Artifacts

- Expanded PIT-lite OHLCV: `data/processed/us_nasdaq100_pitlite_ohlcv.parquet`
- Expanded PIT-lite universe: `data/cache/us/nasdaq100_pitlite/universe/us_universe.parquet`
- Nasdaq 100 change history: `data/cache/us/nasdaq100_pitlite/universe/nasdaq100_changes.parquet`
- Realistic all-signal grid: `data/cache/us/nasdaq100_pitlite/strategy_compare/nasdaq100_pitlite_expanded_all_signal_realistic_grid.parquet`
- A4 realism grid: `data/cache/us/nasdaq100_pitlite/strategy_compare/nasdaq100_a4_pitlite_expanded_realism_grid.parquet`
- Best realistic refit returns: `data/cache/us/nasdaq100_pitlite/strategy_compare/nasdaq100_pitlite_expanded_realistic_best_refit.parquet`

## Verdict

After including financing, tax/implementation drag, slippage, capacity, and a PIT-lite Nasdaq 100 universe, the QLD-beating result does not survive.

The current research conclusion changes from "A4 1.5x looks better than QLD" to:

> No QLD-beating strategy was found under the realistic PIT-lite refit.

The next valid path is not more parameter fitting on this dataset. It is getting better point-in-time index membership and delisted security data, then rerunning the same grid.
