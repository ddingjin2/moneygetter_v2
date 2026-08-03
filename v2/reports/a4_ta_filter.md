# A4 + TA rebalance filter backtest

## Rules

- Baseline: A4 cross-sectional z-score, top decile, 20-trading-day rebalance, next-open fills (same engine as a4_risk_overlay).
- Filter applied only at rebalance selection, using the decision-day close. Excluded names are dropped; capital redistributes equally among survivors.
- Filters: `rsi_gt70` RSI14 > 70, `disp_gt10` close more than 10% above MA20, `below_ma20` close below MA20, `ta11_gt80` intraday close position above 0.8.
- NaN indicator keeps the stock.
- Improvement pass at each cost: Sharpe at least +0.02 over baseline, annual return no more than 1%p lower, MDD no more than 1%p worse.

## Results

| variant | cost_bps | sharpe | ann_return | max_dd | sharpe_vs_baseline | ann_return_vs_baseline | max_dd_vs_baseline | avg_positions | min_positions | improve_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 10 | 1.5702 | 0.2568 | -0.1774 | 0.0000 | 0.0000 | 0.0000 | 72.4974 | 72 | False |
| disp_gt10 | 10 | 1.4814 | 0.2420 | -0.1774 | -0.0888 | -0.0148 | 0.0000 | 71.5241 | 67 | False |
| ta11_gt80 | 10 | 1.4658 | 0.2705 | -0.1755 | -0.1044 | 0.0137 | 0.0019 | 55.8414 | 26 | False |
| rsi_gt70 | 10 | 1.4500 | 0.2368 | -0.1787 | -0.1202 | -0.0200 | -0.0012 | 69.4415 | 46 | False |
| below_ma20 | 10 | 1.0127 | 0.1519 | -0.2548 | -0.5575 | -0.1048 | -0.0773 | 33.0884 | 4 | False |
| baseline | 30 | 1.5123 | 0.2471 | -0.1807 | 0.0000 | 0.0000 | 0.0000 | 72.4974 | 72 | False |
| disp_gt10 | 30 | 1.4209 | 0.2318 | -0.1807 | -0.0915 | -0.0152 | 0.0000 | 71.5241 | 67 | False |
| rsi_gt70 | 30 | 1.3806 | 0.2253 | -0.1822 | -0.1317 | -0.0218 | -0.0014 | 69.4415 | 46 | False |
| ta11_gt80 | 30 | 1.3549 | 0.2501 | -0.1859 | -0.1575 | 0.0030 | -0.0052 | 55.8414 | 26 | False |
| below_ma20 | 30 | 0.7773 | 0.1170 | -0.3167 | -0.7350 | -0.1300 | -0.1359 | 33.0884 | 4 | False |

## Decision

- 30bp pass count: 0
