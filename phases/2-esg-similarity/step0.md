# Step 0: evaluate-esg-taxonomy-and-event-retrieval

## 읽어야 할 파일

- `docs/StockEcho_사건위험_리밸런싱_구현계획.md`
- `collector/historical_events/search.py`
- `collector/topic_modeling/issue_classifier.py`
- `collector/topic_modeling/pipeline.py`
- `tests/test_historical_event_search.py`

## 작업

ESG 다중 라벨과 일반 사건 유형을 분리하고, 현재 키워드 검색을 고정 기준선으로
삼아 Event embedding 검색을 구현·평가한다.

- owned files: `collector/event_taxonomy/`, `collector/event_retrieval/`, migration, tests
- non-goals: 수익률 예측과 리밸런싱
- interface contract: 검색 결과는 유사도 구성요소와 근거 Event를 반환한다.

## Acceptance Criteria

```bash
.venv/bin/python -m unittest tests.test_event_taxonomy tests.test_event_retrieval -v
.venv/bin/python -m collector.jobs.evaluate_event_retrieval --fixture
```

## 검증 절차

1. 미래 Event와 동일 Event가 검색 결과에 없는지 확인한다.
2. 고정 gold set에서 키워드 기준선과 embedding 결과를 비교한다.
3. 개선이 없으면 운영 승격 없이 phase 결과에 기록한다.

## 금지사항

- 사건안전성 점수를 논문상의 ESG 점수라고 부르지 마라.
- 평가 없이 embedding 검색을 기본값으로 바꾸지 마라.
