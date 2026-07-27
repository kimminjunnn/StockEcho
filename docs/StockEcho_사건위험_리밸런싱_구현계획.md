# StockEcho 사건위험 예측·리밸런싱 구현계획

> 목표: 최신 뉴스·공시 Event를 과거 유사 Event 및 실제 시장 반응과 연결하고,
> 검증된 하락 위험 추정치를 포트폴리오 영향과 제약 리밸런싱에 반영한다.

## 1. 최종 사용자 결과

사용자는 최신 Event마다 다음을 확인한다.

- 실제 과거 유사 Event와 원문 근거
- 과거 Event의 D+1·D+5·D+20 거래일 수익률과 시장 대비 비정상수익률
- 현재 Event의 `하락 확률`, `예상 중앙값`, `하방 분위수`, `예측 구간`
- 표본 수, 유사도, 데이터 기준시각, 모델 버전, 신뢰도
- 보유 비중을 반영한 종목별·포트폴리오별 손실 시나리오
- 위험 선호도별 현재 비중과 제안 비중 비교

과거 관측값과 현재 예측값은 화면과 API에서 별도 필드로 구분한다. 결과는
자동매매나 확정 수익률이 아니라 근거가 연결된 연구·교육용 시나리오다.

## 2. 구현 원칙

1. 현재 구현된 NAVER 수집, 관련도 v2, BERTopic Event, Supabase Event 저장,
   KIS 거래일 수익률을 재사용한다.
2. 유사 Event 평균을 그대로 예측값으로 부르지 않는다. 먼저 유사도 가중 경험분포
   기준선을 만들고, 시간순 검증과 확률 보정을 통과한 모델만 예측값으로 노출한다.
3. 미래 기사, 미래 가격, 같은 사건의 중복 기사가 학습·평가에 섞이지 않도록
   Event 시각 기준으로 데이터 누수를 차단한다.
4. Logistic Regression과 유사사건 기준선을 먼저 확정한다. MLP는 독립된 시간
   테스트에서 기준선보다 개선될 때만 승격한다.
5. Pedersen et al.의 논문은 사건 예측 모델이 아니라 위험·수익·책임투자 선호를
   결합하는 포트폴리오 계층에 사용한다.
6. 논문의 ESG 점수와 StockEcho의 뉴스 기반 사건안전성 점수를 같은 값이라고
   주장하지 않는다. 논문 재현 실험과 서비스 확장 모델을 구분한다.

## 3. 목표 출력 계약

```json
{
  "eventId": "event-id",
  "asOf": "2026-07-27T12:00:00Z",
  "observedHistory": {
    "sampleCount": 24,
    "returns": {
      "d1": { "median": -0.8, "downRate": 0.58 },
      "d5": { "median": -2.1, "downRate": 0.67 },
      "d20": { "median": -3.4, "downRate": 0.63 }
    }
  },
  "forecast": {
    "horizon": "d5",
    "lossProbability": 0.64,
    "medianReturn": -1.7,
    "lowerQuantile": -6.2,
    "upperQuantile": 2.4,
    "confidence": "medium",
    "modelVersion": "event-risk-logit-v1",
    "datasetVersion": "event-study-2026q3-v1"
  },
  "limitations": []
}
```

## 4. 단계별 구현

### Phase 0. 계약·진실성·기술부채 정리

- D+1·D+5·D+20을 제품 표준으로 확정하고 D+30은 연구용 선택 필드로 둔다.
- 현재 하드코딩된 리밸런싱·산정기준 값을 실제 데이터가 연결되기 전까지
  `데모 예시`로 명시한다.
- API 타입, 모델·데이터 버전, `asOf`, `stale`, 부족 데이터 상태를 확정한다.
- KIS 환경변수 로딩, API 인증·rate limit, ESLint 오류를 정리한다.

완료 조건: 기존 70개 Python 테스트, 프런트 lint, production build가 모두 통과한다.

### Phase 1. Event Study 학습 데이터셋

- `market_daily`를 수정주가 OHLCV와 KOSPI 벤치마크를 저장하도록 확장한다.
- Event의 최초 탐지시각, 장 마감 전후, 근거 문서 cutoff를 저장한다.
- D+1·D+5·D+20 원수익률과 시장모형/벤치마크 비정상수익률을 생성한다.
- NAVER 과거 데이터와 이후 OpenDART 공시를 동일 Event 계약으로 정규화한다.
- 중복 Event, 거래정지, 결측, 미래정보를 제외한 버전 Parquet를 export한다.

권장 초기 범위는 지원 종목 전체의 3~5년이며, MLP 승격 여부는 독립 Event 수를
확인한 뒤 결정한다.

완료 조건: 같은 입력으로 동일 dataset hash가 생성되고 Event 단위 시간 분할과
누수 검사가 통과한다.

### Phase 2. ESG·유사 Event 검색

- ESG는 `E/S/G/기타` 다중 라벨과 하위 사건 유형을 분리한다.
- 규칙 기반 weak label과 사람이 검토한 gold sample을 함께 만든다.
- 현재 키워드 유사도를 기준선으로 고정한다.
- SentenceTransformer Event embedding과 후보 필터를 추가한다.
- 현재 Event보다 과거인 Event만 검색하고 동일 사건·기사 중복을 차단한다.
- 사람 평가 Precision@K, nDCG@K와 사후수익률 분포 안정성으로 검색기를 비교한다.

완료 조건: embedding 검색이 고정 평가셋에서 키워드 기준선을 개선할 때만
운영 검색기로 승격한다.

### Phase 3. 하락 위험 예측

세 모델을 같은 시간 분할에서 비교한다.

1. 유사도 가중 경험분포: 가장 설명 가능한 제품 기준선
2. Logistic Regression: 사건·유사도·시장상태 특징을 사용하는 ML 기준선
3. 작은 MLP: 데이터량과 성능 기준을 만족할 때만 후보로 평가

예측 target은 horizon별 `수익률 < 0`, `비정상수익률 < 임계값` 분류와 수익률
분위수다. 평가는 PR-AUC, ROC-AUC, Brier score, calibration error, log loss,
기간·종목·사건유형별 안정성을 사용한다.

완료 조건: 모델이 미래 기간 holdout에서 기준선보다 개선되고 calibration 기준을
통과해야 한다. 그렇지 않으면 경험분포만 서비스한다.

### Phase 4. 포트폴리오 영향·Pedersen 계층

- 종목 Event 예측을 보유 비중으로 가중해 포트폴리오 손실 기여도를 계산한다.
- 공분산, 집중도, turnover, 거래비용을 포함한 최적화 입력을 만든다.
- 논문 재현용 ESG-efficient frontier와 서비스용 Event-Safety frontier를 구분한다.
- 서비스 목적함수는 다음 구조를 사용한다.

```text
maximize
  expected_return
  - risk_aversion × portfolio_variance
  + safety_preference × event_safety_score
  - turnover_penalty × turnover
```

- long-only, 합계 100%, 종목 상한, 최소 현금, 최대 turnover 제약을 둔다.
- 한 개의 정답 비중 대신 안전성 선호도별 3개 시나리오와 frontier를 제공한다.

완료 조건: 모든 결과가 제약을 만족하고 동일 입력에 결정적이며, 현재 비중 대비
위험·turnover·비용 변화가 재계산된다.

### Phase 5. API·실제 리밸런싱 화면

- 사용자 요청 중 Python subprocess로 무거운 분석을 실행하지 않고 저장된 결과를
  DAL/API가 읽도록 전환한다.
- `/api/events/[eventId]/risk`, `/api/portfolio/analyze`,
  `/api/portfolio/rebalance` 계약을 구현한다.
- `localStorage`의 수량과 KIS 가격으로 현재 비중을 계산한다.
- 고정된 리밸런싱 페이지와 모달을 실제 계산 결과로 교체한다.
- 과거 관측, 모델 추정, 데이터 부족, stale, fallback 상태를 시각적으로 분리한다.
- 제안 비중과 계산상 매매 수량만 제공하며 실제 주문 기능은 만들지 않는다.

완료 조건: 사용자가 종목·수량을 입력한 뒤 최신 Event, 유사 사례, 예측,
포트폴리오 영향, 제안 비중까지 하나의 E2E 흐름으로 확인할 수 있다.

### Phase 6. 연구 검증·운영 승격

- Colab notebook을 데이터 다운로드, 학습, 평가, artifact export가 재현되는 형태로
  정리한다.
- 시간순 walk-forward, 종목 제외 holdout, 사건유형 제외 실험을 수행한다.
- 모델 카드, 데이터셋 카드, 오류 사례, ablation 결과를 저장한다.
- 서비스 지표와 논문 표·그림이 같은 dataset/model version을 사용하게 한다.
- drift, calibration, 데이터 최신성, 외부 API 실패, queue 지연을 모니터링한다.

완료 조건: 재실행 가능한 실험 결과, 서비스 E2E 테스트, 모델 rollback 경로,
금융 안전 문구와 데이터 한계 표시가 모두 준비된다.

## 5. 현실적인 출시 순서

1. **Risk Replay v1**: 현재 구현 + D+20 통일 + 포트폴리오 과거 시나리오
2. **Risk Forecast v1**: 유사도 가중 경험분포와 확률·구간
3. **Risk Forecast v2**: 검증된 Logistic/MLP와 calibration
4. **Event-Safety Rebalancing**: 제약 최적화와 frontier
5. **ESG 연구 확장**: ESG gold label, 논문 재현, 서비스 적응 모델 비교

첫 출시에는 딥러닝을 필수로 두지 않는다. 데이터가 충분하지 않거나 미래
holdout에서 개선되지 않으면 MLP를 연구 결과로만 남기는 것이 올바른 결론이다.

## 6. 주요 중단 기준

- 독립 Event 표본이 부족하면 예측 모델 대신 관측 분포만 제공한다.
- calibration이 무너지면 확률을 노출하지 않는다.
- 유사 사건 평가가 기준선을 개선하지 못하면 embedding 검색을 운영에 넣지 않는다.
- optimizer가 작은 입력 변화에 과도한 매매를 만들면 turnover 제약을 강화한다.
- ESG 라벨 신뢰도가 낮으면 ESG를 마케팅 문구로 사용하지 않는다.
