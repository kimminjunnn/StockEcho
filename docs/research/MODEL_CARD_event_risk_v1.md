# StockEcho Event Risk Model Card v1

## 운영 선택

현재 운영 정책은 `similarity-weighted-empirical-v1`이다. 유사 Event의 실제
시장조정 수익률을 유사도·출처 수로 가중하고 Beta prior로 작은 표본의 하락확률
과신을 줄인다.

## 출력

- D+1·D+5·D+20 하락확률
- 수익률 p10·p50·p90
- 관측 Event 수와 유효표본수
- `high/medium/low/insufficient` 신뢰도
- model/dataset version, 생성·stale 시각, 근거 Event ID

`medium` 이상만 검증 기준 리밸런싱의 입력으로 사용한다. 그보다 낮아도 과거
가격 관측이 있으면 모달과 참고용 리밸런싱에 `탐색적 추정`으로 명시해
보여준다. 참고용 계산은 하락확률을 50% 중립값 쪽으로 축소하고 `low`는 종목당
최대 ±3%p, `insufficient`는 최대 ±1%p로 비중 변경을 제한한다. 실제 주문이나
검증 기준 계산에는 사용하지 않는다.

## 비교 후보와 승격 gate

동일 시간순 분할에서 경험 기준선, TF-IDF Logistic Regression, 작은 MLP를
비교한다. 후보 모델은 다음을 모두 만족해야 한다.

1. 실제 train Event 100건 이상
2. 실제 미래 test Event 100건 이상
3. 경험 기준선보다 PR-AUC 상승
4. 경험 기준선보다 Brier score 감소
5. Expected Calibration Error 0.10 이하
6. 종목·사건유형 제외 holdout에서 치명적 붕괴 없음

현재 fixture는 배선과 재현성 확인용이므로 Logistic/MLP 승격 근거가 아니다.
2026-07-27 D+5 실측 분할은 train 16건, validation 32건, test 160건이며,
두 후보 모두 경험 기준선보다 Brier/ECE가 나빠 운영 승격하지 않았다.

## 의도하지 않은 사용

- 확정 주가 전망, 자동매매, 단일 종목 매수·매도 권유
- 공인 ESG rating 또는 Pedersen 논문의 ESG score
- 보유종목 밖 신규 투자대상 추천

## 실패·fallback

- forecast 없음: `unavailable`
- 유효표본 부족: `insufficient`, 확률 비공개
- stale: 경고와 기준시각 표시
- 후보 모델 calibration 실패: 경험분포로 rollback
