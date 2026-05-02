# PR-7.A.2.a Step 3 pykrx Market-cap Diagnosis

## Scope

Diagnostic only. No production collection retry, no code changes.

## 1. pykrx Version

```text
1.2.4
```

## 2. `stock.get_market_cap_by_date("20240102", "20240105", "005930")`

Result: returned an empty DataFrame without raising an exception.

### Columns

```python
[]
```

### Sample Data

```text
Empty DataFrame
Columns: []
Index: []
```

### Dtypes

```text
Series([], )
```

## 3. Fallback `stock.get_market_ohlcv_by_date("20240102", "20240105", "005930")`

Result: returned data successfully.

### Columns

```python
['??', '??', '??', '??', '???', '???']
```

### Sample Data

```text
               ??     ??     ??     ??       ???       ???
??                                                        
2024-01-02  78200  79800  78200  79600  17142847  1.401274
2024-01-03  78500  78800  77000  77000  21753644 -3.266332
2024-01-04  76100  77300  76100  76600  15324439 -0.519481
2024-01-05  76700  77100  76400  76600  11304316  0.000000
```

### Dtypes

```text
??       int64
??       int64
??       int64
??       int64
???      int64
???    float64
```

## 4. Estimated Cause

- The installed pykrx version is `1.2.4`.
- The date-level market-cap endpoint for a single ticker returns an empty DataFrame for Samsung Electronics over `2024-01-02 ~ 2024-01-05`.
- The OHLCV endpoint works for the same ticker/date range, so the basic pykrx installation and network path are not fully broken.
- Most likely cause: pykrx market-cap endpoint behavior/schema changed upstream, or the endpoint currently does not expose the expected market-cap payload through this pykrx version/environment. This looks more like endpoint/version compatibility than a locale issue, because Korean OHLCV columns decode correctly.

## Gate

Stop here. Do not retry full market-cap collection from pykrx without a new approved source plan.


---

## 5. Additional Diagnosis: pykrx Upgrade Check

### Latest Version Check

Command: `pip index versions pykrx`

```text
pykrx (1.2.7)
Available versions include: 1.2.7, 1.2.6, 1.2.5, 1.2.4, ...
INSTALLED before upgrade: 1.2.4
LATEST: 1.2.7
```

### Upgrade Attempt

Command: `pip install --upgrade pykrx`

Result: upgraded successfully.

```text
Successfully installed numpy-2.4.4 pykrx-1.2.7
```

Note: pip also upgraded `numpy` from `1.26.4` to `2.4.4` as a dependency of pykrx 1.2.7.

### Encoding Check

Command: `python -c "import sys; print(sys.stdout.encoding); import locale; print(locale.getpreferredencoding())"`

```text
cp949
cp949
```

### Retry After Upgrade

Command:

```python
from pykrx import stock

df = stock.get_market_cap_by_date("20240102", "20240105", "005930")
print(df.columns.tolist())
print(df.head())
```

Observed output:

```text
KRX ??? ??: KRX_ID ?? KRX_PW ?? ??? ???? ?????.
1.2.7
Error occurred in get_market_cap_by_date: Expecting value: line 1 column 1 (char 0)
[]
Empty DataFrame
Columns: []
Index: []
Series([], )
```

### Result Classification

- Tried latest pykrx version: `1.2.7`
- Upgrade result: successful
- Market-cap retry result: empty DataFrame
- Additional error/message after upgrade: KRX login credentials are missing (`KRX_ID` / `KRX_PW` environment variables), followed by JSON parse failure inside `get_market_cap_by_date`.

### Updated Estimated Cause

The earlier empty DataFrame was not fixed by upgrading from pykrx `1.2.4` to `1.2.7`. With 1.2.7, pykrx explicitly reports missing KRX login environment variables before returning an empty result. The most likely cause is now pykrx/KRX endpoint access requiring credentials in this environment, rather than a simple locale problem. Encoding is `cp949`, and Korean OHLCV output decoded correctly in the prior fallback test.

## Stop Gate

Upgrade did not resolve market-cap retrieval. Stop here; no full market-cap collection retry or additional debugging performed.
