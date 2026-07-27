# Step 0: freeze-contract-and-remove-false-signals

## 읽어야 할 파일

- `docs/StockEcho_사건위험_리밸런싱_구현계획.md`
- `docs/StockEcho_PRD.md`
- `frontend/src/app/rebalancing/page.tsx`
- `frontend/src/app/criteria/page.tsx`
- `frontend/src/lib/historicalIssues.ts`
- `collector/historical_events/price_reaction.py`

## 작업

제품 horizon, 관측·예측 분리, 버전·최신성·부족 상태 계약을 확정한다.
프런트의 하드코딩 수치를 실제 결과로 오인하지 않도록 처리하고 기존 lint 및
환경변수 부채를 정리한다.

- owned files: 위 계약 문서, 관련 TypeScript 타입, 가격반응 계약, lint 대상 파일
- non-goals: 예측 모델 학습, optimizer, 실제 주문
- interface contract: D+1·D+5·D+20 관측값과 forecast는 별도 객체다.

## Acceptance Criteria

```bash
.venv/bin/python -m unittest discover -s tests -v
cd frontend && npm run lint && npm run build
```

## 검증 절차

1. AC 명령을 실행한다.
2. 하드코딩된 결과가 실제 AI 결과처럼 표시되지 않는지 확인한다.
3. `phases/0-contract-quality/index.json`의 상태를 업데이트한다.

## 금지사항

- 기존 사용자 변경을 되돌리지 마라.
- 실제 주문 기능을 추가하지 마라.
