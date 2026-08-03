# A4 paper-trading operation plan

Decision snapshot from user:
- Start capital: 100,000,000 KRW (rebuilt from 2026-04-17 on 2026-07-15)
- Mode: paper trading first, later connect real broker API
- Data update: after market close
- Rebalance: use the empirically best live/backtest candidate, currently aggressive A4 20d top10
- Broker API preference later: choose easiest/most maintainable implementation. Current recommendation: KIS/Open Trading API first, because it has HTTP API docs and paper/live separation is generally easier than desktop/COM-based APIs.

## Current scripts

1. Target/order generator:

```bash
python3 scripts/paper_trade_a4.py --capital 100000000 --buy-fee 0.001 --sell-fee 0.001
```

2. Paper account ledger:

```bash
# one-time initialization, overwrites only with --force
python3 scripts/paper_account_a4.py init --capital 100000000 --buy-fee 0.001 --sell-fee 0.001 --force

# generate rebalance orders from current paper positions
python3 scripts/paper_account_a4.py rebalance

# fill generated orders at latest cached close, applying buy/sell fee assumptions
python3 scripts/paper_account_a4.py fill

# mark positions to latest cached close and print account summary
python3 scripts/paper_account_a4.py status
```

## Current verified account state

As of cached date 2026-07-14 after rebuilding from 2026-04-17:
- Initial capital: 100,000,000 KRW
- Rebalances replayed: 2026-06-02 and 2026-07-01
- Remaining cash: 657,511.075 KRW
- Market value: 100,756,090 KRW
- Equity: 101,413,601.075 KRW
- Cumulative return: +1.4136%
- Positions: 77
- SK hynix (000660): no trades and no final position because A4 ranked it outside the selected low-traded-value decile.

Files:
- `data/cache/paper_trading/a4_20d_top10/account.json`
- `data/cache/paper_trading/a4_20d_top10/positions.csv`
- `data/cache/paper_trading/a4_20d_top10/positions_mtm.csv`
- `data/cache/paper_trading/a4_20d_top10/trades.csv`
- `data/cache/paper_trading/a4_20d_top10/equity_curve.csv`
- `data/cache/paper_trading/a4_20d_top10/orders_YYYYMMDD.csv`
- `data/cache/paper_trading/a4_20d_top10/target_portfolio_YYYYMMDD.csv`

## Daily after-close workflow

Until fresh data download is automated:
1. Run the normal wrapper so v1 processed data is updated first, then v2 cache is rebuilt from it.
   ```bash
   python3 scripts/run_after_close_a4.py
   ```
   If v1 is already current and only the v2 per-symbol cache should be regenerated:
   ```bash
   python3 scripts/run_after_close_a4.py --skip-v1-update
   ```
   The wrapper runs `scripts/audit_daily_a4.py` at the end and writes:
   - `data/cache/paper_trading/a4_20d_top10/daily_audit.json`
   - `reports/daily_a4_audit.md`
2. Mark current paper account:
   ```bash
   python3 scripts/paper_account_a4.py mark
   ```
3. If it is a rebalance day, run:
   ```bash
   python3 scripts/paper_account_a4.py rebalance
   python3 scripts/paper_account_a4.py fill
   python3 scripts/paper_account_a4.py status
   ```

Recommended rebalance rule for now:
- Rebalance every 20 trading days from the initial fill date.
- Do not optimize rebalance timing on recent paper results until enough live/paper observations accumulate.

## Next implementation step

Automate after-close data refresh. Preferred order:
1. Reuse existing `scripts/prepare_price_market_cap_full.py` / pykrx pipeline if stable.
2. Add a wrapper command that runs data update, mark-to-market, and rebalance only if due.
3. Later add KIS API adapter:
   - paper/live environment variables
   - account balance/positions pull
   - quote pull
   - order submit disabled by default, enabled only with explicit flag

## Caveats

- Paper fills currently use latest cached close, not next open or live quote.
- Taxes are not modeled separately; current 0.1% buy/sell fee is a combined fee/slippage assumption.
- Verified delistings are handled through `config/delistings.csv` at the exact final trading close; unknown missing prices still block execution. Dividends, rejected orders, partial fills, and limit-up/down execution failures are not yet modeled.
- This strategy targets low traded-value names, so real order sizing must eventually enforce order-size vs daily traded-value constraints.
