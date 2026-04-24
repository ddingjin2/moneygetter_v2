# PR-7.A.1 Investor Flow Data Exploration

## Step 0. Scope
- Diagnostic/data-exploration only.
- Stock: Samsung Electronics (`005930`).
- Requested period: `2020-01-01` to `2026-04-17`.
- Source priority: Naver Finance first; FinanceDataReader fallback only if Naver fails.
- pykrx was not retried.

## Step 1. Naver Pilot Result
- Source used: `naver`.
- Pages fetched: `78`.
- Rows collected in requested period: `1545`.
- Pilot parquet: `v2\data\cache\investor_flow_pilot\005930.parquet`.
- Date range: `2020-01-02` to `2026-04-17`.
- Business-day row ratio: `0.9403530127814973`.
- Missing vs simple Mon-Fri business days: `98`.

## Step 2. Schema
| column | dtype |
| --- | --- |
| date | datetime64[ns] |
| close | Int64 |
| volume | Int64 |
| foreign_net_buy_shares | Int64 |
| institutional_net_buy_shares | Int64 |
| foreign_holding_shares | Int64 |
| foreign_holding_ratio | float64 |

## Step 3. Required Column Completeness
| column | exists | non_null_ratio |
| --- | --- | --- |
| foreign_net_buy_shares | True | 1.0000 |
| institutional_net_buy_shares | True | 1.0000 |

## Step 4. Individual Net Buy Feasibility
- Individual net buy calculable: `False`.
- Note: Naver frgn.naver exposes institutional and foreign net buy shares, but no direct total net buy or individual net buy column. Individual net buy cannot be derived from volume alone.

## Step 5. Fallback Check
```json
{
  "attempted": false,
  "note": "Naver pilot succeeded."
}
```

## Step 6. Errors
```text
(none)
```

## Step 7. User Gate
Step 1 pilot collection is complete. Do not proceed to full-universe collection until user approval.
