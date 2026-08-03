# US Signal Catalog

- Universe mode: `survivorship_biased_current_universe`.
- Data source mode: `free_yfinance_research_data` unless config says otherwise.
- Signals are OHLCV-only Phase 1 candidates; no strategy is promoted from this report alone.

## Signals
| signal_id | name | formula |
| --- | --- | --- |
| US_A1_12_1_momentum | 12-1 momentum | adj_close.shift(21) / adj_close.shift(252) - 1 |
| US_A2_1m_reversal | 1m reversal | -1m return |
| US_A3_low_volatility | low volatility | -rolling_std(ret_1d, 60) |
| US_A4_liquidity_size | liquidity size | -log(avg dollar volume 60d) |
| US_A5_illiquidity | Amihud illiquidity | -abs(ret)/dollar_volume |
| US_A6_volume_shock | volume shock | avg volume 5d / prior avg volume 60d - 1 |
| US_A7_near_high | near 252d high | adj_close / rolling_252d_high |
| US_A8_gap_reversal | overnight gap reversal | -overnight gap |
| US_A9_beta_residual | beta residual reversal | -21d beta residual |

## Sanity
| signal_id            |   rows |   non_nan_ratio |   z_non_nan_ratio |
|:---------------------|-------:|----------------:|------------------:|
| US_A1_12_1_momentum  | 159756 |        0.839105 |          0.839105 |
| US_A2_1m_reversal    | 159756 |        0.986592 |          0.986592 |
| US_A3_low_volatility | 159756 |        0.961692 |          0.961692 |
| US_A4_liquidity_size | 159756 |        0.955501 |          0.955501 |
| US_A5_illiquidity    | 159756 |        0.993966 |          0.993966 |
| US_A6_volume_shock   | 159756 |        0.959138 |          0.959138 |
| US_A7_near_high      | 159756 |        0.839743 |          0.839743 |
| US_A8_gap_reversal   | 159756 |        0.999362 |          0.999362 |
| US_A9_beta_residual  | 159756 |        0.948284 |          0.948284 |
