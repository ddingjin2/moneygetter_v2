# A4 20d top10 paper-trading MVP

This is a paper-trading/order-prep environment, not a broker integration.

Strategy:
- A4_60 20d top10
- KOSPI cached universe
- Signal: lowest 60-trading-day average traded value (`close * volume`), cross-sectional top 10%
- Portfolio: long-only equal-weight target
- Rebalance cadence: intended every 20 trading days
- Default paper capital: 100,000,000 KRW
- Default buy fee/slippage: 0.1%
- Default sell fee/slippage: 0.1%

Main script:
- `scripts/paper_trade_a4.py`

Default run:

```bash
cd /mnt/c/dev/moneygetter_v2/v2
python3 scripts/paper_trade_a4.py --capital 100000000 --buy-fee 0.001 --sell-fee 0.001
```

Outputs:
- `data/cache/paper_trading/a4_20d_top10/latest_state.json`
- `data/cache/paper_trading/a4_20d_top10/rank_YYYYMMDD.csv`
- `data/cache/paper_trading/a4_20d_top10/target_portfolio_YYYYMMDD.csv`
- `data/cache/paper_trading/a4_20d_top10/orders_YYYYMMDD.csv`

Current verified snapshot after the 100M historical rebuild:
- asof date: 2026-07-14
- initial capital: 100,000,000 KRW
- 20-trading-day rebalances replayed on 2026-06-02 and 2026-07-01
- current positions: 77
- current cash: 657,511.075 KRW
- current equity: 101,413,601.075 KRW
- cumulative return: 1.4136%
- SK hynix (000660) was never selected by A4; its absence was a signal-rank result, not a share-rounding failure.

To rebalance from existing paper positions, create a CSV like:

```csv
code,shares
075180,43
069640,199
```

Then run:

```bash
python3 scripts/paper_trade_a4.py \
  --capital 100000000 \
  --buy-fee 0.001 \
  --sell-fee 0.001 \
  --positions path/to/current_positions.csv
```

The generated `orders_YYYYMMDD.csv` will contain BUY/SELL rows with estimated shares, value, fee, and cash flow.

Important caveats:
- Uses the latest cached price data only. It does not fetch fresh market data yet.
- Uses last close for sizing. Real orders should be checked against current quotes before execution.
- Does not submit orders to a broker.
- Does not yet maintain a persistent paper ledger with actual fills, cash, realized/unrealized PnL, dividends, taxes, or failed fills.
- High-priced names can still round to 0 shares, but selection happens before affordability. Rebalance sizing now uses current account equity rather than the original capital, preventing code-order-dependent skipped buys after losses or fees.

Needed for a fuller simulation:
1. Starting paper capital.
2. Rebalance day/time rule, e.g. every 20 trading days after close, trade next open.
3. Whether orders should be sized from close, next open, or live quote.
4. Whether to integrate a Korean broker API later, e.g. KIS, Kiwoom, LS, etc.
5. Realistic minimum order/market impact rule, e.g. max order <= 5% of recent daily traded value.
