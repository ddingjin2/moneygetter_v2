# PR-6 Final Decision Report

## Section 1. Executive Summary
- 프로젝트 목표: 한국 시장 long-only 조건에서 공개 OHLCV와 OPENDART 실적 데이터를 사용해 상업화 가능한 cross-sectional 엣지를 검증했다.
- v1 결과: Breakout55, Breakout55 + Profit Protect, Liquid Gap Stop 모두 최종 탈락했으며, 주 원인은 WF 붕괴, common trade PF 약화, 월별 PnL 집중이었다. Source: `C:\dev\moneygetter\reports\stage6\DECISION_FINAL.md`, `C:\dev\moneygetter\reports\stage6_diagnosis\diagnosis_report.md`.
- v2 결과: 사용자 결정에 따라 옵션 B(OPENDART 실적 기반 cross-sectional)는 공식 폐기한다; 주 원인은 정상 레짐 PF 약화, Fold_3의 2025-05 이후 기형 상승 구간 의존, Goh & Jeon 방향성 실패다. Source: `pr4_proximity_report.md` Section 2/5/6, `pr4_7_regime_reevaluation.md` Step 4/6.
- 근본 판정: 사용자 판정 기준으로 공개 OHLCV + OPENDART realized earnings만으로는 한국 시장 cross-sectional 엣지 확보가 불가하다고 정리한다.
- 다음 사이클 선택지는 6개다: 옵션 E(주봉), 옵션 D(이미지 CNN), 옵션 A(투자자별 매매), 유료 데이터 확장, 완전 재설계, 데이터 기간 확장.

## Section 2. v1 Result Summary

### 2.1 Tried Strategies
| Strategy | Test PF (70bps) | WF median PF | Common trade PF | Verdict | Source |
|---|---:|---:|---:|---|---|
| Breakout55 | 1.1316 | 0.1764 | - | dropped | `stage2_stage5/breakout55_cost_followup.md`; `stage6/stage15_vs_stage6_comparison.csv` |
| Breakout55 + PP | 1.1823 | 0.9201 | - | dropped | `stage2_stage5/report.md`; `stage6/stage15_vs_stage6_comparison.csv` |
| Liquid Gap Stop | 1.3287 | 0.2339 | 0.0206 | dropped | `stage2_stage5/report.md`; `stage6/walkforward_v2_summary.csv`; `stage6_diagnosis/diagnosis_report.md` |

### 2.2 Confirmed v1 Failure Patterns
1. Common trade PF was `0.0206`, so the edge did not survive without the Stage 1-only trade set. Source: `stage6_diagnosis/diagnosis_report.md` Section 2.
2. Top 3 months explained `185.15%` of Stage 1 Test PnL. Source: `stage6_diagnosis/diagnosis_report.md` Section 4.
3. Fold outliers distorted aggregate statistics: Liquid Gap Stop `year_2020` PF was `19.5713`. Source: `audit_stage_1_5/audit_report.md` outlier rows.
4. The validation system used Stage 6 walk-forward with zero-position fold starts and the 70bps scenario; Liquid Gap Stop failed the mandatory median PF gate. Source: `stage6/DECISION_FINAL.md` Section 2/3.

## Section 3. v2 Journey Timeline
| PR | Purpose | Main Result | Gate Result | Source |
|---|---|---|---|---|
| PR-1 | Validation framework | `walkforward`, `common_trade_pf`, `leakage_check` infrastructure defined | Infra PASS | `v2/README.md` Validation Before Strategy / Gates |
| PR-2 | OPENDART collection | `22,441` events existed; baseline SUE non-null only `680`, revenue YoY pair `3.58%` | Recollection required | `pr2_5_recollection_handoff.md` Baseline Before PR-2.5 Recollection |
| PR-2.5 | Recollection | SUE `15,323`; revenue YoY pair `78.08%`; financial payload files `26,266` | PASS | `pr2_5_recollection_report.md` Section 1/3 |
| PR-3 | SUE baseline | Test PF `1.2241`; WF median PF `1.3883`; common trade PF `1.5033`; test trades `199` | PASS | `pr3_sue_baseline_report.md` Measurements 1-3 |
| PR-3.5 | Data quality diagnosis | YoY pair availability: revenue `0.7808`, net income `0.6855`; SUE calculable `15,323` | Completed | `pr3_5_data_quality_diagnosis.md` Section 1 |
| PR-4 | Goh & Jeon reproduction | B WF median PF `0.7586`; directionality B>A False, B>C False, B>D True | FAIL | `pr4_proximity_report.md` Section 2/5/6 |
| PR-4.5 | Option B reevaluation | A/B concentration checked; B 2025-05 exclusion reduced Fold_3 PF `6.5985 -> 1.7209`; A top-month exclusion reduced Fold_3 PF `3.1521 -> 1.2372` | Diagnostic completed | `pr4_5_option_b_reevaluation.md` Step 2.3/2.4 |
| PR-4.6 | Ledger infrastructure + rerun | Rerun diff: OK `40`, WARN `0`, CRITICAL `0`; PR-3/4 numbers deterministic | PASS | `pr4_6_rerun_diff.md` Sections 6.2-6.5 |
| PR-4.7 | Regime-conditional reevaluation | A Fold_1/2 pooled PF `1.0024`; A Bull Extreme excluded PF `1.1407`; formal current result `Scenario B` | Scenario B; PR-6 user instruction treats this as effectively terminal for Option B | `pr4_7_regime_reevaluation.md` Step 4/6 |

## Section 4. Core v2 Numbers

### 4.1 A Baseline Summary
- Test PF at 70bps: `1.2241`. Source: `pr3_sue_baseline_report.md` Measurement 1.
- WF median PF: `1.3883`. Source: `pr3_sue_baseline_report.md` Measurement 2.
- WF fold PF: `1.3883 / 0.8414 / 3.1521`. Source: `pr3_sue_baseline_report.md` Measurement 2.
- Common trade PF: `1.5033`. Source: `pr3_sue_baseline_report.md` Measurement 3.
- Test trades: `199`. Source: `pr3_sue_baseline_report.md` Measurement 1.

### 4.2 Regime-Conditional Numbers
- 2025-05 ~ 2026-04 KOSPI return: `+141.89%`. Source: `pr4_7_regime_reevaluation.md` Step 1/2.3.
- Bull Extreme months: `9/12` in 2025-05 ~ 2026-04 versus prior annualized count `1.94`. Source: `pr4_7_regime_reevaluation.md` Step 2.3.
- A Fold_1/2 pooled PF: `1.0024`. Source: `pr4_7_regime_reevaluation.md` Step 4.1.
- A Bull Extreme excluded full WF PF: `1.1407`. Source: `pr4_7_regime_reevaluation.md` Step 4.1.
- A Bull Extreme entry months only PF: `3.6510` with `43` trades. Source: `pr4_7_regime_reevaluation.md` Step 4.1.
- A beta vs KOSPI: `0.9216`. Source: `pr4_7_regime_reevaluation.md` Step 5.
- A alpha: `0.0103`. Source: `pr4_7_regime_reevaluation.md` Step 5.
- A R2: `0.0845`. Source: `pr4_7_regime_reevaluation.md` Step 5.

### 4.3 B Variant Failure Summary
- B WF fold PF: `0.2966 / 0.7586 / 6.5985`. Source: `pr4_proximity_report.md` Section 3.
- Goh & Jeon directionality: B > A failed, B > C failed, B > D passed; overall reproduced `False`. Source: `pr4_proximity_report.md` Section 2.
- B commercialization gates failed: WF median PF `0.7586 < 1.3`, minimum fold PF `0.2966 < 0.9`. Source: `pr4_proximity_report.md` Section 5.
- B 2025-05 trades: `18` trades; excluding 2025-05 changed Fold_3 PF from `6.5985` to `1.7209`. Source: `pr4_5_option_b_reevaluation.md` Step 2.2/2.3.

## Section 5. Grounds For Retiring Option B
1. **Market beta was a primary driver**: A beta vs KOSPI was `0.9216`, alpha was `0.0103`, and R2 was `0.0845`. Source: `pr4_7_regime_reevaluation.md` Step 5.
2. **Normal-regime performance was near breakeven**: A Fold_1/2 pooled PF was `1.0024`. Source: `pr4_7_regime_reevaluation.md` Step 4.1.
3. **The abnormal period distorted the decision**: A Bull Extreme entry months only produced PF `3.6510` on `43` trades, while Bull Extreme excluded full WF PF was `1.1407`. The `43` trades are about 21% of A WF test trades (`205`). Source: `pr4_7_regime_reevaluation.md` Step 4.1; `pr3_sue_baseline_report.md` Measurement 2.
4. **Fold_2 weakness remained unresolved**: A Fold_2 PF was `0.8414`, below the 0.9 fold-stability gate referenced in PR-4.5. Source: `pr3_sue_baseline_report.md` Measurement 2; `pr4_5_option_b_reevaluation.md` Step 1.3/5.1.
5. **The v1 failure pattern repeated structurally**: v1 had top 3 months PnL share `185.15%`; v2 A and B both showed 2025-05/Fold_3 dependence. Source: `stage6_diagnosis/diagnosis_report.md` Section 4; `pr4_5_option_b_reevaluation.md` Step 2.3/2.4; `pr4_7_regime_reevaluation.md` Step 4.1.

## Section 6. Project Learnings

### 6.1 Methodology Learnings
- Walk-forward + common_trade_pf + leakage_check remained useful as a validation bundle. Source: `v2/README.md` Gates; `pr3_sue_baseline_report.md` Measurements 2-4.
- Test PF alone was insufficient: PR-3 Test PF `1.2241` and common PF `1.5033` looked acceptable before fold concentration and regime mapping. Source: `pr3_sue_baseline_report.md` Measurements 1-3; `pr4_7_regime_reevaluation.md` Step 4/6.
- Fold PF cannot be interpreted without market regime mapping: Fold_3 overlapped the abnormal window by `90.41%`. Source: `pr4_7_regime_reevaluation.md` Step 6.1.
- Trade-level ledger parquet storage should exist before diagnostic PRs: PR-4.6 added deterministic ledgers and produced OK `40`, CRITICAL `0`. Source: `pr4_6_rerun_diff.md` Section 6.4.

### 6.2 Korean Market Specifics
- 2025-05 ~ 2026-04 KOSPI returned `+141.89%`; tests including this period carry beta bias. Source: `pr4_7_regime_reevaluation.md` Step 1/2.3.
- Eom & Park (2021) / high-turnover negative momentum note is retained as a user-provided research memo; it was not independently revalidated in local reports.
- Long-only constraints and unusual short-sale-ban-period regimes are recorded as uncertainty. Source: `pr4_proximity_report.md` Section 7.
- The `0.15% -> 0.20%` transaction tax restoration note is retained as a user-provided market-structure memo; it was not independently revalidated in local reports.

### 6.3 Data Limitations
- OPENDART data contains realized earnings only; analyst revisions and forecasts are absent. Source: project scope in `v2/README.md` Earnings Dataset and PR-6 user instruction.
- Sector fields were not present in `earnings_events.parquet`; sector analysis was skipped. Source: `pr4_5_option_b_reevaluation.md` Step 3.2.
- Market-cap buckets were unavailable because local OHLCV market_cap had no positive usable values. Source: `pr4_5_option_b_reevaluation.md` Step 3.3.
- Investor flow data is not present in the current v2 cache. Source: PR-6 user instruction and absence from current cache inventory.

## Section 7. Next-Cycle Options

### 7.1 Option E: Daily Bars To Weekly Bars
- Pros: Reuses existing OHLCV and validation infrastructure; lower implementation cost; may reduce daily noise.
- Cons: The 2025-05 ~ 2026-04 abnormal regime remains in sample; changing bar frequency does not remove beta exposure by itself.
- Deep Research prior probability estimate: `26%`.
- Prerequisite: whether weekly aggregation dilutes Fold_3 abnormality remains unknown.
- Expected PR number: `PR-7.E`.
- Expected duration: TBD.
- Current infrastructure reuse: `75%`.
- Commercialization-candidate status if successful: possible only after passing the same WF/common_trade/leakage gates.

### 7.2 Option D: Image-Based CNN
- Pros: New modeling surface; potential nonlinear pattern capture.
- Cons: Higher implementation cost; harder interpretation; higher overfitting risk.
- Deep Research prior probability estimate: `14%`.
- Prerequisite: long accumulation period and stricter holdout discipline.
- Expected PR number: `PR-7.D`.
- Expected duration: TBD.
- Current infrastructure reuse: `30%`.
- Commercialization-candidate status if successful: possible after a new validation harness maps image signals to trade ledgers.

### 7.3 Option A: Add Investor Flow
- Pros: Korea-specific data source; foreign/institutional flow has academic and market-practitioner basis.
- Cons: Data is absent from the current repository and must be collected.
- Deep Research prior probability estimate: `22%`.
- Expected PR number: `PR-7.A`.
- Expected duration: TBD.
- Current infrastructure reuse: `60%`.
- Commercialization-candidate status if successful: possible after the investor-flow signal passes existing v2 gates.

### 7.4 Paid Data Expansion
- Pros: Analyst revisions, forecasts, and richer factors become available depending on vendor.
- Cons: Cost and license constraints.
- Prerequisite: monthly/yearly cost and usage rights must be specified before ingestion.
- Expected PR number: `PR-7.PAID`.
- Expected duration: TBD.
- Current infrastructure reuse: `50%`.
- Commercialization-candidate status if successful: possible if vendor data produces durable trade-level edge under existing gates.

### 7.5 Complete Redesign Outside Quant Equity
- Pros: Exits sunk cost in Korean equity long-only cross-sectional research.
- Cons: Existing v2 strategy/data code may be mostly discarded.
- Example domains: crypto, derivatives, options, macro trading.
- Expected PR number: `PR-7.REDESIGN`.
- Expected duration: TBD.
- Current infrastructure reuse: `15%`.
- Commercialization-candidate status if successful: undefined until a new domain validation framework is chosen.

### 7.6 Extend Data Period To 2015-2020
- Pros: Adds normal-regime samples and improves regime diversity.
- Cons: OPENDART recollection cost; older filing format differences may appear.
- Prerequisite: useful if the explicit goal is diluting the 2025-05 ~ 2026-04 abnormal window.
- Expected PR number: `PR-7.HISTORY`.
- Expected duration: TBD.
- Current infrastructure reuse: `80%`.
- Commercialization-candidate status if successful: possible only if the extended period improves normal-regime WF behavior.

### 7.7 Option Scenario Table
| Option | Expected PR | Expected Duration | Current Infra Reuse | Success-State Commercialization Candidate |
|---|---|---|---:|---|
| Option E: weekly bars | PR-7.E | TBD | 75% | Candidate only after existing gates pass |
| Option D: image CNN | PR-7.D | TBD | 30% | Candidate only after image-ledger validation exists |
| Option A: investor flow | PR-7.A | TBD | 60% | Candidate only after existing gates pass |
| Paid data expansion | PR-7.PAID | TBD | 50% | Candidate only after vendor-data gates pass |
| Complete redesign | PR-7.REDESIGN | TBD | 15% | Undefined until new domain framework exists |
| Data period extension | PR-7.HISTORY | TBD | 80% | Candidate only if normal-regime WF improves |

## Section 8. Data And Code Preservation

### Preserve: Do Not Delete
- `v2/data/cache/earnings_events.parquet`: `22,441` events. Source: `pr2_5_recollection_report.md` and cache inventory.
- `v2/data/cache/raw_dart/`: OPENDART raw payload cache. Source: cache inventory.
- `v2/data/cache/trades/*_latest.parquet`: five latest ledgers exist for PR-3/PR-4 A/B/C/D. Source: cache inventory.
- `v2/data/cache/kospi_daily.parquet`: KOSPI daily cache, `1,545` rows. Source: `pr4_7_regime_reevaluation.md` Step 1.
- `v2/reports/` entire directory, especially `_v1` preserved copies. Source: report inventory.

### Archive If No Rerun Is Needed
- `v2/data/cache/earnings_events_partial.parquet`.
- `v2/data/cache/earnings_events.pr2_5_backup_*.parquet`.

### Git Initialization Plan
- Git init is deferred to a separate task after PR-6.
- First commit message proposed by user instruction: `v2 옵션 B 종결 시점 스냅샷`.
- Whether `.gitignore` should exclude `v2/data/cache/` remains an explicit separate decision.

## Section 9. User Decisions
1. 다음 사이클 옵션은 무엇인가? 선택지는 Section 7의 Option E, Option D, Option A, paid data expansion, complete redesign, data period extension이다.
2. 다음 사이클 시작 전 Git 초기화를 수행할 것인가?
3. v2 infrastructure(`ledger`, `walkforward`, `common_trade_pf`, `leakage_check`)를 재사용할 것인가, 폐기할 것인가?
