# Step 0: build-leakage-safe-event-study-dataset

## 읽어야 할 파일

- `docs/StockEcho_사건위험_리밸런싱_구현계획.md`
- `collector/historical_events/price_reaction.py`
- `collector/historical_events/service.py`
- `collector/clients/kis.py`
- `supabase/migrations/202607230003_historical_issue_analysis.sql`
- `notebooks/StockEcho_BERTopic_Colab.ipynb`

## 작업

Event 시각 cutoff, 수정주가 OHLCV, KOSPI 벤치마크, 원수익률과 비정상수익률을
포함하는 버전 학습 데이터셋을 만든다. Event 단위로 중복과 미래정보를 차단한다.

- owned files: 새 migration, `collector/event_study/`, dataset export job, 관련 tests
- non-goals: 예측 모델과 UI
- interface contract: 한 행은 한 Event이며 dataset/model/preprocessing version을 가진다.

## Acceptance Criteria

```bash
.venv/bin/python -m unittest tests.test_event_study_dataset -v
.venv/bin/python -m collector.jobs.export_event_study_dataset --help
```

## 검증 절차

1. 같은 fixture에서 dataset hash가 동일한지 확인한다.
2. 시간 분할마다 Event ID와 근거 문서가 겹치지 않는지 확인한다.
3. phase 상태를 업데이트한다.

## 금지사항

- 미래 기사나 미래 가격 특징을 Event 입력에 포함하지 마라.
- Colab에 Supabase secret을 저장하지 마라.
