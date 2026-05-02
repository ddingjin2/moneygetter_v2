# PR-7.A.2.a Step 2 Independent Validation

Scope: validation-only supplement for Step 2 investor-flow collection. No Step 3, signal, IC, forward return, or backtest work is included.

## Summary
| code | name | note | listed_date | delisted_date | rows_collected | expected_days | diff | missing_gap_count | extra_date_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 005930 | 삼성전자 | Samsung Electronics; pre-2020 listing | 2020-01-02 |  | 1486 | 1486 | 0 | 0 | 0 |
| 302440 | SK바이오사이언스 | SK Bioscience; listed 2021-03-18 | 2021-03-18 |  | 1247 | 1247 | 0 | 0 | 0 |
| 373220 | LG에너지솔루션 | LG Energy Solution; listed 2022-01-27 | 2022-01-27 |  | 1031 | 1031 | 0 | 0 | 0 |
| 008110 | 대동전자 | Daedong Electronics; delisted 2026-03-17 | 2020-01-02 | 2026-03-17 | 1463 | 1463 | 0 | 0 | 0 |
| 300720 | 한일시멘트 | Hanil Cement; deterministic small-cap sample | 2020-01-02 |  | 1486 | 1486 | 0 | 0 | 0 |

## Method
- Expected days use `v2/data/cache/kospi_daily.parquet` KOSPI trading dates.
- Window is `max(listed_date, 2020-03-27)` through `min(delisted_date, 2026-04-17)`.
- Flow columns use the collected parquet schema: `foreign_net_buy_shares` and `institutional_net_buy_shares`.
- Both-zero streaks count consecutive rows where both net-share columns are zero.

## 005930 삼성전자

- Active validation window: `2020-03-27 ~ 2026-04-17`
- Rows collected: `1486`
- Expected KOSPI trading days: `1486`
- Difference rows - expected: `0`
- Missing trading-date gaps: `0`
- Missing dates: `none`
- Extra dates outside expected window: `none`
- Both-zero flow streak distribution: `none`
- Delisted last 5 trading days check: `not delisted sample`

### Head 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2020-03-27 | -3113042 | 966564 |
| 2020-03-30 | -1034196 | -18826 |
| 2020-03-31 | -202651 | -3001427 |
| 2020-04-01 | -2443481 | -4655042 |
| 2020-04-02 | -1507802 | 1345934 |

### Tail 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2026-04-13 | -1437638 | -2225119 |
| 2026-04-14 | -505391 | 3088118 |
| 2026-04-15 | 64984 | 575516 |
| 2026-04-16 | 1689165 | 1432694 |
| 2026-04-17 | -3177110 | 869054 |

## 302440 SK바이오사이언스

- Active validation window: `2021-03-18 ~ 2026-04-17`
- Rows collected: `1247`
- Expected KOSPI trading days: `1247`
- Difference rows - expected: `0`
- Missing trading-date gaps: `0`
- Missing dates: `none`
- Extra dates outside expected window: `none`
- Both-zero flow streak distribution: `none`
- Delisted last 5 trading days check: `not delisted sample`

### Head 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2021-03-18 | -79508 | -81994 |
| 2021-03-19 | -680647 | -160200 |
| 2021-03-22 | -166678 | -8034 |
| 2021-03-23 | -66847 | 7321 |
| 2021-03-24 | -9530 | 35280 |

### Tail 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2026-04-13 | 6286 | -11640 |
| 2026-04-14 | 3077 | 8351 |
| 2026-04-15 | 35000 | 16832 |
| 2026-04-16 | 5139 | 25787 |
| 2026-04-17 | -67245 | 1812 |

## 373220 LG에너지솔루션

- Active validation window: `2022-01-27 ~ 2026-04-17`
- Rows collected: `1031`
- Expected KOSPI trading days: `1031`
- Difference rows - expected: `0`
- Missing trading-date gaps: `0`
- Missing dates: `none`
- Extra dates outside expected window: `none`
- Both-zero flow streak distribution: `none`
- Delisted last 5 trading days check: `not delisted sample`

### Head 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2022-01-27 | -2881287 | 5773397 |
| 2022-01-28 | -827684 | 316180 |
| 2022-02-03 | 177938 | 287194 |
| 2022-02-04 | 115800 | 419222 |
| 2022-02-07 | 109528 | 266914 |

### Tail 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2026-04-13 | -10776 | -64113 |
| 2026-04-14 | -50672 | -15055 |
| 2026-04-15 | 37980 | 19029 |
| 2026-04-16 | 36318 | 77773 |
| 2026-04-17 | -1479 | 16700 |

## 008110 대동전자

- Active validation window: `2020-03-27 ~ 2026-03-17`
- Rows collected: `1463`
- Expected KOSPI trading days: `1463`
- Difference rows - expected: `0`
- Missing trading-date gaps: `0`
- Missing dates: `none`
- Extra dates outside expected window: `none`
- Both-zero flow streak distribution: `1d: 1, 2d: 1, 422d: 1`
- Delisted last 5 trading days check: `present all 5: 2026-03-11, 2026-03-12, 2026-03-13, 2026-03-16, 2026-03-17`

### Head 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2020-03-27 | 0 | -1870 |
| 2020-03-30 | 0 | -1972 |
| 2020-03-31 | 0 | -14508 |
| 2020-04-01 | 99 | -11582 |
| 2020-04-02 | 0 | 13 |

### Tail 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2026-03-11 | 0 | 0 |
| 2026-03-12 | 0 | 0 |
| 2026-03-13 | 0 | 0 |
| 2026-03-16 | 0 | 0 |
| 2026-03-17 | 0 | 0 |

## 300720 한일시멘트

- Active validation window: `2020-03-27 ~ 2026-04-17`
- Rows collected: `1486`
- Expected KOSPI trading days: `1486`
- Difference rows - expected: `0`
- Missing trading-date gaps: `0`
- Missing dates: `none`
- Extra dates outside expected window: `none`
- Both-zero flow streak distribution: `3d: 1`
- Delisted last 5 trading days check: `not delisted sample`

### Head 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2020-03-27 | -275 | -3072 |
| 2020-03-30 | 1044 | -4562 |
| 2020-03-31 | 344 | 141 |
| 2020-04-01 | 0 | -1421 |
| 2020-04-02 | 311 | -1324 |

### Tail 5
| date | foreign_net_buy_shares | institutional_net_buy_shares |
| --- | --- | --- |
| 2026-04-13 | -22516 | -15965 |
| 2026-04-14 | -1148 | -7784 |
| 2026-04-15 | -95338 | -87889 |
| 2026-04-16 | -14925 | -36937 |
| 2026-04-17 | -16721 | 15220 |

## Gate
Validation supplement only. Stop here before any Step 3/IC/backtest work.
