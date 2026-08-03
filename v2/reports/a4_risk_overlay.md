# A4 risk overlay backtest

## Rules

- A4 60-day average traded-value signal, bottom traded-value decile, 20-trading-day rebalance.
- Stop observed at close and executed at next available open.
- Position candidates: fixed -10%/-15%/-20% from average cost and trailing -15% from highest close.
- Portfolio guard: cycle MDD -10%, then all cash or 50% exposure until next scheduled rebalance.
- Re-entry only at next scheduled rebalance.
- Costs: 10bp and conservative 30bp one-way.
- Balanced pass at 30bp: Sharpe no lower than baseline, MDD improves at least 3%p, annual return falls no more than 3%p.

## Results

| variant | cost_bps | sharpe | ann_return | max_dd | max_dd_improvement | ann_return_vs_baseline | avg_exposure | position_stop_triggers | portfolio_guard_triggers | balanced_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 10 | 1.5702 | 0.2568 | -0.1774 | 0.0000 | 0.0000 | 0.9598 | 0 | 0 | False |
| fixed_20_mdd10_half | 10 | 1.5099 | 0.2387 | -0.1771 | 0.0003 | -0.0181 | 0.9444 | 200 | 2 | False |
| fixed_15_mdd10_cash | 10 | 1.5081 | 0.2348 | -0.1808 | -0.0034 | -0.0220 | 0.9310 | 346 | 1 | False |
| fixed_20_mdd10_cash | 10 | 1.5063 | 0.2379 | -0.1776 | -0.0002 | -0.0189 | 0.9414 | 180 | 2 | False |
| fixed_15_mdd10_half | 10 | 1.5060 | 0.2345 | -0.1776 | -0.0001 | -0.0223 | 0.9325 | 357 | 1 | False |
| trailing_15_mdd10_half | 10 | 1.4783 | 0.2232 | -0.1849 | -0.0074 | -0.0336 | 0.9002 | 775 | 1 | False |
| trailing_15_mdd10_cash | 10 | 1.4700 | 0.2220 | -0.1890 | -0.0116 | -0.0348 | 0.8998 | 767 | 1 | False |
| fixed_10_mdd10_half | 10 | 1.4590 | 0.2206 | -0.1689 | 0.0085 | -0.0361 | 0.9103 | 649 | 1 | False |
| fixed_10_mdd10_cash | 10 | 1.4529 | 0.2196 | -0.1714 | 0.0060 | -0.0372 | 0.9087 | 653 | 1 | False |
| baseline | 30 | 1.5123 | 0.2471 | -0.1807 | 0.0000 | 0.0000 | 0.9586 | 0 | 0 | False |
| fixed_20_mdd10_half | 30 | 1.4288 | 0.2257 | -0.1824 | -0.0016 | -0.0214 | 0.9430 | 205 | 2 | False |
| fixed_15_mdd10_cash | 30 | 1.4271 | 0.2220 | -0.1867 | -0.0059 | -0.0251 | 0.9291 | 351 | 1 | False |
| fixed_15_mdd10_half | 30 | 1.4262 | 0.2219 | -0.1869 | -0.0062 | -0.0252 | 0.9305 | 363 | 1 | False |
| fixed_20_mdd10_cash | 30 | 1.4221 | 0.2245 | -0.1829 | -0.0022 | -0.0226 | 0.9401 | 187 | 2 | False |
| trailing_15_mdd10_half | 30 | 1.3840 | 0.2091 | -0.2006 | -0.0199 | -0.0380 | 0.8993 | 775 | 1 | False |
| trailing_15_mdd10_cash | 30 | 1.3754 | 0.2078 | -0.2049 | -0.0241 | -0.0392 | 0.8989 | 767 | 1 | False |
| fixed_10_mdd10_half | 30 | 1.3684 | 0.2068 | -0.1983 | -0.0175 | -0.0403 | 0.9075 | 664 | 1 | False |
| fixed_10_mdd10_cash | 30 | 1.3622 | 0.2058 | -0.2033 | -0.0225 | -0.0413 | 0.9059 | 668 | 1 | False |

## Decision

- 30bp pass count: 0
