# StockEcho MVP 데이터 수집·처리·모델링 결정안

> 작성일: 2026-07-21
> 상태: MVP 구현 기준
> 상위 기준: [MVP 백엔드·데이터 수집 아키텍처 결정안](./MVP_백엔드_데이터_수집_아키텍처_결정안.md)

## 1. 문서 목적

이 문서는 StockEcho MVP의 데이터 구조, 정규화 규칙, 관련도 판정, 사건 생성, 포트폴리오 계산, 모델 도입 순서를 정의한다.

기술 결정이 충돌하면 상위 아키텍처 결정안을 우선한다.

```text
KIS·NAVER API HUB·OpenDART
→ Lightsail Python 증분 수집기
→ 정규화·중복 제거·관련도 판정
→ Supabase PostgreSQL
→ Next.js DAL 직접 조회
→ 사용자 포트폴리오 영향 계산
```

## 2. 데이터 범위

### 2.1 지원 범위

- KOSPI 인기 대형주 20개
- 사용자는 지원 종목 중 1~5개 선택
- 포트폴리오 비중 합계 100%
- 로그인 없이 `localStorage` 사용
- 사용자 포트폴리오는 MVP 서버 DB에 저장하지 않음

지원 종목과 Tier는 `companies` 테이블에서 관리한다. 목록은 상위 아키텍처 결정안을 따른다.

### 2.2 데이터 원천

| 데이터 | 원천 | 운영 저장 |
|---|---|---|
| 현재가 | KIS Open API | 영구 저장하지 않고 5~10초 메모리 캐시 |
| 일봉 OHLCV | KIS Open API | PostgreSQL |
| 뉴스 | NAVER API HUB | 제목·요약·링크·발행시각·검색 근거 |
| 공시 | OpenDART | 공시 메타데이터·원문 링크 |
| Raw 응답 | 각 외부 API | 변경·신규·오류 시 Private Storage에 gzip 저장 |

언론사 본문 HTML은 MVP 기본 수집 대상이 아니다.

## 3. 데이터 생명주기

```text
API 응답
→ Raw payload hash 비교
→ 필드 검증
→ 텍스트·URL·시각 정규화
→ 기사 중복 제거
→ 기사-검색어 연결
→ 기사-종목 관련도 판정
→ 키워드 후보 계산
→ 정제 테이블 upsert
→ Next.js 조회
```

모든 단계는 같은 입력을 반복 처리해도 결과가 중복되지 않아야 한다.

### 3.1 Raw 보관

- `collection_runs`는 실행할 때마다 기록한다.
- Raw payload는 이전 hash와 다르거나 신규 데이터·오류가 있을 때 저장한다.
- Raw 기본 보관 기간은 14일이다.
- 자동 품질 평가 결과, 학습 데이터셋, 오류 재현 자료는 별도 prefix에 장기 보관한다.

```text
raw/news/<source>/2026-07-21/<query_id>/153250_<hash>.json.gz
datasets/news-relevance/v1/train.parquet
models/news-relevance/v1/<artifact>
```

## 4. 핵심 데이터 모델

### 4.1 companies

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | uuid | 내부 PK |
| `stock_code` | text unique | 6자리 종목 코드 |
| `corp_code` | text unique nullable | OpenDART 고유번호 |
| `name` | text | 정식 회사명 |
| `market` | text | `KOSPI` |
| `sector` | text nullable | 업종 힌트 |
| `is_supported` | boolean | 서비스 지원 여부 |
| `collection_tier` | text | `A` 또는 `B` |
| `activated_at` | timestamptz | 수집 활성화 시각 |

업종은 세부 사업 키워드의 정답이 아니라 약한 prior로만 사용한다.

### 4.2 market_daily

| 필드 | 타입 | 설명 |
|---|---|---|
| `company_id` | uuid | 회사 FK |
| `trading_date` | date | 실제 거래일 |
| `open` | numeric | 시가 |
| `high` | numeric | 고가 |
| `low` | numeric | 저가 |
| `close` | numeric | 종가 |
| `volume` | bigint | 거래량 |
| `adjusted` | boolean | 수정주가 여부 |
| `source` | text | `KIS` |
| `collected_at` | timestamptz | 수집 시각 |

PK는 `(company_id, trading_date)`로 한다. 휴장일 행은 만들지 않는다.

### 4.3 news_articles

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | uuid | 내부 PK |
| `source` | text | `NAVER_NEWS_SEARCH` |
| `source_id` | text nullable | 원천 식별자 |
| `title` | text | 태그 제거 제목 |
| `summary` | text | 태그 제거 요약 |
| `canonical_url` | text unique | 정규화 원문 URL |
| `source_url` | text nullable | 수집 소스가 제공한 링크 |
| `published_at` | timestamptz | 발행시각 UTC 저장 |
| `content_hash` | text | 정규화 콘텐츠 hash |
| `collected_at` | timestamptz | 최초 수집시각 |
| `updated_at` | timestamptz | 마지막 갱신시각 |

`canonical_url`을 우선 중복 기준으로 사용하고 URL이 불안정할 때 `content_hash`를 보조 기준으로 사용한다.

### 4.4 article_companies

| 필드 | 타입 | 설명 |
|---|---|---|
| `article_id` | uuid | 기사 FK |
| `company_id` | uuid | 회사 FK |
| `relation_type` | text | `direct`, `product`, `industry` |
| `confidence` | numeric | 0~1 관련도 |
| `evidence` | jsonb | 판정 근거 |
| `rule_version` | text | 판정 규칙 버전 |

PK는 `(article_id, company_id)`다. 관련도 판정 근거가 없는 연결은 저장하지 않는다.

### 4.5 search_queries와 query_companies

`search_queries`는 뉴스 source adapter가 실행하는 검색 단위다. NAVER는 현재 연결된 첫 adapter다.

| 필드 | 설명 |
|---|---|
| `query` | 정규화 검색어, unique |
| `query_type` | `company`, `product`, `industry`, `event` |
| `status` | `active`, `paused`, `expired` |
| `last_seen_published_at` | 증분 수집 checkpoint |
| `last_collected_at` | 마지막 실행 시각 |

`query_companies`는 검색어와 영향 종목의 다대다 관계를 저장한다.

| 필드 | 설명 |
|---|---|
| `query_id` | 검색어 FK |
| `company_id` | 회사 FK |
| `weight` | 연결 강도 |
| `evidence` | 연결 근거 |

발견 초기에는 `삼성전자 HBM`처럼 회사 문맥을 포함해 정밀도를 우선한다. 동일 산업어가 여러 회사에서 검증되면 공용 `HBM` 검색으로 승격하고 한 번 수집한 기사를 여러 회사에 연결한다.

### 4.6 article_queries

기사가 어떤 검색으로 들어왔는지 보존한다.

```text
PK: (article_id, query_id)
fields: rank, collected_at
```

### 4.7 keyword_candidates

| 필드 | 설명 |
|---|---|
| `company_id` | 대상 회사 |
| `keyword` | 후보 키워드 |
| `score` | 종합 점수 |
| `document_count` | 등장 기사 수 |
| `source_count` | 서로 다른 출처 수 |
| `title_count` | 제목 등장 수 |
| `status` | `candidate`, `active`, `expired`, `rejected` |
| `evidence_article_ids` | 근거 기사 목록 |
| `discovered_at` | 발견 시각 |
| `expires_at` | 만료 기준시각 |
| `rule_version` | 생성 규칙 버전 |

### 4.8 disclosures

| 필드 | 설명 |
|---|---|
| `rcept_no` | OpenDART 접수번호, unique |
| `company_id` | 회사 FK |
| `report_name` | 보고서명 |
| `filer_name` | 공시 제출인 |
| `received_at` | 접수시각 |
| `url` | OpenDART 원문 링크 |
| `collected_at` | 수집시각 |

### 4.9 collection_runs

| 필드 | 설명 |
|---|---|
| `job_name` | 작업 이름 |
| `source` | KIS, NAVER, DART |
| `query_id` | 검색 작업일 때 FK |
| `started_at`, `finished_at` | 실행 구간 |
| `status` | `running`, `success`, `partial`, `failed` |
| `request_count` | 외부 호출 수 |
| `received_count` | 수신 건수 |
| `new_count` | 신규 건수 |
| `duplicate_count` | 중복 건수 |
| `ignored_count` | 무관 기사 수 |
| `payload_hash` | Raw hash |
| `raw_path` | Storage 경로 |
| `error_code`, `error_message` | 오류 정보 |
| `code_version` | 실행 코드 버전 |

## 5. 정규화 규칙

### 5.1 텍스트

- NAVER `<b>` 태그와 HTML entity 제거
- 연속 공백 정리
- 원문 제목은 보존하고 비교용 제목 key를 별도로 생성
- 검색어 포함 여부만으로 관련 기사라고 판단하지 않음

### 5.2 URL

- scheme·host 소문자화
- fragment 제거
- `utm_*`, `fbclid`, `gclid` 등 추적 파라미터 제거
- `originallink`를 우선 canonical URL로 사용
- URL이 없으면 제목·발행시각 조합 hash 사용

### 5.3 시각

- DB에는 UTC `timestamptz`로 저장
- 거래일 판단과 화면 표시는 Asia/Seoul 기준
- API 응답에는 데이터 기준시각 `asOf` 포함

### 5.4 수치

- 가격은 float가 아니라 PostgreSQL `numeric` 사용
- 비중은 0 초과 100 이하, 합계 100 검증
- 수익률 계산 시 거래정지·결측·상장 전 구간 제외

## 6. 뉴스 관련도

### 6.1 관계 유형

```text
direct   회사가 제목·요약에 직접 언급됨
product  검증된 제품·사업이 회사와 직접 연결됨
industry 회사명이 없지만 산업 사건의 영향 대상임
irrelevant 수집됐지만 해당 종목과 의미 있는 관계가 없음
```

### 6.2 규칙 기반 P0

P0는 회사명 위치, 문장 내 역할, 검색어-회사 연결 근거를 사용하는 설명 가능한 공통 규칙으로 시작한다.

- 정식 회사명이 제목에 등장하면 direct 높은 점수
- 요약에만 등장하면 문맥과 주어를 추가 확인
- 모호한 그룹명 단독 등장은 direct 근거로 사용하지 않음
- active 제품 검색어는 회사-제품 evidence가 있을 때만 product 후보
- 산업 기사는 `query_companies.weight`와 사건 문맥을 함께 사용
- 부고·채용·지역 행사·주가 나열처럼 분석 가치가 낮은 패턴은 감점

규칙은 특정 회사명에 종속시키지 않고 모든 종목에 동일하게 적용한다. 종목별 신규·무시 비율과 근거 유형 분포를 저장하여 자동화 품질을 비교한다.

### 6.3 키워드 승격

- 회사명이 제목에 직접 등장한 고신뢰 seed 기사에서 추출
- 서로 다른 기사 2건 이상
- 서로 다른 출처 2개 이상
- 제목 등장 또는 회사명과 같은 문맥
- 일반어·경쟁사 전용어 제외
- 종목당 active 3~5개 이하
- 7일간 근거가 약해지면 만료 후보

조건을 모두 통과한 후보만 자동 승격하며, 종목당 active 검색어 상한을 초과하면 점수가 낮은 후보는 candidate로 유지한다.

## 7. 사건 데이터

P0에서는 기사를 완전 자동 군집화하지 않는다. 먼저 기사와 공시를 종목·날짜·정규화 사건 key로 묶는 규칙 기반 사건을 만든다.

### 7.1 risk_events

| 필드 | 설명 |
|---|---|
| `company_id` | 회사 FK |
| `event_date` | KST 기준 사건일 |
| `event_type` | 실적, 규제, 소송, 공급망 등 |
| `direction` | `negative`, `neutral`, `positive`, `unknown` |
| `title` | 대표 사건명 |
| `confidence` | 사건 신뢰도 |
| `source_count` | 근거 문서 수 |
| `rule_version` | 생성 규칙 버전 |

공시가 연결된 경우 공시를 우선 근거로 삼는다. 같은 사건의 기사 여러 건은 `event_documents`로 연결한다.

### 7.2 가격 반응

사건일 이후 실제 거래일 기준 1일·5일·20일 수익률을 계산한다.

```text
return_n = close(event_date + n trading days) / close(event_date) - 1
```

사건이 장 마감 뒤 발생하면 다음 거래일을 기준일로 사용한다. 시장 대비 비정상수익률은 데이터가 안정된 뒤 추가한다.

## 8. 사용자 응답 모델

### 8.1 종목 뉴스

```json
{
  "stockCode": "005930",
  "asOf": "2026-07-21T07:30:00Z",
  "stale": false,
  "items": [
    {
      "articleId": "uuid",
      "title": "기사 제목",
      "summary": "기사 요약",
      "publishedAt": "2026-07-21T07:20:00Z",
      "url": "https://publisher.example/article",
      "relationType": "direct",
      "confidence": 0.92,
      "evidence": ["title_company_name"]
    }
  ]
}
```

### 8.2 가격

현재가는 요청 시 KIS에서 조회한다. 호출 실패 시 마지막 일봉 종가를 반환하고 `priceType: EOD_FALLBACK`, `stale: true`로 표시한다.

```json
{
  "stockCode": "005930",
  "price": 74900,
  "priceType": "LIVE_DELAYED",
  "asOf": "2026-07-21T07:30:05Z",
  "stale": false
}
```

### 8.3 포트폴리오 분석

```json
{
  "holdings": [
    { "stockCode": "005930", "weight": 60 },
    { "stockCode": "000660", "weight": 40 }
  ]
}
```

서버는 지원 종목·개수·비중 합계를 검증하고, 선택 종목의 최신 사건과 과거 가격 반응을 비중 가중하여 계산한다.

```text
portfolioImpact = Σ(weight_i × companyImpact_i)
```

MVP 결과는 예측 수익률이 아니라 과거 관측을 기반으로 한 영향 시나리오로 표현한다.

## 9. 모델 도입 순서

### P0: 모델 없이 검증 가능한 기준선

- URL·content hash 중복 제거
- Kiwi·TF-IDF 키워드 후보
- 규칙 기반 기사 관련도
- 규칙 기반 사건 연결
- 사건 전후 수익률
- 비중 가중 포트폴리오 영향

### P1: 가격 반응 기반 방향·위험 모델

- 사건 이후 실제 가격 반응으로 자동 생성한 target 사용
- Logistic Regression 기준선보다 개선될 때만 작은 MLP 도입
- 시간순 train/validation/test 분할
- PR-AUC, recall, calibration과 기간별 안정성 평가

### P2: 유사 사건 검색

- BERTopic·SentenceTransformer 실험
- pgvector 도입 여부 평가
- 규칙 기반 후보보다 검색 품질이 개선될 때만 운영 승격

Colab은 버전 고정 Parquet를 signed URL로 받아 사용한다. Supabase Secret key를 Colab에 넣지 않는다.

## 10. 데이터 품질 기준

- 동일 기사 중복 저장 0건
- 모든 기사-종목 연결에 relation type·confidence·evidence 존재
- 종목별 직접·제품·산업·무시 비율과 근거 누락률 기준 확정
- 수집 실행별 신규·중복·무시·오류 건수 기록
- 최신 데이터 실패 시 마지막 정상 데이터와 `asOf/stale` 반환
- Raw payload가 14일 보관 정책 없이 누적되지 않음
- 모델 산출물에 dataset·model·rule version 기록

## 11. 구현 순서

1. 삼성전자 NAVER 최신순 증분 수집 완성
2. 정규화·중복 제거·공통 관련도 규칙 구현
3. Supabase migration과 RLS 작성
4. `collection_runs`와 idempotent upsert 연결
5. 핵심 5종목으로 품질 검증 확장
6. KIS 일봉과 OpenDART 연결
7. Tier A 10종목 확장
8. Tier B를 포함한 20종목 확장
9. 사건·가격 반응·포트폴리오 영향 연결
10. 기준선이 완성된 뒤 Colab 모델 실험

## 12. 완료 기준

- 20종목의 뉴스·공시·일봉이 동일 회사 master로 연결된다.
- 검색어와 종목이 다대다로 관리되어 산업 검색이 중복 호출되지 않는다.
- 기사 관련도와 키워드 승격 근거를 재현할 수 있다.
- 모든 저장이 idempotent하다.
- 포트폴리오 분석이 1~5개 종목과 비중 합계를 검증한다.
- 학습 모델 없이도 P0 사용자 흐름이 끝까지 동작한다.
