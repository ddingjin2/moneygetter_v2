# PR-3 SUE Baseline Report

Strategy: top-quintile SUE events, next trading-day open entry, fixed 20-trading-day close exit, equal-weight capacity of 20 positions.

## Measurement 1. Train/Test
| period | scenario | trades | PF | win_rate | total_return | MDD |
| --- | --- | --- | --- | --- | --- | --- |
| train | round_trip_0bps | 348 | 1.9982 | 0.5431 | 0.9683 | -0.1569 |
| test | round_trip_0bps | 199 | 1.4033 | 0.5327 | 0.1924 | -0.1675 |
| train | round_trip_50bps | 348 | 1.8145 | 0.5230 | 0.8043 | -0.1693 |
| test | round_trip_50bps | 199 | 1.2730 | 0.5176 | 0.1335 | -0.1719 |
| train | round_trip_70bps | 348 | 1.7470 | 0.5144 | 0.7426 | -0.1741 |
| test | round_trip_70bps | 199 | 1.2241 | 0.4925 | 0.1107 | -0.1737 |

## Measurement 2. Walk-forward
| fold_id | start | end | trades | PF | total_return |
| --- | --- | --- | --- | --- | --- |
| fold_1 | 2023-03-27 | 2024-03-26 | 67 | 1.3883 | 0.0356 |
| fold_2 | 2024-03-27 | 2025-03-26 | 73 | 0.8414 | -0.0348 |
| fold_3 | 2025-03-27 | 2026-03-26 | 65 | 3.1521 | 0.2042 |

| scenario | test_folds | test_trades_total | pf_median | pf_mean | pf_min | pf_max | passes_stage6_gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| round_trip_70bps | 3 | 205 | 1.3883 | 1.7939 | 0.8414 | 3.1521 | True |

## Measurement 3. Common Trade PF
| stage1_test_pf | wf_median_pf | common_trade_count | common_trade_pf | stage1_only_pnl_share | verdict |
| --- | --- | --- | --- | --- | --- |
| 1.2241 | 0.8414 | 139 | 1.5033 | 0.1986 | edge_confirmed |

## Measurement 4. Leakage
| source | violation_type | count | examples |
| --- | --- | --- | --- |
| trade_ledger | point_in_time | 0 |  |
| trade_ledger | earnings_after_close | 0 |  |
| trade_ledger | future_price | 0 |  |
| trade_ledger | universe_lookahead | 0 |  |
| earnings_dataset | data_source_after_receipt | 0 |  |
| earnings_dataset | fiscal_quarter_after_receipt | 0 |  |
| earnings_dataset | pr1_leakage | 0 |  |

## Verdict
PASS: baseline 엣지 확인. PR-4 진행 권고.

## Interpretation
SUE 단독 신호가 비용 적용 후 WF median PF 1.3883, common PF 1.5033를 통과했다.

## Next Step
PR-4의 52-week high proximity 조건화를 진행한다.
