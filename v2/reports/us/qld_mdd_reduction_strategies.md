# QLD MDD Reduction Strategies

- Analysis date: 2026-05-31.
- Data: yfinance adjusted QLD, QQQ, and ^IRX prices through 2026-05-29. Returns are open-to-open forward returns through 2026-05-28.
- Benchmark: QLD buy-and-hold, no tactical trading cost.
- Tactical strategy cost: 10 bps on notional weight changes. Cash sleeve earns the prior-day 13-week T-bill proxy from ^IRX.
- Signal timing: QQQ close/SMA and QLD realized volatility are shifted by one trading day, so decisions use information known before the entry open.
- QLD reference: ProShares Ultra QQQ targets 2x the daily performance of the Nasdaq-100 before fees and expenses.

## Answer

The best MDD-reduction candidate from this run is `QLD_MA175_vol20_target45_cash_10bps`:

- Rule: hold QLD only when prior-day QQQ close is above its 175-day moving average; when risk-on, cap QLD exposure with a 20-day realized-volatility target of 45%; otherwise hold T-bill cash.
- 2020-2026 result: CAGR 37.6% vs QLD 33.8%, MDD -32.2% vs QLD -64.3%.
- Full QLD history check, 2007-2026: CAGR 23.3% vs QLD 25.6%, MDD -41.6% vs QLD -82.5%.

Interpretation: it improves drawdown dramatically. The 2020-2026 CAGR also beats QLD, but the longer 2007-2026 check says the honest expectation should be slightly lower CAGR than QLD with roughly half the drawdown.

## 2020-2026 Comparison

| strategy | family | CAGR | Sharpe | ann vol | MDD | MDD improve pp | CAGR gap pp | avg exposure | ann turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| QLD_buy_hold | None | 33.8% | 0.84 | 48.7% | -64.3% | 0.0 | 0.0 | 100.0% | 0.00 |
| QLD_MA175_cash_10bps | trend | 39.6% | 1.10 | 36.3% | -42.8% | 21.5 | 5.8 | 78.8% | 4.23 |
| QLD_MA200_cash_10bps | trend | 34.6% | 1.00 | 36.6% | -42.8% | 21.5 | 0.7 | 79.5% | 3.92 |
| QLD_MA175_vol20_target45_cash_10bps | trend_vol | 37.6% | 1.13 | 33.2% | -32.2% | 32.1 | 3.8 | 75.6% | 4.81 |
| QLD_MA175_vol20_target30_cash_10bps | trend_vol | 32.3% | 1.16 | 27.4% | -27.0% | 37.3 | -1.5 | 65.2% | 5.98 |
| QLD_MA175_vol20_target20_cash_10bps | trend_vol | 23.9% | 1.17 | 20.0% | -19.7% | 44.6 | -9.9 | 47.9% | 6.37 |

## 2007-2026 Robustness Check

| strategy | family | CAGR | Sharpe | ann vol | MDD | MDD improve pp | CAGR gap pp | avg exposure | ann turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| QLD_buy_hold | None | 25.6% | 0.74 | 44.0% | -82.5% | 0.0 | 0.0 | 100.0% | 0.00 |
| QLD_MA175_cash_10bps | trend | 23.9% | 0.85 | 31.1% | -42.8% | 39.7 | -1.6 | 79.4% | 6.04 |
| QLD_MA200_cash_10bps | trend | 20.3% | 0.75 | 31.5% | -47.9% | 34.5 | -5.3 | 79.7% | 6.14 |
| QLD_MA175_vol20_target45_cash_10bps | trend_vol | 23.3% | 0.86 | 29.6% | -41.6% | 40.9 | -2.2 | 77.8% | 6.30 |
| QLD_MA175_vol20_target30_cash_10bps | trend_vol | 21.0% | 0.87 | 25.6% | -39.6% | 42.9 | -4.5 | 70.4% | 7.07 |
| QLD_MA175_vol20_target20_cash_10bps | trend_vol | 17.0% | 0.91 | 19.4% | -29.7% | 52.8 | -8.6 | 55.2% | 7.43 |

## Pre-2020 Selection Check

This section asks whether similar rules would have looked attractive before the 2020-2026 test window.

| strategy | family | CAGR | Sharpe | ann vol | MDD | MDD improve pp | CAGR gap pp | avg exposure | ann turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| QLD_buy_hold | None | 21.7% | 0.68 | 41.5% | -82.5% | 0.0 | 0.0 | 100.0% | 0.00 |
| QLD_MA175_cash_10bps | trend | 16.9% | 0.69 | 28.2% | -41.6% | 40.9 | -4.8 | 79.7% | 7.01 |
| QLD_MA200_cash_10bps | trend | 13.8% | 0.60 | 28.7% | -47.9% | 34.5 | -7.9 | 79.7% | 7.32 |
| QLD_MA175_vol20_target45_cash_10bps | trend_vol | 16.8% | 0.70 | 27.7% | -41.6% | 40.9 | -4.9 | 78.9% | 7.12 |
| QLD_MA175_vol20_target30_cash_10bps | trend_vol | 15.8% | 0.72 | 24.7% | -39.6% | 42.9 | -5.8 | 73.0% | 7.69 |
| QLD_MA175_vol20_target20_cash_10bps | trend_vol | 13.7% | 0.77 | 19.1% | -29.7% | 52.8 | -8.0 | 58.8% | 8.01 |

## Balanced Full-History Candidates

These keep full-history CAGR above 20% while improving QLD MDD by at least 25 percentage points.

| strategy | family | CAGR | Sharpe | ann vol | MDD | MDD improve pp | CAGR gap pp | avg exposure | ann turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| QLD_MA175_vol20_target45_cash_10bps | trend_vol | 23.3% | 0.86 | 29.6% | -41.6% | 40.9 | -2.2 | 77.8% | 6.30 |
| QLD_MA175_cash_10bps | trend | 23.9% | 0.85 | 31.1% | -42.8% | 39.7 | -1.6 | 79.4% | 6.04 |
| QLD_MA175_vol40_target45_cash_10bps | trend_vol | 23.3% | 0.86 | 29.6% | -42.3% | 40.2 | -2.2 | 77.5% | 5.97 |
| QLD_MA175_vol20_target40_cash_10bps | trend_vol | 22.9% | 0.86 | 28.8% | -41.8% | 40.6 | -2.7 | 76.5% | 6.50 |
| QLD_MA175_vol20_target30_cash_10bps | trend_vol | 21.0% | 0.87 | 25.6% | -39.6% | 42.9 | -4.5 | 70.4% | 7.07 |
| QLD_MA175_vol40_target40_cash_10bps | trend_vol | 22.9% | 0.86 | 28.8% | -43.1% | 39.3 | -2.7 | 76.2% | 5.86 |
| QLD_MA175_vol20_target35_cash_10bps | trend_vol | 22.0% | 0.86 | 27.6% | -41.8% | 40.7 | -3.5 | 74.3% | 6.75 |
| QLD_MA150_vol40_target40_cash_10bps | trend_vol | 21.8% | 0.84 | 28.3% | -41.4% | 41.0 | -3.8 | 76.5% | 6.34 |
| QLD_MA175_vol60_target45_cash_10bps | trend_vol | 22.3% | 0.83 | 29.6% | -43.1% | 39.4 | -3.2 | 77.1% | 5.92 |
| QLD_MA150_vol40_target45_cash_10bps | trend_vol | 22.1% | 0.83 | 29.1% | -43.2% | 39.3 | -3.4 | 77.8% | 6.46 |

## Defensive Full-History Candidates

These prioritize MDD below roughly 35%, accepting a larger return give-up.

| strategy | family | CAGR | Sharpe | ann vol | MDD | MDD improve pp | CAGR gap pp | avg exposure | ann turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| QLD_MA175_vol20_target20_cash_10bps | trend_vol | 17.0% | 0.91 | 19.4% | -29.7% | 52.8 | -8.6 | 55.2% | 7.43 |
| QLD_MA150_vol20_target20_cash_10bps | trend_vol | 16.2% | 0.87 | 19.3% | -31.4% | 51.1 | -9.4 | 55.5% | 7.62 |
| QLD_MA175_vol40_target20_cash_10bps | trend_vol | 15.7% | 0.86 | 19.0% | -33.1% | 49.4 | -9.9 | 52.6% | 5.39 |
| QLD_MA50_vol20_target45_cash_10bps | trend_vol | 15.0% | 0.67 | 26.1% | -32.7% | 49.7 | -10.6 | 68.2% | 15.71 |
| QLD_MA150_vol40_target20_cash_10bps | trend_vol | 14.9% | 0.84 | 18.7% | -32.8% | 49.7 | -10.6 | 52.8% | 5.65 |
| QLD_MA175_vol60_target20_cash_10bps | trend_vol | 14.9% | 0.84 | 18.7% | -33.3% | 49.2 | -10.7 | 50.9% | 4.64 |
| QLD_MA250_vol20_target20_cash_10bps | trend_vol | 14.6% | 0.80 | 19.6% | -34.3% | 48.1 | -10.9 | 55.0% | 6.87 |
| QLD_MA50_vol20_target40_cash_10bps | trend_vol | 14.5% | 0.66 | 25.4% | -33.8% | 48.7 | -11.0 | 67.1% | 15.51 |

## Existing PIT-lite Factor Candidates

These come from the realistic Nasdaq 100 PIT-lite all-signal grid: 30 bps base cost, 10 bps extra slippage, financing at ^IRX + 2%, and 4% annual tax/implementation drag. They reduce drawdown, but they are stock-selection sleeves rather than a direct QLD overlay.

| constraint | strategy | CAGR | Sharpe | MDD | MDD improve pp | CAGR gap pp |
| :-- | --: | --: | --: | --: | --: | --: |
| MDD >= -25% | US_A4_liquidity_size_LO_decile_20d_30bps @ 1.15x | 10.6% | 0.57 | -24.9% | 39.5 | -23.2 |
| MDD >= -30% | US_A4_liquidity_size_LO_decile_20d_30bps @ 1.40x | 12.2% | 0.57 | -29.5% | 34.8 | -21.7 |
| MDD >= -35% | US_A4_liquidity_size_LO_decile_20d_30bps @ 1.70x | 13.7% | 0.56 | -34.9% | 29.4 | -20.1 |
| MDD >= -40% | US_A4_liquidity_size_LO_decile_20d_30bps @ 1.95x | 14.8% | 0.56 | -39.2% | 25.1 | -19.0 |
| MDD >= -45% | US_A4_liquidity_size_LO_decile_20d_30bps @ 2.30x | 15.9% | 0.56 | -44.8% | 19.5 | -18.0 |

## Verdict

- Practical balanced rule: `QLD_MA175_vol20_target45_cash_10bps`.
- Simpler live-paper rule: `QLD_MA175_cash_10bps` or the more standard `QLD_MA200_cash_10bps`.
- Maximum drawdown-reduction rule in the balanced family: lower the volatility target to 30% or 20%, accepting materially lower CAGR.

The strategy should be treated as research-grade. The main remaining risks are parameter overfit, tax impact from switching, and the fact that QLD is a daily-reset leveraged ETF.

## Artifacts

- Tactical 2020 grid: `data/cache/us/qld_mdd/qld_tactical_mdd_grid.parquet`
- Tactical 2020 returns: `data/cache/us/qld_mdd/qld_tactical_mdd_returns.parquet`
- 2007/2020 split grid: `data/cache/us/qld_mdd/qld_tactical_mdd_oos_grid.parquet`
- Pre-2020 selected candidates: `data/cache/us/qld_mdd/qld_tactical_mdd_train_selected.parquet`
- Existing factor MDD candidates: `data/cache/us/qld_mdd/qld_mdd_factor_candidates.parquet`
