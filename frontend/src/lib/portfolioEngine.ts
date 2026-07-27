import type { EventRiskForecast, ForecastHorizon } from "@/lib/riskForecasts";

export type RebalancingScenario = "risk_first" | "balanced" | "safety_first";
export type RebalancingRiskMode = "exploratory" | "validated";

export interface PortfolioHoldingInput {
  code: string;
  name: string;
  quantity: number;
  currentPrice: number;
}

export interface PortfolioPositionAnalysis {
  code: string;
  name: string;
  quantity: number;
  currentPrice: number;
  marketValue: number;
  currentWeight: number;
  targetWeight?: number;
  weightChange?: number;
  estimatedQuantityChange?: number;
  forecastAvailable: boolean;
  evidenceAvailable: boolean;
  productionEligible: boolean;
  lossProbability: number | null;
  rawLossProbability: number | null;
  downsideReturnPercent: number | null;
  downsideContributionPercent: number | null;
  probabilityAdjustmentFactor: number | null;
  confidence: string | null;
  eventId: string | null;
}

export interface PortfolioAnalysis {
  schemaVersion: "portfolio-analysis-v1";
  horizon: ForecastHorizon;
  riskMode: RebalancingRiskMode;
  asOf: string;
  totalMarketValue: number;
  coverageWeight: number;
  validatedCoverageWeight: number;
  exploratoryCoverageWeight: number;
  coverageStatus: "complete" | "partial" | "unavailable";
  portfolioLossProbabilityScore: number | null;
  portfolioDownsideScenarioPercent: number | null;
  stale: boolean;
  positions: PortfolioPositionAnalysis[];
  limitations: string[];
}

export interface RebalancingResult extends Omit<PortfolioAnalysis, "schemaVersion"> {
  schemaVersion: "portfolio-rebalancing-v1";
  status: "optimal" | "infeasible" | "hold";
  scenario: RebalancingScenario;
  method: "event-safety-bounded-blend-v1";
  turnover: number;
  maximumTurnover: number;
  maximumWeight: number;
  estimatedTransactionCost: number;
  currentSafety: number | null;
  targetSafety: number | null;
}

export function validatePortfolioHoldings(
  holdings: PortfolioHoldingInput[],
): string | null {
  if (holdings.length < 1 || holdings.length > 10) {
    return "보유 종목은 1개 이상 10개 이하여야 합니다.";
  }
  if (new Set(holdings.map((holding) => holding.code)).size !== holdings.length) {
    return "중복 종목은 허용되지 않습니다.";
  }
  const invalid = holdings.some((holding) => (
    !/^\d{6}$/.test(holding.code)
    || !Number.isFinite(holding.quantity)
    || holding.quantity <= 0
    || !Number.isFinite(holding.currentPrice)
    || holding.currentPrice <= 0
  ));
  return invalid ? "지원 종목 코드와 양의 수량·현재가가 필요합니다." : null;
}

export function analyzePortfolio(
  holdings: PortfolioHoldingInput[],
  forecasts: Map<string, EventRiskForecast>,
  horizon: ForecastHorizon,
  riskMode: RebalancingRiskMode = "validated",
): PortfolioAnalysis {
  const validationError = validatePortfolioHoldings(holdings);
  if (validationError) throw new Error(validationError);
  const totalMarketValue = holdings.reduce(
    (sum, holding) => sum + holding.quantity * holding.currentPrice,
    0,
  );
  let coverageWeight = 0;
  let validatedCoverageWeight = 0;
  let exploratoryCoverageWeight = 0;
  let lossScore = 0;
  let downsideScenario = 0;
  let anyStale = false;
  const positions = holdings.map((holding): PortfolioPositionAnalysis => {
    const marketValue = holding.quantity * holding.currentPrice;
    const currentWeight = marketValue / totalMarketValue;
    const forecast = forecasts.get(holding.code);
    const evidenceAvailable = Boolean(
      forecast
      && forecast.forecast.lossProbability !== null
      && forecast.forecast.returnPercentiles.p10 !== null,
    );
    const productionEligible = Boolean(
      evidenceAvailable && forecast?.forecast.productionEligible,
    );
    if (evidenceAvailable) exploratoryCoverageWeight += currentWeight;
    if (productionEligible) validatedCoverageWeight += currentWeight;
    const available = riskMode === "exploratory"
      ? evidenceAvailable
      : productionEligible;
    const rawLossProbability = evidenceAvailable
      ? forecast?.forecast.lossProbability ?? null
      : null;
    const confidence = forecast?.forecast.confidence ?? null;
    const adjustmentFactor = available
      ? productionEligible
        ? 1
        : confidence === "low"
          ? 0.5
          : confidence === "insufficient"
            ? 0.2
            : 0.75
      : null;
    const lossProbability = (
      rawLossProbability !== null && adjustmentFactor !== null
        ? 0.5 + adjustmentFactor * (rawLossProbability - 0.5)
        : null
    );
    const rawDownside = evidenceAvailable
      ? forecast?.forecast.returnPercentiles.p10 ?? null
      : null;
    const downside = (
      rawDownside !== null && adjustmentFactor !== null
        ? rawDownside * adjustmentFactor
        : null
    );
    if (available && lossProbability !== null && downside !== null) {
      coverageWeight += currentWeight;
      lossScore += currentWeight * lossProbability;
      downsideScenario += currentWeight * downside;
      anyStale ||= Boolean(forecast?.stale);
    }
    return {
      code: holding.code,
      name: holding.name,
      quantity: holding.quantity,
      currentPrice: holding.currentPrice,
      marketValue,
      currentWeight,
      forecastAvailable: available,
      evidenceAvailable,
      productionEligible,
      lossProbability,
      rawLossProbability,
      downsideReturnPercent: downside,
      downsideContributionPercent: downside === null ? null : currentWeight * downside,
      probabilityAdjustmentFactor: adjustmentFactor,
      confidence,
      eventId: forecast?.eventId ?? null,
    };
  });
  return {
    schemaVersion: "portfolio-analysis-v1",
    horizon,
    riskMode,
    asOf: new Date().toISOString(),
    totalMarketValue,
    coverageWeight,
    validatedCoverageWeight,
    exploratoryCoverageWeight,
    coverageStatus: coverageWeight > 0.999999
      ? "complete"
      : coverageWeight > 0
        ? "partial"
        : "unavailable",
    portfolioLossProbabilityScore: coverageWeight > 0 ? lossScore : null,
    portfolioDownsideScenarioPercent: coverageWeight > 0 ? downsideScenario : null,
    stale: anyStale,
    positions,
    limitations: [
      "종목별 하방 분위수의 비중 가중 시나리오이며 공동 꼬리위험 확률은 아닙니다.",
      riskMode === "exploratory"
        ? "검증 기준 미달 예측은 50% 중립 확률 쪽으로 보정하고 비중 변경폭을 제한했습니다."
        : "검증 기준을 통과한 예측만 계산에 사용했습니다.",
      "실제 주문을 생성하지 않는 연구·교육용 계산입니다.",
    ],
  };
}

function capAndNormalize(weights: number[], maximumWeight: number): number[] | null {
  if (weights.length * maximumWeight < 1 - 1e-9) return null;
  const result = Array(weights.length).fill(0);
  const remaining = new Set(weights.map((_value, index) => index));
  let budget = 1;
  while (remaining.size > 0) {
    const totalScore = [...remaining].reduce((sum, index) => sum + weights[index], 0);
    const equal = totalScore <= 0;
    let capped = false;
    for (const index of [...remaining]) {
      const value = equal
        ? budget / remaining.size
        : budget * weights[index] / totalScore;
      if (value > maximumWeight + 1e-12) {
        result[index] = maximumWeight;
        budget -= maximumWeight;
        remaining.delete(index);
        capped = true;
      }
    }
    if (!capped) {
      for (const index of remaining) {
        result[index] = equal
          ? budget / remaining.size
          : budget * weights[index] / totalScore;
      }
      break;
    }
  }
  return result;
}

export function rebalancePortfolio(
  analysis: PortfolioAnalysis,
  scenario: RebalancingScenario,
  {
    maximumWeight = 0.6,
    maximumTurnover = 0.3,
    transactionCostBps = 10,
  } = {},
): RebalancingResult {
  const effectiveMaximumWeight = Math.max(maximumWeight, 1 / analysis.positions.length);
  const effectiveMaximumTurnover = analysis.riskMode === "exploratory"
    ? Math.min(maximumTurnover, 0.1)
    : maximumTurnover;
  const scenarioPower = { risk_first: 0.75, balanced: 1.5, safety_first: 3 }[scenario];
  if (analysis.coverageWeight <= 1e-12) {
    return {
      ...analysis,
      schemaVersion: "portfolio-rebalancing-v1",
      status: "hold",
      scenario,
      method: "event-safety-bounded-blend-v1",
      turnover: 0,
      maximumTurnover: effectiveMaximumTurnover,
      maximumWeight: effectiveMaximumWeight,
      estimatedTransactionCost: 0,
      currentSafety: null,
      targetSafety: null,
      positions: analysis.positions.map((position) => ({
        ...position,
        targetWeight: position.currentWeight,
        weightChange: 0,
        estimatedQuantityChange: 0,
      })),
    };
  }
  const current = analysis.positions.map((position) => position.currentWeight);
  const coveredIndexes = analysis.positions
    .map((position, index) => position.forecastAvailable ? index : -1)
    .filter((index) => index >= 0);
  const coveredSafety = coveredIndexes.map(
    (index) => 1 - (analysis.positions[index].lossProbability ?? 0.5),
  );
  const normalizedCovered = capAndNormalize(
    coveredSafety.map((value) => Math.max(value, 0.01) ** scenarioPower),
    effectiveMaximumWeight / analysis.coverageWeight,
  );
  const desired = [...current];
  coveredIndexes.forEach((positionIndex, coveredIndex) => {
    desired[positionIndex] = normalizedCovered
      ? normalizedCovered[coveredIndex] * analysis.coverageWeight
      : current[positionIndex];
  });
  const fullTurnover = 0.5 * desired.reduce(
    (sum, weight, index) => sum + Math.abs(weight - current[index]),
    0,
  );
  const turnoverBlend = fullTurnover > 0
    ? Math.min(1, effectiveMaximumTurnover / fullTurnover)
    : 1;
  const confidenceBlend = coveredIndexes.reduce((minimum, index) => {
    const delta = Math.abs(desired[index] - current[index]);
    if (delta <= 1e-12 || analysis.riskMode === "validated") return minimum;
    const position = analysis.positions[index];
    const maximumDelta = position.productionEligible
      ? 0.1
      : position.confidence === "low"
        ? 0.03
        : 0.01;
    return Math.min(minimum, maximumDelta / delta);
  }, 1);
  const blend = Math.min(turnoverBlend, confidenceBlend);
  const target = desired.map(
    (weight, index) => current[index] + blend * (weight - current[index]),
  );
  const turnover = 0.5 * target.reduce(
    (sum, weight, index) => sum + Math.abs(weight - current[index]),
    0,
  );
  const violatesCap = target.some(
    (weight, index) => (
      analysis.positions[index].forecastAvailable
      && weight > effectiveMaximumWeight + 1e-8
      && weight > current[index] + 1e-8
    ),
  );
  const positions = analysis.positions.map((position, index) => {
    const targetValue = target[index] * analysis.totalMarketValue;
    const targetQuantity = Math.round(targetValue / position.currentPrice);
    return {
      ...position,
      targetWeight: target[index],
      weightChange: target[index] - position.currentWeight,
      estimatedQuantityChange: targetQuantity - position.quantity,
    };
  });
  return {
    ...analysis,
    schemaVersion: "portfolio-rebalancing-v1",
    status: violatesCap ? "infeasible" : "optimal",
    scenario,
    method: "event-safety-bounded-blend-v1",
    turnover,
    maximumTurnover: effectiveMaximumTurnover,
    maximumWeight: effectiveMaximumWeight,
    estimatedTransactionCost: analysis.totalMarketValue * turnover * transactionCostBps / 10_000,
    currentSafety: coveredIndexes.reduce(
      (sum, index, coveredIndex) => sum + current[index] * coveredSafety[coveredIndex],
      0,
    ) / analysis.coverageWeight,
    targetSafety: coveredIndexes.reduce(
      (sum, index, coveredIndex) => sum + target[index] * coveredSafety[coveredIndex],
      0,
    ) / analysis.coverageWeight,
    positions,
  };
}
