# StockEcho 뉴스 수집기

## 환경 준비

프로젝트 루트의 `.env`에 다음 값이 필요하다.

```dotenv
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

의존성을 설치한다.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 뉴스 수집

삼성전자 최신 뉴스 최대 100건을 수집한다.

```bash
.venv/bin/python -m collector.jobs.collect_company_news --stock-code 005930
```

NAVER는 현재 연결된 첫 번째 source adapter다. 수집 domain은 종목 코드가 아닌 `SearchQuery`를 입력받으므로, 다른 뉴스 API를 추가해도 키워드 발견과 기사-종목 연결 로직은 그대로 사용한다. NAVER adapter는 `sort=date`로 호출한다.

```text
data/raw/news/<source>/<date>/<queryId>/*.json.gz
data/processed/news/articles.jsonl
data/processed/news/article_queries.jsonl
data/processed/news/article_companies.jsonl
data/state/news/<source>/<queryId>.json
```

Raw는 응답 내용이 달라졌거나 신규 기사가 있을 때만 gzip으로 저장한다. 실행 결과는 Git에 커밋하지 않는다.

공용 기사와 검색어 연결, 기사와 종목 연결을 각각 저장한다. 따라서 같은 검색어는 한 번만 수집한 뒤 여러 종목에 연결할 수 있다.

```json
{
  "relation_type": "direct",
  "confidence": 0.95,
  "evidence": ["title_exact_company_name"]
}
```

## 확장 검색어 발견

먼저 회사명으로 모은 직접 기사에서 Kiwi 형태소 분석과 TF-IDF 기반 통계를 이용해 반복되는 제품·기술·이슈 표현을 찾는다.

```bash
.venv/bin/python -m collector.jobs.discover_company_queries --stock-code 005930
```

활성 검색어까지 실제로 수집하려면 다음처럼 실행한다.

```bash
.venv/bin/python -m collector.jobs.discover_company_queries \
  --stock-code 005930 \
  --collect-active
```

키워드 발견에는 회사명이 제목에 직접 등장한 고신뢰 기사만 사용한다. 활성 조건은 최소 2개 기사, 2개 언론사, 제목 1회 이상이며 한 종목당 최대 5개다. `삼성`, `반도체` 같은 넓은 표현과 지원 종목의 다른 회사명은 단독 활성화하지 않는다. 발견어는 `삼성전자 로봇`, `삼성전자 갤럭시`처럼 회사명과 결합해 검색하고, 결과 기사에도 회사 문맥과 발견어가 모두 있어야 종목에 연결한다. `삼성전자 반도체 수출 규제` 같은 이벤트 검색어는 직접 기사에서 두 표현이 실제로 함께 반복됐을 때만 생성한다. 후보에는 점수, 기사·언론사·제목 빈도, 근거 기사 ID, 만료일과 규칙 버전이 함께 저장된다.

## 관련도 v2 재평가

기존 수집 기사를 회사명·검색 주제의 위치와 저가치 기사 패턴으로 다시 점수화한다.

```bash
.venv/bin/python -m collector.jobs.reevaluate_company_news \
  --stock-code 005930
```

판정 상태는 다음 세 가지다.

```text
eligible  0.65 이상, BERTopic 입력 대상
candidate 0.45 이상 0.65 미만, 검토·통계용 보관
rejected  0.45 미만, BERTopic 입력 제외
```

회사명과 발견 주제가 제목에 있으면 가점하고, 증시 종목 나열·채용·판촉·수상·혼합 뉴스 모음은 감점한다. 판정 결과에는 `relevance-v2` 규칙 버전과 모든 가감 근거를 저장한다.

```text
data/processed/relevance/<stockCode>_assessments.jsonl
data/processed/bertopic/<stockCode>_articles.jsonl
data/processed/keyword_seed/<stockCode>_articles.jsonl
```

`bertopic` 파일에는 검색어 관계 중 하나라도 `eligible`인 기사를 한 번만 넣는다. `keyword_seed` 파일에는 회사명 직접 검색에서 통과한 기사만 넣어 확장 키워드의 순환 오염을 막는다.

## 키워드 기반 과거 이슈 뉴스 수집

현재 Event의 핵심 키워드로 과거 뉴스를 찾을 때는 자사 정확 검색, 기업명을 뺀 공통 산업 검색, 부족할 때만 동종기업 검색 순서로 `sort=sim`을 호출한다.

```bash
.venv/bin/python -m collector.jobs.backfill_issue_news \
  --stock-code 005930 \
  --keyword 반도체 \
  --keyword 수출 \
  --keyword 규제 \
  --before 2026-07-22
```

`--before` 당일과 미래 기사는 과거 후보 집계에서 제외한다. 기본적으로 `반도체 수출 규제`와 보수적인 동의어 변형인 `반도체 수출 통제`를 만들고, 자사 날짜별 Event proxy 1건과 서로 다른 외부 기업 2곳을 확보하면 호출을 멈춘다. 한 날짜의 Event proxy는 서로 다른 출처가 기본 2곳 이상이어야 한다.

한 검색어는 최대 3페이지, 전체 작업은 최대 12회만 호출한다. 결과는 다음 경로에 저장하며 동일한 종목·키워드·기준일 요청은 저장 결과를 재사용한다. 다시 호출하려면 `--refresh`를 사용한다.

```text
data/processed/historical_search/issue_search_<hash>.json
data/state/news/<source>/<queryId>__sim__<start>.json
```

수집 후 관련 기업에 `reevaluate_company_news`를 실행하고 BERTopic/Event 산출물을 다시 생성해야 실제 과거 Event 검색 대상에 포함된다.

제품의 `과거 유사 사례 분석` 요청은 현재 카드의 Topic/Event와 키프레이즈를
`analyze_historical_issue`에 전달한다. Supabase의 `historical_events`를 먼저
검색하고 부족한 경우에만 위 NAVER backfill을 실행한다. 현재 Event 직전 2일은
같은 사건의 연속 보도를 다시 과거 사례로 고르는 일을 줄이기 위해 제외한다.
제품 결과는 자사 Event 최대 1건과 서로 다른 외부 기업 Event 최대 3건을
선택하며, 품질 기준을 통과한 사례가 부족하면 개수를 임의로 채우지 않는다.
결과와 검색·가격 조회 여부는 결정적 `cache_key`로
`historical_issue_analyses`에 저장되므로 동일 요청은 NAVER를 다시 호출하지
않는다.

```bash
.venv/bin/python -m collector.jobs.analyze_historical_issue \
  --stock-code 005930 \
  --topic-id <topic-id> \
  --event-id <event-id> \
  --event-date 2026-07-23 \
  --name "현재 주요 이슈명" \
  --topic-label "현재 Topic 이름" \
  --keyword "핵심 키프레이즈"
```

과거 Event별 가격은 KIS 일봉을 `market_daily`에 캐시한 뒤 Event 기준 거래일
종가와 다음 1·5·15·30번째 거래일 종가로 계산한다. 장 마감 후·휴일·시각
불확실 보도는 다음 거래일을 기준으로 하며, 거래일이 아직 도달하지 않았거나
가격이 누락되면 해당 구간을 `partial` 또는 `unavailable`로 반환한다.

## BERTopic Topic/Event 실험

수집기와 분리된 실험 의존성을 설치한 뒤 종목별 corpus를 실행한다.

```bash
.venv/bin/python -m pip install -r requirements-bertopic.txt
.venv/bin/python -m collector.jobs.run_bertopic --stock-code 005930
.venv/bin/python -m collector.jobs.run_bertopic --stock-code 000660
```

기본 임베딩은 한국어 SentenceTransformer인 `jhgan/ko-sroberta-multitask`를 사용한다. BERTopic c-TF-IDF의 `CountVectorizer`에는 Kiwi 명사·동사·형용사 tokenizer를 연결한다. BERTopic의 `-1` 문서는 하나의 가짜 Topic으로 묶지 않고 각각 outlier로 저장한다.

Topic 내부 기사는 한국 시간(`Asia/Seoul`)의 발행일별 Event로 분리한다. 주요 이슈는 outlier를 제외하고 기간 내 기사 2건 이상인 서로 다른 Topic 중 Top 3를 선정한다. 7일에 세 Topic이 없으면 14일, 그래도 부족하면 30일까지 순서대로 보충한다. `--as-of YYYY-MM-DD`를 생략하면 corpus의 최신 발행일이 기준일이다.

Event의 화면용 이슈명은 단순 빈도 상위 단어를 이어 붙이지 않는다. Kiwi로 제목의 2~3어절 후보 구문을 만들고, Event 임베딩 중심과의 유사도와 기사 커버리지를 합산한 뒤 MMR로 중복 구문을 줄인다. 최종 이름은 중심에 가까운 대표 기사 3개의 자연어 구절 중 핵심 구문을 가장 잘 포괄하는 문장을 추출한다. 결과에는 `label_method=extractive-semantic-mmr-v1`을 기록하며, LLM은 사용하지 않는다.

```text
data/processed/topics/<stockCode>_topics.jsonl
data/processed/topics/<stockCode>_major_issues.jsonl
```

뉴스 수집부터 주요 이슈 생성까지 여러 종목을 한 번에 갱신하려면 통합 작업을 실행한다. 종목별 실패는 다른 종목의 실행을 막지 않으며 마지막 결과에 함께 표시된다.

```bash
.venv/bin/python -m collector.jobs.analyze_companies \
  --stock-code 042700 \
  --stock-code 005380 \
  --stock-code 035420 \
  --stock-code 035720
```

백엔드 정기 작업에서 지원 종목 전체를 갱신할 때는 다음 명령을 사용한다.

```bash
.venv/bin/python -m collector.jobs.analyze_companies --all-supported
```

## Supabase 저장 및 분석 큐

루트 `.env`에 `SUPABASE_DB_URL`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`를 설정한다. 최초 한 번 스키마를 적용하고 기존 snapshot을 이전한다.

```bash
.venv/bin/python -m collector.jobs.setup_supabase \
  --stock-code 005930 \
  --stock-code 000660
```

분석 요청은 `stock_analysis` 큐에 넣고 Python worker가 순서대로 처리한다. 동일 종목이 이미 대기 또는 실행 중이면 중복 요청을 만들지 않는다.

```bash
.venv/bin/python -m collector.jobs.enqueue_analysis --stock-code 005930
.venv/bin/python -m collector.jobs.enqueue_analysis --all-supported
.venv/bin/python -m collector.jobs.run_analysis_worker
```

worker는 성공한 메시지를 archive하고 분석 결과·마지막 실행 시각을 Supabase에 저장한다. 실패한 메시지는 visibility timeout 뒤 재시도하며 세 번째 실패에서는 archive한다.

운영에서는 뉴스 수집과 Topic 분석을 분리한다. 아래 수집 작업은 Supabase에 새 기사와 관련도를 먼저 저장한 뒤, `eligible` 새 기사가 5건 이상이면 분석 큐에 넣는다. 마지막 분석 후 24시간이 지난 종목은 새 기사 1건만 있어도 갱신하고, 공시·거래정지 등 긴급 이벤트는 즉시 우선 등록한다.

```bash
.venv/bin/python -m collector.jobs.collect_and_schedule --all-supported
.venv/bin/python -m collector.jobs.run_analysis_worker
```

예를 들어 서버의 cron에서 첫 명령을 매시간 실행하고, worker는 별도 프로세스로 계속 실행한다. worker는 큐가 비어 있으면 기본 5초 간격으로 다시 확인하며 `--poll-interval`로 간격을 바꿀 수 있다. Supabase Queue는 작업 상태와 재시도를 보존하지만 Python 수집기와 BERTopic 자체를 실행하지는 않으므로 이 두 명령이 돌아갈 서버가 필요하다.

`runtime_topic_id`는 실험 진단용 BERTopic 숫자일 뿐 외부 참조 키로 사용하지 않는다. 영구 참조 후보인 `topic_id`와 `event_id`는 `model_version`, 종목 코드, 소속 문서 fingerprint를 바탕으로 만든 UUIDv5다. corpus 또는 모델 버전이 달라지면 새 ID가 생기므로, 운영 단계에서 Topic 계보를 유지하려면 이전 snapshot과의 유사도 매칭 registry를 추가해야 한다.

### Google Colab

[`notebooks/StockEcho_BERTopic_Colab.ipynb`](../notebooks/StockEcho_BERTopic_Colab.ipynb)을 Colab에서 열면 설치, JSONL 업로드, GPU/CPU 자동 선택, 실행, 결과 zip 다운로드를 순서대로 진행할 수 있다.

직접 셀을 구성할 때는 저장소를 연 뒤 아래 셀을 순서대로 실행한다. GPU runtime을 선택하면 `--device cuda`, CPU면 해당 옵션을 생략한다.

```python
!git clone <repository-url> StockEcho
%cd StockEcho
!pip install -q -r requirements-bertopic.txt
```

로컬의 Git 제외 입력 파일을 Colab 세션의 `data/processed/bertopic/`에 업로드하거나 Google Drive에서 복사한 다음 실행한다.

```python
!python -m collector.jobs.run_bertopic \
  --stock-code 005930 \
  --device cuda \
  --output-dir /content/bertopic-results
```

모델 다운로드가 필요한 첫 실행에는 인터넷 연결이 필요하다. 결과 디렉터리를 Drive로 지정하면 세션 종료 후에도 JSONL을 보존할 수 있다.

## 테스트

```bash
.venv/bin/python -m unittest discover -s tests -v
```
