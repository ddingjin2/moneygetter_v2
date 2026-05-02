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
| A3 | LS_decile | 1d | 0 | 0.5999 | 0.1352 | 0.2253 | -0.2969 | 0.0538 |
| A3 | LS_decile | 1d | 15 | 0.4194 | 0.0945 | 0.2253 | -0.3225 | 0.0538 |
| A3 | LS_decile | 1d | 30 | 0.2388 | 0.0538 | 0.2253 | -0.3580 | 0.0538 |
| A3 | LS_decile | 1d | 50 | -0.0020 | -0.0005 | 0.2254 | -0.4024 | 0.0538 |
| A3 | LS_quintile | 1d | 0 | 0.4134 | 0.0737 | 0.1783 | -0.2884 | 0.0458 |
| A3 | LS_quintile | 1d | 15 | 0.2191 | 0.0391 | 0.1783 | -0.3059 | 0.0458 |
| A3 | LS_quintile | 1d | 30 | 0.0249 | 0.0044 | 0.1783 | -0.3359 | 0.0458 |
| A3 | LS_quintile | 1d | 50 | -0.2341 | -0.0418 | 0.1784 | -0.3740 | 0.0458 |
| A3 | LO_decile | 1d | 0 | 1.4078 | 0.1211 | 0.0860 | -0.1353 | 0.0284 |
| A3 | LO_decile | 1d | 15 | 1.1588 | 0.0996 | 0.0859 | -0.1742 | 0.0284 |
| A3 | LO_decile | 1d | 30 | 0.9093 | 0.0781 | 0.0859 | -0.2321 | 0.0284 |
| A3 | LO_decile | 1d | 50 | 0.5762 | 0.0495 | 0.0859 | -0.3038 | 0.0284 |
| A3 | LS_decile | 5d | 0 | 0.3616 | 0.0804 | 0.2223 | -0.3228 | 0.0357 |
| A3 | LS_decile | 5d | 15 | 0.2401 | 0.0534 | 0.2224 | -0.3461 | 0.0357 |
| A3 | LS_decile | 5d | 30 | 0.1187 | 0.0264 | 0.2225 | -0.3686 | 0.0357 |
| A3 | LS_decile | 5d | 50 | -0.0431 | -0.0096 | 0.2227 | -0.3974 | 0.0357 |
| A3 | LS_quintile | 5d | 0 | 0.2308 | 0.0406 | 0.1759 | -0.3010 | 0.0305 |
| A3 | LS_quintile | 5d | 15 | 0.0995 | 0.0175 | 0.1760 | -0.3210 | 0.0305 |
| A3 | LS_quintile | 5d | 30 | -0.0317 | -0.0056 | 0.1761 | -0.3405 | 0.0305 |
| A3 | LS_quintile | 5d | 50 | -0.2064 | -0.0364 | 0.1763 | -0.3656 | 0.0305 |
| A3 | LO_decile | 5d | 0 | 1.3083 | 0.1168 | 0.0893 | -0.1637 | 0.0176 |
| A3 | LO_decile | 5d | 15 | 1.1595 | 0.1035 | 0.0892 | -0.1846 | 0.0176 |
| A3 | LO_decile | 5d | 30 | 1.0102 | 0.0902 | 0.0893 | -0.2069 | 0.0176 |
| A3 | LO_decile | 5d | 50 | 0.8106 | 0.0724 | 0.0893 | -0.2409 | 0.0176 |
| A3 | LS_decile | 20d | 0 | 0.2678 | 0.0577 | 0.2156 | -0.3273 | 0.0262 |
| A3 | LS_decile | 20d | 15 | 0.1758 | 0.0379 | 0.2157 | -0.3452 | 0.0262 |
| A3 | LS_decile | 20d | 30 | 0.0839 | 0.0181 | 0.2160 | -0.3626 | 0.0262 |
| A3 | LS_decile | 20d | 50 | -0.0383 | -0.0083 | 0.2166 | -0.3851 | 0.0262 |
| A3 | LS_quintile | 20d | 0 | 0.3564 | 0.0619 | 0.1738 | -0.2887 | 0.0217 |
| A3 | LS_quintile | 20d | 15 | 0.2619 | 0.0456 | 0.1740 | -0.3039 | 0.0217 |
| A3 | LS_quintile | 20d | 30 | 0.1675 | 0.0292 | 0.1743 | -0.3188 | 0.0217 |
| A3 | LS_quintile | 20d | 50 | 0.0421 | 0.0074 | 0.1749 | -0.3382 | 0.0217 |
| A3 | LO_decile | 20d | 0 | 1.1017 | 0.1035 | 0.0940 | -0.1784 | 0.0118 |
| A3 | LO_decile | 20d | 15 | 1.0069 | 0.0946 | 0.0940 | -0.1933 | 0.0118 |
| A3 | LO_decile | 20d | 30 | 0.9113 | 0.0857 | 0.0941 | -0.2079 | 0.0118 |
| A3 | LO_decile | 20d | 50 | 0.7833 | 0.0739 | 0.0943 | -0.2271 | 0.0118 |
| A4 | LS_decile | 1d | 0 | 0.3617 | 0.0692 | 0.1913 | -0.4630 | 0.0246 |
| A4 | LS_decile | 1d | 15 | 0.2645 | 0.0506 | 0.1913 | -0.4952 | 0.0246 |
| A4 | LS_decile | 1d | 30 | 0.1673 | 0.0320 | 0.1914 | -0.5255 | 0.0246 |
| A4 | LS_decile | 1d | 50 | 0.0378 | 0.0072 | 0.1914 | -0.5631 | 0.0246 |
| A4 | LS_quintile | 1d | 0 | 0.5908 | 0.0898 | 0.1520 | -0.3836 | 0.0196 |
| A4 | LS_quintile | 1d | 15 | 0.4932 | 0.0750 | 0.1520 | -0.3914 | 0.0196 |
| A4 | LS_quintile | 1d | 30 | 0.3957 | 0.0602 | 0.1521 | -0.3992 | 0.0196 |
| A4 | LS_quintile | 1d | 50 | 0.2657 | 0.0404 | 0.1522 | -0.4093 | 0.0196 |
| A4 | LO_decile | 1d | 0 | 1.9000 | 0.2364 | 0.1244 | -0.1649 | 0.0145 |
| A4 | LO_decile | 1d | 15 | 1.8116 | 0.2254 | 0.1244 | -0.1662 | 0.0145 |
| A4 | LO_decile | 1d | 30 | 1.7231 | 0.2144 | 0.1244 | -0.1674 | 0.0145 |
| A4 | LO_decile | 1d | 50 | 1.6050 | 0.1997 | 0.1244 | -0.1692 | 0.0145 |
| A4 | LS_decile | 5d | 0 | 0.3088 | 0.0588 | 0.1904 | -0.4895 | 0.0181 |
| A4 | LS_decile | 5d | 15 | 0.2371 | 0.0451 | 0.1903 | -0.5040 | 0.0181 |
| A4 | LS_decile | 5d | 30 | 0.1653 | 0.0314 | 0.1902 | -0.5186 | 0.0181 |
| A4 | LS_decile | 5d | 50 | 0.0695 | 0.0132 | 0.1901 | -0.5435 | 0.0181 |
| A4 | LS_quintile | 5d | 0 | 0.4962 | 0.0753 | 0.1517 | -0.3820 | 0.0151 |
| A4 | LS_quintile | 5d | 15 | 0.4209 | 0.0638 | 0.1516 | -0.3880 | 0.0151 |
| A4 | LS_quintile | 5d | 30 | 0.3455 | 0.0524 | 0.1516 | -0.3939 | 0.0151 |
| A4 | LS_quintile | 5d | 50 | 0.2448 | 0.0371 | 0.1516 | -0.4018 | 0.0151 |
| A4 | LO_decile | 5d | 0 | 1.8339 | 0.2292 | 0.1250 | -0.1698 | 0.0107 |
| A4 | LO_decile | 5d | 15 | 1.7694 | 0.2211 | 0.1249 | -0.1709 | 0.0107 |
| A4 | LO_decile | 5d | 30 | 1.7047 | 0.2130 | 0.1249 | -0.1721 | 0.0107 |
| A4 | LO_decile | 5d | 50 | 1.6181 | 0.2022 | 0.1249 | -0.1743 | 0.0107 |
| A10 | LS_decile | 1d | 0 | 2.0114 | 0.4045 | 0.2011 | -0.1573 | 0.7298 |
| A10 | LS_decile | 1d | 15 | -0.7315 | -0.1472 | 0.2012 | -0.6806 | 0.7298 |
| A10 | LS_decile | 1d | 30 | -3.4652 | -0.6989 | 0.2017 | -0.9866 | 0.7298 |
| A10 | LS_decile | 1d | 50 | -7.0717 | -1.4346 | 0.2029 | -0.9998 | 0.7298 |
| A10 | LS_quintile | 1d | 0 | 1.9854 | 0.2854 | 0.1438 | -0.1177 | 0.6460 |
| A10 | LS_quintile | 1d | 15 | -1.4107 | -0.2030 | 0.1439 | -0.7421 | 0.6460 |
| A10 | LS_quintile | 1d | 30 | -4.7875 | -0.6914 | 0.1444 | -0.9844 | 0.6460 |
| A10 | LS_quintile | 1d | 50 | -9.2157 | -1.3426 | 0.1457 | -0.9997 | 0.6460 |
| A10 | LO_decile | 1d | 0 | 1.0678 | 0.2524 | 0.2364 | -0.2864 | 0.3891 |
| A10 | LO_decile | 1d | 15 | -0.1765 | -0.0417 | 0.2364 | -0.6746 | 0.3891 |
| A10 | LO_decile | 1d | 30 | -1.4198 | -0.3359 | 0.2366 | -0.9098 | 0.3891 |
| A10 | LO_decile | 1d | 50 | -3.0730 | -0.7281 | 0.2369 | -0.9893 | 0.3891 |
| A10 | LS_decile | 5d | 0 | 0.8035 | 0.1466 | 0.1824 | -0.1848 | 0.3205 |
| A10 | LS_decile | 5d | 15 | -0.5208 | -0.0957 | 0.1837 | -0.6275 | 0.3205 |
| A10 | LS_decile | 5d | 30 | -1.7762 | -0.3380 | 0.1903 | -0.8980 | 0.3205 |
| A10 | LS_decile | 5d | 50 | -3.2050 | -0.6610 | 0.2062 | -0.9834 | 0.3205 |
| A10 | LS_quintile | 5d | 0 | 0.8542 | 0.1098 | 0.1286 | -0.1394 | 0.2920 |
| A10 | LS_quintile | 5d | 15 | -0.8484 | -0.1110 | 0.1308 | -0.6057 | 0.2920 |
| A10 | LS_quintile | 5d | 30 | -2.3863 | -0.3317 | 0.1390 | -0.8768 | 0.2920 |
| A10 | LS_quintile | 5d | 50 | -3.9731 | -0.6261 | 0.1576 | -0.9778 | 0.2920 |
| A10 | LO_decile | 5d | 0 | 0.8071 | 0.1889 | 0.2340 | -0.3819 | 0.1618 |
| A10 | LO_decile | 5d | 15 | 0.2841 | 0.0665 | 0.2342 | -0.5972 | 0.1618 |
| A10 | LO_decile | 5d | 30 | -0.2371 | -0.0558 | 0.2354 | -0.7383 | 0.1618 |
| A10 | LO_decile | 5d | 50 | -0.9173 | -0.2189 | 0.2387 | -0.8586 | 0.1618 |
| A2 | LS_decile | 1d | 0 | 1.3416 | 0.3047 | 0.2271 | -0.2867 | 0.3830 |
| A2 | LS_decile | 1d | 15 | 0.0669 | 0.0152 | 0.2271 | -0.4730 | 0.3830 |
| A2 | LS_decile | 1d | 30 | -1.2080 | -0.2744 | 0.2271 | -0.8572 | 0.3830 |
| A2 | LS_decile | 1d | 50 | -2.9059 | -0.6604 | 0.2273 | -0.9841 | 0.3830 |
| A2 | LS_quintile | 1d | 0 | 0.9475 | 0.1597 | 0.1685 | -0.2239 | 0.3279 |
| A2 | LS_quintile | 1d | 15 | -0.5232 | -0.0882 | 0.1686 | -0.5388 | 0.3279 |
| A2 | LS_quintile | 1d | 30 | -1.9922 | -0.3361 | 0.1687 | -0.8867 | 0.3279 |
| A2 | LS_quintile | 1d | 50 | -3.9455 | -0.6666 | 0.1689 | -0.9827 | 0.3279 |
| A2 | LO_decile | 1d | 0 | 0.8728 | 0.2226 | 0.2550 | -0.3253 | 0.2161 |
| A2 | LO_decile | 1d | 15 | 0.2323 | 0.0592 | 0.2550 | -0.5806 | 0.2161 |
| A2 | LO_decile | 1d | 30 | -0.4084 | -0.1041 | 0.2549 | -0.7610 | 0.2161 |
| A2 | LO_decile | 1d | 50 | -1.2625 | -0.3219 | 0.2550 | -0.9073 | 0.2161 |
| A2 | LS_decile | 5d | 0 | 0.6005 | 0.1319 | 0.2196 | -0.3332 | 0.1707 |
| A2 | LS_decile | 5d | 15 | 0.0129 | 0.0028 | 0.2203 | -0.4994 | 0.1707 |
| A2 | LS_decile | 5d | 30 | -0.5682 | -0.1262 | 0.2221 | -0.6605 | 0.1707 |
| A2 | LS_decile | 5d | 50 | -1.3170 | -0.2983 | 0.2265 | -0.8729 | 0.1707 |
| A2 | LS_quintile | 5d | 0 | 0.4219 | 0.0679 | 0.1610 | -0.2100 | 0.1471 |
| A2 | LS_quintile | 5d | 15 | -0.2682 | -0.0433 | 0.1614 | -0.4140 | 0.1471 |
| A2 | LS_quintile | 5d | 30 | -0.9473 | -0.1545 | 0.1631 | -0.6784 | 0.1471 |
| A2 | LS_quintile | 5d | 50 | -1.8106 | -0.3027 | 0.1672 | -0.8626 | 0.1471 |
| A2 | LO_decile | 5d | 0 | 0.7204 | 0.1797 | 0.2495 | -0.4041 | 0.0934 |
| A2 | LO_decile | 5d | 15 | 0.4372 | 0.1091 | 0.2496 | -0.5102 | 0.0934 |
| A2 | LO_decile | 5d | 30 | 0.1540 | 0.0385 | 0.2500 | -0.6139 | 0.0934 |
| A2 | LO_decile | 5d | 50 | -0.2216 | -0.0556 | 0.2511 | -0.7190 | 0.0934 |
| B1 | LS_decile | 1d | 0 | 2.8010 | 0.4305 | 0.1537 | -0.0887 | 0.6148 |
| B1 | LS_decile | 1d | 15 | -0.2228 | -0.0342 | 0.1537 | -0.5249 | 0.6148 |
| B1 | LS_decile | 1d | 30 | -3.2457 | -0.4990 | 0.1537 | -0.9596 | 0.6148 |
| B1 | LS_decile | 1d | 50 | -7.2608 | -1.1187 | 0.1541 | -0.9988 | 0.6148 |
| B1 | LS_quintile | 1d | 0 | 2.9499 | 0.3269 | 0.1108 | -0.0562 | 0.5280 |
| B1 | LS_quintile | 1d | 15 | -0.6516 | -0.0722 | 0.1108 | -0.4750 | 0.5280 |
| B1 | LS_quintile | 1d | 30 | -4.2496 | -0.4714 | 0.1109 | -0.9441 | 0.5280 |
| B1 | LS_quintile | 1d | 50 | -9.0207 | -1.0036 | 0.1113 | -0.9975 | 0.5280 |
| B1 | LO_decile | 1d | 0 | 1.6306 | 0.3457 | 0.2120 | -0.2244 | 0.3199 |
| B1 | LO_decile | 1d | 15 | 0.4895 | 0.1038 | 0.2120 | -0.5585 | 0.3199 |
| B1 | LO_decile | 1d | 30 | -0.6511 | -0.1381 | 0.2121 | -0.8037 | 0.3199 |
| B1 | LO_decile | 1d | 50 | -2.1703 | -0.4606 | 0.2122 | -0.9565 | 0.3199 |
| B1 | LS_decile | 5d | 0 | 1.5622 | 0.2203 | 0.1410 | -0.1149 | 0.2959 |
| B1 | LS_decile | 5d | 15 | -0.0241 | -0.0034 | 0.1426 | -0.4723 | 0.2959 |
| B1 | LS_decile | 5d | 30 | -1.5174 | -0.2271 | 0.1497 | -0.8038 | 0.2959 |
| B1 | LS_decile | 5d | 50 | -3.1587 | -0.5254 | 0.1663 | -0.9644 | 0.2959 |
| B1 | LS_quintile | 5d | 0 | 1.7334 | 0.1735 | 0.1001 | -0.0767 | 0.2657 |
| B1 | LS_quintile | 5d | 15 | -0.2680 | -0.0273 | 0.1020 | -0.4200 | 0.2657 |
| B1 | LS_quintile | 5d | 30 | -2.0770 | -0.2282 | 0.1099 | -0.7797 | 0.2657 |
| B1 | LS_quintile | 5d | 50 | -3.8828 | -0.4960 | 0.1278 | -0.9530 | 0.2657 |
| B1 | LO_decile | 5d | 0 | 1.1979 | 0.2498 | 0.2085 | -0.3287 | 0.1504 |
| B1 | LO_decile | 5d | 15 | 0.6527 | 0.1361 | 0.2084 | -0.4897 | 0.1504 |
| B1 | LO_decile | 5d | 30 | 0.1068 | 0.0224 | 0.2094 | -0.6515 | 0.1504 |
| B1 | LO_decile | 5d | 50 | -0.6090 | -0.1292 | 0.2122 | -0.7908 | 0.1504 |
| C3 | LS_decile | 1d | 0 | 1.1647 | 0.0808 | 0.0693 | -0.0723 | 0.2051 |
| C3 | LS_decile | 1d | 15 | -1.0763 | -0.0743 | 0.0691 | -0.4103 | 0.2051 |
| C3 | LS_decile | 1d | 30 | -3.0819 | -0.2294 | 0.0744 | -0.7477 | 0.2051 |
| C3 | LS_decile | 1d | 50 | -4.9301 | -0.4362 | 0.0885 | -0.9258 | 0.2051 |
| C3 | LS_quintile | 1d | 0 | 1.3295 | 0.0665 | 0.0500 | -0.0448 | 0.2029 |
| C3 | LS_quintile | 1d | 15 | -1.7269 | -0.0868 | 0.0503 | -0.4260 | 0.2029 |
| C3 | LS_quintile | 1d | 30 | -4.1604 | -0.2402 | 0.0577 | -0.7600 | 0.2029 |
| C3 | LS_quintile | 1d | 50 | -5.9311 | -0.4447 | 0.0750 | -0.9287 | 0.2029 |
| C3 | LO_decile | 1d | 0 | -0.1830 | -0.0200 | 0.1094 | -0.2739 | 0.1024 |
| C3 | LO_decile | 1d | 15 | -0.8871 | -0.0974 | 0.1098 | -0.4924 | 0.1024 |
| C3 | LO_decile | 1d | 30 | -1.5729 | -0.1748 | 0.1111 | -0.6663 | 0.1024 |
| C3 | LO_decile | 1d | 50 | -2.4330 | -0.2780 | 0.1142 | -0.8139 | 0.1024 |
| C3 | LS_decile | 5d | 0 | 1.1647 | 0.0808 | 0.0693 | -0.0723 | 0.2051 |
| C3 | LS_decile | 5d | 15 | -1.0763 | -0.0743 | 0.0691 | -0.4103 | 0.2051 |
| C3 | LS_decile | 5d | 30 | -3.0819 | -0.2294 | 0.0744 | -0.7477 | 0.2051 |
| C3 | LS_decile | 5d | 50 | -4.9301 | -0.4362 | 0.0885 | -0.9258 | 0.2051 |
| C3 | LS_quintile | 5d | 0 | 1.3295 | 0.0665 | 0.0500 | -0.0448 | 0.2029 |
| C3 | LS_quintile | 5d | 15 | -1.7269 | -0.0868 | 0.0503 | -0.4260 | 0.2029 |
| C3 | LS_quintile | 5d | 30 | -4.1604 | -0.2402 | 0.0577 | -0.7600 | 0.2029 |
| C3 | LS_quintile | 5d | 50 | -5.9311 | -0.4447 | 0.0750 | -0.9287 | 0.2029 |
| C3 | LO_decile | 5d | 0 | -0.1830 | -0.0200 | 0.1094 | -0.2739 | 0.1024 |
| C3 | LO_decile | 5d | 15 | -0.8871 | -0.0974 | 0.1098 | -0.4924 | 0.1024 |
| C3 | LO_decile | 5d | 30 | -1.5729 | -0.1748 | 0.1111 | -0.6663 | 0.1024 |
| C3 | LO_decile | 5d | 50 | -2.4330 | -0.2780 | 0.1142 | -0.8139 | 0.1024 |
| C3 | LS_decile | 20d | 0 | 1.1647 | 0.0808 | 0.0693 | -0.0723 | 0.2051 |
| C3 | LS_decile | 20d | 15 | -1.0763 | -0.0743 | 0.0691 | -0.4103 | 0.2051 |
| C3 | LS_decile | 20d | 30 | -3.0819 | -0.2294 | 0.0744 | -0.7477 | 0.2051 |
| C3 | LS_decile | 20d | 50 | -4.9301 | -0.4362 | 0.0885 | -0.9258 | 0.2051 |
| C3 | LS_quintile | 20d | 0 | 1.3295 | 0.0665 | 0.0500 | -0.0448 | 0.2029 |
| C3 | LS_quintile | 20d | 15 | -1.7269 | -0.0868 | 0.0503 | -0.4260 | 0.2029 |
| C3 | LS_quintile | 20d | 30 | -4.1604 | -0.2402 | 0.0577 | -0.7600 | 0.2029 |
| C3 | LS_quintile | 20d | 50 | -5.9311 | -0.4447 | 0.0750 | -0.9287 | 0.2029 |
| C3 | LO_decile | 20d | 0 | -0.1830 | -0.0200 | 0.1094 | -0.2739 | 0.1024 |
| C3 | LO_decile | 20d | 15 | -0.8871 | -0.0974 | 0.1098 | -0.4924 | 0.1024 |
| C3 | LO_decile | 20d | 30 | -1.5729 | -0.1748 | 0.1111 | -0.6663 | 0.1024 |
| C3 | LO_decile | 20d | 50 | -2.4330 | -0.2780 | 0.1142 | -0.8139 | 0.1024 |

## 5. Recommended Combination Details

### Signal A3

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.2388 | 0.0538 | 0.2253 | -0.3580 | 0.0538 |
| LS_quintile | 0.0249 | 0.0044 | 0.1783 | -0.3359 | 0.0458 |
| LO_decile | 0.9093 | 0.0781 | 0.0859 | -0.2321 | 0.0284 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.1187 | 0.0264 | 0.2225 | -0.3686 | 0.0357 |
| LS_quintile | -0.0317 | -0.0056 | 0.1761 | -0.3405 | 0.0305 |
| LO_decile | 1.0102 | 0.0902 | 0.0893 | -0.2069 | 0.0176 |

#### 20d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.0839 | 0.0181 | 0.2160 | -0.3626 | 0.0262 |
| LS_quintile | 0.1675 | 0.0292 | 0.1743 | -0.3188 | 0.0217 |
| LO_decile | 0.9113 | 0.0857 | 0.0941 | -0.2079 | 0.0118 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -1.3206 | -0.2616 | -0.2326 |
| year_2021 | 0.9493 | 0.2077 | -0.1100 |
| year_2022 | 1.0323 | 0.2330 | -0.1336 |
| year_2023 | 0.1818 | 0.0371 | -0.2106 |
| year_2024 | 1.1327 | 0.2320 | -0.1048 |
| year_2025 | -0.3026 | -0.0687 | -0.1449 |
| year_2026 | -2.7608 | -0.9614 | -0.2423 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | 0.0224 | 0.0047 | -0.2433 | 0.4256 |
| sub2_2022 | 1.0323 | 0.2330 | -0.1336 | 0.5244 |
| sub3_2023_2024 | 0.6576 | 0.1343 | -0.2106 | 0.5133 |
| sub4_2025_2026 | -1.0505 | -0.2733 | -0.3410 | 0.4586 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -0.5700 | -0.1630 | 0.2860 | -0.7383 | 0.0417 |
| mid | 0.2201 | 0.0715 | 0.3249 | -0.6055 | 0.0419 |
| small | 0.9158 | 0.2046 | 0.2234 | -0.2346 | 0.0375 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.1548 | 0.1927 | -0.8030 |

### Signal A4

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.1673 | 0.0320 | 0.1914 | -0.5255 | 0.0246 |
| LS_quintile | 0.3957 | 0.0602 | 0.1521 | -0.3992 | 0.0196 |
| LO_decile | 1.7231 | 0.2144 | 0.1244 | -0.1674 | 0.0145 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.1653 | 0.0314 | 0.1902 | -0.5186 | 0.0181 |
| LS_quintile | 0.3455 | 0.0524 | 0.1516 | -0.3939 | 0.0151 |
| LO_decile | 1.7047 | 0.2130 | 0.1249 | -0.1721 | 0.0107 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | 0.2158 | 0.0316 | -0.1429 |
| year_2021 | 3.1960 | 0.4997 | -0.0578 |
| year_2022 | 1.7959 | 0.2999 | -0.1208 |
| year_2023 | -0.3266 | -0.0614 | -0.1672 |
| year_2024 | -0.0998 | -0.0165 | -0.1849 |
| year_2025 | -1.3871 | -0.3063 | -0.3702 |
| year_2026 | -2.4659 | -0.8856 | -0.2262 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | 1.9462 | 0.2972 | -0.1429 | 0.5057 |
| sub2_2022 | 1.7959 | 0.2999 | -0.1208 | 0.5447 |
| sub3_2023_2024 | -0.2205 | -0.0390 | -0.2066 | 0.4826 |
| sub4_2025_2026 | -1.6960 | -0.4391 | -0.4518 | 0.4108 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | 0.8228 | 0.2145 | 0.2607 | -0.5791 | 0.0217 |
| mid | 2.2453 | 0.5095 | 0.2269 | -0.1411 | 0.0327 |
| small | 1.8291 | 0.3615 | 0.1976 | -0.1080 | 0.0305 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.0320 | 0.1881 | -0.1698 |

### Signal A10

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.4652 | -0.6989 | 0.2017 | -0.9866 | 0.7298 |
| LS_quintile | -4.7875 | -0.6914 | 0.1444 | -0.9844 | 0.6460 |
| LO_decile | -1.4198 | -0.3359 | 0.2366 | -0.9098 | 0.3891 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -1.7762 | -0.3380 | 0.1903 | -0.8980 | 0.3205 |
| LS_quintile | -2.3863 | -0.3317 | 0.1390 | -0.8768 | 0.2920 |
| LO_decile | -0.2371 | -0.0558 | 0.2354 | -0.7383 | 0.1618 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -0.1707 | -0.0284 | -0.1234 |
| year_2021 | -2.6906 | -0.4943 | -0.4261 |
| year_2022 | -2.0478 | -0.3793 | -0.3396 |
| year_2023 | -2.7732 | -0.4576 | -0.4075 |
| year_2024 | -2.0719 | -0.4079 | -0.3708 |
| year_2025 | -1.5277 | -0.3256 | -0.3517 |
| year_2026 | 0.5162 | 0.1316 | -0.1339 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.6549 | -0.2928 | -0.4666 | 0.3959 |
| sub2_2022 | -2.0478 | -0.3793 | -0.3396 | 0.4634 |
| sub3_2023_2024 | -2.3855 | -0.4328 | -0.6114 | 0.4315 |
| sub4_2025_2026 | -0.9886 | -0.2208 | -0.3957 | 0.4618 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.7401 | -0.5052 | 0.2903 | -0.9697 | 0.3251 |
| mid | -1.3886 | -0.3617 | 0.2605 | -0.9200 | 0.3220 |
| small | -1.0323 | -0.1949 | 0.1888 | -0.7802 | 0.3214 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.3007 | 0.2257 | -1.3327 |

### Signal A2

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -1.2080 | -0.2744 | 0.2271 | -0.8572 | 0.3830 |
| LS_quintile | -1.9922 | -0.3361 | 0.1687 | -0.8867 | 0.3279 |
| LO_decile | -0.4084 | -0.1041 | 0.2549 | -0.7610 | 0.2161 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.5682 | -0.1262 | 0.2221 | -0.6605 | 0.1707 |
| LS_quintile | -0.9473 | -0.1545 | 0.1631 | -0.6784 | 0.1471 |
| LO_decile | 0.1540 | 0.0385 | 0.2500 | -0.6139 | 0.0934 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -0.6105 | -0.1105 | -0.1465 |
| year_2021 | -1.7821 | -0.3500 | -0.3245 |
| year_2022 | -0.4950 | -0.1019 | -0.2085 |
| year_2023 | -1.1346 | -0.2501 | -0.4225 |
| year_2024 | 0.0303 | 0.0063 | -0.1719 |
| year_2025 | -0.3816 | -0.0910 | -0.2803 |
| year_2026 | 0.9492 | 0.3739 | -0.1099 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.2982 | -0.2464 | -0.4238 | 0.4439 |
| sub2_2022 | -0.4950 | -0.1019 | -0.2085 | 0.5488 |
| sub3_2023_2024 | -0.5704 | -0.1221 | -0.4225 | 0.4703 |
| sub4_2025_2026 | 0.0556 | 0.0156 | -0.2971 | 0.4331 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.2413 | -0.3930 | 0.3166 | -0.9334 | 0.1753 |
| mid | 0.1094 | 0.0326 | 0.2983 | -0.5899 | 0.1730 |
| small | 0.1024 | 0.0213 | 0.2081 | -0.3372 | 0.1740 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.2064 | 0.2315 | -0.8916 |

### Signal B1

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.2457 | -0.4990 | 0.1537 | -0.9596 | 0.6148 |
| LS_quintile | -4.2496 | -0.4714 | 0.1109 | -0.9441 | 0.5280 |
| LO_decile | -0.6511 | -0.1381 | 0.2121 | -0.8037 | 0.3199 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -1.5174 | -0.2271 | 0.1497 | -0.8038 | 0.2959 |
| LS_quintile | -2.0770 | -0.2282 | 0.1099 | -0.7797 | 0.2657 |
| LO_decile | 0.1068 | 0.0224 | 0.2094 | -0.6515 | 0.1504 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | 0.8702 | 0.1460 | -0.1201 |
| year_2021 | -2.8520 | -0.4004 | -0.3422 |
| year_2022 | -2.7650 | -0.3646 | -0.3282 |
| year_2023 | -3.5356 | -0.4372 | -0.3668 |
| year_2024 | -0.8056 | -0.1152 | -0.1688 |
| year_2025 | -1.0668 | -0.1652 | -0.2098 |
| year_2026 | -0.0537 | -0.0130 | -0.0879 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.0685 | -0.1641 | -0.3920 | 0.4714 |
| sub2_2022 | -2.7650 | -0.3646 | -0.3282 | 0.4268 |
| sub3_2023_2024 | -2.0648 | -0.2765 | -0.4603 | 0.4601 |
| sub4_2025_2026 | -0.7313 | -0.1303 | -0.2381 | 0.4459 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.7190 | -0.4144 | 0.2411 | -0.9472 | 0.3021 |
| mid | -0.9859 | -0.2124 | 0.2155 | -0.8295 | 0.3056 |
| small | -0.7863 | -0.1212 | 0.1542 | -0.6413 | 0.2873 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.2226 | 0.2114 | -1.0528 |

### Signal C3

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0819 | -0.2294 | 0.0744 | -0.7477 | 0.2051 |
| LS_quintile | -4.1604 | -0.2402 | 0.0577 | -0.7600 | 0.2029 |
| LO_decile | -1.5729 | -0.1748 | 0.1111 | -0.6663 | 0.1024 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0819 | -0.2294 | 0.0744 | -0.7477 | 0.2051 |
| LS_quintile | -4.1604 | -0.2402 | 0.0577 | -0.7600 | 0.2029 |
| LO_decile | -1.5729 | -0.1748 | 0.1111 | -0.6663 | 0.1024 |

#### 20d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0819 | -0.2294 | 0.0744 | -0.7477 | 0.2051 |
| LS_quintile | -4.1604 | -0.2402 | 0.0577 | -0.7600 | 0.2029 |
| LO_decile | -1.5729 | -0.1748 | 0.1111 | -0.6663 | 0.1024 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -2.7036 | -0.1110 | -0.0869 |
| year_2021 | -3.3632 | -0.2416 | -0.2137 |
| year_2022 | -3.7989 | -0.3485 | -0.2914 |
| year_2023 | -3.5699 | -0.1884 | -0.1515 |
| year_2024 | -2.8012 | -0.1648 | -0.1544 |
| year_2025 | -3.8463 | -0.3205 | -0.2676 |
| year_2026 | -1.0487 | -0.1442 | -0.0727 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -3.0569 | -0.1851 | -0.2820 | 0.0389 |
| sub2_2022 | -3.7989 | -0.3485 | -0.2914 | 0.0447 |
| sub3_2023_2024 | -3.1637 | -0.1766 | -0.2779 | 0.0389 |
| sub4_2025_2026 | -2.8501 | -0.2801 | -0.2990 | 0.0382 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.6060 | -0.1688 | 0.1051 | -0.6701 | 0.2057 |
| mid | -2.4773 | -0.2575 | 0.1039 | -0.7912 | 0.2053 |
| small | -3.2526 | -0.2563 | 0.0788 | -0.7873 | 0.2051 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.4197 | 0.2147 | -1.9550 |


## 6. Cross-signal Verdict Table
| signal_id | rebalance | gate_a_30bp_sharpe | gate_b_subperiod | gate_c_lo_alpha | verdict | ls_decile_30bp_sharpe | subperiod_min_sharpe | lo_decile_30bp_alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | 0.1187 | -1.0505 | -0.1548 |
| A3 | 20d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | 0.0839 | -1.1086 | -0.1592 |
| C3 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -3.0819 | -3.7989 | -0.4197 |
| C3 | 20d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -3.0819 | -3.7989 | -0.4197 |
| A4 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | 0.1653 | -1.6960 | -0.0320 |
| A10 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -1.7762 | -2.3855 | -0.3007 |
| A2 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -0.5682 | -1.2982 | -0.2064 |
| B1 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -1.5174 | -2.7650 | -0.2226 |

## 7. Reference: Option A Baseline
- LS_decile 5d 30bp Sharpe: -3.24.
- LO_decile 5d 30bp alpha: -22.3%.
- Verdict: FAIL (already discarded).

## 8. C3 Sparsity
- avg_exposure_pct: 13.0%
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
