# Step 0: train-calibrate-and-gate-risk-models

## 읽어야 할 파일

- `docs/StockEcho_사건위험_리밸런싱_구현계획.md`
- `collector/historical_events/search.py`
- Phase 1 dataset schema
- Phase 2 retrieval metrics
- `requirements-bertopic.txt`

## 작업

유사도 가중 경험분포, Logistic Regression, 작은 MLP를 동일한 시간 분할에서
학습·평가하고 확률을 calibration한다. 승격 기준을 통과한 artifact만 저장한다.

- owned files: `collector/risk_model/`, train/evaluate jobs, model artifact manifest, tests
- non-goals: 포트폴리오 비중 계산과 UI
- interface contract: horizon별 확률·분위수·신뢰도·버전을 반환한다.

## Acceptance Criteria

```bash
.venv/bin/python -m unittest tests.test_risk_model -v
.venv/bin/python -m collector.jobs.evaluate_risk_models --fixture
```

## 검증 절차

1. 시간순 holdout의 PR-AUC, Brier, ECE를 기록한다.
2. calibration plot과 기간·종목·유형별 성능을 확인한다.
3. 기준선 미개선 시 경험분포만 production으로 지정한다.

## 금지사항

- 랜덤 행 분할로 모델 성능을 보고하지 마라.
- calibration을 통과하지 않은 확률을 제품에 노출하지 마라.
