# PR-4.6 Rerun Diff

## 6.1 Execution Info
| item | value |
| --- | --- |
| rerun_timestamp | 2026-04-19T19:46:17 |
| git_rev_parse_HEAD | unavailable (CalledProcessError) |
| python_version | 3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)] |
| pandas_version | 2.3.3 |
| numpy_version | 1.26.4 |

## 6.2 PR-3 A Baseline Diff
| metric | old_v1 | rerun | abs_diff | verdict |
| --- | --- | --- | --- | --- |
| Test trades | 199.0000 | 199.0000 | 0.0000 | OK |
| Test PF (70bps) | 1.2241 | 1.2241 | 0.0000 | OK |
| WF median PF | 1.3883 | 1.3883 | 0.0000 | OK |
| Common trade count | 139.0000 | 139.0000 | 0.0000 | OK |
| Common trade PF | 1.5033 | 1.5033 | 0.0000 | OK |
| Fold_1 PF | 1.3883 | 1.3883 | 0.0000 | OK |
| Fold_2 PF | 0.8414 | 0.8414 | 0.0000 | OK |
| Fold_3 PF | 3.1521 | 3.1521 | 0.0000 | OK |

## 6.3 PR-4 Variant Diff
| scope | metric | old_v1 | rerun | abs_diff | verdict |
| --- | --- | --- | --- | --- | --- |
| PR-4 A | Test trades | 199.0000 | 199.0000 | 0.0000 | OK |
| PR-4 A | Test PF (70bps) | 1.2241 | 1.2241 | 0.0000 | OK |
| PR-4 A | WF median PF | 1.3883 | 1.3883 | 0.0000 | OK |
| PR-4 A | Common trade count | 139.0000 | 139.0000 | 0.0000 | OK |
| PR-4 A | Common trade PF | 1.5033 | 1.5033 | 0.0000 | OK |
| PR-4 A | Fold_1 PF | 1.3883 | 1.3883 | 0.0000 | OK |
| PR-4 A | Fold_2 PF | 0.8414 | 0.8414 | 0.0000 | OK |
| PR-4 A | Fold_3 PF | 3.1521 | 3.1521 | 0.0000 | OK |
| PR-4 B | Test trades | 81.0000 | 81.0000 | 0.0000 | OK |
| PR-4 B | Test PF (70bps) | 2.4353 | 2.4353 | 0.0000 | OK |
| PR-4 B | WF median PF | 0.7586 | 0.7586 | 0.0000 | OK |
| PR-4 B | Common trade count | 53.0000 | 53.0000 | 0.0000 | OK |
| PR-4 B | Common trade PF | 3.0427 | 3.0427 | 0.0000 | OK |
| PR-4 B | Fold_1 PF | 0.2966 | 0.2966 | 0.0000 | OK |
| PR-4 B | Fold_2 PF | 0.7586 | 0.7586 | 0.0000 | OK |
| PR-4 B | Fold_3 PF | 6.5985 | 6.5985 | 0.0000 | OK |
| PR-4 C | Test trades | 139.0000 | 139.0000 | 0.0000 | OK |
| PR-4 C | Test PF (70bps) | 0.9499 | 0.9499 | 0.0000 | OK |
| PR-4 C | WF median PF | 1.0972 | 1.0972 | 0.0000 | OK |
| PR-4 C | Common trade count | 92.0000 | 92.0000 | 0.0000 | OK |
| PR-4 C | Common trade PF | 1.3504 | 1.3504 | 0.0000 | OK |
| PR-4 C | Fold_1 PF | 1.0972 | 1.0972 | 0.0000 | OK |
| PR-4 C | Fold_2 PF | 1.0035 | 1.0035 | 0.0000 | OK |
| PR-4 C | Fold_3 PF | 3.3019 | 3.3019 | 0.0000 | OK |
| PR-4 D | Test trades | 184.0000 | 184.0000 | 0.0000 | OK |
| PR-4 D | Test PF (70bps) | 1.1329 | 1.1329 | 0.0000 | OK |
| PR-4 D | WF median PF | 0.7143 | 0.7143 | 0.0000 | OK |
| PR-4 D | Common trade count | 124.0000 | 124.0000 | 0.0000 | OK |
| PR-4 D | Common trade PF | 1.9757 | 1.9757 | 0.0000 | OK |
| PR-4 D | Fold_1 PF | 0.4272 | 0.4272 | 0.0000 | OK |
| PR-4 D | Fold_2 PF | 0.7143 | 0.7143 | 0.0000 | OK |
| PR-4 D | Fold_3 PF | 4.2262 | 4.2262 | 0.0000 | OK |

## 6.4 Verdict Counts
| verdict | count |
| --- | --- |
| OK | 40 |

## 6.5 Notes
- OK: trade counts match and PF deltas are within the requested thresholds.
- WARN: threshold exceeded without a trade-count mismatch.
- CRITICAL: any trade-count mismatch.
