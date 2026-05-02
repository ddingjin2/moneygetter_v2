# PR-7.A.2.a Final Verdict: Option A DISCARDED

## Summary

- Hypothesis: institutional net buying predicts negative forward returns
- IC measurement (Step 6): statistically significant negative IC (5d IC = -0.0094, t = -6.24, p < 0.0001) but absolute strength very weak (|IC| ~0.01)
- Backtest (Step 7): FAIL all PASS criteria
  - LS decile 30bp Sharpe = -3.24
  - All 4 subperiods Sharpe < -2.5
  - LS decile even at 0bp cost Sharpe = -0.05
  - LO top decile vs KOSPI 30bp alpha = -22.3%
- Verdict: discard Option A as standalone tradable signal

## Key Learnings

- mini-pilot 30 stocks IC ~-0.05 strength did not survive at universe scale (universe-wide IC ~-0.01)
- Mini-pilot in/out IC consistency confirmed signal is universe-wide (not cherry-picked) but at ~-0.01 strength only
- Statistical significance (large t-stat) driven by N, not signal strength
- At |IC| ~0.01, decile portfolios show negative even at 0bp due to cross-section noise dominating
- Yearly long-only pattern suggests size/style beta, not alpha (negative KOSPI alpha confirms)

## Process Wins

- Survivorship bias acknowledged early (Step 1) and documented as caveat
- 100% coverage achieved on universe-wide flow collection (Step 2)
- market_cap unavailability handled with trading-value proxy (Step 3 -> decision documented)
- Pre-set PASS/FAIL criteria prevented post-hoc rationalization (Step 7 entry)
- Mini-pilot in/out separation distinguished real-but-weak signal from cherry-picked illusion (key v1/v2 trap avoided)

## Caveats Carried Forward

- alive-only universe (delisted 30-80 stocks missing) applies if similar studies continue on this dataset
- market_cap unavailable from free sources (KRX paid, pykrx blocked, FDR MARCAP unimplemented) needs alternate source if size-aware research resumes
- trading-value proxy for size buckets is weaker than true market_cap

## Next Steps Options

- Option B (different hypothesis) review
- Option C (Option A variants: different lookback, different weighting) review; however, with |IC| ~0.01, variants are unlikely to survive
- PR-7.A redesign if Option A/B/C are all weak

## Artifacts (Preserved For Future Reference)

- `v2/scripts/collect_investor_flow_full.py`
- `v2/scripts/prepare_price_market_cap_full.py`
- `v2/data/cache/investor_flow_full/` (gitignored, backed up)
- `v2/data/cache/price_market_cap_full/` (gitignored, backed up)
- `v2/data/cache/signals/`, `returns/`, `ic/`, `backtest/` (gitignored, backed up)
- All step reports in `v2/reports/pr7_a_2_a_*.md`
