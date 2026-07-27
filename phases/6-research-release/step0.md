# Step 0: validate-document-and-release

## 읽어야 할 파일

- `docs/StockEcho_사건위험_리밸런싱_구현계획.md`
- 전체 phase 결과와 model/dataset manifests
- `deploy/systemd/`
- `notebooks/StockEcho_BERTopic_Colab.ipynb`

## 작업

walk-forward와 종목·사건유형 holdout을 완료하고 Colab, 모델 카드, 데이터셋 카드,
논문 표·그림, 운영 모니터링과 rollback 절차를 동일 버전으로 묶는다.

- owned files: notebooks, reports, model/dataset cards, monitoring jobs, runbooks, E2E tests
- non-goals: 성능이 검증되지 않은 모델의 강제 production 승격
- interface contract: 모든 제품 수치에서 dataset/model version과 생성시각을 추적한다.

## Acceptance Criteria

```bash
.venv/bin/python -m unittest discover -s tests -v
cd frontend && npm run lint && npm run build
.venv/bin/python -m collector.jobs.verify_production_artifacts
```

## 검증 절차

1. 논문 결과와 서비스 결과가 같은 artifact version인지 확인한다.
2. 외부 API 실패, stale snapshot, model rollback을 연습한다.
3. 완료 기준과 알려진 한계를 release 문서에 기록한다.

## 금지사항

- 테스트 기간 결과를 학습에 재사용하지 마라.
- 실패한 실험이나 데이터 한계를 숨기지 마라.
