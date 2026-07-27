# StockEcho Event Study Dataset Card v1

## 목적

한국 상장사 뉴스 Event와 이후 D+1·D+5·D+20 거래일 가격 반응을 연결해
유사사건 경험분포와 하락위험 모델을 평가한다. 투자수익 보장이나 전 종목 대표
데이터셋이 아니다.

## 관측 단위와 시간 계약

- 한 행은 중복 기사가 아니라 하나의 `event_id`다.
- 입력 특징은 `feature_cutoff_at` 이전에 공개된 기사만 사용한다.
- label은 cutoff 이후 D+1·D+5·D+20 종목 수익률 및 KOSPI 차감
  시장조정 비정상수익률이다.
- 분할은 Event 날짜 순서의 train/validation/test이며 랜덤 행 분할을 금지한다.
- `dataset_hash`는 정렬된 전체 행의 canonical JSON SHA-256이다.

## 필드

- 식별: `event_id`, `stock_code`, `event_date`
- 누수 감사: `feature_cutoff_at`, `feature_document_ids`, `feature_text`
- 사건 특징: `event_category`, `impact_direction`, 기사·출처 수
- 관측값: `return_d*`, `benchmark_return_d*`, `abnormal_return_d*`
- label: `loss_label_d*`, `material_downside_label_d*`
- 추적: `dataset_schema_version`, `split`, export manifest

## 데이터 출처와 범위

- 뉴스: NAVER 검색 API 및 StockEcho 관련도 필터를 통과한 기사
- 가격: 한국투자증권 Open API 수정주가 일봉
- 벤치마크: KOSPI 일봉
- 기업: StockEcho에 명시적으로 등록된 국내 지원 종목

NAVER 검색은 전체 언론 보도나 공시 전수를 보장하지 않는다. 과거 Event 표본은
지원 종목·검색 recall·서로 다른 원문 출처 기준에 영향을 받는다.

## 알려진 한계와 사용 gate

- 현재 저장 Event의 역사 길이와 사람 검증 label 수가 연구 목표보다 적을 수 있다.
- 거래정지·상장일·장 마감 후 보도는 별도 감사 대상이다.
- embedding 검색은 사람 판정 검색셋 30 query를 채우기 전에는 승격하지 않는다.
- Logistic/MLP는 실제 train·시간순 test가 각각 100 Event 이상이고 모델 카드의
  성능·calibration gate를 모두 통과하기 전에는 승격하지 않는다.
- 데이터가 부족하면 제품은 관측 사례와 `insufficient` 상태를 반환한다.
