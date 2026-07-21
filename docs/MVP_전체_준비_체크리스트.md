# StockEcho MVP 전체 준비 체크리스트

> 작성일: 2026-07-21  
> 상태: 기획·디자인 확정 전 데이터·모델링 선행 작업  
> 가격 원천: 토스증권 Open API  
> 사건 원천: OpenDART + NAVER API HUB

## 체크 표시 기준

- `[ ]` 시작 전
- `[~]` 진행 중
- `[x]` 완료
- `P0` 핵심 MVP
- `P1` 핵심 흐름 완료 후
- `결정 필요` 팀 합의가 있어야 완료 가능

---

## 0. 범위와 계약

- [ ] `P0` 서비스명과 핵심 문장 확정: 최신 사건 → 과거 유사 사건 → 주가 반응 → 내 영향
- [ ] `P0` MVP 종목 10개 확정
- [ ] `P0` 종목별 `stockCode`, 정식 회사명, 검색 별칭 작성
- [ ] `P0` OpenDART `corpCode` 매핑
- [ ] `P0` 분석 기간 확정: 가격 최소 2년, 공시 확보 가능 기간, 뉴스 확보 가능 기간
- [ ] `P0` 분석 기준 타임존 `Asia/Seoul` 확정
- [ ] `P0` 가격은 토스 수정 일봉을 학습 기준으로 사용
- [ ] `P0` 현재가는 토스 REST API 5~10초 폴링으로 표시
- [ ] `P0` 포트폴리오 입력은 직접 종목·비중 입력 방식
- [ ] `P0` 계좌 연결·보유자산 조회·주문 기능 제외
- [ ] `결정 필요` 투자 성향별 최대 종목 비중 기본값 확정
- [ ] `결정 필요` 하락 라벨 `향후 5일 -3% 이하` 유지 여부 확정
- [ ] `결정 필요` 사건 방향을 P0에서 `risk/neutral`만 할지 `opportunity`까지 포함할지 확정

완료 조건: 모든 팀원이 같은 입력·출력·비목표를 한 문장으로 설명할 수 있다.

---

## 1. API·인증·보안

### 토스증권

- [ ] `P0` Open API `client_id`, `client_secret` 발급 완료
- [ ] `P0` 호출 서버의 고정 허용 IP 준비 및 등록
- [ ] `P0` OAuth2 Client Credentials 토큰 발급 테스트
- [ ] `P0` 토큰 만료 전 재발급 로직
- [ ] `P0` `.env`에 인증정보 저장, Git 추적 제외 확인
- [ ] `P0` `GET /api/v1/stocks` 종목 정보 호출 테스트
- [ ] `P0` `GET /api/v1/prices` 10종목 다건 현재가 호출 테스트
- [ ] `P0` `GET /api/v1/candles?interval=1d&adjusted=true` 호출 테스트
- [ ] `P0` `before=nextBefore` 페이지네이션 테스트
- [ ] `P0` KOSPI 시장 지표 현재가·일봉 호출 테스트
- [ ] `P0` 응답의 `X-RateLimit-*`, `Retry-After` 기록
- [ ] `P0` 401·403·429·500 오류 처리
- [ ] `P0` 토스 응답 원문에서 키·토큰이 로그에 남지 않는지 검사
- [ ] `P1` 1분봉 캔들 호출 검증

토스증권은 현재 REST API만 제공한다. 현재가는 최대 200종목 다건 조회, 캔들은 1분봉·일봉과 최대 200개씩 페이지네이션을 지원한다. 계좌 관련 API를 쓰지 않으면 `X-Tossinvest-Account`는 필요하지 않다.

### OpenDART

- [ ] `P0` API 키 발급
- [ ] `P0` 고유번호 파일 다운로드·파싱
- [ ] `P0` 종목코드와 `corpCode` 매핑 검증
- [ ] `P0` 기업별·기간별 공시 목록 호출 테스트
- [ ] `P0` 페이지네이션·호출 제한·오류코드 처리
- [ ] `P0` 공시 원문 링크 생성 확인
- [ ] `P1` 필요한 공시만 원문 파일 다운로드

### NAVER API HUB

- [ ] `P0` 애플리케이션 등록과 뉴스 검색 권한 설정
- [ ] `P0` Client ID·Secret 서버 환경변수 저장
- [ ] `P0` 회사명·별칭 검색 호출 테스트
- [ ] `P0` `display=100`, `start`, `sort=date` 동작 확인
- [ ] `P0` 일일 호출량 예산 계산
- [ ] `P0` 429·인증 오류·검색 결과 없음 처리

완료 조건: 대표 종목 1개의 가격·공시·뉴스 원본 JSON을 각각 확보한다.

---

## 2. 프로젝트 데이터 구조

- [ ] `P0` `data/raw/toss/{date}` snapshot 규칙
- [ ] `P0` `data/raw/dart/{date}` snapshot 규칙
- [ ] `P0` `data/raw/news/{date}` snapshot 규칙
- [ ] `P0` `data/processed` 정규화 산출물 규칙
- [ ] `P0` `data/features` 모델 특징 산출물 규칙
- [ ] `P0` `models` 모델·전처리기 artifact 규칙
- [ ] `P0` `reports` 평가 보고서 규칙
- [ ] `P0` 원본 데이터 Git 제외 또는 소용량 sample만 추적
- [ ] `P0` 데이터·모델 버전 이름 규칙
- [ ] `P0` 수집 checkpoint 저장 방식
- [ ] `P0` 마지막 정상 snapshot 보존 방식
- [ ] `P0` 개발용 seed/sample JSON 생성

권장 구조:

```text
src/
  collectors/      toss_price.py, dart.py, naver_news.py
  pipelines/       normalize.py, event_pipeline.py, feature_pipeline.py
  models/          baseline.py, mlp.py, topic_model.py
  replay/          event_study.py, similarity.py
  portfolio/       impact.py, optimizer.py
  rag/             index.py, retrieve.py, validate.py
data/
  raw/
  processed/
  features/
  samples/
models/
reports/
tests/
```

---

## 3. 공통 스키마

- [ ] `P0` `Company` 스키마
- [ ] `P0` `MarketDaily` 스키마
- [ ] `P0` `LiveQuote` 스키마
- [ ] `P0` `CompanyDocument` 스키마
- [ ] `P0` `RiskEvent` 스키마
- [ ] `P0` `DailyFeature` 스키마
- [ ] `P0` `ReplayResult` 스키마
- [ ] `P0` `PortfolioAnalysis` 스키마
- [ ] `P0` 필드명은 API·Python·DB 간 동일하게 맞춤
- [ ] `P0` 가격은 부동소수점 오차를 피하도록 Decimal 또는 정수 원화 사용
- [ ] `P0` 모든 레코드에 `source`, `collectedAt`, `dataVersion` 포함
- [ ] `P0` 문서에 `contentHash`, 가격에 `(stockCode, tradingDate)` 유니크 키
- [ ] `P0` `analysisAsOf`, `modelVersion`, `topicModelVersion` 저장
- [ ] `P0` JSON 예시와 Pydantic 모델 작성
- [ ] `P0` 누가 어떤 테이블을 쓰고 읽는지 소유권 표 작성

완료 조건: 데이터팀 sample JSON만으로 백엔드와 프런트가 mock 연동할 수 있다.

---

## 4. 가격 데이터 파이프라인

### 종목과 현재가

- [ ] `P0` 10종목 종목 마스터 수집
- [ ] `P0` 상장 상태·거래정지·KRX/NXT 지원 여부 저장
- [ ] `P0` 10종목 현재가를 한 요청으로 조회
- [ ] `P0` 서버 폴링 주기 5~10초 설정
- [ ] `P0` 현재가에 실제 API `timestamp` 포함
- [ ] `P0` 장 운영 정보로 장중·장마감·휴장 상태 구분
- [ ] `P0` 현재가 실패 시 마지막 일봉 종가 fallback
- [ ] `P0` 우리 API에서 `isRealtime`, `asOf`, `source` 반환
- [ ] `P0` 현재가 원문은 학습 데이터에 섞지 않음

### 일봉과 그래프

- [ ] `P0` 10종목 최근 2년 수정 일봉 backfill
- [ ] `P0` 캔들 최대 200개 페이지네이션 반복
- [ ] `P0` 최신 일봉 증분 수집
- [ ] `P0` 중복 날짜 upsert
- [ ] `P0` 거래일 오름차순 정렬
- [ ] `P0` OHLC 가격 관계 검사: `low ≤ open/close ≤ high`
- [ ] `P0` 음수 가격·거래량 검사
- [ ] `P0` 결측 거래일을 국내 장 캘린더와 대조
- [ ] `P0` 수정주가 적용 여부를 데이터 버전에 기록
- [ ] `P0` 1개월·3개월·1년 그래프 API용 배열 생성
- [ ] `P0` 홈 sparkline용 최근 20일 종가 생성
- [ ] `P0` KOSPI 일봉과 종목 일봉 날짜 정렬
- [ ] `P1` 토스 일봉과 KRX/로컬 CSV 표본 교차검증
- [ ] `P1` 1분봉 그래프

완료 조건: 삼성전자 2년 일봉 그래프가 나오고 마지막 종가가 토스 현재가의 장 마감 값과 논리적으로 연결된다.

---

## 5. 공시·뉴스 수집 파이프라인

### OpenDART

- [ ] `P0` 대상 10종목 과거 공시 backfill
- [ ] `P0` 최신 공시 증분 수집
- [ ] `P0` 접수번호를 원천 고유키로 사용
- [ ] `P0` 제목·접수일·보고서명·원문 URL 정규화
- [ ] `P0` 정정공시와 원공시 연결 규칙
- [ ] `P0` 불필요한 반복 정기공시 필터 후보 작성
- [ ] `P0` 장 마감 후 공시의 사건일 처리 규칙

### 뉴스

- [ ] `P0` 회사별 검색어 사전: 정식명·브랜드·대표 약칭
- [ ] `P0` 동명이인·일반명사 오탐 규칙
- [ ] `P0` 제목의 HTML 태그 제거
- [ ] `P0` `originallink` 우선 URL 정규화
- [ ] `P0` 제목·요약·발행일·링크 저장
- [ ] `P0` URL 중복 제거
- [ ] `P0` 제목+요약 content hash 중복 제거
- [ ] `P0` 동일 기사의 재전송·제휴기사 제거 실험
- [ ] `P0` 최신 뉴스 증분 수집
- [ ] `P0` 뉴스 API는 완전한 과거 아카이브가 아님을 메타데이터에 기록
- [ ] `P1` 이용약관이 허용하는 범위의 본문 수집 검토

### 통합

- [ ] `P0` 공시·뉴스를 `CompanyDocument`로 통합
- [ ] `P0` `stockCode` 매핑 성공률 측정
- [ ] `P0` `publishedAt` KST 변환
- [ ] `P0` 원문과 정제 텍스트 분리
- [ ] `P0` 수집 성공·실패·신규·중복 수 로그

완료 조건: 대표 종목의 최신 공시·뉴스 카드가 같은 스키마로 조회된다.

---

## 6. 데이터 품질과 골든 샘플

- [ ] `P0` 가격 결측률 리포트
- [ ] `P0` 공시·뉴스 필수값 결측률 리포트
- [ ] `P0` 중복 제거 전후 건수
- [ ] `P0` 회사 매핑 실패 문서 목록
- [ ] `P0` 날짜 파싱 실패 목록
- [ ] `P0` 뉴스 오탐 50건 수동 검토
- [ ] `P0` 위험 사건 30~50건 골든 샘플 라벨링
- [ ] `P0` 골든 샘플 필드: 종목, 사건일, 주제, 방향, ESG, 대표 문서
- [ ] `P0` 팀원 2명이 일부 중복 라벨링해 기준 차이 확인
- [ ] `P0` 공시와 뉴스가 같은 사건인 사례 표시
- [ ] `P0` 장 마감 전후 사건 사례 포함
- [ ] `P0` 데이터 품질 기준 미달 시 화면 신뢰도 규칙

완료 조건: 모델이 틀렸는지를 확인할 사람이 검수한 기준 데이터가 존재한다.

---

## 7. 텍스트 처리 기준선

- [ ] `P0` 한국어 정규화 함수
- [ ] `P0` HTML·특수문자·언론사 머리말 제거
- [ ] `P0` Kiwi 형태소 분석 적용 여부 실험
- [ ] `P0` 금융·주식 불용어 사전
- [ ] `P0` E/S/G 위험 키워드 사전 v1
- [ ] `P0` risk/opportunity/neutral 방향 키워드 사전 v1
- [ ] `P0` TF-IDF 벡터라이저 학습
- [ ] `P0` 문서별 상위 위험 키워드 추출
- [ ] `P0` 최근 7일 `textRisk` 계산
- [ ] `P0` 키워드 기준선의 골든 샘플 성능 확인
- [ ] `P0` 부정 표현·인용 표현 오분류 사례 기록
- [ ] `P1` LSTM 위험/일반 문장 분류 비교

완료 조건: 최신 문서 카드에 위험 키워드와 E/S/G 기준선 결과가 표시된다.

---

## 8. BERT 임베딩·BERTopic·사건 생성

- [ ] `P0` 한국어 SentenceTransformer 후보 2개 비교
- [ ] `P0` 제목만 사용한 임베딩과 제목+요약 비교
- [ ] `P0` 임베딩 모델명·버전 기록
- [ ] `P0` 중복·짧은 문서 제거 후 BERTopic 학습
- [ ] `P0` 토픽 수·잡음 비율 확인
- [ ] `P0` 토픽별 대표 키워드·대표 문서 저장
- [ ] `P0` 팀원이 토픽명을 사람이 이해하는 용어로 검수
- [ ] `P0` 잡음 토픽 Replay 제외
- [ ] `P0` 사건 병합 규칙 구현: 종목+거래일+토픽+유사도
- [ ] `P0` 공시 우선 대표 문서 선정
- [ ] `P0` 사건 방향은 BERTopic과 분리
- [ ] `P0` `topicModelVersion` 저장
- [ ] `P0` 현재 사건 → 같은 토픽 → 벡터 Top-K 검색
- [ ] `P0` 유사도 임계값 튜닝
- [ ] `P0` 골든 샘플에서 유사 사건 검색 Precision@K 평가

완료 조건: 현재 사건 하나를 선택하면 사람이 납득할 과거 사건 3~5건이 반환된다.

---

## 9. Event Study와 Risk Replay

- [ ] `P0` 문서 발행시각을 거래일에 귀속하는 함수
- [ ] `P0` 장 마감 이후 사건은 다음 거래일 처리
- [ ] `P0` 휴장일 사건은 다음 거래일 처리
- [ ] `P0` 사건 후 1·5·20거래일 단순수익률
- [ ] `P0` KOSPI 대비 1·5·20일 비정상수익률
- [ ] `P0` 평균·중앙값·하락 비율·표본 수
- [ ] `P0` 최악·최선 사례
- [ ] `P1` 회복 기간
- [ ] `P0` 표본 부족 기준
- [ ] `P0` 낮은 유사도 경고 기준
- [ ] `P0` 동일 사건 문서를 여러 표본으로 세지 않는 검사
- [ ] `P0` 현재 사건 이후의 미래 사건이 검색되지 않는 검사
- [ ] `P0` 사건 통계 결과와 사용 문서 ID 저장

완료 조건: 대표 사건 하나에 대해 계산을 손으로 재검산할 수 있다.

---

## 10. 하락 위험 학습 데이터

- [ ] `P0` 분석 단위 `stockCode × featureDate` 생성
- [ ] `P0` 1·5·20일 과거 수익률
- [ ] `P0` 5·20일 변동성
- [ ] `P0` 거래량 비율
- [ ] `P0` 20일 낙폭
- [ ] `P0` 이동평균 괴리
- [ ] `P0` KOSPI 과거 수익률
- [ ] `P0` 최근 7일 뉴스·공시 수
- [ ] `P0` 최근 7일 textRisk
- [ ] `P0` E/S/G 점수
- [ ] `P0` 유사 사건 과거 하락 비율
- [ ] `P0` 향후 5일 수익률과 downside label 생성
- [ ] `P0` 특징 시점에 미래 정보가 없는지 자동 검사
- [ ] `P0` 종목별·전체 라벨 분포 리포트
- [ ] `P0` 결측치 처리 정책
- [ ] `P0` Train 70% / Validation 15% / Test 15% 시간순 분할
- [ ] `P0` 분할 사이 5거래일 embargo

완료 조건: 한 행의 모든 특징과 라벨을 원천 데이터까지 역추적할 수 있다.

---

## 11. 모델 학습과 평가

### 기준선

- [ ] `P0` 단순 규칙 기반 위험점수
- [ ] `P0` Logistic Regression 학습
- [ ] `P0` StandardScaler는 Train에만 fit
- [ ] `P0` class weight 적용
- [ ] `P0` Recall·Precision·F1·PR-AUC
- [ ] `P0` Confusion Matrix
- [ ] `P0` 종목별 성능
- [ ] `P0` 기간별 성능
- [ ] `P0` 오분류 사례 20건 분석

### MLP

- [ ] `P0 조건부` Dense 64 → Dense 32 → sigmoid
- [ ] `P0 조건부` early stopping
- [ ] `P0 조건부` Logistic Regression과 동일 분할 비교
- [ ] `P0 조건부` 기준선보다 실제 개선됐는지 확인
- [ ] `P0 조건부` 개선되지 않으면 제품에서 기준선 사용
- [ ] `P1` 하이퍼파라미터 실험
- [ ] `P1` LSTM 비교 실험
- [ ] `P1` 기본 RNN은 교육용 비교 외 제품 적용 제외

### 산출물

- [ ] `P0` 모델 파일
- [ ] `P0` scaler·feature 목록
- [ ] `P0` model card
- [ ] `P0` 학습 데이터 기간·종목·라벨 정의
- [ ] `P0` 재학습 명령어
- [ ] `P0` random seed와 라이브러리 버전
- [ ] `P0` 모델 로드 실패 fallback

완료 조건: 한 명령으로 재학습하고 저장된 테스트 리포트를 재생성할 수 있다.

---

## 12. 포트폴리오 영향과 최적화

### 영향 시나리오

- [ ] `P0` 종목 비중 × 유사 사건 5일 중앙값
- [ ] `P0` 종목별 충격 기여도
- [ ] `P0` 포트폴리오 영향 합산
- [ ] `P0` 평균·중앙값·하락 비율·표본 수 함께 반환
- [ ] `P0` 미래 예측이 아닌 시나리오 문구
- [ ] `P0` 유사 사건 부족 시 계산 제한

### 비중 최적화

- [ ] `P0` 동일가중 기준선
- [ ] `P0` 최소분산 기준선
- [ ] `P0` 하락 위험 패널티
- [ ] `P0` 텍스트 위험 패널티
- [ ] `P0` turnover 패널티
- [ ] `P0` 비중 합 1
- [ ] `P0` 공매도 금지
- [ ] `P0` 투자 성향별 최대 비중
- [ ] `P0` solver 결과 사후 검증
- [ ] `P0` 실패 시 현재 비중 또는 동일가중 fallback
- [ ] `P0` 안정형 위험이 적극형보다 높아지지 않는지 테스트
- [ ] `P0` textRisk 이중 반영 검사
- [ ] `P1` CVaR 모델 비교

완료 조건: 샘플 포트폴리오에서 현재·제안 비중 합이 모두 100%이고 위험 변화가 설명 가능하다.

---

## 13. RAG 근거 계층

- [ ] `P0` CompanyDocument 인덱싱 텍스트 형식
- [ ] `P0` 문서 임베딩과 사건 임베딩 저장
- [ ] `P0` 필수 필터: stockCode
- [ ] `P0` 필수 필터: `publishedAt ≤ analysisAsOf`
- [ ] `P0` 토픽·기간·출처 선택 필터
- [ ] `P0` Top 5 검색
- [ ] `P0` source ID·제목·날짜·URL 포함
- [ ] `P0` LLM에 계산 결과를 읽기 전용으로 전달
- [ ] `P0` 구조화 JSON 출력
- [ ] `P0` source ID 존재 여부 검증
- [ ] `P0` 제목·날짜·URL을 DB 메타데이터로 덮어쓰기
- [ ] `P0` 근거 없는 주장을 제거
- [ ] `P0` 매수·매도·확정 하락 금지 표현 검사
- [ ] `P0` LLM 실패 시 키워드·문서 제목 템플릿
- [ ] `P0` 근거 없음 시 답변 생성 중단

완료 조건: 모든 핵심 주장에 클릭 가능한 실제 원문이 연결된다.

---

## 14. 기획·디자인을 기다리지 않고 만들 API 계약

- [ ] `P0` `GET /health`
- [ ] `P0` `GET /companies`
- [ ] `P0` `GET /companies/{stockCode}/status`
- [ ] `P0` `GET /companies/{stockCode}/prices?range=3M`
- [ ] `P0` `GET /quotes?symbols=...`
- [ ] `P0` `GET /companies/{stockCode}/events`
- [ ] `P0` `GET /events/{eventId}/replay`
- [ ] `P0` `POST /portfolio/analyze`
- [ ] `P0` `POST /portfolio/analyses/{analysisId}/rebalance`
- [ ] `P0` `POST /portfolio/analyses/{analysisId}/ask`
- [ ] `P0` 오류 코드와 UI 메시지 계약
- [ ] `P0` 실제 데이터와 동일한 mock JSON
- [ ] `P0` OpenAPI/Pydantic 스키마
- [ ] `P0` 현재가 응답에 `asOf`, `source`, `isRealtime` 포함
- [ ] `P0` 모든 분석 응답에 `analysisAsOf`, `dataVersion`, `modelVersion` 포함

완료 조건: 디자인이 없어도 Swagger 또는 JSON으로 전체 흐름을 시연할 수 있다.

---

## 15. 저장·관측성·fallback

- [ ] `P0` 원천별 수집 시작·완료·실패 로그
- [ ] `P0` 요청 건수와 신규·중복 건수
- [ ] `P0` 토스 rate limit 헤더 관측
- [ ] `P0` 모델 추론 시간
- [ ] `P0` 최적화 solver 상태
- [ ] `P0` RAG 검색 문서 ID·점수
- [ ] `P0` LLM 시간과 fallback 여부
- [ ] `P0` 비밀키·토큰·원문 전체 로그 금지
- [ ] `P0` 마지막 정상 가격 snapshot
- [ ] `P0` 마지막 정상 문서 snapshot
- [ ] `P0` 토스 장애 시 저장 일봉 사용
- [ ] `P0` 뉴스 장애 시 공시 중심 분석
- [ ] `P0` 모델 장애 시 Logistic/규칙 기준선
- [ ] `P0` 최적화 장애 시 현재/동일가중
- [ ] `P0` LLM 장애 시 템플릿 설명

---

## 16. 테스트

### 데이터

- [ ] `P0` 날짜·타임존 변환
- [ ] `P0` URL·content hash 중복 제거
- [ ] `P0` corpCode 매핑
- [ ] `P0` 캔들 페이지네이션
- [ ] `P0` 수정주가 옵션 유지
- [ ] `P0` 장 캘린더와 결측 거래일
- [ ] `P0` snapshot fallback

### 모델

- [ ] `P0` 미래 데이터 누출 검사
- [ ] `P0` 시간순 분할 검사
- [ ] `P0` scaler 학습 범위
- [ ] `P0` 저장·로드 후 동일 예측
- [ ] `P0` 기준선 비교

### Replay·최적화·RAG

- [ ] `P0` 사건 후 수익률 손계산 대조
- [ ] `P0` 비중 합 100%
- [ ] `P0` 음수·최대 비중 제약
- [ ] `P0` source hallucination 차단
- [ ] `P0` 분석 기준시점 이후 문서 차단

### E2E 장애 시나리오

- [ ] `P0` 토스 API 429
- [ ] `P0` 토스 토큰 만료
- [ ] `P0` OpenDART 장애
- [ ] `P0` 뉴스 결과 없음
- [ ] `P0` 모델 파일 없음
- [ ] `P0` 유사 사건 0건
- [ ] `P0` optimizer 실패
- [ ] `P0` LLM timeout
- [ ] `P0` 모든 외부 API 차단 상태에서 snapshot 데모

---

## 17. 기획·디자인 확정 후 연결할 항목

- [ ] 화면에 보여줄 종목 필드 최종 선택
- [ ] 그래프 기간 버튼과 차트 종류
- [ ] 최신 사건 카드 개수
- [ ] 위험 상태의 색·문구·임계값
- [ ] Risk Replay 통계 표시 우선순위
- [ ] 근거 문서 카드 필드
- [ ] 비중 입력 UX와 오류 메시지
- [ ] 신뢰도 표현 방식
- [ ] 로딩·빈 상태·장애 상태 디자인
- [ ] 모바일 정보 우선순위
- [ ] 교육용 분석 고지 위치

데이터팀은 이 항목이 확정되기 전까지 mock JSON과 API 계약으로 작업한다.

---

## 18. 지금 바로 시작할 2주 권장 순서

### 1~2일차: 연결 확인

- [ ] 토스 OAuth·허용 IP·종목·현재가·일봉 호출
- [ ] OpenDART·NAVER 인증 확인
- [ ] 삼성전자 1종목 raw snapshot 확보
- [ ] 공통 스키마와 sample JSON 확정

### 3~4일차: 세로 데이터 파이프라인

- [ ] 삼성전자 2년 일봉
- [ ] 삼성전자 과거 공시·최근 뉴스
- [ ] 정규화·중복 제거
- [ ] 일봉 그래프와 최신 사건 API

### 5~6일차: 사건 분석

- [ ] TF-IDF 위험 키워드
- [ ] BERT 임베딩
- [ ] BERTopic 초벌 모델
- [ ] RiskEvent 병합

### 7~8일차: Replay

- [ ] 1·5·20일 수익률
- [ ] KOSPI 비정상수익률
- [ ] 유사 사건 Top-K
- [ ] 포트폴리오 단순 영향

### 9~10일차: 학습 기준선

- [ ] DailyFeature 생성
- [ ] Logistic Regression
- [ ] 시간순 평가·오류 분석
- [ ] 표본이 충분하면 MLP 비교

### 11~12일차: 포트폴리오와 근거

- [ ] 최소분산·위험 패널티 최적화
- [ ] RAG 검색과 source 검증
- [ ] fallback 구현

### 13~14일차: 확장·검증

- [ ] 10종목 확장
- [ ] 데이터 품질 보고서
- [ ] E2E 장애 테스트
- [ ] Swagger·JSON 기반 데모

---

## 19. 핵심 MVP 완료 정의

- [ ] 10개 종목의 종목 정보·현재가·2년 일봉이 수집된다.
- [ ] 가격·공시·뉴스가 공통 종목코드와 거래일로 연결된다.
- [ ] 최신 사건이 중복 없이 생성된다.
- [ ] 현재 사건과 유사한 과거 사건 3~5건이 검색된다.
- [ ] 사건 후 1·5·20일 반응과 표본 수가 계산된다.
- [ ] 사용자의 현재 비중을 반영한 영향 시나리오가 나온다.
- [ ] Logistic Regression 기준선이 시간순 테스트로 평가된다.
- [ ] MLP는 기준선보다 좋을 때만 채택된다.
- [ ] 제안 비중의 합이 100%이고 제약조건을 통과한다.
- [ ] 모든 RAG 핵심 주장에 실제 source ID와 원문 링크가 있다.
- [ ] 데이터 기준시각·버전·신뢰도·한계가 결과에 포함된다.
- [ ] 모든 외부 API가 실패해도 저장된 snapshot으로 핵심 데모가 작동한다.

---

## 공식 자료

- [토스증권 Open API 가이드](https://developers.tossinvest.com/docs)
- [토스증권 서버 소유 OpenAPI 명세](https://openapi.tossinvest.com/openapi-docs/latest/openapi.json)
- [OpenDART 공시검색 API](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001)
- [NAVER API HUB 뉴스 검색](https://api.ncloud-docs.com/docs/en/naver-api-hub-search-news)
- [KRX OPEN API 서비스 목록](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd)
