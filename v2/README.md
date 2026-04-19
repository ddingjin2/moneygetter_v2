# MoneyGetter v2

MoneyGetter v2 is a separate validation-first project for Option B: earnings-centered long-only strategies in the Korean market.

## Relationship To v1

v1 remains untouched. v2 code lives only under `v2/` and may read shared v1 market data through wrappers, but it must not modify existing v1 directories such as `strategy/`, `backtest/`, or `scripts/`.

## Validation Before Strategy

PR-1 contains evaluation tools only. No strategy logic belongs in this PR. Future strategy work must use the Stage 2+5 execution and cost assumptions:

- Long-only trades.
- Intraday stop fill: gap below stop fills at open, otherwise low touching stop fills at stop.
- Round-trip 70 bps default cost: 20 bps transaction cost plus 15 bps slippage per side.
- Korean limit-up/limit-down bars are treated as unfillable when the +/-30% limit is reached.
- Nonmicrocap universe filter excludes the bottom 20% by market cap using point-in-time data.
- Earnings data must be point-in-time. If an earnings disclosure is after market close, entry is allowed no earlier than the next trading day.

## Gates

Every future PR must run `compute_common_trade_pf` before promoting a signal. The minimum continuation gate is:

- `common_trade_pf >= 0.8`

The final Stage 6 walk-forward gate remains stricter:

- 3-year train / 1-year test rolling folds.
- Each fold starts with zero positions and reset cash.
- Test PF median after the 70 bps round-trip cost scenario must be at least `1.2`.

## Stop Conditions

If a candidate signal has `common_trade_pf < 0.8`, the strategy is treated as having no durable edge and must be dropped. If all earnings-centered long-only candidates fail this gate, the v2 project stops instead of continuing with parameter tuning.

## Earnings Dataset

PR-2 builds a free OPENDART earnings-event dataset before any strategy backtest. The builder uses cached OPENDART responses under `v2/data/cache/raw_dart/`, writes normalized events to `v2/data/cache/earnings_events.parquet`, and writes the quality report to `v2/reports/earnings_data_quality.md`.

Required API key setup. Either use a shell environment variable:

```powershell
$env:OPENDART_API_KEY = "<your key>"
```

Or store it in the repository-local `.env` file, which is ignored by git:

```text
OPENDART_API_KEY=<your key>
```

Build and validate:

```powershell
python v2/scripts/build_earnings_dataset.py
python v2/scripts/validate_earnings_data.py
```

The dataset keeps `rcept_dt`, `rcept_time`, and `tradable_entry_date` separate so after-close and holiday disclosures can be checked before any signal consumes the data.
