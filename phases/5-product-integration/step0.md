# Step 0: connect-stored-analysis-to-real-ui

## 읽어야 할 파일

- `frontend/AGENTS.md`
- `docs/StockEcho_사건위험_리밸런싱_구현계획.md`
- `frontend/src/app/rebalancing/page.tsx`
- `frontend/src/components/RebalancingExecutionModal.tsx`
- `frontend/src/components/IssueAnalysisModal.tsx`
- `frontend/src/app/api/stocks/[stockCode]/historical-issues/route.ts`

## 작업

저장된 forecast와 optimizer 결과를 DAL/API/UI에 연결하고 모든 고정 리밸런싱
값을 제거한다. 사용자 요청 경로에서 무거운 Python subprocess 실행을 제거한다.

- owned files: portfolio/event API, DAL, rebalancing/criteria UI, TypeScript contracts, tests
- non-goals: 주문 API와 자동매매
- interface contract: 과거 관측과 모델 추정은 다른 카드와 필드로 표시한다.

## Acceptance Criteria

```bash
cd frontend && npm run lint && npm run build
cd frontend && npm test -- --run
```

## 검증 절차

1. 1~10개 종목, 빈 데이터, stale, 부분 실패, infeasible 상태를 확인한다.
2. API가 canonical Event와 지원 종목·비중 합계를 검증하는지 확인한다.
3. 고정 날짜·비중·수익률·수수료 문자열이 남지 않았는지 검색한다.

## 금지사항

- 브라우저에 secret이나 모델 내부 경로를 노출하지 마라.
- `리밸런싱하기`를 실제 주문 실행처럼 표현하지 마라.
