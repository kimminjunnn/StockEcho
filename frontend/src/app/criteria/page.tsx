import Link from "next/link";

const steps = [
  {
    title: "1. 사건을 Event로 묶기",
    body: "같은 사건의 중복 기사를 하나의 Event로 묶고, 서로 다른 원문 출처가 2곳 이상인 사례를 우선 사용합니다.",
  },
  {
    title: "2. 과거 반응 관측",
    body: "사건일 기준 D+1·D+5·D+20 거래일 종목 수익률과 KOSPI를 뺀 비정상수익률을 따로 저장합니다.",
  },
  {
    title: "3. 현재 위험 범위 계산",
    body: "유사도와 출처 수로 과거 사례에 가중치를 주고 하락 비율, 중앙값, 하방·상방 분위수를 계산합니다.",
  },
  {
    title: "4. 보유 비중에 반영",
    body: "종목별 하락확률과 하방 분위수를 현재 평가금액 비중으로 가중해 포트폴리오 시나리오를 만듭니다.",
  },
  {
    title: "5. 제약 안에서 목표 비중 계산",
    body: "long-only, 종목당 최대 60%, turnover 최대 30% 조건 안에서 사건안전성 선호에 따른 계산상 비중을 제시합니다.",
  },
];

export default function CriteriaPage() {
  return (
    <main className="mx-auto w-full max-w-[1100px] flex-grow px-6 py-12 lg:px-8">
      <div className="mb-10">
        <div className="mb-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-primary">
          Methodology v1
        </div>
        <h1 className="text-4xl font-black tracking-tight text-gray-900">사건 위험과 비중 산정 기준</h1>
        <p className="mt-4 max-w-[760px] text-sm leading-7 text-gray-600">
          StockEcho는 기사 문체의 감성을 투자수익률로 바꾸지 않습니다. 과거 유사 Event의 실제 가격 반응을 관측하고,
          표본 수와 불확실성을 함께 표시한 뒤 포트폴리오 비중 시뮬레이션에 사용합니다.
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {steps.map((step) => (
          <section key={step.title} className="rounded-2xl border border-gray-100 bg-white p-7 shadow-sm">
            <h2 className="text-lg font-black text-gray-900">{step.title}</h2>
            <p className="mt-3 text-sm leading-7 text-gray-600">{step.body}</p>
          </section>
        ))}
      </div>

      <section className="mt-8 rounded-2xl bg-gray-950 p-8 text-white">
        <h2 className="text-2xl font-black">서비스 목적함수</h2>
        <div className="mt-5 overflow-x-auto rounded-xl bg-white/10 px-5 py-4 font-mono text-sm leading-7">
          minimize portfolio variance + downside risk + turnover penalty
          <br />
          subject to event safety target, weight sum = 100%, long-only, max weight, max turnover
        </div>
        <p className="mt-5 text-sm leading-7 text-gray-300">
          Event Safety는 1 − 사건 하락확률로 정의한 서비스 지표입니다. 이는 Pedersen et al. (2021)의
          ESG-efficient frontier에서 “금융 위험과 책임 특성의 trade-off를 경계로 보여준다”는 구조를 참고했지만,
          논문의 기업 ESG 점수나 ESG-CAPM을 재현한 값은 아닙니다.
        </p>
      </section>

      <div className="mt-8 grid gap-5 md:grid-cols-3">
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
          <h2 className="font-black text-amber-900">표본 부족</h2>
          <p className="mt-2 text-sm leading-6 text-amber-800">
            유사 사례가 3건 미만이면 insufficient, 3~7건이면 low로 표시하며 목표 비중을 만들지 않을 수 있습니다.
          </p>
        </section>
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
          <h2 className="font-black text-amber-900">확률의 의미</h2>
          <p className="mt-2 text-sm leading-6 text-amber-800">
            현재 운영값은 유사도 가중 경험분포입니다. 시간순 holdout과 calibration을 통과한 모델만 향후 교체됩니다.
          </p>
        </section>
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
          <h2 className="font-black text-amber-900">주문 기능 없음</h2>
          <p className="mt-2 text-sm leading-6 text-amber-800">
            목표 비중과 정수 수량은 교육용 계산값입니다. 세금·수수료·슬리피지와 실제 체결을 보장하지 않습니다.
          </p>
        </section>
      </div>

      <div className="mt-10 flex justify-center">
        <Link href="/rebalancing" className="rounded-xl bg-primary px-6 py-3 text-sm font-bold text-white hover:bg-blue-600">
          내 포트폴리오로 계산하기
        </Link>
      </div>
    </main>
  );
}
