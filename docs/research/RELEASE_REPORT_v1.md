# StockEcho Risk Replay / Event-Safety Rebalancing v1

## 구현 결과

- 최신 Event와 저장된 과거 유사 Event를 연결한다.
- 과거 D+1·D+5·D+20 원수익률과 KOSPI 시장조정 수익률을 분리했다.
- E/S/G 사건 다중 라벨과 일반 사건 유형을 분리했다.
- 경험분포, Logistic, MLP의 시간순 평가 코드와 calibration 지표를 만들었다.
- 보유 평가금액 기반 하방 기여도와 long-only 제약 optimizer를 구현했다.
- 사용자 API는 무거운 Python subprocess 대신 저장 forecast만 읽는다.
- materialized forecast가 늦어도 저장 과거사례가 있으면 요청 시 가벼운
  탐색적 경험분포를 계산한다.
- 리밸런싱 화면의 고정 종목·비중·수익률을 제거하고 실제 localStorage
  보유수량·현재가·저장 forecast를 연결했다.
- 리밸런싱을 참고용과 검증 기준 모드로 분리했다. 참고용 모드는 낮은 신뢰도를
  중립 확률 쪽으로 보정하고 종목별 변경폭을 제한하며, 근거 없는 종목은 현재
  비중으로 고정한다.
- 홈 현재가는 KIS 실패 시 저장 최신 일봉과 전일 대비 등락률로 대체한다.

## 운영 승격 상태

| 구성요소 | 상태 | 근거 |
|---|---|---|
| 키워드 유사사건 검색 | 운영 기준선 | 기존 실제 Event 검색 |
| embedding 검색 | 연구 전용 | 사람판정 30 query 미충족 |
| 경험분포 forecast | 조건부 운영 | medium 이상은 검증 모드, 그 미만은 보정된 참고용 시뮬레이션 |
| Logistic | 연구 전용 | D+5 train 16건, Brier/ECE 기준선보다 악화 |
| MLP | 연구 전용 | D+5 train 16건, Brier/ECE 기준선보다 악화 |
| Event-Safety rebalancing | 교육용 시뮬레이션 | 주문 API 없음 |
| ESG-efficient frontier | 연구 계약만 구현 | 외부 공인 ESG score 미확보 |

## 2026-07-27 실제 Event Study 결과

- dataset hash: `4d11a0e200970932a81a6088ece790e5fac084d182d0187f5b8a426733f047b5`
- 전체 Event: 573
- D+5 유효 시간순 분할: train 16 / validation 32 / test 160
- 경험 기준선: PR-AUC 0.348973, Brier 0.259933, ECE 0.156730
- Logistic: PR-AUC 0.388511, Brier 0.281640, ECE 0.221190
- MLP: PR-AUC 0.445087, Brier 0.269286, ECE 0.212496

두 후보 모두 Brier와 ECE가 경험 기준선보다 나빠 calibration gate를 통과하지
못했다. 특히 train Event 16건은 최소 100건 기준보다 작다. 따라서 실제 평가
결론은 경험분포 유지이며, 이 결과를 ML/DL 성능 개선으로 해석하지 않는다.

## 2026-07-27 운영 저장소 스냅샷

- 최신 horizon forecast: 282건
- 계산 가능: 195건, unavailable: 87건, stale: 0건
- 자동 리밸런싱 사용 가능(`productionEligible`): high 3건, medium 21건
- 탐색적 표시·보정 시뮬레이션 전용: low 77건, insufficient 94건
- 저장 historical analysis: ready 109건, failed 0건
- 최신 화면 이슈: 분석 49/49건, 과거 가격 근거 41/49건
- 기본 D+5 예측: 계산 가능 37/49건, 자동 리밸런싱 사용 가능 4/49건
- 종목 일봉: 28,286건, KOSPI 일봉: 1,363건
- ESG 관련 사건 다중 라벨: 148 / 573건

계산 가능 상태는 자동 투자판단에 사용해도 된다는 뜻이 아니다. 표본 gate를
통과한 `productionEligible` 결과만 검증 기준 입력으로 사용한다. 그 미만은
모달과 참고용 리밸런싱에서 `탐색적 추정`으로 명시하고 중립 보정·변경폭
제한을 적용한다. 가격 관측이 없는 12건은 숫자를 만들지 않고 현재 비중으로
고정한다.

## Pedersen et al.과의 관계

논문은 ESG 정보의 금융적 역할(Type-A)과 투자자 선호 역할(Type-M), 그리고
ESG-efficient frontier를 제공한다. StockEcho는 이 구분을 유지한다.
뉴스 기반 Event Safety를 공인 ESG score로 부르지 않으며, 서비스 frontier는
논문의 구조를 참고한 long-only 제약 확장이다.

## 남은 데이터 한계

현재 데이터로 ML/DL이 좋아 보이도록 gate를 낮추지 않았다. 더 긴 과거 Event
corpus, 사람 판정 ESG·검색 gold set, 장 마감 시각 및 공시 데이터가 확보되면
같은 Colab과 evaluation job으로 재평가한다. 통과 전에는 경험분포 fallback을
유지한다.
