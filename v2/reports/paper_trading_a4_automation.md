# A4 after-close automation and KIS prep

Implemented items:
1. After-close operation runner
2. Rebalance calendar / last rebalance state
3. KIS API skeleton for future broker integration

## Files

- `scripts/run_after_close_a4.py`
- `scripts/audit_daily_a4.py`
- `scripts/kis_client.py`
- `config/kis_config.example.json`
- `data/cache/paper_trading/a4_20d_top10/rebalance_state.json`
- `data/cache/paper_trading/a4_20d_top10/after_close_log.csv` (created on non-dry runs)

Existing files used:
- `scripts/paper_account_a4.py`
- `scripts/paper_trade_a4.py`

## After-close runner

Dry run:

```bash
cd /mnt/c/dev/moneygetter_v2/v2
python3 scripts/run_after_close_a4.py --dry-run --skip-data-update
```

Normal run, including v1 processed dataset update and v2 price-cache refresh:

```bash
python3 scripts/run_after_close_a4.py
```

Data update order on a normal run:
1. Run v1 `scripts/update_dataset.py --config config/data_pipeline.yaml` under `/mnt/c/dev/moneygetter` or `MONEYGETTER_V1_ROOT`.
2. Run v2 `scripts/prepare_price_market_cap_full.py`, which reads v1 `data/processed/market_ohlcv.parquet` through `v2.data.ohlcv.load_ohlcv` and rewrites the per-symbol cache.

Use a non-default v1 checkout/config:

```bash
python3 scripts/run_after_close_a4.py --v1-root /mnt/c/dev/moneygetter --v1-config config/data_pipeline.yaml
```

Refresh only the v2 cache from the existing v1 parquet, without calling v1 update first:

```bash
python3 scripts/run_after_close_a4.py --skip-v1-update
```

Normal run without data refresh:

```bash
python3 scripts/run_after_close_a4.py --skip-data-update
```

Force rebalance regardless of 20-trading-day interval:

```bash
python3 scripts/run_after_close_a4.py --skip-data-update --force-rebalance
```

Generate orders but do not paper-fill:

```bash
python3 scripts/run_after_close_a4.py --skip-data-update --force-rebalance --no-fill
```

Run the audit harness directly:

```bash
python3 scripts/audit_daily_a4.py
```

Audit outputs:
- `data/cache/paper_trading/a4_20d_top10/daily_audit.json`
- `reports/daily_a4_audit.md`

The normal after-close runner executes this audit at the end unless `--skip-audit` is passed.

## Rebalance rule

Current default:
- interval: 20 trading days
- state path: `data/cache/paper_trading/a4_20d_top10/rebalance_state.json`
- initial `last_rebalance_date`: `2026-04-17`

Dry-run verification result:
- latest price date: 2026-04-17
- last rebalance date: 2026-04-17
- elapsed trading days: 0
- due: false

## KIS skeleton

Template config generated at:
- `config/kis_config.example.json`

Recommended secret handling:
- Use environment variables or a local untracked `.env`, not committed files.

Required env vars later:

```bash
export KIS_MODE=paper
export KIS_APP_KEY='<issued app key>'
export KIS_APP_SECRET='<issued app secret>'
export KIS_ACCOUNT_NO='<8 digit account number before dash>'
export KIS_PRODUCT_CODE='01'
```

Check env:

```bash
python3 scripts/kis_client.py check-env
```

Quote test:

```bash
python3 scripts/kis_client.py quote 005930
```

Balance test:

```bash
python3 scripts/kis_client.py balance
```

Safety:
- Real order submission is intentionally not implemented yet.
- First verify token/quote/balance with paper account.
- Add order submission only behind an explicit safety flag later.

## Verification performed

```bash
python3 -m py_compile scripts/run_after_close_a4.py scripts/audit_daily_a4.py scripts/kis_client.py scripts/paper_account_a4.py scripts/paper_trade_a4.py
python3 scripts/kis_client.py write-template
python3 scripts/run_after_close_a4.py --dry-run --skip-data-update
python3 scripts/audit_daily_a4.py
python3 scripts/paper_account_a4.py status
```

Current account state remains:
- cash: 556,411.846 KRW
- market value: 9,434,154 KRW
- equity: 9,990,565.846 KRW
- positions: 75
- cumulative return: -0.0943%

## Next recommended implementation

Before actual money:
1. Automate fresh OHLCV download beyond the static v1 source. Current `prepare_price_market_cap_full.py` only refreshes v2 cache from existing local v1 OHLCV data.
2. Add order liquidity guard, e.g. max buy/sell amount <= 3~5% of 20d average traded value.
3. Verify KIS paper account token, quote, and balance.
4. Add broker order preview comparing `orders_YYYYMMDD.csv` against live quote.
5. Only then add actual order submission with explicit confirmation flags.
