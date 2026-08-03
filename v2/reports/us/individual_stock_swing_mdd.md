# Individual Stock Swing Strategies For QLD MDD Reduction

- Analysis date: 2026-05-31.
- Universe/data: Nasdaq 100 PIT-lite expanded individual-stock universe, 2020-01-02 to 2026-05-28 returns. The final price date is 2026-05-29.
- Base strategy set: 36 long-only individual-stock swing portfolios from 9 OHLCV factors, decile/quintile selection, and 5-day/20-day rebalance.
- Base stock rebalance cost: 30 bps already embedded in `base_net_return`.
- Added realism here: 10 bps extra stock slippage, 10 bps cost for exposure changes, 4% annual tax/implementation drag, and ^IRX + 2% financing spread when exposure cap is above 1.0x.
- Market filter: QQQ moving-average risk-on/off signal, shifted one day to avoid look-ahead.

## Answer

Yes. There are individual-stock swing candidates that reduce MDD much more than QLD buy-and-hold.

Best practical no-margin candidate:

`US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol60_target30_cap1_realistic`

- Uses `US_A5_illiquidity`, `LO_decile`, 20-day rebalance.
- Market/risk filter: `ma175`, vol window 60 days, target vol 30.0%, cap 1.0x.
- Result: CAGR 20.5% vs QLD 33.8%, MDD -17.5% vs QLD -64.3%.
- MDD improvement: 46.8 percentage points. CAGR give-up: 13.3 percentage points annually.

Best return/MDD trade-off if margin up to 2.0x is allowed:

`US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target40_cap2_realistic`

- Result: CAGR 25.8%, MDD -31.0%.
- This still trails QLD CAGR by 8.0 percentage points, but cuts MDD by 33.4 percentage points.

Simplest no-margin version:

`US_A5_illiquidity_LO_decile_20d_30bps_ma175_cap1_realistic`

- No volatility target, just QQQ moving-average risk-on/off.
- Result: CAGR 18.9%, MDD -25.2%.

## No-Margin Candidates

These are capped at 1.0x exposure and have MDD no worse than roughly -25%.

| strategy | signal | portfolio | rebalance | filter | vol win | target vol | cap | CAGR | Sharpe | ann vol | MDD | MDD improve pp | CAGR gap pp | avg exposure | ann overlay turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol60_target30_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 60.00 | 30.0% | 1.00 | 20.5% | 1.08 | 19.0% | -17.5% | 46.8 | -13.3 | 73.8% | 3.66 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target40_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 40.0% | 1.00 | 19.2% | 0.95 | 20.8% | -22.5% | 41.9 | -14.6 | 77.4% | 4.18 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol60_target25_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 60.00 | 25.0% | 1.00 | 19.1% | 1.05 | 18.2% | -17.5% | 46.8 | -14.7 | 71.5% | 3.61 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol40_target30_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 40.00 | 30.0% | 1.00 | 19.0% | 0.99 | 19.6% | -17.5% | 46.8 | -14.8 | 74.7% | 4.23 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target35_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 35.0% | 1.00 | 18.9% | 0.95 | 20.6% | -21.7% | 42.6 | -14.9 | 77.0% | 4.32 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target30_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 30.0% | 1.00 | 18.6% | 0.95 | 20.0% | -19.9% | 44.4 | -15.2 | 76.1% | 4.50 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma150_vol60_target30_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma150 | 60.00 | 30.0% | 1.00 | 18.6% | 0.99 | 19.0% | -17.5% | 46.8 | -15.2 | 73.6% | 4.54 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol40_target25_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 40.00 | 25.0% | 1.00 | 18.0% | 0.98 | 18.7% | -17.5% | 46.8 | -15.8 | 72.2% | 4.18 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target25_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 25.0% | 1.00 | 17.8% | 0.95 | 19.2% | -17.9% | 46.5 | -16.1 | 73.8% | 4.84 |
| US_A5_illiquidity_LO_quintile_20d_30bps_ma175_vol60_target30_cap1_realistic | US_A5_illiquidity | LO_quintile | 20 | ma175 | 60.00 | 30.0% | 1.00 | 17.5% | 1.02 | 17.3% | -17.0% | 47.4 | -16.3 | 74.1% | 3.59 |

## Margin-Allowed Balanced Candidates

These allow caps above 1.0x and include financing drag. They have MDD no worse than -35% and CAGR above 15%.

| strategy | signal | portfolio | rebalance | filter | vol win | target vol | cap | CAGR | Sharpe | ann vol | MDD | MDD improve pp | CAGR gap pp | avg exposure | ann overlay turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target40_cap2_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 40.0% | 2.00 | 25.8% | 0.83 | 35.0% | -31.0% | 33.4 | -8.0 | 137.5% | 11.51 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target40_cap1.75_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 40.0% | 1.75 | 24.9% | 0.85 | 32.5% | -28.6% | 35.7 | -8.9 | 126.2% | 9.09 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target40_cap1.5_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 40.0% | 1.50 | 24.0% | 0.88 | 29.3% | -27.0% | 37.4 | -9.8 | 112.1% | 7.01 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target35_cap2_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 35.0% | 2.00 | 23.8% | 0.82 | 32.4% | -29.3% | 35.0 | -10.0 | 128.4% | 12.32 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target35_cap1.75_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 35.0% | 1.75 | 23.8% | 0.85 | 30.6% | -27.5% | 36.8 | -10.1 | 120.3% | 10.07 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target35_cap1.5_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 35.0% | 1.50 | 22.7% | 0.87 | 28.1% | -25.1% | 39.3 | -11.1 | 108.8% | 7.65 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma150_vol20_target40_cap2_realistic | US_A5_illiquidity | LO_decile | 20 | ma150 | 20.00 | 40.0% | 2.00 | 22.6% | 0.76 | 35.0% | -31.0% | 33.3 | -11.3 | 137.1% | 13.42 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol20_target30_cap2_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 20.00 | 30.0% | 2.00 | 22.1% | 0.83 | 29.1% | -26.7% | 37.7 | -11.7 | 116.2% | 13.00 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol60_target30_cap1.5_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 60.00 | 30.0% | 1.50 | 22.1% | 0.93 | 25.0% | -25.3% | 39.1 | -11.7 | 98.6% | 5.69 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_vol60_target30_cap2_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 | 60.00 | 30.0% | 2.00 | 22.1% | 0.88 | 26.8% | -27.3% | 37.1 | -11.8 | 106.2% | 7.30 |

## Simple No-Margin Variants

These skip the volatility target and only switch the stock-selection sleeve on/off with the QQQ moving-average filter.

| strategy | signal | portfolio | rebalance | filter | vol win | target vol | cap | CAGR | Sharpe | ann vol | MDD | MDD improve pp | CAGR gap pp | avg exposure | ann overlay turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| US_A5_illiquidity_LO_decile_20d_30bps_ma175_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma175 |  |  | 1.00 | 18.9% | 0.92 | 21.2% | -25.2% | 39.1 | -15.0 | 78.8% | 4.23 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma150_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma150 |  |  | 1.00 | 16.5% | 0.83 | 21.0% | -24.8% | 39.5 | -17.3 | 78.6% | 5.17 |
| US_A5_illiquidity_LO_quintile_20d_30bps_ma175_cap1_realistic | US_A5_illiquidity | LO_quintile | 20 | ma175 |  |  | 1.00 | 15.6% | 0.85 | 19.4% | -27.4% | 36.9 | -18.3 | 78.8% | 4.23 |
| US_A5_illiquidity_LO_decile_20d_30bps_ma200_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | ma200 |  |  | 1.00 | 15.2% | 0.77 | 21.5% | -27.9% | 36.4 | -18.6 | 79.5% | 3.92 |
| US_A5_illiquidity_LO_decile_20d_30bps_always_cap1_realistic | US_A5_illiquidity | LO_decile | 20 | always |  |  | 1.00 | 14.5% | 0.63 | 27.7% | -51.3% | 13.0 | -19.3 | 100.0% | 0.16 |
| US_A5_illiquidity_LO_quintile_20d_30bps_ma150_cap1_realistic | US_A5_illiquidity | LO_quintile | 20 | ma150 |  |  | 1.00 | 13.9% | 0.77 | 19.3% | -26.6% | 37.8 | -20.0 | 78.6% | 5.17 |
| US_A5_illiquidity_LO_quintile_20d_30bps_ma200_cap1_realistic | US_A5_illiquidity | LO_quintile | 20 | ma200 |  |  | 1.00 | 13.4% | 0.74 | 19.5% | -28.9% | 35.5 | -20.5 | 79.5% | 3.92 |
| US_A5_illiquidity_LO_quintile_20d_30bps_always_cap1_realistic | US_A5_illiquidity | LO_quintile | 20 | always |  |  | 1.00 | 12.5% | 0.59 | 25.6% | -45.8% | 18.5 | -21.3 | 100.0% | 0.16 |

## Interpretation

- The recurring winner is `US_A5_illiquidity`, long-only decile, 20-day rebalance, combined with a QQQ trend filter.
- No-margin stock swing is a strong MDD reducer: best candidate MDD is around -17.5% versus QLD -64.3%, but it gives up about 13.3 annual percentage points of CAGR.
- The margin-allowed version recovers some return: about 25.8% CAGR with -31.0% MDD, still below QLD CAGR but far better drawdown.
- Compared with the QLD ETF tactical overlay, this stock-swing route is more defensive and stock-selection dependent. The ETF overlay is simpler and had better 2020-2026 CAGR; this route has lower MDD.
- Main caveat: this is still PIT-lite. Missing unavailable delisted/acquired histories can bias individual-stock results, especially illiquidity-style factors.

## Artifacts

- Grid: `data/cache/us/nasdaq100_pitlite/strategy_compare/individual_stock_swing_mdd/individual_stock_swing_mdd_grid.parquet`
- Selected candidates: `data/cache/us/nasdaq100_pitlite/strategy_compare/individual_stock_swing_mdd/individual_stock_swing_mdd_selected.parquet`
- Selected period metrics: `data/cache/us/nasdaq100_pitlite/strategy_compare/individual_stock_swing_mdd/individual_stock_swing_mdd_selected_periods.parquet`
- Selected daily returns: `data/cache/us/nasdaq100_pitlite/strategy_compare/individual_stock_swing_mdd/individual_stock_swing_mdd_selected_returns.parquet`
