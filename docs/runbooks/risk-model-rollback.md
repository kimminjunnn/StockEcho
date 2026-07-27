# Event Risk 모델 rollback runbook

## 발동 조건

- 최근 시간창 ECE가 0.10 초과
- Brier score가 경험 기준선보다 악화
- forecast stale 비율 50% 이상
- artifact manifest와 서비스 응답의 model/dataset version 불일치
- Event cutoff 누수 또는 동일 Event 검색 포함 발견

## 절차

1. materializer timer를 중지하고 현재 `event_risk_forecasts` 행 수·버전을 기록한다.
2. 제품 설정의 선택 모델을 `similarity-weighted-empirical-v1`로 되돌린다.
3. 문제가 된 후보 model version을 새 forecast materialize 대상에서 제외한다.
4. `.venv/bin/python -m collector.jobs.materialize_risk_forecasts`로 경험분포를
   다시 생성한다.
5. `.venv/bin/python -m collector.jobs.verify_production_artifacts`와 프런트
   E2E를 실행한다.
6. 원인, 영향 Event, 시작·종료 시각, rollback version을 release report에 남긴다.

DB 행을 즉시 삭제하지 않는다. `model_version`으로 이전 artifact를 보존해 감사와
재현에 사용한다. 실제 주문 기능이 없으므로 주문 취소 절차는 없다.
