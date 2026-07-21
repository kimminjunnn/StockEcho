# StockEcho MVP 백엔드·데이터 수집 아키텍처 결정안

> 작성일: 2026-07-21
> 상태: MVP 구현 기준
> 범위: 국내 인기 대형주 20개, KIS 가격, NAVER 뉴스, OpenDART 공시

## 1. 최종 결정

StockEcho MVP는 **국내 인기 대형주 20개**를 지원한다.

```text
브라우저
├─ 보유 종목·비중 입력(localStorage)
└─ 뉴스·가격·포트폴리오 영향 표시
        ↓
Next.js on Lightsail
├─ Server Components → DAL 직접 조회
├─ Route Handlers → 브라우저 비동기 API·health
├─ 포트폴리오 영향 계산
└─ KIS 현재가 조회 + 5~10초 메모리 캐시
        ↓
Supabase
├─ PostgreSQL: 정제 뉴스·공시·일봉·관계·수집 이력
└─ Private Storage: 선별 Raw·학습 데이터·모델 산출물
        ↑
Lightsail Python jobs
├─ NAVER 뉴스 증분 수집
├─ KIS 일봉 수집
├─ OpenDART 공시 수집
├─ 정규화·중복 제거
└─ 키워드 후보·기사 관련도 계산

Google Colab
├─ 버전 고정 데이터셋으로 모델 학습
├─ 평가·실험
└─ 승인된 모델 산출물 생성
```

MVP에는 별도 FastAPI 서버를 만들지 않는다. Python은 HTTP 서비스가 아니라 정해진 시간에 끝나는 배치 작업으로 실행한다. Python 온라인 추론이 사용자 응답 경로에 필요해지거나 여러 클라이언트가 공통 분석 API를 요구할 때 FastAPI를 분리한다.

가격 원천은 **KIS Open API**, 뉴스의 첫 source adapter는 **NAVER API HUB**, 공시 원천은 **OpenDART**를 사용한다. 뉴스 수집 domain은 `SearchQuery`를 입력받고 NAVER 응답 형식은 adapter 내부에서만 다루므로 다른 뉴스 API를 같은 계약으로 추가할 수 있다.

## 2. 20종목 지원 가능성

20종목은 현재 Lightsail 사양과 외부 API 한도 안에서 충분히 운영할 수 있다.

### 2.1 NAVER 호출량

NAVER 뉴스 검색 API의 공식 일일 호출 한도는 25,000회이며, 한 번에 최대 100건을 조회할 수 있다.

MVP 예상 호출량은 다음과 같다.

| 구분 | 계산 | 예상 호출량/일 |
|---|---:|---:|
| 회사명 직접 검색 | 20종목 × 장중 30분 + 장외 2시간 | 약 600~700회 |
| 동적 문맥 검색어 | 종목당 최대 5개 × 차등 주기 | 약 500~1,000회 |
| 추가 페이지·재시도 | 신규 뉴스가 많은 날의 여유분 | 약 400~1,400회 |
| 합계 | 평상시~보수적 상한 | 약 1,500~3,000회 |

보수적으로 잡아도 일일 한도의 약 6~12% 수준이다. 종목을 20개로 늘려도 NAVER 호출량은 병목이 아니다. MVP는 `삼성전자 로봇`처럼 회사명과 발견어를 결합해 정밀도를 우선한다. 이후 여러 회사에서 같은 산업어가 검증되면 공용 검색어로 승격해 한 번만 호출하고 여러 종목에 연결한다.

### 2.2 Lightsail 자원

현재 `rupa-1`은 2 vCPU, 2GB RAM, 60GB SSD이며 관측 당시 available RAM 약 1.1GB, 남은 디스크 약 26GB였다.

20종목의 제목·요약 정제와 Kiwi·TF-IDF 계산은 GPU가 필요하지 않으며, 종목을 순차 처리하면 현재 서버에서 가능하다. 다음 제한을 둔다.

- 수집 작업을 동시에 여러 개 실행하지 않는다.
- `flock`으로 중복 실행을 방지한다.
- Python worker에 메모리 제한을 둔다.
- 대량 임베딩과 모델 학습은 Colab에서 한다.
- Raw 데이터는 압축하고 보관 기간을 둔다.

실제 병목은 서버 성능보다 **검색어 증가와 기사 관련도 자동 판정의 정확성**이다. 따라서 제품 지원 범위는 20개로 잡되 자동화 품질 지표를 확인하며 5개 → 10개 → 20개 순서로 확장한다.

## 3. 지원 종목

초기 지원 목록은 기존 10종목을 유지하고, 시가총액·거래 관심도·산업 대표성을 고려한 10종목을 추가한다.

| Tier | 종목 | 코드 | 대표 영역 |
|---|---|---:|---|
| A | 삼성전자 | `005930` | 반도체·전자 |
| A | SK하이닉스 | `000660` | 반도체 |
| A | 현대차 | `005380` | 자동차 |
| A | LG에너지솔루션 | `373220` | 배터리 |
| A | 삼성바이오로직스 | `207940` | 바이오 |
| A | KB금융 | `105560` | 금융 |
| A | POSCO홀딩스 | `005490` | 철강·소재 |
| A | 한화에어로스페이스 | `012450` | 방산·항공 |
| A | NAVER | `035420` | 플랫폼·인터넷 |
| A | SK텔레콤 | `017670` | 통신 |
| B | 기아 | `000270` | 자동차 |
| B | 셀트리온 | `068270` | 바이오 |
| B | 카카오 | `035720` | 플랫폼·인터넷 |
| B | 신한지주 | `055550` | 금융 |
| B | HD현대중공업 | `329180` | 조선 |
| B | 두산에너빌리티 | `034020` | 원전·에너지 |
| B | SK스퀘어 | `402340` | 반도체 투자·지주 |
| B | 삼성물산 | `028260` | 건설·상사·지주 |
| B | 삼성생명 | `032830` | 보험 |
| B | 삼성전기 | `009150` | 전자부품 |

Tier는 사용자에게 노출하는 등급이 아니라 구축 순서를 뜻한다. 20개 모두 서비스에서 동일하게 지원한다.

지원 종목을 영구 하드코딩하지 않는다. `companies` 테이블의 `is_supported`, `collection_tier`, `activated_at`으로 관리한다. 분기마다 다음 기준으로 교체 여부를 검토한다.

- 최근 시가총액
- 최근 평균 거래대금
- 실제 사용자의 포트폴리오 선택 빈도
- 산업 대표성
- 뉴스 검색의 정밀도와 데이터 충분성

초기에는 KOSPI 종목만 지원한다. KOSDAQ 추가는 아키텍처 변경 없이 `market`, 종목 코드, DART corpCode를 등록하여 확장할 수 있다.

## 4. 사용자 범위

사용자는 지원 종목 중 1~5개를 선택하며 비중 합계는 100%여야 한다.

사용자가 화면에 들어올 때 외부 데이터를 새로 수집하지 않는다. 20종목의 공통 데이터는 백그라운드에서 미리 수집하고, 사용자 요청에는 선택 종목의 데이터만 필터링한다.

MVP에서는 로그인을 만들지 않는다. 종목과 비중은 브라우저 `localStorage`에 저장하고 분석 요청 시 Next.js로 전달한다. 사용자 포트폴리오는 서버 DB에 저장하지 않는다. 계정 간 동기화 요구가 확인된 이후 Supabase Auth와 사용자별 RLS를 추가한다.

## 5. 데이터 원천과 저장 범위

| 데이터 | 원천 | 저장 정책 |
|---|---|---|
| 현재가 | KIS Open API | 사용자 요청 시 조회, 5~10초 메모리 캐시 |
| 일봉 | KIS Open API | 장 마감 후 PostgreSQL 영구 저장 |
| 뉴스 | NAVER API HUB | 제목·요약·링크·발행시각·검색 근거 저장 |
| 공시 | OpenDART | 공시 메타데이터와 원문 링크 저장 |
| 사용자 입력 | 브라우저 | localStorage 저장, 서버 DB 미저장 |

NAVER API가 제공하는 제목·요약·링크만 기본 저장한다. 언론사 본문 HTML을 임의 크롤링하거나 전문을 복제하지 않는다. 본문이 필요해질 경우 매체별 이용 약관, robots 정책, 저작권을 먼저 검토한다.

## 6. 환경 변수와 권한

```dotenv
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...
DART_API_KEY=...
SUPABASE_URL=...
SUPABASE_PUBLISHABLE_KEY=...
SUPABASE_SECRET_KEY=...
```

MVP 브라우저는 Supabase를 직접 호출하지 않고 Next.js만 호출한다.

- 브라우저: Supabase key를 받지 않는다.
- Next.js: 서버 측 publishable key + read-only RLS로 공용 데이터를 조회한다.
- Python worker: 정제 데이터와 Private Storage를 쓰기 위해 Secret key를 사용한다.
- Colab: Secret key를 사용하지 않고 단기 signed URL로 데이터셋을 받는다.

Secret이 필요한 Next.js 코드는 서버 전용 모듈에 격리한다. Secret에는 `NEXT_PUBLIC_` 접두사를 붙이지 않고 Git, 로그, 오류 응답에 포함하지 않는다.

## 7. 뉴스 수집 흐름

### 7.1 직접 뉴스

모든 지원 종목은 정식 회사명을 seed 검색어로 사용한다.

```text
정식 회사명 검색
→ 최신순 결과 수신
→ HTML·URL·시각 정규화
→ URL·content hash 중복 제거
→ 회사 직접 언급 기사 분류
→ PostgreSQL upsert
```

`삼성`, `현대`, `SK`처럼 여러 계열사를 가리키는 그룹명은 단독 검색어로 사용하지 않는다.

### 7.2 동적 키워드

업종 정보만으로 회사의 실제 사업 주제를 결정하지 않는다. 업종은 후보 점수의 약한 힌트로만 사용하고 최근 직접 기사에서 제품·사업·산업 키워드를 발견한다.

```text
직접 기사 제목·요약
→ Kiwi로 명사·복합명사·영문 기술어 추출
→ TF-IDF·문서 빈도·제목 빈도 계산
→ 일반어·매체명·직함 제거
→ candidate 저장
→ 품질 기준을 통과한 소수만 active 검색어로 승격
```

키워드는 `candidate → active → expired/rejected` 상태로 관리한다.

자동 승격 전 최소 기준:

- 회사명이 제목에 직접 등장한 고신뢰 seed 기사에서 추출
- 서로 다른 기사 2건 이상 등장
- 서로 다른 출처 2개 이상 등장
- 제목에 등장하거나 회사명과 같은 문맥에 등장
- 경쟁사에만 해당하거나 지나치게 일반적인 단어가 아님
- 검색 결과에서 회사·제품·산업 연결 근거 비율이 기준치 충족
- active 검색어는 종목당 3~5개 이하
- 7일 동안 근거가 약해지면 만료 후보 처리

승격 조건을 모두 만족한 candidate만 자동으로 active가 된다. 조건을 만족하지 못하면 candidate 상태로 유지되고 검색어로 사용하지 않는다.

### 7.3 문맥 검색어와 공용 산업 검색어

발견 직후에는 `삼성전자 HBM`처럼 회사명과 결합해 오탐을 줄인다. 검색 결과에서도 회사 문맥과 발견어가 모두 확인된 기사만 종목에 연결한다. 두 개 이상의 회사에서 같은 산업어가 독립적으로 검증되면 `HBM` 공용 검색어로 승격할 수 있다.

```text
search_queries
├─ query: HBM
├─ status: active
└─ last_collected_at

query_companies
├─ query_id
├─ company_id
├─ weight
└─ evidence
```

공용 승격 이후에는 `HBM` 뉴스를 한 번만 수집하고 기사 관련도에 따라 삼성전자, SK하이닉스, SK스퀘어 등에 연결한다.

### 7.4 기사-종목 관계

```text
direct   : 회사가 제목·요약에 직접 언급됨
product  : 검증된 제품·사업과 직접 연결됨
industry : 회사명은 없지만 산업 사건의 영향 대상임
```

`article_companies`에는 `relation_type`, `confidence`, `evidence`를 저장한다. 모든 연결은 “왜 이 종목의 기사인지” 설명할 수 있어야 한다.

## 8. 증분 수집 주기

| 작업 | 기본 주기 |
|---|---|
| 회사명 직접 뉴스 | 평일 07:00~20:00 KST 30분, 그 외 2시간 |
| active 산업 검색어 | 장중 60분, 그 외 3시간 |
| 키워드 후보 재계산 | 매일 1회 |
| KIS 현재가 | 사용자 요청 시, 5~10초 메모리 캐시 |
| KIS 일봉 | 장 마감 후 1회 |
| OpenDART 최신 공시 | 장중 30분, 그 외 2시간 |
| 모델 학습 | MVP 수동 실행 |

NAVER 수집은 매번 100건을 전부 다시 처리하지 않는다.

1. `sort=date`로 최신순 조회한다.
2. 검색어별 `last_seen_published_at`과 최근 URL을 checkpoint로 둔다.
3. 이미 처리한 구간을 만나면 페이지 순회를 중단한다.
4. 일시 장애는 지수 백오프로 재시도한다.
5. `429` 응답에서는 호출을 중단하고 다음 실행으로 넘긴다.
6. 모든 쓰기는 재실행해도 결과가 같은 idempotent upsert로 처리한다.

호출량은 `collection_runs`에서 일별로 집계한다. 일일 사용량이 15,000회를 넘으면 산업 검색 주기를 자동으로 늦추고, 20,000회를 넘으면 회사명 직접 검색만 유지한다.

## 9. 저장 구조

### 9.1 PostgreSQL

```text
companies
news_articles
article_companies
search_queries
query_companies
article_queries
keyword_candidates
disclosures
market_daily
collection_runs
```

중요 제약 조건:

- `news_articles.canonical_url` unique
- URL이 불안정한 경우 `content_hash`를 보조 중복 기준으로 사용
- `article_companies(article_id, company_id)` unique
- `article_queries(article_id, query_id)` unique
- 외부 시각과 수집 시각은 UTC `timestamptz`로 저장하고 화면에서 KST로 변환
- `source`, `source_id`, `query`, `collected_at`, `payload_hash`, `data_version` 저장

PostgreSQL의 정제 데이터를 서비스 기준 데이터로 사용한다.

### 9.2 Raw Storage

Raw payload는 디버깅과 재처리를 위한 자료이며 서비스 화면에서 직접 읽지 않는다.

- `collection_runs`에는 성공 여부, 호출 수, 신규 수, 중복 수, 지연, 오류를 매번 기록한다.
- payload가 이전과 다르거나 신규 데이터·오류가 있을 때만 gzip Raw를 저장한다.
- 파일은 덮어쓰지 않는 immutable 경로를 사용한다.
- 기본 보관 기간은 14일이다.
- 오류 재현용, 자동 품질 평가 결과, 버전 학습 데이터셋은 별도 prefix에 장기 보관한다.

```text
raw/news/<source>/2026-07-21/<query_id>/153250_<hash>.json.gz
datasets/news-relevance/v1/train.parquet
models/news-relevance/v1/<artifact>
```

로컬 `data/raw`, `data/processed`와 운영 Raw 파일은 Git에 커밋하지 않는다.

## 10. Next.js 역할

서버 렌더링 화면은 자기 서버의 Route Handler를 HTTP로 다시 호출하지 않는다.

```text
Server Component
→ application service
→ repository/DAL
→ Supabase
```

Route Handler는 브라우저 비동기 요청과 상태 확인에만 사용한다.

```text
GET  /api/stocks/[stockCode]/price
GET  /api/stocks/[stockCode]/news
POST /api/portfolio/analyze
GET  /api/health
```

입력 검증 기준:

- 종목 코드는 활성화된 20종목 allowlist에 포함되어야 한다.
- 종목 수는 1~5개다.
- 각 비중은 0 초과 100 이하이며 합계가 100이어야 한다.
- 알 수 없는 필드는 제거하거나 요청을 거부한다.
- 분석 POST에는 Nginx `limit_req` 기반 IP rate limit을 적용한다.

캐시 기준:

- 최신성의 기준은 Supabase 정제 데이터와 `asOf`다.
- 공용 뉴스·일봉은 DAL 단위의 짧은 서버 캐시를 선택적으로 적용한다.
- Next.js 16 Cache Components를 사용하면 대상 DAL 함수에만 `'use cache'`, `cacheLife`, `cacheTag`를 적용한다.
- KIS 현재가는 persistent cache를 사용하지 않고 단일 Next.js 프로세스 메모리에 5~10초만 둔다.
- Supabase·KIS client는 module import 시 만들지 않고 런타임에 lazy initialize한다.

## 11. Lightsail 운영

기존 `rupa-1`을 재사용한다.

```text
사양: 2 vCPU / 2GB RAM / 60GB SSD / 서울
StockEcho Next.js: 127.0.0.1:3100
기존 rupa-nest-api: 3000
기존 rupa-vision-service: 127.0.0.1:8000
```

운영 기준:

- Nginx가 도메인 기준으로 각 서비스를 reverse proxy한다.
- 외부 공개 포트는 80/443만 허용한다.
- SSH 22는 가능한 접속 IP를 제한한다.
- Python job은 상시 서버가 아니라 실행 후 종료되는 프로세스다.
- Ubuntu `systemd timer`로 실행하고 `flock`으로 중복을 막는다.
- Next.js와 worker container에 메모리 제한을 둔다.
- 서버에서 `next build`하지 않고 CI에서 Docker 이미지를 빌드한다.
- 서버는 registry에서 이미지를 pull하여 실행한다.
- Docker 로그 용량 제한과 logrotate를 설정한다.
- 배포 전 Lightsail snapshot을 생성한다.

KIS가 IP allowlist를 요구하면 Lightsail Static IP를 연결한 뒤 등록한다. Stop/Start로 변경될 수 있는 기본 Public IPv4에 의존하지 않는다.

## 12. Colab과 모델

Colab은 운영 스케줄러가 아니라 재현 가능한 학습·실험 환경으로 사용한다.

```text
운영 DB
→ 버전 고정 Parquet export
→ Private Storage
→ 단기 signed URL로 Colab 다운로드
→ 시간순 train/validation/test
→ 모델·전처리기·metrics 저장
→ 자동 평가 기준 통과 후 production 승격
```

모델 상태는 `candidate → staging → production → retired`로 관리한다.

산출물에는 dataset version, model version, preprocessing version, random seed, package version, 평가 지표, 오류 샘플, 생성 시각을 포함한다.

BERTopic, SentenceTransformer, pgvector는 초기 필수 요소가 아니다. 규칙 기반 파이프라인의 자동 품질 지표와 시간 구간별 기준선을 만든 후 모델이 실제 성능을 개선할 때만 추가한다.

## 13. 관측성과 장애 처리

`collection_runs`와 JSON 로그에서 다음을 확인할 수 있어야 한다.

- 작업 시작·종료 시각과 소요 시간
- 외부 API별 호출 수와 응답 상태
- 신규·중복·무시 기사 수
- 마지막 성공 시각과 연속 실패 횟수
- rate limit·인증·파싱 오류 구분
- Raw 저장 경로와 payload hash
- 코드·데이터 규칙 버전

초기 경고 기준:

- 직접 뉴스 마지막 성공이 장중 90분 이상 지남
- 일봉이 다음 거래일 오전까지 갱신되지 않음
- 디스크 사용량 80% 이상
- worker가 2회 연속 실패
- Supabase, NAVER, KIS 인증 오류 발생

외부 API가 실패하면 화면은 마지막 정상 데이터와 `asOf`, `stale` 상태를 반환한다.

## 14. 구현 순서

### Phase 1. 핵심 5종목

대상: 삼성전자, SK하이닉스, 현대차, LG에너지솔루션, NAVER

1. 직접 뉴스 증분 수집
2. 정규화·canonical URL·content hash 구현
3. PostgreSQL schema와 idempotent upsert 구현
4. `collection_runs`와 선별 Raw 저장 구현
5. 회사명 위치·문맥·검색어 근거를 이용한 공통 관련도 규칙 구현
6. 관련도와 키워드 자동 품질 지표 평가

### Phase 2. Tier A 10종목

1. KIS 일봉과 OpenDART 연결
2. 검색어-종목 다대다 구조 구현
3. Tier A 10종목 데이터 품질 검증
4. Next.js DAL과 서비스 화면 연결
5. `asOf`, stale fallback, 입력 검증 구현

### Phase 3. 20종목 MVP

1. Tier B 10종목 추가
2. 산업 검색어 호출 중복 제거 검증
3. 종목별 오탐 상위 패턴 보정
4. `systemd timer`, `flock`, 재시도 적용
5. Docker 이미지 CI build와 Lightsail 배포
6. 20종목 health·호출량·디스크 사용량 검증

### Phase 4. 사건과 모델

1. 뉴스와 OpenDART 사건 연결
2. 사건일과 KIS 거래일·1/5/20일 수익률 연결
3. 규칙 기반 기준선 측정
4. 버전 학습 데이터셋 export
5. Colab 모델 평가
6. 성능 개선이 확인될 때만 pgvector·유사 사건 검색 추가

## 15. 완료 기준

- 20종목 모두 최근 뉴스·공시·일봉을 조회할 수 있다.
- 사용자가 화면을 열 때 외부 뉴스 수집을 기다리지 않는다.
- 동일 작업을 재실행해도 기사와 관계가 중복 저장되지 않는다.
- 기사마다 종목 연결 유형, 점수, 근거를 설명할 수 있다.
- 키워드 후보의 출처, 점수, 상태, 생성·만료 시각이 남는다.
- NAVER 일일 호출량이 정상 시 3,000회 이내로 유지된다.
- 외부 API 실패 시 마지막 정상 데이터와 `asOf/stale`을 반환한다.
- worker 중복 실행이 방지되고 마지막 성공·실패 원인을 확인할 수 있다.
- Secret이 브라우저, Git, 로그, Colab에 노출되지 않는다.
- Raw 데이터가 보관 정책 없이 무한히 쌓이지 않는다.

## 16. 구현 전 확인 항목

- Supabase 프로젝트 리전과 요금제
- Lightsail Static IP 연결 여부
- StockEcho 도메인과 Nginx 경로
- KIS 계정 유형, IP 등록 요건, 실제 호출 제한
- 20종목 OpenDART `corpCode`
- 자동 관련도 점수와 키워드 승격 임계값
- CI 이미지 registry와 배포 방식
- 실제 사용자 운영 전 장애 알림 채널

## 17. 공식 참고 자료

- [NAVER API HUB 뉴스 검색 API](https://api.ncloud-docs.com/docs/naver-api-hub-search-news)
- [KIS Developers Open API](https://apiportal.koreainvestment.com/)
- [KRX 시가총액 상하위 50종목](https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd?screenId=MDCEASY017)

## 18. 최종 결정 한 줄

StockEcho MVP는 **“20개 국내 인기 대형주를 Lightsail의 Python 증분 수집기로 미리 처리하고, Supabase의 정제 데이터를 Next.js가 즉시 조회하는 구조”**로 구현한다.
