import type {
  HistoricalIssueEvent,
  HistoricalPriceReaction,
} from "@/lib/historicalIssues";
import type {
  ForecastConfidence,
  ForecastHorizon,
} from "@/lib/riskForecasts";

export interface HistoricalReactionEstimate {
  status: "available" | "unavailable";
  horizon: ForecastHorizon;
  direction: "up" | "down" | "flat" | "unknown";
  expectedReturnPercent: number | null;
  returnRange: {
    p10: number | null;
    p90: number | null;
  };
  lossProbability: number | null;
  observedEventCount: number;
  effectiveSampleSize: number;
  confidence: ForecastConfidence;
  returnBasis: "abnormal" | "mixed_or_raw";
  method: "similarity-weighted-historical-replay-v1";
}

interface WeightedObservation {
  value: number;
  weight: number;
  basis: "abnormal" | "raw";
}

function weightedQuantile(
  observations: WeightedObservation[],
  quantile: number,
): number | null {
  if (observations.length === 0) return null;
  const sorted = [...observations].sort((left, right) => left.value - right.value);
  const totalWeight = sorted.reduce((sum, item) => sum + item.weight, 0);
  const threshold = quantile * totalWeight;
  let cumulative = 0;
  for (const item of sorted) {
    cumulative += item.weight;
    if (cumulative >= threshold) return item.value;
  }
  return sorted.at(-1)?.value ?? null;
}

function effectiveSampleSize(observations: WeightedObservation[]): number {
  const totalWeight = observations.reduce((sum, item) => sum + item.weight, 0);
  const squaredWeight = observations.reduce(
    (sum, item) => sum + item.weight ** 2,
    0,
  );
  return squaredWeight > 0 ? totalWeight ** 2 / squaredWeight : 0;
}

function confidenceFor(
  observedEventCount: number,
  effectiveN: number,
): ForecastConfidence {
  if (observedEventCount >= 20 && effectiveN >= 12) return "high";
  if (observedEventCount >= 8 && effectiveN >= 5) return "medium";
  if (observedEventCount >= 3) return "low";
  return "insufficient";
}

function reactionValue(
  reaction: HistoricalPriceReaction,
  horizon: ForecastHorizon,
): { value: number; basis: "abnormal" | "raw" } | null {
  const abnormal = reaction.abnormalReturns?.[horizon];
  if (typeof abnormal === "number" && Number.isFinite(abnormal)) {
    return { value: abnormal, basis: "abnormal" };
  }
  const raw = reaction.returns[horizon];
  return typeof raw === "number" && Number.isFinite(raw)
    ? { value: raw, basis: "raw" }
    : null;
}

export function estimateHistoricalReaction(
  events: HistoricalIssueEvent[],
  horizon: ForecastHorizon,
): HistoricalReactionEstimate {
  const observations = events.flatMap((event): WeightedObservation[] => {
    const reaction = reactionValue(event.priceReaction, horizon);
    if (!reaction) return [];
    const similarity = Math.max(event.similarityScore, 0);
    const sourceEvidence = Math.min(
      Math.log1p(Math.max(event.sourceCount, 1)) / Math.log(6),
      1,
    );
    return [{
      ...reaction,
      weight: Math.max(similarity * sourceEvidence, 0.01),
    }];
  });
  const effectiveN = effectiveSampleSize(observations);
  const expectedReturnPercent = weightedQuantile(observations, 0.5);
  const weightedLoss = observations.reduce(
    (sum, item) => sum + (item.value < 0 ? item.weight : 0),
    0,
  );
  const totalWeight = observations.reduce((sum, item) => sum + item.weight, 0);
  const lossProbability = observations.length > 0
    ? (weightedLoss + 1) / (totalWeight + 2)
    : null;
  const direction = expectedReturnPercent === null
    ? "unknown"
    : expectedReturnPercent > 0.05
      ? "up"
      : expectedReturnPercent < -0.05
        ? "down"
        : "flat";

  return {
    status: observations.length > 0 ? "available" : "unavailable",
    horizon,
    direction,
    expectedReturnPercent,
    returnRange: {
      p10: weightedQuantile(observations, 0.1),
      p90: weightedQuantile(observations, 0.9),
    },
    lossProbability,
    observedEventCount: observations.length,
    effectiveSampleSize: Number(effectiveN.toFixed(4)),
    confidence: confidenceFor(observations.length, effectiveN),
    returnBasis: observations.every((item) => item.basis === "abnormal")
      ? "abnormal"
      : "mixed_or_raw",
    method: "similarity-weighted-historical-replay-v1",
  };
}
