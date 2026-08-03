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
| A3 | LS_decile | 1d | 0 | 0.2628 | 0.0682 | 0.2594 | -0.5834 | 0.0532 |
| A3 | LS_decile | 1d | 15 | 0.1078 | 0.0280 | 0.2594 | -0.5996 | 0.0532 |
| A3 | LS_decile | 1d | 30 | -0.0472 | -0.0122 | 0.2594 | -0.6215 | 0.0532 |
| A3 | LS_decile | 1d | 50 | -0.2539 | -0.0659 | 0.2594 | -0.6488 | 0.0532 |
| A3 | LS_quintile | 1d | 0 | 0.1057 | 0.0215 | 0.2032 | -0.5238 | 0.0453 |
| A3 | LS_quintile | 1d | 15 | -0.0627 | -0.0127 | 0.2032 | -0.5363 | 0.0453 |
| A3 | LS_quintile | 1d | 30 | -0.2311 | -0.0470 | 0.2032 | -0.5571 | 0.0453 |
| A3 | LS_quintile | 1d | 50 | -0.4556 | -0.0926 | 0.2033 | -0.5835 | 0.0453 |
| A3 | LO_decile | 1d | 0 | 1.4299 | 0.1297 | 0.0907 | -0.1353 | 0.0279 |
| A3 | LO_decile | 1d | 15 | 1.1977 | 0.1086 | 0.0907 | -0.1742 | 0.0279 |
| A3 | LO_decile | 1d | 30 | 0.9651 | 0.0875 | 0.0907 | -0.2321 | 0.0279 |
| A3 | LO_decile | 1d | 50 | 0.6547 | 0.0594 | 0.0907 | -0.3038 | 0.0279 |
| A3 | LS_decile | 5d | 0 | -0.0884 | -0.0236 | 0.2665 | -0.6836 | 0.0356 |
| A3 | LS_decile | 5d | 15 | -0.1893 | -0.0505 | 0.2665 | -0.6951 | 0.0356 |
| A3 | LS_decile | 5d | 30 | -0.2902 | -0.0773 | 0.2666 | -0.7061 | 0.0356 |
| A3 | LS_decile | 5d | 50 | -0.4243 | -0.1132 | 0.2668 | -0.7203 | 0.0356 |
| A3 | LS_quintile | 5d | 0 | -0.1434 | -0.0303 | 0.2113 | -0.5864 | 0.0304 |
| A3 | LS_quintile | 5d | 15 | -0.2523 | -0.0533 | 0.2113 | -0.5988 | 0.0304 |
| A3 | LS_quintile | 5d | 30 | -0.3611 | -0.0763 | 0.2113 | -0.6108 | 0.0304 |
| A3 | LS_quintile | 5d | 50 | -0.5060 | -0.1070 | 0.2115 | -0.6262 | 0.0304 |
| A3 | LO_decile | 5d | 0 | 1.3362 | 0.1263 | 0.0945 | -0.1637 | 0.0174 |
| A3 | LO_decile | 5d | 15 | 1.1970 | 0.1132 | 0.0945 | -0.1846 | 0.0174 |
| A3 | LO_decile | 5d | 30 | 1.0574 | 0.1000 | 0.0946 | -0.2069 | 0.0174 |
| A3 | LO_decile | 5d | 50 | 0.8706 | 0.0824 | 0.0947 | -0.2409 | 0.0174 |
| A3 | LS_decile | 20d | 0 | -0.2320 | -0.0631 | 0.2720 | -0.7109 | 0.0260 |
| A3 | LS_decile | 20d | 15 | -0.3041 | -0.0827 | 0.2720 | -0.7186 | 0.0260 |
| A3 | LS_decile | 20d | 30 | -0.3761 | -0.1024 | 0.2722 | -0.7261 | 0.0260 |
| A3 | LS_decile | 20d | 50 | -0.4716 | -0.1286 | 0.2726 | -0.7362 | 0.0260 |
| A3 | LS_quintile | 20d | 0 | -0.1322 | -0.0284 | 0.2148 | -0.6074 | 0.0216 |
| A3 | LS_quintile | 20d | 15 | -0.2081 | -0.0447 | 0.2149 | -0.6169 | 0.0216 |
| A3 | LS_quintile | 20d | 30 | -0.2837 | -0.0610 | 0.2151 | -0.6263 | 0.0216 |
| A3 | LS_quintile | 20d | 50 | -0.3840 | -0.0828 | 0.2155 | -0.6384 | 0.0216 |
| A3 | LO_decile | 20d | 0 | 1.1407 | 0.1132 | 0.0992 | -0.1784 | 0.0117 |
| A3 | LO_decile | 20d | 15 | 1.0513 | 0.1043 | 0.0993 | -0.1933 | 0.0117 |
| A3 | LO_decile | 20d | 30 | 0.9613 | 0.0955 | 0.0993 | -0.2079 | 0.0117 |
| A3 | LO_decile | 20d | 50 | 0.8408 | 0.0837 | 0.0996 | -0.2271 | 0.0117 |
| A4 | LS_decile | 1d | 0 | 0.3691 | 0.0774 | 0.2098 | -0.5774 | 0.0245 |
| A4 | LS_decile | 1d | 15 | 0.2809 | 0.0589 | 0.2099 | -0.6034 | 0.0245 |
| A4 | LS_decile | 1d | 30 | 0.1927 | 0.0405 | 0.2099 | -0.6278 | 0.0245 |
| A4 | LS_decile | 1d | 50 | 0.0752 | 0.0158 | 0.2100 | -0.6581 | 0.0245 |
| A4 | LS_quintile | 1d | 0 | 0.5965 | 0.1013 | 0.1697 | -0.4758 | 0.0195 |
| A4 | LS_quintile | 1d | 15 | 0.5097 | 0.0865 | 0.1698 | -0.4827 | 0.0195 |
| A4 | LS_quintile | 1d | 30 | 0.4228 | 0.0718 | 0.1698 | -0.4896 | 0.0195 |
| A4 | LS_quintile | 1d | 50 | 0.3071 | 0.0522 | 0.1699 | -0.4986 | 0.0195 |
| A4 | LO_decile | 1d | 0 | 1.6684 | 0.2143 | 0.1285 | -0.1793 | 0.0145 |
| A4 | LO_decile | 1d | 15 | 1.5829 | 0.2034 | 0.1285 | -0.1806 | 0.0145 |
| A4 | LO_decile | 1d | 30 | 1.4975 | 0.1924 | 0.1285 | -0.1820 | 0.0145 |
| A4 | LO_decile | 1d | 50 | 1.3834 | 0.1778 | 0.1285 | -0.1838 | 0.0145 |
| A4 | LS_decile | 5d | 0 | 0.3178 | 0.0663 | 0.2086 | -0.6019 | 0.0181 |
| A4 | LS_decile | 5d | 15 | 0.2523 | 0.0526 | 0.2086 | -0.6142 | 0.0181 |
| A4 | LS_decile | 5d | 30 | 0.1867 | 0.0389 | 0.2085 | -0.6261 | 0.0181 |
| A4 | LS_decile | 5d | 50 | 0.0992 | 0.0207 | 0.2084 | -0.6461 | 0.0181 |
| A4 | LS_quintile | 5d | 0 | 0.5243 | 0.0887 | 0.1692 | -0.4737 | 0.0151 |
| A4 | LS_quintile | 5d | 15 | 0.4571 | 0.0773 | 0.1691 | -0.4790 | 0.0151 |
| A4 | LS_quintile | 5d | 30 | 0.3899 | 0.0659 | 0.1691 | -0.4844 | 0.0151 |
| A4 | LS_quintile | 5d | 50 | 0.3002 | 0.0508 | 0.1691 | -0.4914 | 0.0151 |
| A4 | LO_decile | 5d | 0 | 1.6153 | 0.2084 | 0.1290 | -0.1827 | 0.0108 |
| A4 | LO_decile | 5d | 15 | 1.5524 | 0.2002 | 0.1290 | -0.1837 | 0.0108 |
| A4 | LO_decile | 5d | 30 | 1.4894 | 0.1921 | 0.1290 | -0.1847 | 0.0108 |
| A4 | LO_decile | 5d | 50 | 1.4052 | 0.1812 | 0.1290 | -0.1860 | 0.0108 |
| A10 | LS_decile | 1d | 0 | 1.7713 | 0.3598 | 0.2031 | -0.1876 | 0.7100 |
| A10 | LS_decile | 1d | 15 | -0.8707 | -0.1770 | 0.2032 | -0.7032 | 0.7100 |
| A10 | LS_decile | 1d | 30 | -3.5013 | -0.7138 | 0.2039 | -0.9888 | 0.7100 |
| A10 | LS_decile | 1d | 50 | -6.9578 | -1.4295 | 0.2055 | -0.9999 | 0.7100 |
| A10 | LS_quintile | 1d | 0 | 1.7818 | 0.2764 | 0.1551 | -0.1177 | 0.6285 |
| A10 | LS_quintile | 1d | 15 | -1.2799 | -0.1987 | 0.1552 | -0.7421 | 0.6285 |
| A10 | LS_quintile | 1d | 30 | -4.3245 | -0.6738 | 0.1558 | -0.9849 | 0.6285 |
| A10 | LS_quintile | 1d | 50 | -8.3071 | -1.3073 | 0.1574 | -0.9997 | 0.6285 |
| A10 | LO_decile | 1d | 0 | 1.0391 | 0.2496 | 0.2402 | -0.2864 | 0.3786 |
| A10 | LO_decile | 1d | 15 | -0.1526 | -0.0367 | 0.2402 | -0.6746 | 0.3786 |
| A10 | LO_decile | 1d | 30 | -1.3435 | -0.3229 | 0.2403 | -0.9098 | 0.3786 |
| A10 | LO_decile | 1d | 50 | -2.9267 | -0.7046 | 0.2407 | -0.9893 | 0.3786 |
| A10 | LS_decile | 5d | 0 | 0.7284 | 0.1454 | 0.1996 | -0.1848 | 0.3124 |
| A10 | LS_decile | 5d | 15 | -0.4520 | -0.0908 | 0.2008 | -0.6275 | 0.3124 |
| A10 | LS_decile | 5d | 30 | -1.5812 | -0.3269 | 0.2068 | -0.8980 | 0.3124 |
| A10 | LS_decile | 5d | 50 | -2.9000 | -0.6418 | 0.2213 | -0.9841 | 0.3124 |
| A10 | LS_quintile | 5d | 0 | 0.9799 | 0.1478 | 0.1508 | -0.1394 | 0.2848 |
| A10 | LS_quintile | 5d | 15 | -0.4435 | -0.0675 | 0.1522 | -0.6057 | 0.2848 |
| A10 | LS_quintile | 5d | 30 | -1.7813 | -0.2828 | 0.1588 | -0.8783 | 0.2848 |
| A10 | LS_quintile | 5d | 50 | -3.2675 | -0.5698 | 0.1744 | -0.9787 | 0.2848 |
| A10 | LO_decile | 5d | 0 | 0.8744 | 0.2163 | 0.2473 | -0.3819 | 0.1577 |
| A10 | LO_decile | 5d | 15 | 0.3920 | 0.0971 | 0.2476 | -0.5972 | 0.1577 |
| A10 | LO_decile | 5d | 30 | -0.0892 | -0.0222 | 0.2488 | -0.7383 | 0.1577 |
| A10 | LO_decile | 5d | 50 | -0.7191 | -0.1812 | 0.2519 | -0.8586 | 0.1577 |
| A2 | LS_decile | 1d | 0 | 1.3059 | 0.3827 | 0.2931 | -0.2867 | 0.3730 |
| A2 | LS_decile | 1d | 15 | 0.3438 | 0.1007 | 0.2930 | -0.4730 | 0.3730 |
| A2 | LS_decile | 1d | 30 | -0.6184 | -0.1812 | 0.2931 | -0.8572 | 0.3730 |
| A2 | LS_decile | 1d | 50 | -1.9000 | -0.5572 | 0.2932 | -0.9848 | 0.3730 |
| A2 | LS_quintile | 1d | 0 | 1.1334 | 0.2727 | 0.2406 | -0.2239 | 0.3194 |
| A2 | LS_quintile | 1d | 15 | 0.1298 | 0.0312 | 0.2406 | -0.5388 | 0.3194 |
| A2 | LS_quintile | 1d | 30 | -0.8733 | -0.2102 | 0.2407 | -0.8867 | 0.3194 |
| A2 | LS_quintile | 1d | 50 | -2.2086 | -0.5322 | 0.2410 | -0.9827 | 0.3194 |
| A2 | LO_decile | 1d | 0 | 1.0471 | 0.3279 | 0.3131 | -0.3253 | 0.2104 |
| A2 | LO_decile | 1d | 15 | 0.5391 | 0.1688 | 0.3131 | -0.5806 | 0.2104 |
| A2 | LO_decile | 1d | 30 | 0.0310 | 0.0097 | 0.3131 | -0.7610 | 0.2104 |
| A2 | LO_decile | 1d | 50 | -0.6464 | -0.2024 | 0.3131 | -0.9073 | 0.2104 |
| A2 | LS_decile | 5d | 0 | 0.7647 | 0.1820 | 0.2380 | -0.3332 | 0.1670 |
| A2 | LS_decile | 5d | 15 | 0.2337 | 0.0558 | 0.2386 | -0.4994 | 0.1670 |
| A2 | LS_decile | 5d | 30 | -0.2931 | -0.0705 | 0.2404 | -0.6605 | 0.1670 |
| A2 | LS_decile | 5d | 50 | -0.9767 | -0.2388 | 0.2445 | -0.8729 | 0.1670 |
| A2 | LS_quintile | 5d | 0 | 0.8095 | 0.1880 | 0.2322 | -0.2100 | 0.1439 |
| A2 | LS_quintile | 5d | 15 | 0.3411 | 0.0792 | 0.2322 | -0.4140 | 0.1439 |
| A2 | LS_quintile | 5d | 30 | -0.1270 | -0.0296 | 0.2330 | -0.6784 | 0.1439 |
| A2 | LS_quintile | 5d | 50 | -0.7419 | -0.1747 | 0.2354 | -0.8626 | 0.1439 |
| A2 | LO_decile | 5d | 0 | 0.8925 | 0.2516 | 0.2819 | -0.4041 | 0.0913 |
| A2 | LO_decile | 5d | 15 | 0.6472 | 0.1825 | 0.2820 | -0.5102 | 0.0913 |
| A2 | LO_decile | 5d | 30 | 0.4018 | 0.1135 | 0.2825 | -0.6139 | 0.0913 |
| A2 | LO_decile | 5d | 50 | 0.0756 | 0.0214 | 0.2835 | -0.7190 | 0.0913 |
| B1 | LS_decile | 1d | 0 | 2.6284 | 0.4037 | 0.1536 | -0.0887 | 0.5950 |
| B1 | LS_decile | 1d | 15 | -0.3004 | -0.0461 | 0.1535 | -0.5249 | 0.5950 |
| B1 | LS_decile | 1d | 30 | -3.2266 | -0.4959 | 0.1537 | -0.9599 | 0.5950 |
| B1 | LS_decile | 1d | 50 | -7.0939 | -1.0957 | 0.1545 | -0.9989 | 0.5950 |
| B1 | LS_quintile | 1d | 0 | 2.4170 | 0.3510 | 0.1452 | -0.0562 | 0.5111 |
| B1 | LS_quintile | 1d | 15 | -0.2437 | -0.0354 | 0.1452 | -0.4750 | 0.5111 |
| B1 | LS_quintile | 1d | 30 | -2.9013 | -0.4218 | 0.1454 | -0.9444 | 0.5111 |
| B1 | LS_quintile | 1d | 50 | -6.4184 | -0.9370 | 0.1460 | -0.9975 | 0.5111 |
| B1 | LO_decile | 1d | 0 | 1.6154 | 0.3371 | 0.2087 | -0.2244 | 0.3097 |
| B1 | LO_decile | 1d | 15 | 0.4935 | 0.1030 | 0.2087 | -0.5585 | 0.3097 |
| B1 | LO_decile | 1d | 30 | -0.6281 | -0.1311 | 0.2087 | -0.8037 | 0.3097 |
| B1 | LO_decile | 1d | 50 | -2.1214 | -0.4433 | 0.2089 | -0.9565 | 0.3097 |
| B1 | LS_decile | 5d | 0 | 1.4342 | 0.2003 | 0.1397 | -0.1149 | 0.2876 |
| B1 | LS_decile | 5d | 15 | -0.1211 | -0.0171 | 0.1412 | -0.4723 | 0.2876 |
| B1 | LS_decile | 5d | 30 | -1.5828 | -0.2345 | 0.1482 | -0.8157 | 0.2876 |
| B1 | LS_decile | 5d | 50 | -3.1867 | -0.5243 | 0.1645 | -0.9674 | 0.2876 |
| B1 | LS_quintile | 5d | 0 | 1.4415 | 0.1988 | 0.1379 | -0.0767 | 0.2583 |
| B1 | LS_quintile | 5d | 15 | 0.0257 | 0.0036 | 0.1382 | -0.4200 | 0.2583 |
| B1 | LS_quintile | 5d | 30 | -1.3397 | -0.1917 | 0.1431 | -0.7797 | 0.2583 |
| B1 | LS_quintile | 5d | 50 | -2.9021 | -0.4520 | 0.1558 | -0.9535 | 0.2583 |
| B1 | LO_decile | 5d | 0 | 1.1796 | 0.2432 | 0.2062 | -0.3287 | 0.1461 |
| B1 | LO_decile | 5d | 15 | 0.6440 | 0.1327 | 0.2061 | -0.4897 | 0.1461 |
| B1 | LO_decile | 5d | 30 | 0.1076 | 0.0223 | 0.2071 | -0.6515 | 0.1461 |
| B1 | LO_decile | 5d | 50 | -0.5956 | -0.1250 | 0.2099 | -0.7908 | 0.1461 |
| C3 | LS_decile | 1d | 0 | 1.1315 | 0.0772 | 0.0682 | -0.0723 | 0.1995 |
| C3 | LS_decile | 1d | 15 | -1.0837 | -0.0737 | 0.0680 | -0.4103 | 0.1995 |
| C3 | LS_decile | 1d | 30 | -3.0599 | -0.2245 | 0.0734 | -0.7520 | 0.1995 |
| C3 | LS_decile | 1d | 50 | -4.8727 | -0.4256 | 0.0873 | -0.9277 | 0.1995 |
| C3 | LS_quintile | 1d | 0 | 1.3299 | 0.0655 | 0.0493 | -0.0448 | 0.1973 |
| C3 | LS_quintile | 1d | 15 | -1.6897 | -0.0836 | 0.0495 | -0.4260 | 0.1973 |
| C3 | LS_quintile | 1d | 30 | -4.0939 | -0.2328 | 0.0569 | -0.7610 | 0.1973 |
| C3 | LS_quintile | 1d | 50 | -5.8381 | -0.4317 | 0.0739 | -0.9296 | 0.1973 |
| C3 | LO_decile | 1d | 0 | -0.1678 | -0.0180 | 0.1075 | -0.2739 | 0.0995 |
| C3 | LO_decile | 1d | 15 | -0.8643 | -0.0933 | 0.1080 | -0.4924 | 0.0995 |
| C3 | LO_decile | 1d | 30 | -1.5427 | -0.1686 | 0.1093 | -0.6663 | 0.0995 |
| C3 | LO_decile | 1d | 50 | -2.3932 | -0.2689 | 0.1124 | -0.8139 | 0.0995 |
| C3 | LS_decile | 5d | 0 | 1.1315 | 0.0772 | 0.0682 | -0.0723 | 0.1995 |
| C3 | LS_decile | 5d | 15 | -1.0837 | -0.0737 | 0.0680 | -0.4103 | 0.1995 |
| C3 | LS_decile | 5d | 30 | -3.0599 | -0.2245 | 0.0734 | -0.7520 | 0.1995 |
| C3 | LS_decile | 5d | 50 | -4.8727 | -0.4256 | 0.0873 | -0.9277 | 0.1995 |
| C3 | LS_quintile | 5d | 0 | 1.3299 | 0.0655 | 0.0493 | -0.0448 | 0.1973 |
| C3 | LS_quintile | 5d | 15 | -1.6897 | -0.0836 | 0.0495 | -0.4260 | 0.1973 |
| C3 | LS_quintile | 5d | 30 | -4.0939 | -0.2328 | 0.0569 | -0.7610 | 0.1973 |
| C3 | LS_quintile | 5d | 50 | -5.8381 | -0.4317 | 0.0739 | -0.9296 | 0.1973 |
| C3 | LO_decile | 5d | 0 | -0.1678 | -0.0180 | 0.1075 | -0.2739 | 0.0995 |
| C3 | LO_decile | 5d | 15 | -0.8643 | -0.0933 | 0.1080 | -0.4924 | 0.0995 |
| C3 | LO_decile | 5d | 30 | -1.5427 | -0.1686 | 0.1093 | -0.6663 | 0.0995 |
| C3 | LO_decile | 5d | 50 | -2.3932 | -0.2689 | 0.1124 | -0.8139 | 0.0995 |
| C3 | LS_decile | 20d | 0 | 1.1315 | 0.0772 | 0.0682 | -0.0723 | 0.1995 |
| C3 | LS_decile | 20d | 15 | -1.0837 | -0.0737 | 0.0680 | -0.4103 | 0.1995 |
| C3 | LS_decile | 20d | 30 | -3.0599 | -0.2245 | 0.0734 | -0.7520 | 0.1995 |
| C3 | LS_decile | 20d | 50 | -4.8727 | -0.4256 | 0.0873 | -0.9277 | 0.1995 |
| C3 | LS_quintile | 20d | 0 | 1.3299 | 0.0655 | 0.0493 | -0.0448 | 0.1973 |
| C3 | LS_quintile | 20d | 15 | -1.6897 | -0.0836 | 0.0495 | -0.4260 | 0.1973 |
| C3 | LS_quintile | 20d | 30 | -4.0939 | -0.2328 | 0.0569 | -0.7610 | 0.1973 |
| C3 | LS_quintile | 20d | 50 | -5.8381 | -0.4317 | 0.0739 | -0.9296 | 0.1973 |
| C3 | LO_decile | 20d | 0 | -0.1678 | -0.0180 | 0.1075 | -0.2739 | 0.0995 |
| C3 | LO_decile | 20d | 15 | -0.8643 | -0.0933 | 0.1080 | -0.4924 | 0.0995 |
| C3 | LO_decile | 20d | 30 | -1.5427 | -0.1686 | 0.1093 | -0.6663 | 0.0995 |
| C3 | LO_decile | 20d | 50 | -2.3932 | -0.2689 | 0.1124 | -0.8139 | 0.0995 |

## 5. Recommended Combination Details

### Signal A3

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.0472 | -0.0122 | 0.2594 | -0.6215 | 0.0532 |
| LS_quintile | -0.2311 | -0.0470 | 0.2032 | -0.5571 | 0.0453 |
| LO_decile | 0.9651 | 0.0875 | 0.0907 | -0.2321 | 0.0279 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.2902 | -0.0773 | 0.2666 | -0.7061 | 0.0356 |
| LS_quintile | -0.3611 | -0.0763 | 0.2113 | -0.6108 | 0.0304 |
| LO_decile | 1.0574 | 0.1000 | 0.0946 | -0.2069 | 0.0174 |

#### 20d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.3761 | -0.1024 | 0.2722 | -0.7261 | 0.0260 |
| LS_quintile | -0.2837 | -0.0610 | 0.2151 | -0.6263 | 0.0216 |
| LO_decile | 0.9613 | 0.0955 | 0.0993 | -0.2079 | 0.0117 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -1.3206 | -0.2616 | -0.2326 |
| year_2021 | 0.9493 | 0.2077 | -0.1100 |
| year_2022 | 1.0323 | 0.2330 | -0.1336 |
| year_2023 | 0.1818 | 0.0371 | -0.2106 |
| year_2024 | 1.1327 | 0.2320 | -0.1048 |
| year_2025 | -0.3026 | -0.0687 | -0.1449 |
| year_2026 | -3.1028 | -1.8339 | -0.6473 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | 0.0224 | 0.0047 | -0.2433 | 0.4256 |
| sub2_2022 | 1.0323 | 0.2330 | -0.1336 | 0.5244 |
| sub3_2023_2024 | 0.6576 | 0.1343 | -0.2106 | 0.5133 |
| sub4_2025_2026 | -1.6962 | -0.6667 | -0.6933 | 0.3989 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -0.7246 | -0.2186 | 0.3016 | -0.8104 | 0.0415 |
| mid | 0.3650 | 0.1305 | 0.3576 | -0.4649 | 0.0417 |
| small | 0.3527 | 0.1031 | 0.2923 | -0.5807 | 0.0365 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.1431 | 0.2302 | -0.6217 |

### Signal A4

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.1927 | 0.0405 | 0.2099 | -0.6278 | 0.0245 |
| LS_quintile | 0.4228 | 0.0718 | 0.1698 | -0.4896 | 0.0195 |
| LO_decile | 1.4975 | 0.1924 | 0.1285 | -0.1820 | 0.0145 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | 0.1867 | 0.0389 | 0.2085 | -0.6261 | 0.0181 |
| LS_quintile | 0.3899 | 0.0659 | 0.1691 | -0.4844 | 0.0151 |
| LO_decile | 1.4894 | 0.1921 | 0.1290 | -0.1847 | 0.0108 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | 0.2158 | 0.0316 | -0.1429 |
| year_2021 | 3.1960 | 0.4997 | -0.0578 |
| year_2022 | 1.7959 | 0.2999 | -0.1208 |
| year_2023 | -0.3266 | -0.0614 | -0.1672 |
| year_2024 | -0.0998 | -0.0165 | -0.1849 |
| year_2025 | -1.3871 | -0.3063 | -0.3702 |
| year_2026 | -0.9567 | -0.4082 | -0.3990 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | 1.9462 | 0.2972 | -0.1429 | 0.5057 |
| sub2_2022 | 1.7959 | 0.2999 | -0.1208 | 0.5447 |
| sub3_2023_2024 | -0.2205 | -0.0390 | -0.2066 | 0.4826 |
| sub4_2025_2026 | -1.1143 | -0.3408 | -0.5742 | 0.4235 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | 0.7455 | 0.2080 | 0.2790 | -0.6987 | 0.0216 |
| mid | 2.2779 | 0.5590 | 0.2454 | -0.1565 | 0.0327 |
| small | 1.9197 | 0.3917 | 0.2040 | -0.1039 | 0.0307 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.0510 | 0.2232 | -0.2285 |

### Signal A10

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.5013 | -0.7138 | 0.2039 | -0.9888 | 0.7100 |
| LS_quintile | -4.3245 | -0.6738 | 0.1558 | -0.9849 | 0.6285 |
| LO_decile | -1.3435 | -0.3229 | 0.2403 | -0.9098 | 0.3786 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -1.5812 | -0.3269 | 0.2068 | -0.8980 | 0.3124 |
| LS_quintile | -1.7813 | -0.2828 | 0.1588 | -0.8783 | 0.2848 |
| LO_decile | -0.0892 | -0.0222 | 0.2488 | -0.7383 | 0.1577 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -0.1707 | -0.0284 | -0.1234 |
| year_2021 | -2.6906 | -0.4943 | -0.4261 |
| year_2022 | -2.0478 | -0.3793 | -0.3396 |
| year_2023 | -2.7732 | -0.4576 | -0.4075 |
| year_2024 | -2.0719 | -0.4079 | -0.3708 |
| year_2025 | -1.5277 | -0.3256 | -0.3517 |
| year_2026 | 0.1949 | 0.0715 | -0.1350 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.6549 | -0.2928 | -0.4666 | 0.3959 |
| sub2_2022 | -2.0478 | -0.3793 | -0.3396 | 0.4634 |
| sub3_2023_2024 | -2.3855 | -0.4328 | -0.6114 | 0.4315 |
| sub4_2025_2026 | -0.6957 | -0.1911 | -0.3957 | 0.4016 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.0655 | -0.4153 | 0.3898 | -0.9705 | 0.3167 |
| mid | -1.5443 | -0.4266 | 0.2763 | -0.9537 | 0.3138 |
| small | -0.9616 | -0.2229 | 0.2318 | -0.8404 | 0.3126 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.2653 | 0.2703 | -0.9815 |

### Signal A2

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.6184 | -0.1812 | 0.2931 | -0.8572 | 0.3730 |
| LS_quintile | -0.8733 | -0.2102 | 0.2407 | -0.8867 | 0.3194 |
| LO_decile | 0.0310 | 0.0097 | 0.3131 | -0.7610 | 0.2104 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -0.2931 | -0.0705 | 0.2404 | -0.6605 | 0.1670 |
| LS_quintile | -0.1270 | -0.0296 | 0.2330 | -0.6784 | 0.1439 |
| LO_decile | 0.4018 | 0.1135 | 0.2825 | -0.6139 | 0.0913 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -0.6105 | -0.1105 | -0.1465 |
| year_2021 | -1.7821 | -0.3500 | -0.3245 |
| year_2022 | -0.4950 | -0.1019 | -0.2085 |
| year_2023 | -1.1346 | -0.2501 | -0.4225 |
| year_2024 | 0.0303 | 0.0063 | -0.1719 |
| year_2025 | -0.3816 | -0.0910 | -0.2803 |
| year_2026 | 1.8543 | 0.8557 | -0.1099 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.2982 | -0.2464 | -0.4238 | 0.4439 |
| sub2_2022 | -0.4950 | -0.1019 | -0.2085 | 0.5488 |
| sub3_2023_2024 | -0.5704 | -0.1221 | -0.4225 | 0.4703 |
| sub4_2025_2026 | 0.6925 | 0.2298 | -0.2971 | 0.3852 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.2524 | -0.3964 | 0.3165 | -0.9411 | 0.1712 |
| mid | 0.5119 | 0.2408 | 0.4703 | -0.5943 | 0.1694 |
| small | 0.4822 | 0.1361 | 0.2822 | -0.3424 | 0.1694 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.1296 | 0.2984 | -0.4343 |

### Signal B1

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.2266 | -0.4959 | 0.1537 | -0.9599 | 0.5950 |
| LS_quintile | -2.9013 | -0.4218 | 0.1454 | -0.9444 | 0.5111 |
| LO_decile | -0.6281 | -0.1311 | 0.2087 | -0.8037 | 0.3097 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -1.5828 | -0.2345 | 0.1482 | -0.8157 | 0.2876 |
| LS_quintile | -1.3397 | -0.1917 | 0.1431 | -0.7797 | 0.2583 |
| LO_decile | 0.1076 | 0.0223 | 0.2071 | -0.6515 | 0.1461 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | 0.8702 | 0.1460 | -0.1201 |
| year_2021 | -2.8520 | -0.4004 | -0.3422 |
| year_2022 | -2.7650 | -0.3646 | -0.3282 |
| year_2023 | -3.5356 | -0.4372 | -0.3668 |
| year_2024 | -0.8056 | -0.1152 | -0.1688 |
| year_2025 | -1.0668 | -0.1652 | -0.2098 |
| year_2026 | -0.9998 | -0.1938 | -0.1461 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -1.0685 | -0.1641 | -0.3920 | 0.4714 |
| sub2_2022 | -2.7650 | -0.3646 | -0.3282 | 0.4268 |
| sub3_2023_2024 | -2.0648 | -0.2765 | -0.4603 | 0.4601 |
| sub4_2025_2026 | -1.0360 | -0.1749 | -0.2843 | 0.3852 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.7875 | -0.4273 | 0.2391 | -0.9540 | 0.2934 |
| mid | -0.9865 | -0.2115 | 0.2144 | -0.8317 | 0.2962 |
| small | -0.8288 | -0.1265 | 0.1527 | -0.6502 | 0.2796 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.2208 | 0.2475 | -0.8920 |

### Signal C3

#### 1d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0599 | -0.2245 | 0.0734 | -0.7520 | 0.1995 |
| LS_quintile | -4.0939 | -0.2328 | 0.0569 | -0.7610 | 0.1973 |
| LO_decile | -1.5427 | -0.1686 | 0.1093 | -0.6663 | 0.0995 |

#### 5d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0599 | -0.2245 | 0.0734 | -0.7520 | 0.1995 |
| LS_quintile | -4.0939 | -0.2328 | 0.0569 | -0.7610 | 0.1973 |
| LO_decile | -1.5427 | -0.1686 | 0.1093 | -0.6663 | 0.0995 |

#### 20d 30bp Results
| portfolio | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| LS_decile | -3.0599 | -0.2245 | 0.0734 | -0.7520 | 0.1995 |
| LS_quintile | -4.0939 | -0.2328 | 0.0569 | -0.7610 | 0.1973 |
| LO_decile | -1.5427 | -0.1686 | 0.1093 | -0.6663 | 0.0995 |

#### Yearly Summary: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd |
| --- | --- | --- | --- |
| year_2020 | -2.7036 | -0.1110 | -0.0869 |
| year_2021 | -3.3632 | -0.2416 | -0.2137 |
| year_2022 | -3.7989 | -0.3485 | -0.2914 |
| year_2023 | -3.5699 | -0.1884 | -0.1515 |
| year_2024 | -2.8012 | -0.1648 | -0.1544 |
| year_2025 | -3.8463 | -0.3205 | -0.2676 |
| year_2026 | -1.1205 | -0.1188 | -0.0887 |

#### Subperiod Analysis: LS_decile 5d 30bp
| period | sharpe | ann_return | max_dd | hit_ratio |
| --- | --- | --- | --- | --- |
| sub1_2020_2021 | -3.0569 | -0.1851 | -0.2820 | 0.0389 |
| sub2_2022 | -3.7989 | -0.3485 | -0.2914 | 0.0447 |
| sub3_2023_2024 | -3.1637 | -0.1766 | -0.2779 | 0.0389 |
| sub4_2025_2026 | -2.7500 | -0.2522 | -0.3110 | 0.0328 |

#### Size Bucket Analysis: LS_decile 5d 30bp
| size_bucket | sharpe | ann_return | ann_vol | max_dd | avg_turnover |
| --- | --- | --- | --- | --- | --- |
| large | -1.6089 | -0.1678 | 0.1043 | -0.6712 | 0.1999 |
| mid | -2.4301 | -0.2486 | 0.1023 | -0.7915 | 0.1997 |
| small | -3.1695 | -0.2463 | 0.0777 | -0.7889 | 0.1994 |

#### LO Alpha vs KOSPI: 5d 30bp
| ann_alpha | tracking_error | ir |
| --- | --- | --- |
| -0.4117 | 0.2477 | -1.6620 |


## 6. Cross-signal Verdict Table
| signal_id | rebalance | gate_a_30bp_sharpe | gate_b_subperiod | gate_c_lo_alpha | verdict | ls_decile_30bp_sharpe | subperiod_min_sharpe | lo_decile_30bp_alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -0.2902 | -1.6962 | -0.1431 |
| A3 | 20d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -0.3761 | -1.7779 | -0.1476 |
| C3 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -3.0599 | -3.7989 | -0.4117 |
| C3 | 20d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -3.0599 | -3.7989 | -0.4117 |
| A4 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | 0.1867 | -1.1143 | -0.0510 |
| A10 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -1.5812 | -2.3855 | -0.2653 |
| A2 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -0.2931 | -1.2982 | -0.1296 |
| B1 | 5d | False | False | False | FAIL_sharpe+subperiod+lo_alpha | -1.5828 | -2.7650 | -0.2208 |

## 7. Reference: Option A Baseline
- LS_decile 5d 30bp Sharpe: -3.24.
- LO_decile 5d 30bp alpha: -22.3%.
- Verdict: FAIL (already discarded).

## 8. C3 Sparsity
- avg_exposure_pct: 12.6%
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
