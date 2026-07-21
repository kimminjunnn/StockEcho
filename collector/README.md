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

## 테스트

```bash
.venv/bin/python -m unittest discover -s tests -v
```
