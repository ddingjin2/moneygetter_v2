# US Residual Reversal Individual Stock Experiment

- Universe/data: Nasdaq 100 PIT-lite expanded individual stocks, yfinance adjusted OHLCV.
- Research basis: short-term residual reversal, low-volatility anomaly, and conservative formula style low-vol/momentum filtering.
- Quality limitation: no point-in-time US fundamentals are available locally, so `US_R3` and `US_R4` use a price-only low-volatility plus 12-1 momentum proxy rather than gross profitability or leverage.
- Tax limitation: these are daily return simulations; Korean US-stock capital-gains tax requires realized executions, trade-date USD/KRW FX, and lot-level gains.
- Rows tested: `51488` daily rows across `32` strategy variants.

## Most Weekly-Stable Candidates
| strategy_id                                                              |         cagr |     sharpe |    max_dd |   weekly_win_rate |   p05_weekly_return |   worst_weekly_return |   max_consecutive_losing_weeks |   avg_exposure |   ann_turnover |
|:-------------------------------------------------------------------------|-------------:|-----------:|----------:|------------------:|--------------------:|----------------------:|-------------------------------:|---------------:|---------------:|
| US_R1_residual_5d_reversal_LO_decile_10d_always_40bps                    |  0.641392    |  0.840165  | -0.583609 |          0.513433 |          -0.073634  |            -0.239067  |                              8 |       0.986948 |        21.4542 |
| US_R1_residual_5d_reversal_LO_quintile_10d_always_40bps                  |  0.394955    |  0.853285  | -0.440566 |          0.510448 |          -0.065644  |            -0.198056  |                              8 |       0.986948 |        19.18   |
| US_R1_residual_5d_reversal_LO_decile_5d_always_40bps                     |  0.489293    |  0.72196   | -0.7677   |          0.492537 |          -0.0896339 |            -0.220303  |                              7 |       0.986948 |        42.944  |
| US_R1_residual_5d_reversal_LO_quintile_5d_always_40bps                   |  0.26452     |  0.64933   | -0.649375 |          0.492537 |          -0.0757363 |            -0.195125  |                              7 |       0.986948 |        38.7811 |
| US_R2_lowvol_residual_5d_reversal_LO_decile_10d_always_40bps             |  0.00854147  |  0.142108  | -0.533578 |          0.483582 |          -0.045661  |            -0.0972925 |                              9 |       0.962088 |        22.1442 |
| US_R2_lowvol_residual_5d_reversal_LO_quintile_10d_always_40bps           | -0.000956992 |  0.081182  | -0.484767 |          0.477612 |          -0.0378025 |            -0.0880343 |                              8 |       0.962088 |        19.5799 |
| US_R2_lowvol_residual_5d_reversal_LO_decile_5d_always_40bps              |  0.033851    |  0.237569  | -0.728959 |          0.459701 |          -0.0450267 |            -0.0825597 |                              8 |       0.962088 |        43.9795 |
| US_R2_lowvol_residual_5d_reversal_LO_quintile_5d_always_40bps            | -0.0340135   |  0.0508779 | -0.699021 |          0.456716 |          -0.0379824 |            -0.100396  |                              8 |       0.962088 |        39.4613 |
| US_R3_lowvol_momentum_residual_5d_reversal_LO_decile_10d_always_40bps    | -0.066175    | -0.268665  | -0.471066 |          0.420896 |          -0.0540611 |            -0.0967192 |                              9 |       0.788067 |        18.5098 |
| US_R4_lowvol_momentum_residual_10d_reversal_LO_decile_10d_always_40bps   |  0.00644699  |  0.127691  | -0.317747 |          0.414925 |          -0.0423846 |            -0.0910271 |                              5 |       0.788067 |        18.6951 |
| US_R3_lowvol_momentum_residual_5d_reversal_LO_quintile_10d_always_40bps  | -0.0394555   | -0.165623  | -0.354708 |          0.39403  |          -0.0373201 |            -0.0819904 |                              8 |       0.788067 |        16.6185 |
| US_R4_lowvol_momentum_residual_10d_reversal_LO_quintile_10d_always_40bps | -0.0183782   | -0.0304061 | -0.29594  |          0.38806  |          -0.0374487 |            -0.120755  |                              5 |       0.788067 |        16.7609 |

## Balanced Candidates With MDD No Worse Than -30%
| strategy_id                                                              |       cagr |     sharpe |    max_dd |   weekly_win_rate |   p05_weekly_return |   worst_weekly_return |   max_consecutive_losing_weeks |   avg_exposure |   ann_turnover |
|:-------------------------------------------------------------------------|-----------:|-----------:|----------:|------------------:|--------------------:|----------------------:|-------------------------------:|---------------:|---------------:|
| US_R4_lowvol_momentum_residual_10d_reversal_LO_quintile_10d_always_40bps | -0.0183782 | -0.0304061 | -0.29594  |          0.38806  |          -0.0374487 |            -0.120755  |                              5 |       0.788067 |        16.7609 |
| US_R4_lowvol_momentum_residual_10d_reversal_LO_quintile_10d_ma175_40bps  | -0.030791  | -0.191031  | -0.275883 |          0.283582 |          -0.0352836 |            -0.0729091 |                              5 |       0.595401 |        12.7317 |
| US_R3_lowvol_momentum_residual_5d_reversal_LO_quintile_10d_ma175_40bps   | -0.0398477 | -0.279801  | -0.295581 |          0.298507 |          -0.0346642 |            -0.0746601 |                              7 |       0.595401 |        12.7119 |

## Interpretation

- No individual-stock strategy should be expected to make money every week; the weekly-stability ranking is a loss-frequency diagnostic, not a guarantee.
- Variants with the `ma175` risk filter are the practical candidates because they reduce market-regime damage.
- If any residual-reversal candidate is promoted, the next mandatory step is exact after-tax lot accounting with USD/KRW FX and point-in-time fundamental data for a real quality filter.

## Artifacts

- Daily returns: `data/cache/us/nasdaq100_pitlite/strategy_compare/residual_reversal/residual_reversal_pnl_daily.parquet`
- Full metrics: `data/cache/us/nasdaq100_pitlite/strategy_compare/residual_reversal/residual_reversal_metrics.parquet`
- Weekly metrics: `data/cache/us/nasdaq100_pitlite/strategy_compare/residual_reversal/residual_reversal_weekly.parquet`
