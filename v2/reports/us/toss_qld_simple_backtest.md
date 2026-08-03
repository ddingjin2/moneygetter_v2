# Toss Securities Proxy Backtest: QLD Tactical Strategy

- Analysis date: 2026-05-31.
- Strategy: `QLD_MA175_vol20_target45`, the strongest simple ETF candidate from the prior QLD MDD-reduction run.
- Tradability assumption: Toss Securities supports domestic/foreign stocks and ETFs, and says foreign stocks can start from 1,000 KRW. Open API live-order access is still not verified in this workspace.
- Data: yfinance adjusted QLD, QQQ, and ^IRX through 2026-05-29. Backtest returns run from 2020-01-02 to 2026-05-28 using next-open exits.
- Toss proxy execution: rebalance at QLD adjusted open using prior-day QQQ/SMA and prior-day volatility; cash earns prior-day ^IRX proxy; no FX conversion, withholding tax, Korean capital-gains tax, or bid/ask depth model.
- Cost model: fee/slippage scenarios of 10/20/30 bps on traded notional. The main table uses 20 bps per trade as a conservative placeholder, not an official Toss fee claim.

## Rule

Hold QLD only when prior-day QQQ close is above its 175-day moving average. When risk-on, cap QLD exposure using a 20-day realized-volatility target of 45%. Otherwise hold cash.

## Main Result: 10,000 USD, 20 bps, Whole Shares

| strategy | fractional | capital | fee bps | CAGR | Sharpe | ann vol | MDD | total | MDD improve pp | CAGR gap pp | avg exposure | fees | ann turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| QLD_MA175_vol20_target45_toss_proxy | False | $10,000 | 20 | 36.9% | 1.11 | 33.2% | -32.3% | 644.4% | 32.0 | 3.2 | 75.4% | $1,751 | 13.71 |
| QLD_buy_hold_toss_proxy | False | $10,000 | 20 | 33.8% | 0.84 | 48.7% | -64.3% | 541.5% | 0.0 | 0.0 | 99.9% | $20 | 0.16 |
| QLD_MA175_vol20_target45_toss_proxy | True | $10,000 | 20 | 37.0% | 1.11 | 33.2% | -32.4% | 645.9% | 32.0 | 3.2 | 75.5% | $1,754 | 13.73 |
| QLD_buy_hold_toss_proxy | True | $10,000 | 20 | 33.8% | 0.84 | 48.7% | -64.3% | 541.5% | 0.0 | 0.0 | 99.9% | $20 | 0.16 |

## Strategy Sensitivity

| capital | fee bps | fractional | CAGR | Sharpe | ann vol | MDD | total | MDD improve pp | CAGR gap pp | avg exposure | fees | ann turnover |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| $10,000 | 10 | False | 37.6% | 1.13 | 33.2% | -32.2% | 668.0% | 32.2 | 3.8 | 75.4% | $893 | 13.98 |
| $10,000 | 10 | True | 37.6% | 1.13 | 33.2% | -32.2% | 669.2% | 32.1 | 3.8 | 75.5% | $894 | 14.00 |
| $100,000 | 10 | False | 37.6% | 1.13 | 33.2% | -32.2% | 669.1% | 32.1 | 3.8 | 75.5% | $8,938 | 14.00 |
| $100,000 | 10 | True | 37.6% | 1.13 | 33.2% | -32.2% | 669.2% | 32.1 | 3.8 | 75.5% | $8,939 | 14.00 |
| $10,000 | 20 | False | 36.9% | 1.11 | 33.2% | -32.3% | 644.4% | 32.0 | 3.2 | 75.4% | $1,751 | 13.71 |
| $10,000 | 20 | True | 37.0% | 1.11 | 33.2% | -32.4% | 645.9% | 32.0 | 3.2 | 75.5% | $1,754 | 13.73 |
| $100,000 | 20 | False | 37.0% | 1.11 | 33.2% | -32.4% | 645.8% | 32.0 | 3.2 | 75.5% | $17,533 | 13.73 |
| $100,000 | 20 | True | 37.0% | 1.11 | 33.2% | -32.4% | 645.9% | 32.0 | 3.2 | 75.5% | $17,536 | 13.73 |
| $10,000 | 30 | False | 36.3% | 1.10 | 33.2% | -32.5% | 622.5% | 31.8 | 2.5 | 75.4% | $2,576 | 13.45 |
| $10,000 | 30 | True | 36.3% | 1.10 | 33.3% | -32.5% | 623.2% | 31.8 | 2.6 | 75.5% | $2,580 | 13.47 |
| $100,000 | 30 | False | 36.3% | 1.10 | 33.3% | -32.5% | 623.2% | 31.8 | 2.6 | 75.5% | $25,801 | 13.47 |
| $100,000 | 30 | True | 36.3% | 1.10 | 33.3% | -32.5% | 623.2% | 31.8 | 2.6 | 75.5% | $25,803 | 13.47 |

## Period Breakdown: 10,000 USD, 20 bps, Whole Shares

| period | strategy | CAGR | Sharpe | ann vol | MDD | total | avg exposure | fees |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| Full 2020-2026 | QLD_MA175_vol20_target45_toss_proxy | 36.9% | 1.11 | 33.2% | -32.3% | 644.4% | 75.4% | $1,751 |
| 2020-2021 | QLD_MA175_vol20_target45_toss_proxy | 54.7% | 1.29 | 40.1% | -32.3% | 139.7% | 87.8% | $182 |
| 2022 | QLD_MA175_vol20_target45_toss_proxy | -13.0% | -1.18 | 11.3% | -15.8% | -12.9% | 4.6% | $111 |
| 2023-2024 | QLD_MA175_vol20_target45_toss_proxy | 51.0% | 1.38 | 34.2% | -29.7% | 127.3% | 94.5% | $627 |
| 2025-2026 YTD | QLD_MA175_vol20_target45_toss_proxy | 38.2% | 1.20 | 31.1% | -19.8% | 56.9% | 81.1% | $831 |
| Full 2020-2026 | QLD_buy_hold_toss_proxy | 33.8% | 0.84 | 48.7% | -64.3% | 541.5% | 99.9% | $20 |
| 2020-2021 | QLD_buy_hold_toss_proxy | 69.8% | 1.28 | 51.9% | -51.2% | 188.9% | 99.8% | $20 |
| 2022 | QLD_buy_hold_toss_proxy | -60.3% | -1.10 | 64.6% | -63.5% | -60.1% | 100.4% | $0 |
| 2023-2024 | QLD_buy_hold_toss_proxy | 76.3% | 1.76 | 35.9% | -29.7% | 209.4% | 99.8% | $0 |
| 2025-2026 YTD | QLD_buy_hold_toss_proxy | 52.5% | 1.15 | 46.1% | -44.0% | 80.0% | 99.9% | $0 |

## Verdict

For a Toss-style simple implementation, QLD tactical is still the best practical candidate: one ETF, low operational complexity, and much lower drawdown than QLD buy-and-hold. In the conservative 10,000 USD whole-share / 20 bps model, it improves MDD materially and slightly beats buy-and-hold CAGR in this 2020-2026 sample.

Before live operation, the missing pieces are official Toss Open API order documentation, confirmed API support for US ETF orders, and exact account-level fee/FX/tax treatment.

## Artifacts

- Daily returns/equity: `data/cache/us/toss/toss_qld_simple_backtest_returns.parquet`
- Summary grid: `data/cache/us/toss/toss_qld_simple_backtest_summary.parquet`
- Period metrics: `data/cache/us/toss/toss_qld_simple_backtest_periods.parquet`
