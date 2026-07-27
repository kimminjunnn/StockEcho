# StockEcho 최종 연구·제품 통합 목표

> 상태: Pedersen et al. (2021) 원문 반영 최종 작업 정의
> 기준일: 2026-07-27
> 기준 논문: Pedersen, Fitzgibbons, and Pomorski, “Responsible Investing: The ESG-Efficient Frontier,” Journal of Financial Economics 142(2), 572-597

## 1. 최종 목표

StockEcho는 Pedersen et al.의 핵심 구분인 **ESG 정보의 금융적 역할(Type-A)**과 **사용자의 책임투자 선호 역할(Type-M)**을 한국 기업의 공시·뉴스·재무·시장 데이터에 적용한다.

최종 연구 목표는 다음과 같다.

> 한국 기업의 정적 ESG 특성과 동적 ESG 사건 위험이 미래 하방 위험에 추가 정보를 제공하는지 검증하고, 책임 특성을 단순 screening하는 방식과 포트폴리오에 연속적으로 통합하는 방식의 금융 위험·책임 특성·비중 변경 trade-off를 효율적 frontier로 비교한다.

최종 제품 목표는 다음과 같다.

> 사용자의 현재 보유 종목 안에서 시장 위험, ESG 사건 위험, 과거 유사 사건을 분리해 설명하고, 사용자가 감수할 금융 위험과 원하는 책임·사건 안전 수준 사이에서 선택할 수 있는 교육용 리밸런싱 시뮬레이션을 제공한다.

StockEcho는 Pedersen 논문을 그대로 복제하지 않는다. 논문은 기대수익률, Sharpe ratio, 위험자산과 무위험자산, 광범위한 투자 유니버스를 사용한다. StockEcho 서비스는 long-only, 기존 보유 종목 1~10개, 비중 변경 제한, 미래 수익률 비보장을 전제로 한다. 따라서 논문 검증용 ESG-SR frontier와 서비스용 위험 frontier를 구분한다.

## 2. 절대 혼용하지 않을 개념

### 2.1 ESG 특성

논문의 \(s_{i,t}\)에 대응하는 기업 특성이다. 높은 값이 더 나은 책임 특성을 뜻하도록 방향을 통일하고, 동일 시점 투자 유니버스 안에서 cross-sectional z-score로 표준화한다.

초기 후보:

- G: OpenDART 재무제표로 계산한 low-accruals 지표
- E: 검증 가능한 배출·환경 제재·환경 사고 지표
- S: 산업재해·노동·제품 안전 등 검증된 사회 사건 지표
- ESG controversy: 공시·뉴스의 E/S/G 사건을 사람이 검증한 동적 controversy 지표

자료가 없는 E/S/G 값을 LLM이나 임의 규칙으로 채우지 않는다. 외부 ESG rating을 확보하지 못하면 “종합 ESG 점수”라고 부르지 않고 **ESG 사건 안전도** 또는 **controversy score**라고 명시한다.

### 2.2 EventRisk

현재 서비스 문서의 EventRisk는 다음을 결합한 시점별 금융 사건 위험이다.

- 현재 사건의 Severity·Relevance·Recency
- 과거 유사 사건의 실제 가격 반응인 Risk Replay

EventRisk는 ESG rating과 동일하지 않다. EventRisk를 그대로 ESG 점수라고 부르거나 Pedersen 논문의 \(s_i\)에 무검증 치환하지 않는다.

### 2.3 정보와 선호

동일 ESG 정보가 두 역할을 할 수 있다는 것이 Pedersen 논문의 핵심이다.

- 정보 역할: ESG 특성이 미래 fundamentals 또는 하방 위험을 예측하는가
- 선호 역할: 예측력과 별개로 사용자가 더 나은 ESG·사건 안전 수준을 원하는가

StockEcho는 두 역할의 효과를 각각 계산해 보여준다. 단순히 동일 점수를 목적함수에 두 번 더하지 않는다.

## 3. 논문에서 가져올 이론 구조

### 3.1 Type-U: ESG-unaware

시장 가격·거래량 정보만 이용한다.

- Logistic Regression 기준선
- Gradient Boosting 기준선
- 작은 MLP
- 출력: 5거래일 또는 20거래일 하락 확률

### 3.2 Type-A: ESG-aware

시장 정보에 시점 \(t\)까지 공개된 ESG 특성과 사건 특성을 추가한다. Type-U와 같은 target, split, 평가 지표를 사용해 ESG 정보의 증분 예측력을 측정한다.

Type-A 모델이 Type-U보다 시간순 테스트셋에서 개선될 때만 ESG 정보의 금융적 가치가 있다고 결론 내린다.

### 3.3 Type-M: ESG-motivated

Type-A와 동일한 금융 위험 추정치를 사용하되, 사용자가 더 높은 ESG·사건 안전 수준을 선호한다. 이 선호는 예측 확률에 섞지 않고 frontier의 목표 수준 또는 별도 효용으로 적용한다.

Type-M 선택점은 Type-A의 금융위험 최소점보다 더 높은 책임 특성을 선택하면서 발생하는 위험·turnover 비용을 명시한다.

## 4. 두 종류의 frontier

### 4.1 연구용 ESG-SR frontier

Pedersen 논문의 핵심 실증을 한국 데이터에서 제한적으로 재현한다.

\[
\mathrm{SR}_t(\bar{s})
=
\max_{\mathbf w}
\frac{\mathbf w^\top\boldsymbol{\mu}_t}
{\sqrt{\mathbf w^\top\Sigma_t\mathbf w}}
\]

subject to:

\[
\mathbf 1^\top\mathbf w=1,
\qquad
\mathbf w^\top\mathbf s_t=\bar{s}
\]

연구 현실성을 위해 long-only, maxWeight, turnover 조건을 추가한 constrained frontier도 함께 계산한다. 이 경우 원 논문의 closed-form four-fund separation을 그대로 재현했다고 주장하지 않는다.

연구용 기대수익률은 과거 평균을 그대로 쓰지 않고 factor model과 shrinkage를 사용하며, 모든 추정은 walk-forward로 수행한다. ex ante perceived frontier와 다음 기간의 ex post realized frontier를 분리한다.

### 4.2 서비스용 Event-Safety Risk Frontier

서비스에서는 Sharpe ratio나 미래 기대수익률을 사용자에게 제시하지 않는다.

먼저 금융 위험을 정의한다.

\[
\mathrm{FinancialRisk}(\mathbf w,h)
=
\lambda_1(h)\mathrm{VarianceScale}(\mathbf w)
+
\lambda_2(h)\sum_iw_i\mathrm{DownsideNorm}_{i}(h)
\]

이벤트 안전도는 다음과 같이 정의한다.

\[
\mathrm{EventSafety}_i(h)=1-\mathrm{EventRisk}_i(h)
\]

\[
\mathrm{PortfolioEventSafety}(\mathbf w,h)
=
\sum_iw_i\mathrm{EventSafety}_i(h)
\]

목표 안전수준 \(\bar q\)마다 다음 문제를 푼다.

\[
\min_{\mathbf w}
\quad
\mathrm{FinancialRisk}(\mathbf w,h)
+
\lambda_T\|\mathbf w-\mathbf w_{\mathrm{current}}\|_1
\]

subject to:

\[
\mathrm{PortfolioEventSafety}(\mathbf w,h)\ge\bar q
\]

\[
\mathbf 1^\top\mathbf w=1,
\quad
\mathrm{lower}_i\le w_i\le\mathrm{upper}_i
\]

\(\bar q\)를 순차적으로 변경해 frontier를 만들고, 사용자는 다음 시나리오를 비교한다.

1. 금융 위험 우선
2. 균형
3. 사건 안전 우선

단기형·장기형은 데이터 horizon과 감쇠 기간을 결정한다. 책임·사건 안전 선호는 별도 축으로 둔다.

## 5. 논문 연구 질문

### RQ1. 정보 가치

ESG·사건 정보가 시장 데이터만 사용한 모델보다 미래 하락 위험 또는 미래 fundamentals 예측을 개선하는가?

### RQ2. Frontier

ESG 정보를 사용하는 Type-A frontier는 이를 무시하는 Type-U frontier보다 ex post 성과가 개선되는가?

### RQ3. 선호 비용

Type-A 최적점보다 더 높은 ESG·사건 안전 수준을 선택할 때 금융 위험과 turnover가 얼마나 증가하는가?

### RQ4. Integration 대 screening

고위험·저ESG 종목을 제거하는 hard screening과 점수 제약으로 비중을 조정하는 soft integration 중 어느 방식이 더 나은 trade-off를 만드는가?

### RQ5. 모델 복잡도

MLP, SentenceTransformer, BERTopic이 단순 기준선보다 시간순 테스트에서 실제로 개선되는가?

## 6. 연구 가설과 판정 원칙

- H1: Type-A 하락 위험 모델은 Type-U 모델보다 PR-AUC 또는 Brier score를 개선한다.
- H2: Type-A의 ex post frontier는 Type-U보다 동일 책임 수준에서 더 나은 realized risk-adjusted 성과를 보인다.
- H3: soft integration은 hard screening보다 동일 사건 안전 수준에서 낮은 금융 위험 또는 turnover를 달성한다.
- H4: Risk Replay의 표본 수 shrinkage는 미적용 모델보다 out-of-sample 안정성을 높인다.
- H5: 임베딩 기반 검색은 사람이 라벨링한 사건 평가셋에서 규칙·TF-IDF 기준선보다 Precision@3 또는 nDCG@3을 개선한다.

개선되지 않는 ML/DL 모델은 서비스에 채택하지 않는다. 가설 기각과 실패 사례도 논문 결과다.

원 논문의 “screening 후 오히려 ESG가 낮아질 수 있다”는 결과가 StockEcho에서도 발생한다고 미리 가정하지 않는다. 원 논문의 해당 직관은 low-ESG 종목 short와 hedge 가능성의 영향을 받지만 StockEcho는 long-only이기 때문이다.

## 7. 필요한 데이터

### 7.1 연구 유니버스

서비스 지원 범위는 KOSPI 20종목으로 유지할 수 있다. 하지만 논문의 cross-sectional z-score, factor return, frontier를 20종목만으로 검증하면 통계적 설득력이 약하다.

권장 연구 유니버스:

- 최소: KOSPI 100
- 권장: KOSPI 200
- 서비스 데모: 품질이 검증된 20종목

20종목만 사용할 경우 결과를 일반화된 자산가격 연구가 아니라 제한된 사례 연구로 표현한다.

### 7.2 시장·재무

- 수정 OHLCV
- KOSPI benchmark
- 무위험수익률
- 시가총액
- book-to-market
- 영업현금흐름과 발생액 계산용 재무 항목
- 수익성 지표

### 7.3 공시·뉴스·사건

- OpenDART 공시
- 정제된 NAVER 뉴스
- 사건 E/S/G category
- Severity·Relevance·Recency
- 사건 발생시각과 공개 가능시점
- D+5·D+20 abnormal return
- recovery days
- 유사 사건 human relevance label

모든 행에 as-of 시각을 저장해 미래 정보 누수를 차단한다.

## 8. ML/DL 작업

### 8.1 하락 위험

동일 target과 split으로 비교한다.

1. 무조건부 확률
2. Logistic Regression
3. Gradient Boosting
4. 시장 데이터만 사용하는 MLP(Type-U)
5. 시장+ESG·사건 특성을 사용하는 MLP(Type-A)

평가:

- PR-AUC
- ROC-AUC
- recall
- Brier score
- Expected Calibration Error
- 종목·시장 국면별 안정성

### 8.2 사건 검색

1. 키워드 규칙
2. TF-IDF
3. SentenceTransformer
4. BERTopic 필터 + SentenceTransformer

평가:

- Precision@3
- Recall@K
- nDCG@3
- 사건 유형별 오류
- 자사·타사 사건별 오류

BERTopic은 위험점수를 직접 만들지 않고 사건 후보를 묶고 검색하는 데 사용한다.

## 9. Colab 산출물

1. `01_dataset_and_leakage_audit.ipynb`
2. `02_type_u_type_a_downside_models.ipynb`
3. `03_esg_event_score_validation.ipynb`
4. `04_event_retrieval_bertopic.ipynb`
5. `05_esg_sr_frontier.ipynb`
6. `06_screening_vs_integration.ipynb`
7. `07_service_risk_frontier.ipynb`
8. `08_paper_tables_figures.ipynb`

각 실행은 dataset version, split 시점, seed, preprocessing/model version, hyperparameter, 전체·기간별 metric, 오류 사례, Git commit을 저장한다.

## 10. 서비스에서 구현할 기능

1. 실제 보유 수량과 현재가로 현재 비중 계산
2. Type-U/Type-A 중 검증을 통과한 하락 위험 모델 추론
3. 현재 DisclosureRisk 계산
4. 과거 사건 Risk Replay 계산
5. EventRisk와 EventSafety 계산
6. 여러 목표 안전수준에서 constrained frontier 생성
7. 금융 위험 우선·균형·사건 안전 우선 시나리오 비교
8. 현재·제안 비중, 금융 위험, 사건 안전도, turnover 표시
9. 비중 변경의 시장·사건 근거와 원문 출처 표시
10. 데이터 기준시각, 모델 버전, 표본 수, confidence, fallback 표시

현재 `/rebalancing`의 하드코딩 값과 주문 실행처럼 보이는 UI는 제거한다. 서비스는 실제 주문을 전송하지 않는다.

## 11. 비교 실험

- 현재 비중
- 동일가중
- 최소분산
- Type-U 금융 위험 최소화
- Type-A 금융 위험 최소화
- hard screen 10%
- hard screen 20%
- soft integration frontier
- Risk Replay 제거
- shrinkage 제거
- CAP 제거

평가:

- ex ante/realized Sharpe ratio(연구 전용)
- realized volatility
- maximum drawdown
- downside deviation
- CVaR
- worst 5-day/20-day return
- turnover
- 사건 안전도
- 제약 위반과 fallback 비율

## 12. 구현 순서

### Phase A. 연구 설계 고정

- 연구 유니버스와 기간 확정
- ESG·EventRisk 명칭과 label 정의
- Type-U/A/M과 평가 프로토콜 확정

### Phase B. 데이터셋

- KOSPI 100/200 시장·재무 패널 구축
- 20종목 공시·뉴스 사건 데이터 연결
- human-labeled 사건 검색·분류 평가셋 구축
- as-of와 dataset version 적용

### Phase C. 기준선과 ML/DL

- Type-U/A 하락 위험 기준선·MLP 비교
- ESG 사건 score 검증
- 규칙·TF-IDF·SentenceTransformer·BERTopic 비교

### Phase D. Frontier와 실험

- 연구용 ESG-SR frontier
- 서비스용 Event-Safety Risk Frontier
- screening 대 integration
- walk-forward와 ablation

### Phase E. 서비스

- 공통 Python 계산 엔진
- 리밸런싱 API
- frontier·시나리오 UI
- 근거·confidence·fallback UI

### Phase F. 논문·발표

- Colab에서 표·그림 자동 생성
- 연구 결과와 서비스 수식 일치 검증
- 논문, 발표, 데모 마감

## 13. 완료 기준

### 연구

- Pedersen 논문의 U/A/M 구분과 frontier를 정확히 설명한다.
- 원 논문 재현과 StockEcho 확장 부분을 명확히 구분한다.
- 시간 누수가 없는 데이터셋과 walk-forward 결과가 재현된다.
- Type-U/A, screening/integration, 모델 ablation이 모두 비교된다.
- 가설별 결과와 한계가 포함된 논문 원고가 완성된다.

### 제품

- 하드코딩된 종목·비중·위험 숫자가 없다.
- frontier의 모든 비중이 합계 100%와 bounds를 만족한다.
- 사용자가 금융 위험과 사건 안전 trade-off를 확인할 수 있다.
- 각 사건에서 원문과 Risk Replay 표본을 확인할 수 있다.
- 데이터 부족을 임의 숫자로 채우지 않는다.
- 정상 최적화와 fallback이 테스트된다.
- 실제 브라우저에서 전체 흐름이 검증된다.

## 14. 하지 않을 주장

- EventRisk가 공인 ESG rating이라는 주장
- StockEcho가 Pedersen 논문의 four-fund separation 또는 ESG-CAPM을 그대로 구현했다는 주장
- 20종목 결과를 전체 한국 주식시장에 일반화
- ML/DL 사용 자체가 성능 개선을 의미한다는 주장
- 미래 수익률, 목표가, 손실 방지를 보장한다는 주장
- LLM이 위험점수나 비중을 직접 계산한다는 주장
