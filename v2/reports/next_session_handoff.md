# Moneygetter v2 — 현재 작업 인수인계

역할: 이 프로젝트의 **현재 상태·blocker·다음 행동의 단일 정본**. 장기 색인은 `C:/dev/knowledge/second-brain/Projects/Moneygetter.md`, 상세 운영·연구는 해당 보고서를 따른다.

## 현재 상태 · 2026-09-19 문서 정리 기준

- A4 모의계좌 운영과 한국 주식 전략 연구 레포다. 이번 작업에서 시장 갱신·계좌 조회·거래·백테스트·감사를 실행하지 않았다.
- 실제 branch는 문서 정리 시작 시 `option_a_investor_flow`였고 기존 코드·데이터 변경이 다수 있다. 시작 시 현재 Git 상태를 다시 확인하며 reset·일괄 덮어쓰기·임의 commit을 하지 않는다.
- 최신 계좌 잔액·보유 종목·거래일·리밸런싱 필요 여부는 **미조회**다. 문서에 남아 있던 7월 수치나 4월 감사 PASS를 현재 상태로 인용하지 않는다.
- 과거 Hermes cron·WSL 설정은 현재 동작이 확인되지 않았다. 과거 스케줄을 복원하거나 새 자동화를 중복 등록하지 않는다.
- 최근 연결된 Vault 운영 기록은 `C:/dev/knowledge/second-brain/Daily/2026-09-06.md`다. 이것도 당시 기록이며 현재 계좌의 증거는 아니다.

## 유지할 운영 원칙

- **모의거래 전용. 실주문은 별도 승인 전 금지.** 승인 초기자금은 1억 원이고 리밸런싱 목표금액은 해당 시점 평가액 기준이다. 과거 1천만 원 설정을 복원하지 않는다.
- 모의계좌와 연구 백테스트의 비용·수익률·전략 판정을 혼합하지 않는다. 연구별 비용·PIT·검증 gate는 `v2/README.md`와 해당 보고서의 계약을 확인한다.
- OHLCV·KOSPI 원시 캐시·연구 benchmark의 마지막 거래일을 함께 확인한다. benchmark가 오래되면 alpha·verdict를 최신이라고 보고하지 않는다.
- 빈 응답만으로 상장폐지를 추정하지 않는다. 사용자 원장·저장·기존 변경을 보존한다.
- 향후 한국 주식 브로커는 유지관리하기 쉬운 KIS/Open Trading API 방향을 선호하지만 구현·실주문 승인은 아니다.

## 다음 행동

1. 사용자의 요청이 일일 운영인지 전략 연구인지 확인한다. 이 문서의 존재만으로 실행하지 않는다.
2. 운영 요청이면 적용 환경의 `moneygetter-daily-operations` 스킬 또는 `paper_trading_a4_operation.md`를 읽는다. 현재 원장·시장·benchmark·자동화 중복 여부를 조회한 뒤 승인된 작업만 수행한다.
3. 손절·계좌 방어 연구 요청이면 `C:/dev/knowledge/second-brain/Daily/2026-07-20.md`의 승인 조건과 실제 후속 구현을 확인한다. 기존 보유분 즉시 적용과 다음 리밸런싱 적용을 임의 결정하지 않는다.
4. 연구 요청이면 해당 전략의 보고서·코드·기준 데이터만 확인한다. 과거 자동 메모리의 FIRE·QLD·TA11 TODO나 verdict를 현재 실행 승인으로 사용하지 않는다.

## 정본 위치

경로는 저장소 루트 기준이다.

- 실행 코드: `v2/scripts/`; 전략·검증 기본 계약: `v2/README.md`
- A4 원장: `v2/data/cache/paper_trading/a4_20d_top10/`
- 최신 생성 감사 자료: `v2/reports/daily_a4_audit.md`, `paper_trading_quality_gate.md` 및 원장 폴더 `daily_audit.json` — 파일 존재·시각·데이터 기준일을 대조한다.
- 운영 절차: `v2/reports/paper_trading_a4_operation.md`, `paper_trading_a4_automation.md`
- 과거 Hermes 설정·7월 인수인계 원문은 문서 전환 외부 백업에 보존했다. 복구 위치는 Vault `Areas/에이전트 메모리 관리.md`를 따른다.

## 검증 경계

이번에는 문서 구조·경로·원문 보존만 검사한다. 계좌 감사·시장 신선도·전략 성능·실행 환경의 정상 동작을 확인한 것으로 보고하지 않는다.
