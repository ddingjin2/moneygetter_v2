# PR-7.A.2.a Step 3 FinanceDataReader Diagnosis

Scope: diagnostic only. `finance-datareader` was installed, but no full-universe collection was attempted.

## Install Result

```text
Successfully installed finance-datareader-0.9.110 narwhals-2.20.0 plotly-6.7.0 requests-file-3.0.1
```

## Summary
| code | name | ohlcv_rows | ohlcv_cap_col | snap_rows | snap_cap_col | full_rows | full_dates | full_cap_cols | snap_error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 005930 | Samsung Electronics | 7 | no | 0 | no | 1486 | 2020-03-27 ~ 2026-04-17 | none | NotImplementedError: "KRX/MARCAP/STOCK/005930" is not implemented |
| 302440 | SK Bioscience | 7 | no | 0 | no | 1247 | 2021-03-18 ~ 2026-04-17 | none | NotImplementedError: "KRX/MARCAP/STOCK/302440" is not implemented |
| 008110 | Daedong Electronics delisted | 7 | no | 0 | no | 1471 | 2020-03-27 ~ 2026-03-27 | none | NotImplementedError: "KRX/MARCAP/STOCK/008110" is not implemented |

## Findings

- `FinanceDataReader.DataReader` returns normal OHLCV columns, but no market-cap column for the tested Korean stock codes.
- 6-year `DataReader` calls return rows for active and newly listed stocks, bounded by available/listed dates.
- The delisted ticker `008110` returns data through `2026-03-17`, so delisting-window price availability works in this spot check.
- `SnapDataReader("KRX/MARCAP/STOCK/{code}")` failed for all tested tickers with HTTP 404, so the attempted Marcap snap path is not usable as called.
- Based on FinanceDataReader behavior and naming, the tested `DataReader` path appears to provide exchange/market OHLCV data, while the attempted `KRX/MARCAP` snap endpoint is the intended market-cap route. This diagnosis did not inspect FDR internals further because the prompt forbids additional debugging.

## Raw Diagnostic Output

```text
===== 005930 Samsung Electronics =====
OHLCV columns: ['Open', 'High', 'Low', 'Close', 'Volume', 'Change']
             Open   High    Low  Close    Volume    Change
Date                                                      
2024-01-02  78200  79800  78200  79600  17142847  0.014013
2024-01-03  78500  78800  77000  77000  21753644 -0.032663
2024-01-04  76100  77300  76100  76600  15324439 -0.005195
2024-01-05  76700  77100  76400  76600  11304316  0.000000
2024-01-08  77000  77500  76400  76500  11088724 -0.001305
2024-01-09  77400  77700  74300  74700  26019249 -0.023529
2024-01-10  75000  75200  73200  73600  20259529 -0.014726
SnapDataReader failed: NotImplementedError: "KRX/MARCAP/STOCK/005930" is not implemented
6?? rows: 1486
??: ['Open', 'High', 'Low', 'Close', 'Volume', 'Change']
===== 302440 SK Bioscience =====
OHLCV columns: ['Open', 'High', 'Low', 'Close', 'Volume', 'Change']
              Open    High     Low   Close    Volume    Change
Date                                                          
2021-03-18  130000  169000  130000  169000    876189       NaN
2021-03-19  184000  190000  166000  166500  12468903 -0.014793
2021-03-22  161000  162500  143000  144000   4675116 -0.135135
2021-03-23  147000  149500  138000  140500   2980953 -0.024306
2021-03-24  138000  142000  135500  136500   1707179 -0.028470
2021-03-25  138500  140000  135500  136000   1111829 -0.003663
2021-03-26  136500  138000  131500  132000   1157841 -0.029412
SnapDataReader failed: NotImplementedError: "KRX/MARCAP/STOCK/302440" is not implemented
6?? rows: 1247
??: ['Open', 'High', 'Low', 'Close', 'Volume', 'Change']
===== 008110 Daedong Electronics delisted =====
OHLCV columns: ['Open', 'High', 'Low', 'Close', 'Volume', 'Change']
            Open  High  Low  Close  Volume  Change
Date                                              
2026-03-09     0     0    0  15040       0     0.0
2026-03-10     0     0    0  15040       0     0.0
2026-03-11     0     0    0  15040       0     0.0
2026-03-12     0     0    0  15040       0     0.0
2026-03-13     0     0    0  15040       0     0.0
2026-03-16     0     0    0  15040       0     0.0
2026-03-17     0     0    0  15040       0     0.0
SnapDataReader failed: NotImplementedError: "KRX/MARCAP/STOCK/008110" is not implemented
6?? rows: 1471
??: ['Open', 'High', 'Low', 'Close', 'Volume', 'Change']
```

## Per-symbol Details

### 005930 Samsung Electronics

- OHLCV columns: `['Open', 'High', 'Low', 'Close', 'Volume', 'Change']`
- OHLCV rows in short window: `7`
- SnapDataReader columns: `[]`
- SnapDataReader rows: `0`
- SnapDataReader error: `NotImplementedError: "KRX/MARCAP/STOCK/005930" is not implemented`
- 6-year rows: `1486`
- 6-year date range: `2020-03-27 ~ 2026-04-17`
- 6-year columns: `['Open', 'High', 'Low', 'Close', 'Volume', 'Change']`
- Market-cap columns in 6-year DataReader: `none`

Short-window OHLCV sample:

```text
             Open   High    Low  Close    Volume    Change
Date                                                      
2024-01-02  78200  79800  78200  79600  17142847  0.014013
2024-01-03  78500  78800  77000  77000  21753644 -0.032663
2024-01-04  76100  77300  76100  76600  15324439 -0.005195
2024-01-05  76700  77100  76400  76600  11304316  0.000000
2024-01-08  77000  77500  76400  76500  11088724 -0.001305
2024-01-09  77400  77700  74300  74700  26019249 -0.023529
2024-01-10  75000  75200  73200  73600  20259529 -0.014726
```

6-year tail sample:

```text
              Open    High     Low   Close    Volume    Change
Date                                                          
2026-04-13  198200  203000  198200  201000  19603415 -0.024272
2026-04-14  208000  210000  205500  206500  23672078  0.027363
2026-04-15  215000  215500  210000  211000  24092884  0.021792
2026-04-16  212000  218000  210500  217500  21499788  0.030806
2026-04-17  217000  218000  215000  216000  18079322 -0.006897
```

### 302440 SK Bioscience

- OHLCV columns: `['Open', 'High', 'Low', 'Close', 'Volume', 'Change']`
- OHLCV rows in short window: `7`
- SnapDataReader columns: `[]`
- SnapDataReader rows: `0`
- SnapDataReader error: `NotImplementedError: "KRX/MARCAP/STOCK/302440" is not implemented`
- 6-year rows: `1247`
- 6-year date range: `2021-03-18 ~ 2026-04-17`
- 6-year columns: `['Open', 'High', 'Low', 'Close', 'Volume', 'Change']`
- Market-cap columns in 6-year DataReader: `none`

Short-window OHLCV sample:

```text
              Open    High     Low   Close    Volume    Change
Date                                                          
2021-03-18  130000  169000  130000  169000    876189       NaN
2021-03-19  184000  190000  166000  166500  12468903 -0.014793
2021-03-22  161000  162500  143000  144000   4675116 -0.135135
2021-03-23  147000  149500  138000  140500   2980953 -0.024306
2021-03-24  138000  142000  135500  136500   1707179 -0.028470
2021-03-25  138500  140000  135500  136000   1111829 -0.003663
2021-03-26  136500  138000  131500  132000   1157841 -0.029412
```

6-year tail sample:

```text
             Open   High    Low  Close  Volume    Change
Date                                                    
2026-04-13  41550  41850  41250  41650   55096 -0.008333
2026-04-14  42050  42400  41850  42200   73842  0.013205
2026-04-15  42900  43950  42800  43850  114129  0.039100
2026-04-16  44350  44700  44100  44650   92626  0.018244
2026-04-17  47400  47400  45650  46600  257313  0.043673
```

### 008110 Daedong Electronics delisted

- OHLCV columns: `['Open', 'High', 'Low', 'Close', 'Volume', 'Change']`
- OHLCV rows in short window: `7`
- SnapDataReader columns: `[]`
- SnapDataReader rows: `0`
- SnapDataReader error: `NotImplementedError: "KRX/MARCAP/STOCK/008110" is not implemented`
- 6-year rows: `1471`
- 6-year date range: `2020-03-27 ~ 2026-03-27`
- 6-year columns: `['Open', 'High', 'Low', 'Close', 'Volume', 'Change']`
- Market-cap columns in 6-year DataReader: `none`

Short-window OHLCV sample:

```text
            Open  High  Low  Close  Volume  Change
Date                                              
2026-03-09     0     0    0  15040       0     0.0
2026-03-10     0     0    0  15040       0     0.0
2026-03-11     0     0    0  15040       0     0.0
2026-03-12     0     0    0  15040       0     0.0
2026-03-13     0     0    0  15040       0     0.0
2026-03-16     0     0    0  15040       0     0.0
2026-03-17     0     0    0  15040       0     0.0
```

6-year tail sample:

```text
             Open   High    Low  Close  Volume    Change
Date                                                    
2026-03-23  14500  14550  14240  14500   67993  0.004155
2026-03-24  14500  14760  14500  14650   26389  0.010345
2026-03-25  14700  14700  14430  14490   65485 -0.010922
2026-03-26  14500  14530  14500  14530   30362  0.002761
2026-03-27  14540  14640  14530  14550   70094  0.001376
```

## Gate

Stop here. FinanceDataReader was diagnosed only; no full collection was attempted.
