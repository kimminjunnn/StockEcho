import { describe, expect, it } from "vitest";
import {
  analyzePortfolio,
  rebalancePortfolio,
  validatePortfolioHoldings,
  type PortfolioHoldingInput,
} from "./portfolioEngine";
import type { EventRiskForecast } from "./riskForecasts";

function forecast(
  stockCode: string,
  probability: number,
  { stale = false, confidence = "medium" } = {},
): EventRiskForecast {
  return {
    eventId: `event-${stockCode}`,
    stockCode,
    horizon: "d5",
    asOf: "2026-07-27T00:00:00Z",
    staleAfter: "2026-08-01T00:00:00Z",
    stale,
    forecast: {
      lossProbability: probability,
      returnPercentiles: { p10: -10 * probability, p50: -2, p90: 3 },
      observedEventCount: 10,
      effectiveSampleSize: 7,
      confidence: confidence as EventRiskForecast["forecast"]["confidence"],
      productionEligible: true,
      returnBasis: "abnormal",
      modelVersion: "test",
      datasetVersion: "test",
    },
    observedHistory: { sampleCount: 10, events: [] },
    limitations: [],
  };
}

const holdings: PortfolioHoldingInput[] = [
  { code: "005930", name: "삼성전자", quantity: 1, currentPrice: 600 },
  { code: "035420", name: "NAVER", quantity: 1, currentPrice: 400 },
];

describe("portfolio engine", () => {
  it("validates one to ten unique domestic holdings", () => {
    expect(validatePortfolioHoldings(holdings)).toBeNull();
    expect(validatePortfolioHoldings([])).toContain("1개 이상");
    expect(validatePortfolioHoldings([...holdings, holdings[0]])).toContain("중복");
  });

  it("reports partial coverage and stale data", () => {
    const analysis = analyzePortfolio(
      holdings,
      new Map([["005930", forecast("005930", 0.7, { stale: true })]]),
      "d5",
    );

    expect(analysis.coverageStatus).toBe("partial");
    expect(analysis.coverageWeight).toBeCloseTo(0.6);
    expect(analysis.stale).toBe(true);
  });

  it("keeps current weights when validated mode has no eligible evidence", () => {
    const low = forecast("005930", 0.7, { confidence: "low" });
    low.forecast.productionEligible = false;
    const analysis = analyzePortfolio(
      holdings,
      new Map([["005930", low]]),
      "d5",
    );
    const result = rebalancePortfolio(analysis, "balanced");

    expect(analysis.coverageWeight).toBe(0);
    expect(analysis.exploratoryCoverageWeight).toBeCloseTo(0.6);
    expect(result.status).toBe("hold");
    expect(result.positions.every(
      (position) => position.targetWeight === position.currentWeight,
    )).toBe(true);
  });

  it("shrinks exploratory probabilities and limits low-confidence weight changes", () => {
    const highRisk = forecast("005930", 0.8, { confidence: "low" });
    const lowRisk = forecast("035420", 0.2, { confidence: "low" });
    highRisk.forecast.productionEligible = false;
    lowRisk.forecast.productionEligible = false;
    const analysis = analyzePortfolio(
      holdings,
      new Map([
        ["005930", highRisk],
        ["035420", lowRisk],
      ]),
      "d5",
      "exploratory",
    );
    const result = rebalancePortfolio(analysis, "safety_first");

    expect(analysis.coverageWeight).toBeCloseTo(1);
    expect(analysis.positions[0].rawLossProbability).toBe(0.8);
    expect(analysis.positions[0].lossProbability).toBeCloseTo(0.65);
    expect(result.status).toBe("optimal");
    expect(result.maximumTurnover).toBe(0.1);
    expect(result.positions.every(
      (position) => Math.abs(position.weightChange ?? 0) <= 0.03 + 1e-9,
    )).toBe(true);
  });

  it("keeps weights normalized and turnover bounded", () => {
    const analysis = analyzePortfolio(
      holdings,
      new Map([
        ["005930", forecast("005930", 0.8)],
        ["035420", forecast("035420", 0.2)],
      ]),
      "d5",
    );
    const result = rebalancePortfolio(analysis, "safety_first");

    expect(result.status).toBe("optimal");
    expect(result.positions.reduce((sum, row) => sum + (row.targetWeight ?? 0), 0)).toBeCloseTo(1);
    expect(result.turnover).toBeLessThanOrEqual(result.maximumTurnover + 1e-9);
    expect(result.targetSafety).toBeGreaterThan(result.currentSafety ?? 0);
  });

  it("supports a one-asset portfolio without inventing a trade", () => {
    const one = [holdings[0]];
    const analysis = analyzePortfolio(
      one,
      new Map([["005930", forecast("005930", 0.5)]]),
      "d5",
    );
    const result = rebalancePortfolio(analysis, "balanced");

    expect(result.status).toBe("optimal");
    expect(result.maximumWeight).toBe(1);
    expect(result.turnover).toBe(0);
  });
});
