# StockEcho

> 공시·뉴스와 과거 유사 사건의 주가 반응을 연결해, 개인 포트폴리오의 위험 영향을 설명하는 교육용 투자 분석 서비스

StockEcho는 관심 있거나 보유한 종목의 최신 공시·뉴스를 분석하고, 의미가 비슷한 과거 사건을 찾아 당시의 1일·5일·20일 주가 반응을 보여줍니다. 과거 반응을 현재 보유 비중에 적용한 영향 시나리오와 위험을 낮춘 비중 조정안을 함께 제공합니다.

미래 수익률이나 목표가를 예측하는 서비스가 아닙니다. 모든 결과는 과거 사례 기반 시나리오이며 실제 투자 판단을 대신하지 않습니다.

## 핵심 흐름

```text
관심·보유 종목과 비중 입력
→ 최신 공시·뉴스 확인
→ 사건·ESG·위험 주제 분석
→ 과거 유사 사건 검색
→ 사건 후 1·5·20일 시장 반응 분석
→ 내 포트폴리오 영향 계산
→ 위험 조정 비중 비교
→ 출처 기반 설명 확인
```

## 제품 원칙

- 계산과 설명을 분리합니다. 수치는 분석 엔진이 계산하고 LLM은 근거 기반 설명만 담당합니다.
- 핵심 주장마다 공시·뉴스 제목, 발행일, 원문 링크를 연결합니다.
- 미래 수익률을 확정적으로 표현하지 않습니다.
- 표본 수, 유사도, 데이터 기준시각과 분석 한계를 함께 표시합니다.
- 외부 API나 LLM에 장애가 생겨도 마지막 정상 snapshot과 기준선 모델로 핵심 흐름을 유지합니다.

## MVP 범위

- 데이터 품질을 확인한 KOSPI 대형주 약 10개
- 사용자당 2~5개 종목과 합계 100%의 보유 비중 입력
- 최신 공시·뉴스 통합 피드
- E/S/G 및 `risk`·`opportunity`·`neutral` 분류
- BERTopic과 문장 임베딩을 활용한 과거 유사 사건 검색
- 사건 후 1일·5일·20일 수익률과 시장 대비 비정상수익률 분석
- 과거 사건 반응을 적용한 포트폴리오 영향 시나리오
- 현재 비중과 위험 조정 비중 비교
- 실제 원문 출처가 연결된 RAG 설명

## 데이터 원천

| 데이터 | 원천 | 용도 |
|---|---|---|
| 종목·현재가·일봉 | 토스증권 Open API | 준실시간 가격 표시, 특징 생성, 사건 반응 분석 |
| 기업 공시 | OpenDART | 사건 탐지와 공식 근거 |
| 기업 뉴스 | NAVER API HUB | 사건 보강, 토픽·위험 분석 |
| 시장 지표 | KOSPI 벤치마크 | 비정상수익률 계산 |

현재가는 토스증권 REST API를 서버에서 5~10초 간격으로 폴링하는 준실시간 방식으로 표시합니다. 모델 학습과 Risk Replay에는 수정주가가 적용된 일봉을 사용합니다. KRX 데이터는 검증 또는 fallback을 위한 보조 원천으로만 고려합니다.

## 분석 구성

| 영역 | 접근 방식 |
|---|---|
| 텍스트 기준선 | 한국어 정규화, 위험 사전, TF-IDF |
| 사건 주제 | SentenceTransformer 임베딩, BERTopic |
| 유사 사건 | 토픽 필터와 임베딩 유사도 Top-K 검색 |
| 시장 반응 | Event Study, 1·5·20일 수익률과 비정상수익률 |
| 하락 위험 | Logistic Regression 기준선, 성능 검증 후 MLP |
| 포트폴리오 | 영향 시나리오, 최소분산·CVaR 기반 제약 최적화 |
| 설명 | RAG, 구조화 출력, 출처 사후 검증 |

대표적인 포트폴리오 영향은 다음처럼 계산합니다.

```text
종목 영향 = 현재 종목 비중 × 유사 사건의 대표 수익률
포트폴리오 영향 = 종목별 영향의 합
```

대표 수익률은 이상치에 덜 민감한 중앙값을 기본으로 사용하고 평균, 하락 비율, 표본 수를 함께 제공합니다.

## 시스템 구조

```text
Web UI
→ Analysis API
→ Data Store / Feature Store
→ Event & Similarity Engine
→ Risk Model / Optimizer
→ RAG Explanation
→ Structured Result JSON
```

현재 검토 중인 기술 구성은 다음과 같습니다.

- Frontend: Next.js, React, TypeScript
- Analysis API: FastAPI, Pydantic
- Data: PostgreSQL, pandas, NumPy
- Vector Search: pgvector, FAISS 또는 Chroma
- Modeling: scikit-learn, BERTopic, SentenceTransformer
- Optimization: CVXPY 또는 SciPy
- Visualization: Recharts 또는 Plotly

최종 기술 스택은 구현 일정과 실험 결과에 따라 확정합니다.

## 권장 프로젝트 구조

```text
src/
  collectors/      # 토스증권, OpenDART, NAVER 뉴스 수집
  pipelines/       # 정규화, 사건 생성, 특징 생성
  models/          # 기준선, MLP, 토픽 모델
  replay/          # Event Study, 유사 사건 검색
  portfolio/       # 영향 계산, 비중 최적화
  rag/             # 인덱싱, 검색, 출처 검증
data/
  raw/
  processed/
  features/
  samples/
models/
reports/
tests/
```

원본 데이터, 모델 산출물, API 인증정보는 Git에 커밋하지 않고 소용량 sample과 재현 가능한 스크립트만 관리합니다.

## 개발 순서

1. MVP 대상 종목과 종목코드·DART 고유번호·검색 별칭을 확정합니다.
2. 대표 종목 1개의 가격·공시·뉴스 수직 파이프라인을 완성합니다.
3. 사건 생성과 1·5·20일 반응 계산을 검증합니다.
4. TF-IDF와 Logistic Regression 기준선을 구현합니다.
5. BERTopic·임베딩 검색과 포트폴리오 영향 계산을 연결합니다.
6. 최적화와 출처 기반 RAG 설명을 연결합니다.
7. snapshot fallback을 포함한 E2E 흐름을 검증한 뒤 약 10개 종목으로 확장합니다.

## 프로젝트 문서

- [StockEcho PRD](docs/StockEcho_PRD.md): 제품 정의, 요구사항, 확정·미확정 사항
- [MVP 데이터·모델링 결정안](docs/MVP_데이터_모델링_결정안.md): 데이터 원천과 분석 방식의 최신 결정
- [MVP 전체 준비 체크리스트](docs/MVP_전체_준비_체크리스트.md): 구현·검증 작업 목록과 완료 조건
- [mini2 PRD](docs/mini2_PRD.md): 초기 상세 요구사항과 시스템 설계
- [mini2 기획안](docs/mini2_기획안.md): 프로젝트 배경과 수업 기술 활용 계획

문서 간 내용이 충돌할 경우 `MVP 데이터·모델링 결정안`의 최신 결정을 우선하고, 제품 범위는 `StockEcho PRD`를 기준으로 합니다.

## 현재 상태

현재 저장소는 기획·데이터 모델링 설계를 정리하고 구현을 준비하는 단계입니다. 실행 가능한 애플리케이션과 설치 명령은 기술 스택이 확정되고 초기 코드가 추가된 뒤 이 문서에 업데이트할 예정입니다.

## 주의사항

StockEcho는 교육 및 연구 목적의 프로젝트입니다. 제공되는 정보와 시나리오는 투자 권유, 매수·매도 지시, 수익 보장 또는 전문적인 투자자문이 아닙니다.
