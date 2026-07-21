# StockEcho MVP 데이터 수집·처리·모델링 결정안

> 작성일: 2026-07-21  
> 범위: KOSPI 대형주 약 10개, 일봉 기반, 공시·뉴스 기반 사건 분석, 포트폴리오 영향 시나리오

## 0. 먼저 확정할 핵심 원칙

홈 화면을 열 때 브라우저가 KRX·OpenDART·뉴스 API를 직접 호출하지 않는다.

```text
외부 API
→ 백엔드 수집기(하루 1회 또는 수동 갱신)
→ Raw snapshot
→ 검증·정규화·특징 생성
→ 운영 DB
→ 홈 화면이 우리 API 호출
```

이렇게 해야 API 키가 노출되지 않고, 외부 API가 느리거나 중단돼도 화면이 열리며, 같은 기준시점의 데이터로 모델 결과를 재현할 수 있다.

가격의 P0 원천은 **토스증권 Open API**로 변경한다. 토스증권은 현재가, 종목 기본정보, 1분봉·일봉 OHLCV, 국내 시장 캘린더와 시장 지표를 REST API로 제공한다. 현재가는 최대 200종목을 한 번에 조회할 수 있으므로 MVP 10종목은 서버가 한 요청으로 주기 갱신한다. 모델 학습과 Risk Replay는 수정주가가 적용된 일봉을 사용한다.

토스증권은 현재 WebSocket을 제공하지 않으므로 진짜 체결 이벤트 스트리밍이 아니라 서버가 현재가 REST API를 5~10초 간격으로 폴링하는 **준실시간 표시**로 구현한다. 폴링 장애 시 마지막으로 저장한 일봉 종가로 대체한다.

- [토스증권 Open API 공식 가이드](https://developers.tossinvest.com/docs)
- [토스증권 Open API 공식 명세](https://openapi.tossinvest.com/openapi-docs/latest/openapi.json)
- [KRX OPEN API 서비스 목록](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd) — 선택적 검증·fallback

---

## 1. 주식 데이터

### 1.1 어디서 받아오는가

P0 데이터 소스는 토스증권 Open API의 다음 세 종류로 정한다.

1. `GET /api/v1/stocks`: 종목명, 시장, 통화, 상장·거래정지 상태
2. `GET /api/v1/prices`: 현재가와 기준시각, 최대 200종목 다건 조회
3. `GET /api/v1/candles`: 1분봉·일봉 OHLCV, 최대 200개 봉씩 페이지네이션

가격 데이터의 이상 여부를 확인할 때만 KRX 일별매매정보 또는 로컬 CSV snapshot을 보조 원천으로 사용한다.

### 1.2 언제 받아오는가

- 최초 적재: 토스 캔들 API 페이지네이션으로 선정한 10개 종목의 최근 2년 이상 수정 일봉 수집
- 정기 갱신: 장 마감 이후 하루 1회
- 장중 현재가: 서버가 10개 종목을 묶어 5~10초 간격으로 REST 폴링
- 수동 갱신: 관리자용 `/admin/refresh`
- 홈 화면 진입: 외부 API를 호출하지 않고 우리 DB의 마지막 정상 데이터 조회

### 1.3 저장 형식

#### Company

```json
{
  "stockCode": "005930",
  "companyName": "삼성전자",
  "market": "KOSPI",
  "sector": "전기전자",
  "isActive": true
}
```

#### MarketDaily

```json
{
  "stockCode": "005930",
  "tradingDate": "2026-07-20",
  "open": 74200,
  "high": 75100,
  "low": 73800,
  "close": 74900,
  "volume": 14200123,
  "change": 900,
  "changeRate": 1.22,
  "collectedAt": "2026-07-21T18:20:00+09:00",
  "source": "KRX_OPEN_API"
}
```

`change`와 `changeRate`는 원천 값이 일관되게 제공되면 그대로 저장하고, 그렇지 않으면 이전 거래일 종가로 서버에서 계산한다.

```text
change = 오늘 종가 - 이전 거래일 종가
changeRate = change / 이전 거래일 종가 × 100
```

### 1.4 홈 화면 응답 형식

`GET /api/stocks`

```json
{
  "asOf": "2026-07-20T15:30:00+09:00",
  "priceType": "EOD",
  "items": [
    {
      "stockCode": "005930",
      "companyName": "삼성전자",
      "market": "KOSPI",
      "sector": "전기전자",
      "close": 74900,
      "change": 900,
      "changeRate": 1.22,
      "volume": 14200123,
      "sparkline": [72100, 72800, 73500, 74000, 74900],
      "latestEventCount": 2,
      "dataStatus": "fresh"
    }
  ]
}
```

홈 화면에 필요한 최소 필드는 다음과 같다.

- 종목코드, 회사명, 시장, 업종
- 마지막 종가
- 전 거래일 대비 가격 및 등락률
- 거래량
- 데이터 기준일과 `EOD` 표시
- 최근 5~20거래일 sparkline
- 최신 사건 수 또는 최신 위험 상태

사용자가 종목을 담고 편집하고 삭제하는 기능은 가격 데이터와 별개다. MVP에서 로그인 기능이 없다면 포트폴리오 선택 상태는 우선 브라우저 `localStorage`에 저장하고, 분석 요청 시 서버로 전송한다.

### 1.5 그래프 데이터

그래프 이미지를 받아오는 것이 아니라, 날짜별 OHLCV 배열을 JSON으로 받아 프런트에서 그린다.

`GET /api/stocks/{stockCode}/prices?range=3M`

```json
{
  "stockCode": "005930",
  "range": "3M",
  "interval": "1d",
  "asOf": "2026-07-20",
  "items": [
    {
      "date": "2026-07-17",
      "open": 72100,
      "high": 73500,
      "low": 71800,
      "close": 73000,
      "volume": 13102000
    },
    {
      "date": "2026-07-20",
      "open": 74200,
      "high": 75100,
      "low": 73800,
      "close": 74900,
      "volume": 14200123
    }
  ]
}
```

- 홈의 작은 그래프: `close`만 사용한 sparkline
- 종목 상세: OHLC로 캔들 차트, volume으로 거래량 막대
- Risk Replay: 사건일을 기준으로 수익률을 0%로 맞춘 누적수익률 선 그래프
- 휴장일은 행을 만들지 않고 실제 거래일 배열만 반환

---

## 2. 최신 사건

### 2.1 어디서 받아오는가

두 원천을 결합한다.

1. **OpenDART 공시**: 공식 공시검색 API
2. **NAVER API HUB 뉴스 검색**: 회사명·대표 약칭을 검색어로 사용

OpenDART는 회사·기간·공시 유형으로 조회할 수 있고 JSON 응답을 제공한다. NAVER API HUB 뉴스 검색은 REST API이며 제목, 원문 링크, 네이버 링크, 설명, 발행시각을 받을 수 있다.

- [OpenDART 공시검색 API](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001)
- [NAVER API HUB 뉴스 검색](https://api.ncloud-docs.com/docs/en/naver-api-hub-search-news)

### 2.2 어떻게 받아오는가

#### OpenDART

```text
GET https://opendart.fss.or.kr/api/list.json
  ?crtfc_key={SERVER_KEY}
  &corp_code={CORP_CODE}
  &bgn_de={YYYYMMDD}
  &end_de={YYYYMMDD}
  &page_no=1
  &page_count=100
```

종목코드를 DART `corp_code`로 바로 조회할 수 없으므로 고유번호 파일을 먼저 받아 매핑 테이블을 만든다.

#### NAVER API HUB

```text
GET https://naverapihub.apigw.ntruss.com/search/v1/news
  ?query={회사명 또는 회사명+핵심어}
  &display=100
  &start=1
  &sort=date
```

인증키는 서버 요청 헤더에만 둔다. 뉴스 검색은 공식 문서 기준 일일 25,000회 제한이 있으므로 사용자 화면 진입마다 호출하지 않고 배치 수집한다.

### 2.3 정규화 형식

```json
{
  "documentId": "news_005930_hash",
  "stockCode": "005930",
  "sourceType": "news",
  "title": "정제된 제목",
  "summary": "정제된 설명",
  "publishedAt": "2026-07-21T09:10:00+09:00",
  "url": "https://publisher.example/article",
  "contentHash": "sha256...",
  "collectedAt": "2026-07-21T18:20:00+09:00"
}
```

처리 순서는 다음과 같다.

```text
HTML 태그 제거
→ URL 정규화
→ URL/contentHash 중복 제거
→ 회사명 오탐 필터
→ 한국어 텍스트 정제
→ 위험 키워드·ESG 분류
→ 사건 방향 분류
→ 임베딩 생성
→ BERTopic topic 할당
→ CompanyDocument 저장
```

### 2.4 최신 사건 생성 규칙

문서 한 건을 바로 사건 한 건으로 취급하면 같은 사건을 여러 언론사가 보도할 때 중복된다. 따라서 아래 조건으로 문서를 하나의 사건으로 묶는다.

```text
같은 stockCode
+ 같은 거래일
+ 같은 topicId
+ 문서 임베딩 cosine similarity ≥ 임계값
= 하나의 RiskEvent
```

RiskEvent의 대표 제목은 공시가 있으면 공시를 우선하고, 없으면 가장 이른 원문 또는 가장 중심성이 높은 뉴스 제목을 사용한다.

`최신 사건`은 단순히 가장 최근 뉴스가 아니라 다음 우선순위로 정렬한다.

```text
위험 방향
→ 발행시각 최신순
→ 공시 우선
→ 문서 수와 텍스트 위험 강도
```

---

## 3. 과거 사건

### 3.1 어디서 받아오는가

최신 사건과 별도의 API가 있는 것이 아니다. 동일한 OpenDART·뉴스 수집 파이프라인을 과거 기간에 대해 실행해 사건 데이터셋을 먼저 구축한다.

- 공시: OpenDART에서 MVP 대상 기업의 과거 공시를 기간별 수집
- 뉴스: NAVER API HUB 검색 결과에서 확보 가능한 범위 수집
- 가격: KRX 일봉으로 사건 후 시장 반응 계산
- 벤치마크: KOSPI 지수 일봉으로 비정상수익률 계산

중요한 제한이 있다. 뉴스 검색 API는 검색 결과 API이지 완전한 뉴스 아카이브를 보장하는 데이터셋이 아니다. 따라서 MVP의 과거 사건은 **공시를 기준 데이터로 삼고 뉴스는 보강 근거로 사용**한다. 뉴스가 부족한 오래된 사건까지 동일한 커버리지를 가정하면 안 된다.

### 3.2 어떻게 만드는가

```text
과거 공시·뉴스 수집
→ 최신 사건과 동일한 정규화
→ 임베딩 생성
→ BERTopic 학습 및 topicId 부여
→ 같은 종목·거래일·토픽의 문서를 RiskEvent로 병합
→ 사건일과 KRX 거래일 정렬
→ 사건 후 1·5·20일 수익률 계산
→ KOSPI 대비 비정상수익률 계산
→ 벡터 DB와 RiskEvent 테이블 적재
```

장 마감 이후 발표된 문서는 다음 거래일을 사건일로 사용한다. 정확한 발행시각을 얻을 수 없는 공시는 보수적으로 다음 거래일 처리하거나 `eventTimeConfidence=low`를 기록한다.

```json
{
  "eventId": "evt_005930_20250710_12",
  "stockCode": "005930",
  "eventDate": "2025-07-10",
  "topicId": 12,
  "topicLabel": "개인정보·보안·규제",
  "direction": "risk",
  "documentIds": ["dart_x", "news_y"],
  "return1d": -0.012,
  "return5d": -0.046,
  "return20d": -0.031,
  "abnormalReturn5d": -0.039,
  "recoveryDays": 13,
  "topicModelVersion": "bertopic-v1"
}
```

현재 사건 검색은 먼저 `topicId`, 방향, 분석 기준시점으로 후보를 줄인 뒤 문서 임베딩 유사도로 Top-K를 선택한다. BERTopic만으로 유사 사건을 정하지 않고 **토픽 필터 + BERT 계열 문장 임베딩 유사도**를 함께 사용한다.

---

## 4. 내 포트폴리오에 미칠 영향

여기에는 하나의 만능 모델을 쓰지 않는다. 서로 다른 세 문제로 분리한다.

### 4.1 과거 사건 영향 시나리오: 모델 없이 계산

사용자에게 가장 먼저 보여줄 영향은 ML 예측값이 아니라 검증 가능한 산술 계산이다.

```text
종목 충격 = 현재 종목 비중 × 유사 사건의 5일 대표 수익률
포트폴리오 충격 = 모든 종목 충격의 합
```

대표 수익률은 이상치에 덜 민감한 중앙값을 기본으로 사용하고 평균, 하락 비율, 표본 수를 함께 표시한다.

예시:

```text
NAVER 비중 20%
유사 사건 5일 수익률 중앙값 -4.6%
포트폴리오 영향 시나리오 = 0.20 × -4.6% = -0.92%
```

이것은 미래 예측이 아니라 과거 사건 반응을 현재 비중에 적용한 시나리오다.

### 4.2 향후 하락 위험: Logistic Regression → MLP

별도로 각 종목의 향후 5거래일 하락 위험 확률을 학습한다.

```text
라벨 = t+5 누적수익률이 -3% 이하이면 1, 아니면 0
```

입력 특징:

- 1·5·20일 수익률
- 5·20일 변동성
- 거래량 비율
- 20일 낙폭
- 이동평균 괴리
- KOSPI 수익률
- 최근 7일 문서 수
- 최근 7일 텍스트 위험점수
- E/S/G 점수
- 유사 사건 과거 하락 비율

모델 적용 순서:

1. Logistic Regression 기준선
2. MLP `Dense(64) → Dense(32) → sigmoid`
3. 시간순 테스트에서 MLP가 Recall·Precision·F1·PR-AUC를 실제로 개선할 때만 제품에 채택

표본이 적거나 MLP가 기준선보다 낫지 않으면 Logistic Regression을 사용한다. 수업 기술을 보여주기 위해 성능이 낮은 모델을 억지로 제품에 넣지 않는다.

### 4.3 제안 비중: 최적화 모델

제안 비중은 LLM이나 신경망이 생성하지 않는다. SciPy 또는 CVXPY의 제약 최적화를 사용한다.

```text
최소화 = 포트폴리오 분산 또는 CVaR
       + α × 하락 위험 가중합
       + β × 텍스트 위험 가중합
       + γ × 현재 비중 대비 변경량

제약
- 비중 합 = 1
- 비중 ≥ 0
- 성향별 종목 최대 비중
```

최적화가 실패하면 현재 비중과 동일가중 포트폴리오만 비교한다.

---

## 5. 수업에서 배운 기술의 사용 위치

| 기술 | MVP 사용 여부 | 사용 위치 | 결정 이유 |
|---|---|---|---|
| NLP 전처리 | 필수 | 공시·뉴스 HTML 제거, 형태소 분석, 불용어 처리 | 모든 텍스트 분석의 기반 |
| TF-IDF | 필수 | 위험 키워드, 텍스트 위험 기준선, 키워드 유사도 | 설명 가능하고 작은 데이터에서도 안정적 |
| BERT 계열 임베딩 | 필수 | 현재 사건과 과거 사건의 의미 유사도 검색 | 단어가 달라도 의미가 비슷한 문서를 찾기 위함 |
| BERTopic | 필수 | 사건 주제 군집화와 토픽 필터 | 현재 사건을 같은 종류의 과거 사건과 연결 |
| Logistic Regression | 필수 기준선 | 향후 5일 하락 위험 분류 | 작은 표본에서 안정적이고 비교 기준이 됨 |
| MLP | 조건부 P0 | 하락 위험 분류 | 기준선보다 좋아질 때만 사용 |
| LSTM | P1 실험 | 문장 위험/일반 분류 또는 시계열 비교 실험 | 라벨과 표본이 충분하지 않으면 과적합 가능성이 큼 |
| 기본 RNN | 제외 권장 | 별도 제품 역할 없음 | LSTM보다 장기 의존성 처리에 불리하고 중복 시연이 됨 |
| DL | 별도 기술 아님 | MLP·LSTM·BERT를 포괄하는 분류 | “DL 사용” 자체를 별도 기능으로 만들 필요 없음 |
| RAG·LLM | 필수 | 계산 결과를 실제 공시·뉴스 근거로 설명 | 계산이 아니라 설명만 담당 |
| SciPy/CVXPY | 필수 | 제약조건이 있는 비중 최적화 | 검증 가능하고 결과를 통제할 수 있음 |

### 권장 P0 기술 묶음

```text
KRX·OpenDART·NAVER API HUB 수집
→ pandas 정규화·특징 생성
→ NLP·TF-IDF 텍스트 위험
→ BERT 임베딩·BERTopic 사건 군집
→ Event Study Risk Replay
→ Logistic Regression 기준선
→ 성능이 확인되면 MLP
→ SciPy/CVXPY 비중 최적화
→ RAG 근거 설명
```

LSTM과 기본 RNN은 핵심 데모가 완성된 뒤 비교 실험 노트북으로 두는 것이 좋다.

---

## 6. 모델 학습용 데이터셋

### 6.1 사건 데이터셋

분석 단위는 `stockCode × eventDate`다.

용도:

- BERTopic 학습
- 유사 사건 검색
- 사건 후 1·5·20일 반응 통계
- RAG 근거 연결

### 6.2 일별 위험 데이터셋

분석 단위는 `stockCode × featureDate`다.

```text
가격 특징(t 이전)
+ 텍스트 특징(t 이전)
+ ESG 특징(t 이전)
→ downsideLabel5d(t 이후)
```

분할:

```text
Train: 가장 오래된 70%
Embargo: 5거래일
Validation: 다음 15%
Embargo: 5거래일
Test: 가장 최근 15%
```

- 랜덤 분할 금지
- StandardScaler는 Train에만 fit
- class weight 우선
- SMOTE를 쓴다면 Train 안에서만 적용
- 사건일 이후에 나온 문서나 수익률을 해당 시점 특징에 포함하지 않음
- 모델 비교는 Accuracy보다 Recall, Precision, F1, PR-AUC 중심

---

## 7. 구현 순서

1. MVP 대상 종목 10개와 `stockCode ↔ corpCode ↔ companyName/aliases` 확정
2. KRX 일봉 2년 수집 및 `MarketDaily` 저장
3. OpenDART 공시 수집 및 `CompanyDocument` 정규화
4. NAVER 뉴스 수집·중복 제거·회사 오탐 필터
5. 가격 그래프와 최신 사건 API 완성
6. TF-IDF 위험점수와 사건 방향 규칙 기준선 구현
7. BERT 임베딩·BERTopic으로 과거 사건 데이터셋 생성
8. 사건 후 1·5·20일 수익률과 KOSPI 대비 비정상수익률 계산
9. 포트폴리오 단순 영향 시나리오 구현
10. Logistic Regression 학습·시간순 평가
11. MLP 학습 후 기준선과 비교
12. 제약 최적화와 RAG 설명 연결

가장 먼저 완성할 세로 흐름은 다음이다.

```text
삼성전자 1종목
→ 가격·공시·뉴스 수집
→ 최신 사건 1건 생성
→ 과거 유사 사건 검색
→ 5일 반응 계산
→ 사용자 비중 적용
→ 근거와 함께 화면 표시
```

이 흐름이 성공한 뒤 10개 종목으로 확장한다.

---

## 8. 가격 표시 최종 결정

토스증권 API 키 발급을 전제로 다음처럼 확정한다.

- 장중: 토스 현재가 API를 5~10초 간격으로 서버에서 다건 폴링해 `준실시간` 표시
- 장 종료·휴장·API 장애: 마지막 검증 일봉 종가 표시
- 그래프: 토스 1일봉 OHLCV
- 모델 학습·Risk Replay: 토스 수정 일봉 OHLCV
- 1분봉 그래프: P1
- 계좌·보유자산·주문·조건주문 API: Non-Goal

화면에는 `실시간` 대신 실제 갱신시각을 표시한다.

```text
75,100원 · 14:32:10 기준
```

REST 폴링이 중단되면 다음처럼 명확하게 전환한다.

```text
74,900원 · 7월 20일 종가
```
