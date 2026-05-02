# PR-7.A.2.a Step 3 Price + Market-cap Data Readiness

## Summary
- Universe stocks: `808`
- Price files: `808`
- Price rows: `1157935`
- Price coverage 95%+: `808`
- Status counts: `{'ok_price_no_market_cap': 808}`
- Codes with positive market_cap rows: `0`
- Elapsed: `0m 8s`

## Source
- Local OHLCV: `C:/dev/moneygetter/data/processed/market_ohlcv.parquet via v2.data.ohlcv.load_ohlcv`
- Date window: `2020-03-27 ~ 2026-04-17`, intersected with each stock's universe active window.

## Market-cap Availability
- Local OHLCV `market_cap` is present but all values are zero for this universe window.
- `shares_outstanding` is also unavailable in the local OHLCV source.
- pykrx market-cap probe result:
```json
{
  "attempted": true,
  "available": false,
  "error": "KeyError: \"None of [Index(['종가', '시가총액', '거래량', '거래대금'], dtype='object')] are in the [columns]\"",
  "note": "pykrx market-cap endpoint did not return the expected schema in this environment."
}
```

## Delisted Stocks
| code | name | delisted_date | status | rows_collected | price_coverage_ratio | positive_market_cap_rows |
| --- | --- | --- | --- | --- | --- | --- |
| 008110 | 대동전자 | 2026-03-17 00:00:00 | ok_price_no_market_cap | 1463 | 1.0 | 0 |
| 138490 | 코오롱ENP | 2026-03-17 00:00:00 | ok_price_no_market_cap | 1463 | 1.0 | 0 |

## Mini-pilot Price Cache Comparison
- Exact overlap match: `30/30`
- Matched rows: `15210`
| code | mini_rows | full_rows | mini_dates_in_full | value_match | compared_rows |
| --- | --- | --- | --- | --- | --- |
| 000140 | 507 | 1486 | True | True | 507 |
| 000220 | 507 | 1486 | True | True | 507 |
| 000270 | 507 | 1486 | True | True | 507 |
| 000390 | 507 | 1486 | True | True | 507 |
| 000660 | 507 | 1486 | True | True | 507 |
| 001340 | 507 | 1486 | True | True | 507 |
| 001940 | 507 | 1486 | True | True | 507 |
| 002150 | 507 | 1486 | True | True | 507 |
| 003480 | 507 | 1486 | True | True | 507 |
| 004060 | 507 | 1486 | True | True | 507 |
| 004970 | 507 | 1486 | True | True | 507 |
| 005380 | 507 | 1486 | True | True | 507 |
| 005930 | 507 | 1486 | True | True | 507 |
| 010040 | 507 | 1486 | True | True | 507 |
| 012450 | 507 | 1486 | True | True | 507 |
| 013570 | 507 | 1486 | True | True | 507 |
| 015360 | 507 | 1486 | True | True | 507 |
| 015590 | 507 | 1486 | True | True | 507 |
| 034020 | 507 | 1486 | True | True | 507 |
| 037710 | 507 | 1486 | True | True | 507 |
| 063160 | 507 | 1486 | True | True | 507 |
| 090350 | 507 | 1486 | True | True | 507 |
| 100250 | 507 | 1486 | True | True | 507 |
| 108670 | 507 | 1486 | True | True | 507 |
| 109070 | 507 | 1486 | True | True | 507 |
| 123690 | 507 | 1486 | True | True | 507 |
| 207940 | 507 | 1486 | True | True | 507 |
| 329180 | 507 | 1119 | True | True | 507 |
| 373220 | 507 | 1031 | True | True | 507 |
| 402340 | 507 | 1073 | True | True | 507 |

## Sample Validation
| code | name | date | close | volume | market_cap |
| --- | --- | --- | --- | --- | --- |
| 000020 | 동화약품 | 2020-03-27 | 6130 | 193283 | 0 |
| 000020 | 동화약품 | 2020-03-30 | 6350 | 190170 | 0 |
| 000020 | 동화약품 | 2020-03-31 | 6550 | 143491 | 0 |
| 000020 | 동화약품 | 2026-04-15 | 5940 | 75001 | 0 |
| 000020 | 동화약품 | 2026-04-16 | 6040 | 122357 | 0 |
| 000020 | 동화약품 | 2026-04-17 | 6080 | 109972 | 0 |
| 000040 | KR모터스 | 2020-03-27 | 1713 | 220636 | 0 |
| 000040 | KR모터스 | 2020-03-30 | 1719 | 70867 | 0 |
| 000040 | KR모터스 | 2020-03-31 | 1727 | 170216 | 0 |
| 000040 | KR모터스 | 2026-04-15 | 461 | 462474 | 0 |
| 000040 | KR모터스 | 2026-04-16 | 456 | 265840 | 0 |
| 000040 | KR모터스 | 2026-04-17 | 475 | 494885 | 0 |
| 016450 | 한세예스24홀딩스 | 2020-03-27 | 3980 | 26495 | 0 |
| 016450 | 한세예스24홀딩스 | 2020-03-30 | 4935 | 354010 | 0 |
| 016450 | 한세예스24홀딩스 | 2020-03-31 | 4705 | 183057 | 0 |
| 016450 | 한세예스24홀딩스 | 2026-04-15 | 4625 | 60531 | 0 |
| 016450 | 한세예스24홀딩스 | 2026-04-16 | 4680 | 25195 | 0 |
| 016450 | 한세예스24홀딩스 | 2026-04-17 | 4720 | 127795 | 0 |
| 016580 | 환인제약 | 2020-03-27 | 13450 | 327677 | 0 |
| 016580 | 환인제약 | 2020-03-30 | 14200 | 225073 | 0 |
| 016580 | 환인제약 | 2020-03-31 | 14750 | 720810 | 0 |
| 016580 | 환인제약 | 2026-04-15 | 10790 | 106054 | 0 |
| 016580 | 환인제약 | 2026-04-16 | 10780 | 39076 | 0 |
| 016580 | 환인제약 | 2026-04-17 | 11030 | 51397 | 0 |
| 900140 | 엘브이엠씨홀딩스 | 2020-03-27 | 2082 | 988818 | 0 |
| 900140 | 엘브이엠씨홀딩스 | 2020-03-30 | 2119 | 489427 | 0 |
| 900140 | 엘브이엠씨홀딩스 | 2020-03-31 | 2315 | 1065989 | 0 |
| 900140 | 엘브이엠씨홀딩스 | 2026-04-15 | 1674 | 620840 | 0 |
| 900140 | 엘브이엠씨홀딩스 | 2026-04-16 | 1688 | 512113 | 0 |
| 900140 | 엘브이엠씨홀딩스 | 2026-04-17 | 1744 | 962307 | 0 |
| 950210 | 프레스티지바이오파마 | 2021-02-05 | 32800 | 41481126 | 0 |
| 950210 | 프레스티지바이오파마 | 2021-02-08 | 42600 | 22798386 | 0 |
| 950210 | 프레스티지바이오파마 | 2021-02-09 | 50000 | 27039598 | 0 |
| 950210 | 프레스티지바이오파마 | 2026-04-15 | 9110 | 59225 | 0 |
| 950210 | 프레스티지바이오파마 | 2026-04-16 | 9430 | 89308 | 0 |
| 950210 | 프레스티지바이오파마 | 2026-04-17 | 9940 | 145124 | 0 |

## Artifacts
- Price/market-cap parquet directory: `v2\data\cache\price_market_cap_full`
- Quality log: `v2\data\cache\price_market_cap_full\_quality_log.parquet`
- Report: `v2\reports\pr7_a_2_a_step3_price_market_cap.md`

## Gate
Step 3 prepared price data, but market-cap data is not usable from current local/pykrx sources. Do not run IC/backtest until the user accepts a no-market-cap path or provides/approves another market-cap source.
