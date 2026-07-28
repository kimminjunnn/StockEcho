"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import RebalancingExecutionModal from "@/components/RebalancingExecutionModal";
import {
  type PortfolioHoldingInput,
  type RebalancingResult,
  type RebalancingRiskMode,
  type RebalancingScenario,
} from "@/lib/portfolioEngine";
import {
  HOLDINGS_STORAGE_KEY,
  INITIAL_HOLDINGS,
  parseStoredHoldings,
} from "@/lib/portfolio";
import type { ForecastHorizon } from "@/lib/riskForecasts";

type PageState =
  | { status: "idle" | "loading"; result: null; error: null }
  | { status: "ready"; result: RebalancingResult; error: null }
  | { status: "error"; result: null; error: string };

const scenarios: ReadonlyArray<{ key: RebalancingScenario; label: string; description: string }> = [
  { key: "risk_first", label: "위험 우선", description: "현재 비중 변화는 작게" },
  { key: "balanced", label: "균형", description: "안전성과 변경폭의 균형" },
  { key: "safety_first", label: "사건 안전 우선", description: "낮은 사건위험에 더 큰 가중" },
];

function percent(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined ? "데이터 없음" : `${(value * 100).toFixed(digits)}%`;
}

function signedPercentagePoint(value: number | undefined): string {
  if (value === undefined) return "—";
  const points = value * 100;
  return `${points > 0 ? "+" : ""}${points.toFixed(1)}%p`;
}

function quantityAction(value: number | undefined) {
  const quantity = value ?? 0;
  if (quantity > 0) {
    return {
      label: "매수",
      quantity,
      cardClassName: "border-red-100 bg-red-50/60",
      badgeClassName: "bg-red-100 text-chart-up",
      quantityClassName: "text-chart-up",
    };
  }
  if (quantity < 0) {
    return {
      label: "매도",
      quantity: Math.abs(quantity),
      cardClassName: "border-blue-100 bg-blue-50/60",
      badgeClassName: "bg-blue-100 text-chart-down",
      quantityClassName: "text-chart-down",
    };
  }
  return {
    label: "유지",
    quantity: 0,
    cardClassName: "border-gray-200 bg-gray-50",
    badgeClassName: "bg-gray-200 text-gray-600",
    quantityClassName: "text-gray-700",
  };
}

export default function RebalancingPage() {
  const [holdings, setHoldings] = useState<PortfolioHoldingInput[]>([]);
  const [storageReady, setStorageReady] = useState(false);
  const [priceLoading, setPriceLoading] = useState(true);
  const [scenario, setScenario] = useState<RebalancingScenario>("balanced");
  const [riskMode, setRiskMode] = useState<RebalancingRiskMode>("exploratory");
  const [horizon, setHorizon] = useState<ForecastHorizon>("d5");
  const [state, setState] = useState<PageState>({ status: "idle", result: null, error: null });
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (!active) return;
      const stored = parseStoredHoldings(window.localStorage.getItem(HOLDINGS_STORAGE_KEY))
        ?? INITIAL_HOLDINGS;
      const domestic = stored
        .filter((holding) => /^\d{6}$/.test(holding.code))
        .map((holding) => ({
          code: holding.code,
          name: holding.name,
          quantity: holding.quantity,
          currentPrice: holding.currentPrice ?? 0,
        }));
      setHoldings(domestic);
      setPriceLoading(domestic.some((holding) => holding.currentPrice <= 0));
      setStorageReady(true);
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!storageReady || !priceLoading) return;
    const controller = new AbortController();
    const refreshMissingPrices = async () => {
      const missing = holdings.filter((holding) => holding.currentPrice <= 0);
      const updates = new Map<string, number>();
      try {
        const response = await fetch("/api/portfolio/prices", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ codes: missing.map((holding) => holding.code) }),
          cache: "no-store",
          signal: controller.signal,
        });
        const payload = await response.json() as {
          success?: boolean;
          data?: Record<string, { price: number }>;
        };
        if (response.ok && payload.success) {
          Object.entries(payload.data ?? {}).forEach(([code, value]) => {
            if (Number.isFinite(value.price) && value.price > 0) {
              updates.set(code, value.price);
            }
          });
        }
      } catch {
        if (controller.signal.aborted) return;
      }
      if (controller.signal.aborted) return;
      setHoldings((current) => current.map((holding) => ({
        ...holding,
        currentPrice: updates.get(holding.code) ?? holding.currentPrice,
      })));
      setPriceLoading(false);
    };
    void refreshMissingPrices();
    return () => controller.abort();
  }, [holdings, priceLoading, storageReady]);

  const inputError = useMemo(() => {
    if (!storageReady || priceLoading) return null;
    if (holdings.length === 0) return "분석할 국내 보유 종목이 없습니다.";
    if (holdings.length > 10) {
      return "리밸런싱 계산 범위는 최대 10개 종목입니다. 포트폴리오에서 종목을 줄여 주세요.";
    }
    if (holdings.some((holding) => holding.currentPrice <= 0)) {
      return "현재가가 없는 종목이 있습니다. 내 포트폴리오에서 시세를 먼저 갱신해 주세요.";
    }
    return null;
  }, [holdings, priceLoading, storageReady]);

  useEffect(() => {
    if (!storageReady || priceLoading || inputError) return;
    const abortController = new AbortController();
    const run = async () => {
      setState({ status: "loading", result: null, error: null });
      try {
        const response = await fetch("/api/portfolio/rebalance", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ holdings, scenario, horizon, riskMode }),
          signal: abortController.signal,
        });
        const payload = await response.json() as {
          success: boolean;
          data?: RebalancingResult;
          error?: string;
        };
        if (!response.ok || !payload.success || !payload.data) {
          throw new Error(payload.error ?? "리밸런싱 결과가 없습니다.");
        }
        setState({ status: "ready", result: payload.data, error: null });
      } catch (error) {
        if (abortController.signal.aborted) return;
        setState({
          status: "error",
          result: null,
          error: error instanceof Error ? error.message : "리밸런싱 계산에 실패했습니다.",
        });
      }
    };
    void run();
    return () => abortController.abort();
  }, [holdings, horizon, inputError, priceLoading, riskMode, scenario, storageReady]);

  const result = state.status === "ready" ? state.result : null;
  const riskDelta = useMemo(() => {
    if (!result || result.portfolioLossProbabilityScore === null) return null;
    const target = result.positions.reduce(
      (sum, position) => sum
        + (position.targetWeight ?? position.currentWeight) * (position.lossProbability ?? 0),
      0,
    );
    return {
      current: result.portfolioLossProbabilityScore,
      target,
    };
  }, [result]);
  const tradeCounts = useMemo(() => {
    if (!result) return { buy: 0, sell: 0, hold: 0 };
    return result.positions.reduce(
      (counts, position) => {
        const change = position.estimatedQuantityChange ?? 0;
        if (change > 0) counts.buy += 1;
        else if (change < 0) counts.sell += 1;
        else counts.hold += 1;
        return counts;
      },
      { buy: 0, sell: 0, hold: 0 },
    );
  }, [result]);

  return (
    <main className="mx-auto w-full max-w-[1400px] flex-grow px-6 py-10 lg:px-8">
      <div className="mb-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div className="min-w-0">
          <div className="mb-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-primary">
            저장된 사건 분석 + 현재 보유수량
          </div>
          <h1 className="text-4xl font-black tracking-tight text-gray-900">사건 안전 리밸런싱</h1>
          <p className="mt-3 max-w-[760px] text-sm leading-relaxed text-gray-600">
            최신 유사사건 경험분포를 보유 비중에 반영한 교육용 시뮬레이션입니다.
            실제 주문을 전송하지 않으며, Pedersen 논문의 공인 ESG 점수를 사건안전성으로 대체한 결과가 아닙니다.
          </p>
        </div>
        <Link href="/criteria" className="rounded-xl border border-gray-300 px-5 py-3 text-sm font-bold text-gray-700 hover:bg-gray-50">
          산정 기준 보기
        </Link>
      </div>

      <div className="mb-8 grid gap-4 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm lg:grid-cols-[auto_auto_1fr]">
        <div>
          <p className="mb-2 text-xs font-bold text-gray-500">분석 기간</p>
          <div className="flex gap-2">
            {(["d1", "d5", "d20"] as ForecastHorizon[]).map((value) => (
              <button
                type="button"
                key={value}
                onClick={() => setHorizon(value)}
                className={`rounded-lg px-4 py-2 text-sm font-bold ${horizon === value ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"}`}
              >
                D+{value.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <div className="lg:border-l lg:border-gray-100 lg:pl-5">
          <p className="mb-2 text-xs font-bold text-gray-500">계산 기준</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setRiskMode("exploratory")}
              className={`rounded-lg px-4 py-2 text-left text-sm font-bold ${
                riskMode === "exploratory"
                  ? "bg-primary text-white"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              참고용
              <span className="mt-0.5 block text-[10px] font-medium opacity-75">
                보수적 신뢰도 보정
              </span>
            </button>
            <button
              type="button"
              onClick={() => setRiskMode("validated")}
              className={`rounded-lg px-4 py-2 text-left text-sm font-bold ${
                riskMode === "validated"
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              검증 기준
              <span className="mt-0.5 block text-[10px] font-medium opacity-75">
                medium/high만
              </span>
            </button>
          </div>
        </div>
        <div className="lg:border-l lg:border-gray-100 lg:pl-5">
          <p className="mb-2 text-xs font-bold text-gray-500">안전성 선호 시나리오</p>
          <div className="grid gap-2 sm:grid-cols-3">
            {scenarios.map((item) => (
              <button
                type="button"
                key={item.key}
                onClick={() => setScenario(item.key)}
                className={`rounded-xl border px-4 py-2 text-left ${scenario === item.key ? "border-primary bg-blue-50" : "border-gray-200"}`}
              >
                <span className="block text-sm font-bold">{item.label}</span>
                <span className="mt-0.5 block text-[11px] text-gray-500">{item.description}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {!storageReady || priceLoading || state.status === "loading" ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-16 text-center text-sm text-gray-500">
          {!storageReady
            ? "보유 종목을 불러오고 있습니다."
            : priceLoading
              ? "현재가를 순서대로 확인하고 있습니다."
              : "저장된 위험 결과와 현재 비중을 계산하고 있습니다."}
        </div>
      ) : null}
      {(inputError || state.status === "error") && storageReady && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-8">
          <h2 className="font-bold text-amber-900">계산을 시작할 수 없습니다</h2>
          <p className="mt-2 text-sm text-amber-800">
            {inputError ?? (state.status === "error" ? state.error : "")}
          </p>
          <Link href="/" className="mt-5 inline-flex rounded-lg bg-gray-900 px-4 py-2 text-sm font-bold text-white">
            내 포트폴리오 확인
          </Link>
        </div>
      )}

      {result && !inputError && (
        <>
          <div className="mb-8 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <p className="text-xs font-bold text-gray-500">분석 데이터 커버리지</p>
              <p className="mt-3 text-3xl font-black">{percent(result.coverageWeight, 0)}</p>
              <p className="mt-2 text-xs text-gray-500">
                참고용 {percent(result.exploratoryCoverageWeight, 0)}
                {" · "}
                검증 {percent(result.validatedCoverageWeight, 0)}
              </p>
            </section>
            <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <p className="text-xs font-bold text-gray-500">하락확률 가중 점수</p>
              <p className="mt-3 text-3xl font-black">
                {riskDelta ? `${percent(riskDelta.current, 0)} → ${percent(riskDelta.target, 0)}` : "데이터 없음"}
              </p>
              <p className="mt-2 text-xs text-gray-500">종목 확률의 비중 가중값 · 공동확률 아님</p>
            </section>
            <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <p className="text-xs font-bold text-gray-500">Event Safety</p>
              <p className="mt-3 text-3xl font-black">
                {percent(result.currentSafety, 0)} → {percent(result.targetSafety, 0)}
              </p>
              <p className="mt-2 text-xs text-gray-500">1 - 종목별 사건 하락확률</p>
            </section>
            <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <p className="text-xs font-bold text-gray-500">Turnover / 비용 가정</p>
              <p className="mt-3 text-3xl font-black">{percent(result.turnover, 0)}</p>
              <p className="mt-2 text-xs text-gray-500">
                약 {Math.round(result.estimatedTransactionCost).toLocaleString("ko-KR")}원 · 10bp 가정
              </p>
            </section>
          </div>

          {result.stale && (
            <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800">
              일부 forecast의 갱신 시각이 지났습니다. 결과를 참고값으로만 확인해 주세요.
            </div>
          )}
          {result.riskMode === "exploratory" && result.exploratoryCoverageWeight < 0.999999 && (
            <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 px-5 py-4 text-sm text-blue-900">
              가격 근거가 있는 보유 비중 {percent(result.exploratoryCoverageWeight, 0)}만
              참고용으로 조정하고, 나머지 종목은 현재 비중으로 고정했습니다.
            </div>
          )}
          {result.riskMode === "exploratory" && result.validatedCoverageWeight < 0.5 && (
            <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800">
              검증 기준 커버리지가 {percent(result.validatedCoverageWeight, 0)}입니다.
              표시된 목표 비중은 신뢰도를 보수적으로 보정한 탐색적 결과이며 실제 주문 판단에 사용하지 않습니다.
            </div>
          )}
          {result.status !== "optimal" && (
            <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800">
              {result.status === "hold"
                ? "선택한 기준에서 계산 가능한 가격 근거가 없어 현재 비중 유지를 표시합니다."
                : "종목 상한과 turnover 제약을 동시에 만족하는 결과를 만들지 못해 현재 비중을 유지합니다."}
            </div>
          )}

          <section className="mb-8 overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
            <div className="flex flex-col justify-between gap-4 border-b border-gray-100 px-7 py-6 sm:flex-row sm:items-center">
              <div>
                <p className="text-xs font-bold text-primary">계산상 주문 수량</p>
                <h2 className="mt-1 text-2xl font-black text-gray-900">
                  그래서, 몇 주를 사고팔면 되나요?
                </h2>
                <p className="mt-2 text-sm text-gray-500">
                  현재가와 목표 비중을 기준으로 가장 가까운 정수 주수로 계산했습니다.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs font-bold">
                <span className="rounded-full bg-red-50 px-3 py-2 text-chart-up">
                  매수 {tradeCounts.buy}종목
                </span>
                <span className="rounded-full bg-blue-50 px-3 py-2 text-chart-down">
                  매도 {tradeCounts.sell}종목
                </span>
                {tradeCounts.hold > 0 && (
                  <span className="rounded-full bg-gray-100 px-3 py-2 text-gray-600">
                    유지 {tradeCounts.hold}종목
                  </span>
                )}
              </div>
            </div>
            <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
              {result.positions.map((position) => {
                const action = quantityAction(position.estimatedQuantityChange);
                const targetQuantity = position.quantity
                  + (position.estimatedQuantityChange ?? 0);
                return (
                  <article
                    key={position.code}
                    className={`rounded-2xl border p-5 ${action.cardClassName}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <Link
                          href={`/stock/${position.code}`}
                          className="block truncate font-bold text-gray-900 hover:text-primary"
                        >
                          {position.name}
                        </Link>
                        <p className="mt-1 text-xs text-gray-400">{position.code}</p>
                      </div>
                      <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-black ${action.badgeClassName}`}>
                        {action.label}
                      </span>
                    </div>
                    <p className={`mt-5 text-3xl font-black tabular-nums ${action.quantityClassName}`}>
                      {action.quantity.toLocaleString("ko-KR")}주
                    </p>
                    <p className="mt-2 text-sm font-medium text-gray-600">
                      현재 {position.quantity.toLocaleString("ko-KR")}주
                      <span className="mx-2 text-gray-300">→</span>
                      목표 {targetQuantity.toLocaleString("ko-KR")}주
                    </p>
                    <p className="mt-3 text-xs text-gray-500">
                      현재가 {position.currentPrice.toLocaleString("ko-KR")}원 기준
                    </p>
                  </article>
                );
              })}
            </div>
            <p className="border-t border-gray-100 px-7 py-4 text-xs leading-relaxed text-gray-500">
              실제 주문은 전송되지 않습니다. 세금·수수료·슬리피지와 장중 가격 변동에 따라 실제 필요 수량은 달라질 수 있습니다.
            </p>
          </section>

          <section className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
            <div className="flex flex-col justify-between gap-3 border-b border-gray-100 px-7 py-5 sm:flex-row sm:items-center">
              <div>
                <h2 className="text-xl font-black">현재 비중과 계산상 목표 비중</h2>
                <p className="mt-1 text-xs text-gray-500">최대 종목 비중 {percent(result.maximumWeight, 0)} · 최대 turnover {percent(result.maximumTurnover, 0)}</p>
              </div>
              <button
                type="button"
                disabled={result.status === "infeasible"}
                onClick={() => setIsModalOpen(true)}
                className="rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:bg-gray-300"
              >
                표로 자세히 보기
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[850px] text-left">
                <thead className="bg-gray-50 text-xs font-bold text-gray-500">
                  <tr>
                    <th className="px-7 py-4">종목</th>
                    <th className="px-7 py-4 text-center">현재 비중</th>
                    <th className="px-7 py-4 text-center">목표 비중</th>
                    <th className="px-7 py-4 text-center">변화</th>
                    <th className="px-7 py-4 text-center">D+{horizon.slice(1)} 하락확률</th>
                    <th className="px-7 py-4">근거 상태</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.positions.map((position) => (
                    <tr key={position.code}>
                      <td className="px-7 py-5">
                        <Link href={`/stock/${position.code}`} className="font-bold text-gray-900 hover:text-primary">
                          {position.name}
                        </Link>
                        <p className="mt-1 text-xs text-gray-400">{position.code}</p>
                      </td>
                      <td className="px-7 py-5 text-center tabular-nums">{percent(position.currentWeight)}</td>
                      <td className="px-7 py-5 text-center font-bold tabular-nums">{percent(position.targetWeight)}</td>
                      <td className={`px-7 py-5 text-center font-bold tabular-nums ${(position.weightChange ?? 0) > 0 ? "text-chart-up" : "text-chart-down"}`}>
                        {signedPercentagePoint(position.weightChange)}
                      </td>
                      <td className="px-7 py-5 text-center tabular-nums">{percent(position.lossProbability, 0)}</td>
                      <td className="px-7 py-5 text-sm text-gray-600">
                        {position.productionEligible
                          ? `검증 기준 통과 · ${position.confidence}`
                          : position.forecastAvailable
                            ? `참고용 · ${position.confidence} · ${Math.round((position.probabilityAdjustmentFactor ?? 0) * 100)}% 보정`
                            : position.evidenceAvailable
                              ? `참고용 근거 있음 · ${position.confidence}`
                              : position.confidence
                                ? `가격 관측 부족 · ${position.confidence}`
                                : "현재 이슈 forecast 없음"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <p className="mt-6 text-center text-xs leading-relaxed text-gray-500">
            {result.limitations.join(" ")} 기준시각 {new Date(result.asOf).toLocaleString("ko-KR")}
          </p>
        </>
      )}

      <RebalancingExecutionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        result={result}
      />
    </main>
  );
}
