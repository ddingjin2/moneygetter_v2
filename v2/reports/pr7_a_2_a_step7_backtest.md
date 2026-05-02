# PR-7.A.2.a Step 7 Backtest

## 1. Backtest Rules
- Signal: `divergence_5d = institutional_5d_mean - foreign_5d_mean`.
- Direction: Step 6 found negative IC, so lower `divergence_5d` is long and higher `divergence_5d` is short.
- Execution assumption: signal observed at day `t` close, portfolio enters at `t+1` open and earns open-to-open daily returns.
- Portfolios: `LS_decile`, `LS_quintile`, `LO_decile`; all equal-weight internally.
- Rebalance: both `1d` and `5d` are tested.
- Costs: one-way bps scenarios `0, 15, 30, 50`; daily cost is `turnover * cost_rate * 2`.
- Trading halt mask: `volume == 0 and open == 0`; halted rows are excluded from signal selection, and open-to-open returns are invalid if current or next open is halted.

## 2. Universe & Data Summary
- Universe stocks in signal panel: `808`
- Period: `2020-03-27 ~ 2026-04-17`
- Trading days: `1486`
- (code, date) rows: `1157935`
- Trading halt row ratio: `0.0%`

## 3. Full Result Matrix
| portfolio | rebalance | cost_bps | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LS_decile | 1d | 0 | -0.27 | -3.1% | 11.2% | -26.3% | 48.9% |
| LS_decile | 1d | 15 | -3.56 | -40.0% | 11.2% | -91.3% | 48.9% |
| LS_decile | 1d | 30 | -6.82 | -77.0% | 11.3% | -99.0% | 48.9% |
| LS_decile | 1d | 50 | -11.12 | -126.3% | 11.3% | -99.9% | 48.9% |
| LS_decile | 5d | 0 | -0.05 | -0.5% | 10.7% | -25.8% | 24.8% |
| LS_decile | 5d | 15 | -1.75 | -19.2% | 10.9% | -72.6% | 24.8% |
| LS_decile | 5d | 30 | -3.24 | -37.9% | 11.7% | -90.8% | 24.8% |
| LS_decile | 5d | 50 | -4.72 | -62.9% | 13.3% | -97.9% | 24.8% |
| LS_quintile | 1d | 0 | 0.46 | 3.7% | 8.1% | -10.3% | 44.3% |
| LS_quintile | 1d | 15 | -3.68 | -29.8% | 8.1% | -83.7% | 44.3% |
| LS_quintile | 1d | 30 | -7.80 | -63.2% | 8.1% | -97.7% | 44.3% |
| LS_quintile | 1d | 50 | -13.22 | -107.8% | 8.2% | -99.8% | 44.3% |
| LS_quintile | 5d | 0 | 0.50 | 3.9% | 7.7% | -12.1% | 22.6% |
| LS_quintile | 5d | 15 | -1.67 | -13.2% | 7.9% | -58.2% | 22.6% |
| LS_quintile | 5d | 30 | -3.46 | -30.3% | 8.7% | -84.5% | 22.6% |
| LS_quintile | 5d | 50 | -5.08 | -53.1% | 10.5% | -96.0% | 22.6% |
| LO_decile | 1d | 0 | 0.90 | 19.5% | 21.6% | -35.1% | 24.4% |
| LO_decile | 1d | 15 | 0.05 | 1.0% | 21.6% | -64.7% | 24.4% |
| LO_decile | 1d | 30 | -0.81 | -17.4% | 21.6% | -82.3% | 24.4% |
| LO_decile | 1d | 50 | -1.94 | -42.0% | 21.6% | -94.7% | 24.4% |
| LO_decile | 5d | 0 | 0.96 | 20.8% | 21.5% | -37.3% | 12.3% |
| LO_decile | 5d | 15 | 0.53 | 11.5% | 21.5% | -54.0% | 12.3% |
| LO_decile | 5d | 30 | 0.10 | 2.2% | 21.6% | -66.3% | 12.3% |
| LO_decile | 5d | 50 | -0.47 | -10.2% | 21.8% | -78.1% | 12.3% |

## 4. Recommended Combination Details
### Yearly Summary: 5d Rebalance, 30bp
| portfolio | year | return | sharpe |
| --- | --- | --- | --- |
| LS_decile_5d_30bp | 2020 | -15.3% | -1.50 |
| LS_decile_5d_30bp | 2021 | -33.0% | -3.60 |
| LS_decile_5d_30bp | 2022 | -32.8% | -3.64 |
| LS_decile_5d_30bp | 2023 | -41.7% | -5.24 |
| LS_decile_5d_30bp | 2024 | -27.7% | -2.91 |
| LS_decile_5d_30bp | 2025 | -28.8% | -3.04 |
| LS_decile_5d_30bp | 2026 | -10.3% | -2.46 |
| LS_quintile_5d_30bp | 2020 | -16.2% | -2.29 |
| LS_quintile_5d_30bp | 2021 | -31.5% | -4.56 |
| LS_quintile_5d_30bp | 2022 | -29.0% | -4.04 |
| LS_quintile_5d_30bp | 2023 | -32.0% | -5.01 |
| LS_quintile_5d_30bp | 2024 | -20.4% | -2.87 |
| LS_quintile_5d_30bp | 2025 | -21.8% | -2.99 |
| LS_quintile_5d_30bp | 2026 | -5.1% | -1.42 |
| LO_decile_5d_30bp | 2020 | 54.7% | 2.54 |
| LO_decile_5d_30bp | 2021 | 0.3% | 0.13 |
| LO_decile_5d_30bp | 2022 | -36.2% | -1.69 |
| LO_decile_5d_30bp | 2023 | -10.6% | -0.54 |
| LO_decile_5d_30bp | 2024 | -23.5% | -1.38 |
| LO_decile_5d_30bp | 2025 | 15.9% | 0.96 |
| LO_decile_5d_30bp | 2026 | 26.1% | 3.15 |

## 5. Subperiod Analysis: LS Decile, 5d Rebalance, 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -2.55 | -31.9% | -48.3% | 40.0% |
| sub2_2022 | -3.64 | -40.1% | -36.2% | 45.1% |
| sub3_2023_2024 | -4.03 | -44.0% | -59.2% | 41.1% |
| sub4_2025_2026 | -2.86 | -35.2% | -37.5% | 41.1% |

## 6. Size Bucket Analysis: LS Decile, 5d Rebalance, 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -2.19 | -39.5% | 18.0% | -92.3% | 24.9% |
| mid | -2.33 | -43.2% | 18.5% | -93.7% | 27.6% |
| small | -1.77 | -26.6% | 15.1% | -82.8% | 25.4% |

## 7. Long-only Top Decile Alpha vs KOSPI: 5d Rebalance
| cost_bps | ann_alpha | tracking_error | ir |
| --- | --- | --- | --- |
| 0 | -3.7% | 22.2% | -0.17 |
| 15 | -13.0% | 22.2% | -0.59 |
| 30 | -22.3% | 22.2% | -1.00 |
| 50 | -34.7% | 22.4% | -1.55 |
- 30bp alpha threshold check: `-22.3% >= 2.0%` is `False`.

## 8. Verdict
- Verdict: **FAIL**
- Reason: subperiod instability: min subperiod Sharpe -4.03 < -0.30
- Recommendation: Discard Option A. Review Option B/C or close PR-7.A.2.a

## 9. Caveats
- Alive-only universe caveat remains: roughly 30-80 delisted names may be missing from the universe reconstruction.
- Size buckets use trading-value proxy because market_cap is unavailable.
- Market-cap-weighted backtest is not possible; this run is equal-weight only.
- Slippage/market impact is not explicitly modeled beyond flat bps cost scenarios.
- This is an in-sample backtest over the full period with a fixed rule; no walk-forward split is applied.
- t+1 open execution is conservative versus same-close entry, but practical fill assumptions still need live-trading review.
- 5d rebalance reduces turnover versus daily rebalance, but overlapping signal windows can still induce high implementation friction.

## 10. Artifacts
- Benchmark: `v2\data\cache\benchmarks\kospi_daily_returns.parquet`
- Daily PnL: `v2\data\cache\backtest\option_a_pnl_daily.parquet`
- Metrics: `v2\data\cache\backtest\option_a_metrics.parquet`

## Gate
Step 7 verdict and report complete. Stop here; do not enter Step 7.b without user approval.
