export type ForecastHorizon = "d1" | "d5" | "d20";
export type ForecastConfidence = "high" | "medium" | "low" | "insufficient";

export interface EventRiskForecast {
  eventId: string;
  stockCode: string;
  horizon: ForecastHorizon;
  asOf: string;
  staleAfter: string;
  stale: boolean;
  forecast: {
    lossProbability: number | null;
    returnPercentiles: {
      p10: number | null;
      p50: number | null;
      p90: number | null;
    };
    observedEventCount: number;
    effectiveSampleSize: number;
    confidence: ForecastConfidence;
    productionEligible: boolean;
    returnBasis: "abnormal" | "mixed_or_raw";
    modelVersion: string;
    datasetVersion: string;
  };
  observedHistory: {
    sampleCount: number;
    events: unknown[];
  };
  limitations: string[];
}

export interface EventRiskApiResponse {
  success: boolean;
  data?: EventRiskForecast;
  error?: string;
  errorCode?: string;
}
