# PR-7.A.X Step 8.4 Multi-signal Backtest

## 1. Scope & Setup
- 6 signals: A3, A4, A10, A2, B1, C3.
- A3, C3: 20d rebalance added.
- Direction alignment: C3 is sign-flipped; A3, A4, A10, A2, B1 use existing cs_z direction.
- Framework: Option A Step 7 style with t+1 open execution, equal-weight portfolios, and halt mask.

## 2. Backtest Rules
- Signal observed at day t close; portfolio enters at t+1 open and earns open-to-open daily returns.
- Portfolios: LS_decile, LS_quintile, LO_decile.
- Costs: 0, 15, 30, 50 bps one-way; daily cost = turnover x cost_rate x 2.
- C3 sparse days: NaN signal days hold cash; no carry-forward.

## 3. Universe & Data Summary
- Universe stocks: 808.
- Period: 2020-03-27 ~ 2026-04-17.
- Trading days: 1486.
- Alive-only KOSPI universe.

## 4. Full Result Matrix
| signal_id | portfolio | rebalance | cost_bps | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | LS_decile | 1d | 0 | 0.2600 | 0.0667 | 0.2567 | -0.5834 | 0.0521 |
| A3 | LS_decile | 1d | 15 | 0.1067 | 0.0274 | 0.2566 | -0.5996 | 0.0521 |
| A3 | LS_decile | 1d | 30 | -0.0467 | -0.0120 | 0.2566 | -0.6215 | 0.0521 |
| A3 | LS_decile | 1d | 50 | -0.2512 | -0.0645 | 0.2566 | -0.6488 | 0.0521 |
| A3 | LS_quintile | 1d | 0 | 0.1046 | 0.0210 | 0.2010 | -0.5238 | 0.0443 |
| A3 | LS_quintile | 1d | 15 | -0.0621 | -0.0125 | 0.2010 | -0.5363 | 0.0443 |
| A3 | LS_quintile | 1d | 30 | -0.2287 | -0.0460 | 0.2011 | -0.5571 | 0.0443 |
| A3 | LS_quintile | 1d | 50 | -0.4507 | -0.0907 | 0.2011 | -0.5835 | 0.0443 |
| A3 | LO_decile | 1d | 0 | 1.4147 | 0.1270 | 0.0898 | -0.1353 | 0.0273 |
| A3 | LO_decile | 1d | 15 | 1.1850 | 0.1063 | 0.0897 | -0.1742 | 0.0273 |
| A3 | LO_decile | 1d | 30 | 0.9549 | 0.0857 | 0.0897 | -0.2321 | 0.0273 |
| A3 | LO_decile | 1d | 50 | 0.6477 | 0.0581 | 0.0897 | -0.3038 | 0.0273 |
| A3 | LS_decile | 5d | 0 | -0.0875 | -0.0231 | 0.2637 | -0.6836 | 0.0348 |
| A3 | LS_decile | 5d | 15 | -0.1873 | -0.0494 | 0.2637 | -0.6951 | 0.0348 |
| A3 | LS_decile | 5d | 30 | -0.2871 | -0.0757 | 0.2638 | -0.7061 | 0.0348 |
| A3 | LS_decile | 5d | 50 | -0.4199 | -0.1108 | 0.2640 | -0.7203 | 0.0348 |
| A3 | LS_quintile | 5d | 0 | -0.1419 | -0.0297 | 0.2091 | -0.5864 | 0.0298 |
| A3 | LS_quintile | 5d | 15 | -0.2496 | -0.0522 | 0.2090 | -0.5988 | 0.0298 |
| A3 | LS_quintile | 5d | 30 | -0.3573 | -0.0747 | 0.2091 | -0.6108 | 0.0298 |
| A3 | LS_quintile | 5d | 50 | -0.5006 | -0.1047 | 0.2092 | -0.6262 | 0.0298 |
| A3 | LO_decile | 5d | 0 | 1.3220 | 0.1237 | 0.0936 | -0.1637 | 0.0171 |
| A3 | LO_decile | 5d | 15 | 1.1843 | 0.1108 | 0.0935 | -0.1846 | 0.0171 |
| A3 | LO_decile | 5d | 30 | 1.0461 | 0.0979 | 0.0936 | -0.2069 | 0.0171 |
| A3 | LO_decile | 5d | 50 | 0.8614 | 0.0807 | 0.0937 | -0.2409 | 0.0171 |
| A3 | LS_decile | 20d | 0 | -0.2296 | -0.0618 | 0.2691 | -0.7109 | 0.0254 |
| A3 | LS_decile | 20d | 15 | -0.3009 | -0.0810 | 0.2692 | -0.7186 | 0.0254 |
| A3 | LS_decile | 20d | 30 | -0.3721 | -0.1002 | 0.2693 | -0.7261 | 0.0254 |
| A3 | LS_decile | 20d | 50 | -0.4666 | -0.1259 | 0.2697 | -0.7362 | 0.0254 |
| A3 | LS_quintile | 20d | 0 | -0.1308 | -0.0278 | 0.2125 | -0.6074 | 0.0211 |
| A3 | LS_quintile | 20d | 15 | -0.2059 | -0.0438 | 0.2126 | -0.6169 | 0.0211 |
| A3 | LS_quintile | 20d | 30 | -0.2807 | -0.0597 | 0.2128 | -0.6263 | 0.0211 |
| A3 | LS_quintile | 20d | 50 | -0.3800 | -0.0810 | 0.2133 | -0.6384 | 0.0211 |
| A3 | LO_decile | 20d | 0 | 1.1286 | 0.1108 | 0.0982 | -0.1784 | 0.0114 |
| A3 | LO_decile | 20d | 15 | 1.0402 | 0.1022 | 0.0982 | -0.1933 | 0.0114 |
| A3 | LO_decile | 20d | 30 | 0.9512 | 0.0935 | 0.0983 | -0.2079 | 0.0114 |
| A3 | LO_decile | 20d | 50 | 0.8319 | 0.0820 | 0.0985 | -0.2271 | 0.0114 |
| A4 | LS_decile | 1d | 0 | 0.3323 | 0.0730 | 0.2198 | -0.5774 | 0.0246 |
| A4 | LS_decile | 1d | 15 | 0.2477 | 0.0545 | 0.2199 | -0.6034 | 0.0246 |
| A4 | LS_decile | 1d | 30 | 0.1632 | 0.0359 | 0.2199 | -0.6278 | 0.0246 |
| A4 | LS_decile | 1d | 50 | 0.0505 | 0.0111 | 0.2200 | -0.6581 | 0.0246 |
| A4 | LS_quintile | 1d | 0 | 0.5393 | 0.0952 | 0.1764 | -0.4758 | 0.0196 |
| A4 | LS_quintile | 1d | 15 | 0.4554 | 0.0804 | 0.1765 | -0.4827 | 0.0196 |
| A4 | LS_quintile | 1d | 30 | 0.3715 | 0.0656 | 0.1765 | -0.4896 | 0.0196 |
| A4 | LS_quintile | 1d | 50 | 0.2597 | 0.0459 | 0.1766 | -0.4986 | 0.0196 |
| A4 | LO_decile | 1d | 0 | 1.6897 | 0.2176 | 0.1288 | -0.1793 | 0.0146 |
| A4 | LO_decile | 1d | 15 | 1.6038 | 0.2065 | 0.1288 | -0.1806 | 0.0146 |
| A4 | LO_decile | 1d | 30 | 1.5178 | 0.1955 | 0.1288 | -0.1820 | 0.0146 |
| A4 | LO_decile | 1d | 50 | 1.4031 | 0.1807 | 0.1288 | -0.1838 | 0.0146 |
| A4 | LS_decile | 5d | 0 | 0.2849 | 0.0624 | 0.2191 | -0.6019 | 0.0181 |
| A4 | LS_decile | 5d | 15 | 0.2224 | 0.0487 | 0.2190 | -0.6142 | 0.0181 |
| A4 | LS_decile | 5d | 30 | 0.1598 | 0.0350 | 0.2189 | -0.6261 | 0.0181 |
| A4 | LS_decile | 5d | 50 | 0.0764 | 0.0167 | 0.2189 | -0.6461 | 0.0181 |
| A4 | LS_quintile | 5d | 0 | 0.4627 | 0.0814 | 0.1760 | -0.4737 | 0.0151 |
| A4 | LS_quintile | 5d | 15 | 0.3980 | 0.0700 | 0.1759 | -0.4790 | 0.0151 |
| A4 | LS_quintile | 5d | 30 | 0.3332 | 0.0586 | 0.1759 | -0.4844 | 0.0151 |
| A4 | LS_quintile | 5d | 50 | 0.2467 | 0.0434 | 0.1759 | -0.4914 | 0.0151 |
| A4 | LO_decile | 5d | 0 | 1.6484 | 0.2128 | 0.1291 | -0.1827 | 0.0108 |
| A4 | LO_decile | 5d | 15 | 1.5853 | 0.2046 | 0.1291 | -0.1837 | 0.0108 |
| A4 | LO_decile | 5d | 30 | 1.5220 | 0.1965 | 0.1291 | -0.1847 | 0.0108 |
| A4 | LO_decile | 5d | 50 | 1.4373 | 0.1855 | 0.1291 | -0.1860 | 0.0108 |
| A10 | LS_decile | 1d | 0 | 1.7524 | 0.3523 | 0.2010 | -0.1876 | 0.6951 |
| A10 | LS_decile | 1d | 15 | -0.8615 | -0.1733 | 0.2011 | -0.7032 | 0.6951 |
| A10 | LS_decile | 1d | 30 | -3.4626 | -0.6988 | 0.2018 | -0.9888 | 0.6951 |
| A10 | LS_decile | 1d | 50 | -6.8705 | -1.3995 | 0.2037 | -0.9999 | 0.6951 |
| A10 | LS_quintile | 1d | 0 | 1.7627 | 0.2706 | 0.1535 | -0.1177 | 0.6153 |
| A10 | LS_quintile | 1d | 15 | -1.2663 | -0.1945 | 0.1536 | -0.7421 | 0.6153 |
| A10 | LS_quintile | 1d | 30 | -4.2755 | -0.6596 | 0.1543 | -0.9849 | 0.6153 |
| A10 | LS_quintile | 1d | 50 | -8.1959 | -1.2798 | 0.1562 | -0.9997 | 0.6153 |
| A10 | LO_decile | 1d | 0 | 1.0281 | 0.2444 | 0.2377 | -0.2864 | 0.3707 |
| A10 | LO_decile | 1d | 15 | -0.1510 | -0.0359 | 0.2377 | -0.6746 | 0.3707 |
| A10 | LO_decile | 1d | 30 | -1.3293 | -0.3161 | 0.2378 | -0.9098 | 0.3707 |
| A10 | LO_decile | 1d | 50 | -2.8948 | -0.6898 | 0.2383 | -0.9893 | 0.3707 |
| A10 | LS_decile | 5d | 0 | 0.7207 | 0.1423 | 0.1975 | -0.1848 | 0.3058 |
| A10 | LS_decile | 5d | 15 | -0.4472 | -0.0889 | 0.1987 | -0.6275 | 0.3058 |
| A10 | LS_decile | 5d | 30 | -1.5644 | -0.3201 | 0.2046 | -0.8980 | 0.3058 |
| A10 | LS_decile | 5d | 50 | -2.8684 | -0.6284 | 0.2191 | -0.9841 | 0.3058 |
| A10 | LS_quintile | 5d | 0 | 0.9695 | 0.1447 | 0.1492 | -0.1394 | 0.2788 |
| A10 | LS_quintile | 5d | 15 | -0.4388 | -0.0661 | 0.1506 | -0.6057 | 0.2788 |
| A10 | LS_quintile | 5d | 30 | -1.7622 | -0.2768 | 0.1571 | -0.8783 | 0.2788 |
| A10 | LS_quintile | 5d | 50 | -3.2316 | -0.5579 | 0.1726 | -0.9787 | 0.2788 |
| A10 | LO_decile | 5d | 0 | 0.8652 | 0.2117 | 0.2447 | -0.3819 | 0.1544 |
| A10 | LO_decile | 5d | 15 | 0.3879 | 0.0950 | 0.2450 | -0.5972 | 0.1544 |
| A10 | LO_decile | 5d | 30 | -0.0882 | -0.0217 | 0.2462 | -0.7383 | 0.1544 |
| A10 | LO_decile | 5d | 50 | -0.7115 | -0.1774 | 0.2493 | -0.8586 | 0.1544 |
| A2 | LS_decile | 1d | 0 | 1.2920 | 0.3747 | 0.2900 | -0.2867 | 0.3651 |
| A2 | LS_decile | 1d | 15 | 0.3402 | 0.0986 | 0.2899 | -0.4730 | 0.3651 |
| A2 | LS_decile | 1d | 30 | -0.6118 | -0.1774 | 0.2900 | -0.8572 | 0.3651 |
| A2 | LS_decile | 1d | 50 | -1.8797 | -0.5454 | 0.2902 | -0.9848 | 0.3651 |
| A2 | LS_quintile | 1d | 0 | 1.1213 | 0.2670 | 0.2381 | -0.2239 | 0.3127 |
| A2 | LS_quintile | 1d | 15 | 0.1284 | 0.0306 | 0.2381 | -0.5388 | 0.3127 |
| A2 | LS_quintile | 1d | 30 | -0.8641 | -0.2058 | 0.2382 | -0.8867 | 0.3127 |
| A2 | LS_quintile | 1d | 50 | -2.1848 | -0.5210 | 0.2385 | -0.9827 | 0.3127 |
| A2 | LO_decile | 1d | 0 | 1.0360 | 0.3210 | 0.3098 | -0.3253 | 0.2060 |
| A2 | LO_decile | 1d | 15 | 0.5334 | 0.1653 | 0.3098 | -0.5806 | 0.2060 |
| A2 | LO_decile | 1d | 30 | 0.0307 | 0.0095 | 0.3098 | -0.7610 | 0.2060 |
| A2 | LO_decile | 1d | 50 | -0.6396 | -0.1981 | 0.3098 | -0.9073 | 0.2060 |
| A2 | LS_decile | 5d | 0 | 0.7566 | 0.1782 | 0.2355 | -0.3332 | 0.1635 |
| A2 | LS_decile | 5d | 15 | 0.2312 | 0.0546 | 0.2361 | -0.4994 | 0.1635 |
| A2 | LS_decile | 5d | 30 | -0.2900 | -0.0690 | 0.2379 | -0.6605 | 0.1635 |
| A2 | LS_decile | 5d | 50 | -0.9663 | -0.2338 | 0.2419 | -0.8729 | 0.1635 |
| A2 | LS_quintile | 5d | 0 | 0.8009 | 0.1840 | 0.2298 | -0.2100 | 0.1409 |
| A2 | LS_quintile | 5d | 15 | 0.3375 | 0.0775 | 0.2297 | -0.4140 | 0.1409 |
| A2 | LS_quintile | 5d | 30 | -0.1257 | -0.0290 | 0.2305 | -0.6784 | 0.1409 |
| A2 | LS_quintile | 5d | 50 | -0.7341 | -0.1710 | 0.2329 | -0.8626 | 0.1409 |
| A2 | LO_decile | 5d | 0 | 0.8831 | 0.2463 | 0.2789 | -0.4041 | 0.0894 |
| A2 | LO_decile | 5d | 15 | 0.6404 | 0.1787 | 0.2791 | -0.5102 | 0.0894 |
| A2 | LO_decile | 5d | 30 | 0.3975 | 0.1111 | 0.2795 | -0.6139 | 0.0894 |
| A2 | LO_decile | 5d | 50 | 0.0748 | 0.0210 | 0.2805 | -0.7190 | 0.0894 |
| B1 | LS_decile | 1d | 0 | 2.5999 | 0.3952 | 0.1520 | -0.0887 | 0.5825 |
| B1 | LS_decile | 1d | 15 | -0.2972 | -0.0451 | 0.1519 | -0.5249 | 0.5825 |
| B1 | LS_decile | 1d | 30 | -3.1911 | -0.4855 | 0.1521 | -0.9599 | 0.5825 |
| B1 | LS_decile | 1d | 50 | -7.0044 | -1.0727 | 0.1531 | -0.9989 | 0.5825 |
| B1 | LS_quintile | 1d | 0 | 2.3909 | 0.3436 | 0.1437 | -0.0562 | 0.5004 |
| B1 | LS_quintile | 1d | 15 | -0.2411 | -0.0346 | 0.1437 | -0.4750 | 0.5004 |
| B1 | LS_quintile | 1d | 30 | -2.8697 | -0.4129 | 0.1439 | -0.9444 | 0.5004 |
| B1 | LS_quintile | 1d | 50 | -6.3398 | -0.9173 | 0.1447 | -0.9975 | 0.5004 |
| B1 | LO_decile | 1d | 0 | 1.5981 | 0.3300 | 0.2065 | -0.2244 | 0.3032 |
| B1 | LO_decile | 1d | 15 | 0.4883 | 0.1008 | 0.2065 | -0.5585 | 0.3032 |
| B1 | LO_decile | 1d | 30 | -0.6215 | -0.1284 | 0.2065 | -0.8037 | 0.3032 |
| B1 | LO_decile | 1d | 50 | -2.0986 | -0.4339 | 0.2068 | -0.9565 | 0.3032 |
| B1 | LS_decile | 5d | 0 | 1.4189 | 0.1961 | 0.1382 | -0.1149 | 0.2815 |
| B1 | LS_decile | 5d | 15 | -0.1198 | -0.0167 | 0.1397 | -0.4723 | 0.2815 |
| B1 | LS_decile | 5d | 30 | -1.5659 | -0.2296 | 0.1466 | -0.8157 | 0.2815 |
| B1 | LS_decile | 5d | 50 | -3.1517 | -0.5133 | 0.1629 | -0.9674 | 0.2815 |
| B1 | LS_quintile | 5d | 0 | 1.4262 | 0.1946 | 0.1365 | -0.0767 | 0.2528 |
| B1 | LS_quintile | 5d | 15 | 0.0255 | 0.0035 | 0.1368 | -0.4200 | 0.2528 |
| B1 | LS_quintile | 5d | 30 | -1.3255 | -0.1877 | 0.1416 | -0.7797 | 0.2528 |
| B1 | LS_quintile | 5d | 50 | -2.8705 | -0.4425 | 0.1542 | -0.9535 | 0.2528 |
| B1 | LO_decile | 5d | 0 | 1.1671 | 0.2381 | 0.2040 | -0.3287 | 0.1430 |
| B1 | LO_decile | 5d | 15 | 0.6372 | 0.1300 | 0.2040 | -0.4897 | 0.1430 |
| B1 | LO_decile | 5d | 30 | 0.1065 | 0.0218 | 0.2049 | -0.6515 | 0.1430 |
| B1 | LO_decile | 5d | 50 | -0.5893 | -0.1224 | 0.2076 | -0.7908 | 0.1430 |
| C3 | LS_decile | 1d | 0 | 1.1195 | 0.0755 | 0.0675 | -0.0723 | 0.1953 |
| C3 | LS_decile | 1d | 15 | -1.0722 | -0.0721 | 0.0673 | -0.4103 | 0.1953 |
| C3 | LS_decile | 1d | 30 | -3.0264 | -0.2198 | 0.0726 | -0.7520 | 0.1953 |
| C3 | LS_decile | 1d | 50 | -4.8165 | -0.4167 | 0.0865 | -0.9277 | 0.1953 |
| C3 | LS_quintile | 1d | 0 | 1.3158 | 0.0642 | 0.0488 | -0.0448 | 0.1932 |
| C3 | LS_quintile | 1d | 15 | -1.6716 | -0.0819 | 0.0490 | -0.4260 | 0.1932 |
| C3 | LS_quintile | 1d | 30 | -4.0479 | -0.2279 | 0.0563 | -0.7610 | 0.1932 |
| C3 | LS_quintile | 1d | 50 | -5.7683 | -0.4226 | 0.0733 | -0.9296 | 0.1932 |
| C3 | LO_decile | 1d | 0 | -0.1660 | -0.0177 | 0.1064 | -0.2739 | 0.0975 |
| C3 | LO_decile | 1d | 15 | -0.8551 | -0.0913 | 0.1068 | -0.4924 | 0.0975 |
| C3 | LO_decile | 1d | 30 | -1.5262 | -0.1650 | 0.1081 | -0.6663 | 0.0975 |
| C3 | LO_decile | 1d | 50 | -2.3674 | -0.2633 | 0.1112 | -0.8139 | 0.0975 |
| C3 | LS_decile | 5d | 0 | 1.1195 | 0.0755 | 0.0675 | -0.0723 | 0.1953 |
| C3 | LS_decile | 5d | 15 | -1.0722 | -0.0721 | 0.0673 | -0.4103 | 0.1953 |
| C3 | LS_decile | 5d | 30 | -3.0264 | -0.2198 | 0.0726 | -0.7520 | 0.1953 |
| C3 | LS_decile | 5d | 50 | -4.8165 | -0.4167 | 0.0865 | -0.9277 | 0.1953 |
| C3 | LS_quintile | 5d | 0 | 1.3158 | 0.0642 | 0.0488 | -0.0448 | 0.1932 |
| C3 | LS_quintile | 5d | 15 | -1.6716 | -0.0819 | 0.0490 | -0.4260 | 0.1932 |
| C3 | LS_quintile | 5d | 30 | -4.0479 | -0.2279 | 0.0563 | -0.7610 | 0.1932 |
| C3 | LS_quintile | 5d | 50 | -5.7683 | -0.4226 | 0.0733 | -0.9296 | 0.1932 |
| C3 | LO_decile | 5d | 0 | -0.1660 | -0.0177 | 0.1064 | -0.2739 | 0.0975 |
| C3 | LO_decile | 5d | 15 | -0.8551 | -0.0913 | 0.1068 | -0.4924 | 0.0975 |
| C3 | LO_decile | 5d | 30 | -1.5262 | -0.1650 | 0.1081 | -0.6663 | 0.0975 |
| C3 | LO_decile | 5d | 50 | -2.3674 | -0.2633 | 0.1112 | -0.8139 | 0.0975 |
| C3 | LS_decile | 20d | 0 | 1.1195 | 0.0755 | 0.0675 | -0.0723 | 0.1953 |
| C3 | LS_decile | 20d | 15 | -1.0722 | -0.0721 | 0.0673 | -0.4103 | 0.1953 |
| C3 | LS_decile | 20d | 30 | -3.0264 | -0.2198 | 0.0726 | -0.7520 | 0.1953 |
| C3 | LS_decile | 20d | 50 | -4.8165 | -0.4167 | 0.0865 | -0.9277 | 0.1953 |
| C3 | LS_quintile | 20d | 0 | 1.3158 | 0.0642 | 0.0488 | -0.0448 | 0.1932 |
| C3 | LS_quintile | 20d | 15 | -1.6716 | -0.0819 | 0.0490 | -0.4260 | 0.1932 |
| C3 | LS_quintile | 20d | 30 | -4.0479 | -0.2279 | 0.0563 | -0.7610 | 0.1932 |
| C3 | LS_quintile | 20d | 50 | -5.7683 | -0.4226 | 0.0733 | -0.9296 | 0.1932 |
| C3 | LO_decile | 20d | 0 | -0.1660 | -0.0177 | 0.1064 | -0.2739 | 0.0975 |
| C3 | LO_decile | 20d | 15 | -0.8551 | -0.0913 | 0.1068 | -0.4924 | 0.0975 |
| C3 | LO_decile | 20d | 30 | -1.5262 | -0.1650 | 0.1081 | -0.6663 | 0.0975 |
| C3 | LO_decile | 20d | 50 | -2.3674 | -0.2633 | 0.1112 | -0.8139 | 0.0975 |

## 5. Recommended Combination Details

### Signal A3

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.0467 | -0.0120 | 0.2566 | -0.6215 | 0.0521 |
| LS_quintile | -0.2287 | -0.0460 | 0.2011 | -0.5571 | 0.0443 |
| LO_decile | 0.9549 | 0.0857 | 0.0897 | -0.2321 | 0.0273 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.2871 | -0.0757 | 0.2638 | -0.7061 | 0.0348 |
| LS_quintile | -0.3573 | -0.0747 | 0.2091 | -0.6108 | 0.0298 |
| LO_decile | 1.0461 | 0.0979 | 0.0936 | -0.2069 | 0.0171 |

#### 20d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.3721 | -0.1002 | 0.2693 | -0.7261 | 0.0254 |
| LS_quintile | -0.2807 | -0.0597 | 0.2128 | -0.6263 | 0.0211 |
| LO_decile | 0.9512 | 0.0935 | 0.0983 | -0.2079 | 0.0114 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -1.3206 | -0.2616 | -0.2326 |
| year_2021 | 0.9493 | 0.2077 | -0.1100 |
| year_2022 | 1.0323 | 0.2330 | -0.1336 |
| year_2023 | 0.1818 | 0.0371 | -0.2106 |
| year_2024 | 1.1327 | 0.2320 | -0.1048 |
| year_2025 | -0.3026 | -0.0687 | -0.1449 |
| year_2026 | -2.7487 | -1.4484 | -0.6473 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | 0.0224 | 0.0047 | -0.2433 | 0.4256 |
| sub2_2022 | 1.0323 | 0.2330 | -0.1336 | 0.5244 |
| sub3_2023_2024 | 0.6576 | 0.1343 | -0.2106 | 0.5133 |
| sub4_2025_2026 | -1.6240 | -0.6116 | -0.6933 | 0.3659 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -0.7169 | -0.2140 | 0.2984 | -0.8104 | 0.0407 |
| mid | 0.3612 | 0.1278 | 0.3538 | -0.4649 | 0.0408 |
| small | 0.3490 | 0.1009 | 0.2892 | -0.5807 | 0.0358 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.1501 | 0.2527 | -0.5939 |

### Signal A4

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.1632 | 0.0359 | 0.2199 | -0.6278 | 0.0246 |
| LS_quintile | 0.3715 | 0.0656 | 0.1765 | -0.4896 | 0.0196 |
| LO_decile | 1.5178 | 0.1955 | 0.1288 | -0.1820 | 0.0146 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.1598 | 0.0350 | 0.2189 | -0.6261 | 0.0181 |
| LS_quintile | 0.3332 | 0.0586 | 0.1759 | -0.4844 | 0.0151 |
| LO_decile | 1.5220 | 0.1965 | 0.1291 | -0.1847 | 0.0108 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | 0.2158 | 0.0316 | -0.1429 |
| year_2021 | 3.1960 | 0.4997 | -0.0578 |
| year_2022 | 1.7959 | 0.2999 | -0.1208 |
| year_2023 | -0.3266 | -0.0614 | -0.1672 |
| year_2024 | -0.0998 | -0.0165 | -0.1849 |
| year_2025 | -1.3871 | -0.3063 | -0.3702 |
| year_2026 | -0.7953 | -0.3536 | -0.3990 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | 1.9462 | 0.2972 | -0.1429 | 0.5057 |
| sub2_2022 | 1.7959 | 0.2999 | -0.1208 | 0.5447 |
| sub3_2023_2024 | -0.2205 | -0.0390 | -0.2066 | 0.4826 |
| sub4_2025_2026 | -0.9932 | -0.3249 | -0.5742 | 0.4311 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | 0.7165 | 0.2043 | 0.2852 | -0.6987 | 0.0215 |
| mid | 2.1444 | 0.5324 | 0.2483 | -0.1955 | 0.0330 |
| small | 1.8206 | 0.3801 | 0.2088 | -0.1765 | 0.0308 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.0515 | 0.2432 | -0.2117 |

### Signal A10

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.4626 | -0.6988 | 0.2018 | -0.9888 | 0.6951 |
| LS_quintile | -4.2755 | -0.6596 | 0.1543 | -0.9849 | 0.6153 |
| LO_decile | -1.3293 | -0.3161 | 0.2378 | -0.9098 | 0.3707 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -1.5644 | -0.3201 | 0.2046 | -0.8980 | 0.3058 |
| LS_quintile | -1.7622 | -0.2768 | 0.1571 | -0.8783 | 0.2788 |
| LO_decile | -0.0882 | -0.0217 | 0.2462 | -0.7383 | 0.1544 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -0.1707 | -0.0284 | -0.1234 |
| year_2021 | -2.6906 | -0.4943 | -0.4261 |
| year_2022 | -2.0478 | -0.3793 | -0.3396 |
| year_2023 | -2.7732 | -0.4576 | -0.4075 |
| year_2024 | -2.0719 | -0.4079 | -0.3708 |
| year_2025 | -1.5277 | -0.3256 | -0.3517 |
| year_2026 | 0.1733 | 0.0564 | -0.1350 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.6549 | -0.2928 | -0.4666 | 0.3959 |
| sub2_2022 | -2.0478 | -0.3793 | -0.3396 | 0.4634 |
| sub3_2023_2024 | -2.3855 | -0.4328 | -0.6114 | 0.4315 |
| sub4_2025_2026 | -0.6663 | -0.1753 | -0.3957 | 0.3684 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.0542 | -0.4066 | 0.3857 | -0.9705 | 0.3101 |
| mid | -1.5279 | -0.4177 | 0.2734 | -0.9537 | 0.3072 |
| small | -0.9514 | -0.2182 | 0.2293 | -0.8404 | 0.3061 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.2697 | 0.2889 | -0.9334 |

### Signal A2

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.6118 | -0.1774 | 0.2900 | -0.8572 | 0.3651 |
| LS_quintile | -0.8641 | -0.2058 | 0.2382 | -0.8867 | 0.3127 |
| LO_decile | 0.0307 | 0.0095 | 0.3098 | -0.7610 | 0.2060 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.2900 | -0.0690 | 0.2379 | -0.6605 | 0.1635 |
| LS_quintile | -0.1257 | -0.0290 | 0.2305 | -0.6784 | 0.1409 |
| LO_decile | 0.3975 | 0.1111 | 0.2795 | -0.6139 | 0.0894 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -0.6105 | -0.1105 | -0.1465 |
| year_2021 | -1.7821 | -0.3500 | -0.3245 |
| year_2022 | -0.4950 | -0.1019 | -0.2085 |
| year_2023 | -1.1346 | -0.2501 | -0.4225 |
| year_2024 | 0.0303 | 0.0063 | -0.1719 |
| year_2025 | -0.3816 | -0.0910 | -0.2803 |
| year_2026 | 1.6470 | 0.6759 | -0.1099 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.2982 | -0.2464 | -0.4238 | 0.4439 |
| sub2_2022 | -0.4950 | -0.1019 | -0.2085 | 0.5488 |
| sub3_2023_2024 | -0.5704 | -0.1221 | -0.4225 | 0.4703 |
| sub4_2025_2026 | 0.6633 | 0.2108 | -0.2971 | 0.3534 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.2391 | -0.3881 | 0.3132 | -0.9411 | 0.1676 |
| mid | 0.5065 | 0.2357 | 0.4653 | -0.5943 | 0.1659 |
| small | 0.4771 | 0.1332 | 0.2793 | -0.3424 | 0.1659 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.1368 | 0.3149 | -0.4346 |

### Signal B1

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.1911 | -0.4855 | 0.1521 | -0.9599 | 0.5825 |
| LS_quintile | -2.8697 | -0.4129 | 0.1439 | -0.9444 | 0.5004 |
| LO_decile | -0.6215 | -0.1284 | 0.2065 | -0.8037 | 0.3032 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -1.5659 | -0.2296 | 0.1466 | -0.8157 | 0.2815 |
| LS_quintile | -1.3255 | -0.1877 | 0.1416 | -0.7797 | 0.2528 |
| LO_decile | 0.1065 | 0.0218 | 0.2049 | -0.6515 | 0.1430 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | 0.8702 | 0.1460 | -0.1201 |
| year_2021 | -2.8520 | -0.4004 | -0.3422 |
| year_2022 | -2.7650 | -0.3646 | -0.3282 |
| year_2023 | -3.5356 | -0.4372 | -0.3668 |
| year_2024 | -0.8056 | -0.1152 | -0.1688 |
| year_2025 | -1.0668 | -0.1652 | -0.2098 |
| year_2026 | -0.8889 | -0.1531 | -0.1461 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.0685 | -0.1641 | -0.3920 | 0.4714 |
| sub2_2022 | -2.7650 | -0.3646 | -0.3282 | 0.4268 |
| sub3_2023_2024 | -2.0648 | -0.2765 | -0.4603 | 0.4601 |
| sub4_2025_2026 | -0.9922 | -0.1605 | -0.2843 | 0.3534 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.7684 | -0.4183 | 0.2366 | -0.9540 | 0.2873 |
| mid | -0.9761 | -0.2071 | 0.2122 | -0.8317 | 0.2900 |
| small | -0.8201 | -0.1239 | 0.1510 | -0.6502 | 0.2738 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.2261 | 0.2682 | -0.8430 |

### Signal C3

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0264 | -0.2198 | 0.0726 | -0.7520 | 0.1953 |
| LS_quintile | -4.0479 | -0.2279 | 0.0563 | -0.7610 | 0.1932 |
| LO_decile | -1.5262 | -0.1650 | 0.1081 | -0.6663 | 0.0975 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0264 | -0.2198 | 0.0726 | -0.7520 | 0.1953 |
| LS_quintile | -4.0479 | -0.2279 | 0.0563 | -0.7610 | 0.1932 |
| LO_decile | -1.5262 | -0.1650 | 0.1081 | -0.6663 | 0.0975 |

#### 20d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0264 | -0.2198 | 0.0726 | -0.7520 | 0.1953 |
| LS_quintile | -4.0479 | -0.2279 | 0.0563 | -0.7610 | 0.1932 |
| LO_decile | -1.5262 | -0.1650 | 0.1081 | -0.6663 | 0.0975 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -2.7036 | -0.1110 | -0.0869 |
| year_2021 | -3.3632 | -0.2416 | -0.2137 |
| year_2022 | -3.7989 | -0.3485 | -0.2914 |
| year_2023 | -3.5699 | -0.1884 | -0.1515 |
| year_2024 | -2.8012 | -0.1648 | -0.1544 |
| year_2025 | -3.8463 | -0.3205 | -0.2676 |
| year_2026 | -0.9961 | -0.0938 | -0.0887 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -3.0569 | -0.1851 | -0.2820 | 0.0389 |
| sub2_2022 | -3.7989 | -0.3485 | -0.2914 | 0.0447 |
| sub3_2023_2024 | -3.1637 | -0.1766 | -0.2779 | 0.0389 |
| sub4_2025_2026 | -2.6309 | -0.2313 | -0.3110 | 0.0301 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.5917 | -0.1643 | 0.1032 | -0.6712 | 0.1957 |
| mid | -2.4039 | -0.2434 | 0.1013 | -0.7915 | 0.1955 |
| small | -3.1348 | -0.2411 | 0.0769 | -0.7889 | 0.1952 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.4130 | 0.2684 | -1.5388 |


## 6. Cross-signal Verdict Table
| signal_id | rebalance | gate_a_30bp_sharpe | gate_b_subperiod | gate_c_lo_alpha | verdict | ls_decile_30bp_sharpe | subperiod_min_sharpe | lo_decile_30bp_alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -0.2871 | -1.6240 | -0.1501 |
| A3 | 20d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -0.3721 | -1.7021 | -0.1544 |
| C3 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -3.0264 | -3.7989 | -0.4130 |
| C3 | 20d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -3.0264 | -3.7989 | -0.4130 |
| A4 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | 0.1598 | -0.9932 | -0.0515 |
| A10 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -1.5644 | -2.3855 | -0.2697 |
| A2 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -0.2900 | -1.2982 | -0.1368 |
| B1 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -1.5659 | -2.7650 | -0.2261 |

## 7. Reference: Option A Baseline
- LS_decile 5d 30bp Sharpe: -3.24.
- LO_decile 5d 30bp alpha: -22.3%.
- Verdict: FAIL (already discarded).

## 8. C3 Sparsity
- avg_exposure_pct: 12.3%
- C3 has shorter exposure because non-stress days are cash by rule; annualized Sharpe has this exposure caveat.

## 9. Caveats
- Several tested signals have non-trivial IC time-series correlation from Step 8.3.
- C3 uses sign flip after observing negative IC; this post-hoc sign flip risk is explicitly noted.
- Equal-weight portfolios, alive-only universe, flat bps costs, and unavailable market-cap data remain structural caveats.

## 10. Artifacts
- `v2/data/cache/backtest_batch/all_metrics.parquet`
- `v2/data/cache/backtest_batch/option_<signal>_metrics.parquet`
- `v2/data/cache/backtest_batch/option_<signal>_pnl_daily.parquet`

## Gate
Step 8.4 raw measurement complete. PASS/FAIL labels are automatically applied, but standalone entry, combination, and discard decisions are user-owned.
