# Step 0: build-impact-engine-and-efficient-frontier

## 읽어야 할 파일

- `docs/StockEcho_사건위험_리밸런싱_구현계획.md`
- `frontend/src/lib/portfolio.ts`
- Phase 3 forecast contract
- Pedersen et al. (2021) 제공 PDF

## 작업

보유 비중 기반 손실 기여도와 제약 최적화를 구현한다. 논문 재현 ESG frontier와
서비스 Event-Safety frontier를 별도 실험·API 필드로 유지한다.

- owned files: `collector/portfolio/`, portfolio contracts, optimizer tests
- non-goals: 실제 주문과 단일 종목 매수·매도 권유
- interface contract: 현재/목표 비중, 위험, 안전성, turnover, 비용을 반환한다.

## Acceptance Criteria

```bash
.venv/bin/python -m unittest tests.test_portfolio_impact tests.test_portfolio_optimizer -v
```

## 검증 절차

1. 비중 합계, long-only, 종목 상한, turnover 제약을 검증한다.
2. 동일 입력의 결정성과 infeasible 상태를 검증한다.
3. frontier의 각 점이 위험·안전성 변화와 함께 설명되는지 확인한다.

## 금지사항

- 제약을 위반한 해를 반올림으로 숨기지 마라.
- 사건안전성과 ESG를 같은 지표로 합치지 마라.
