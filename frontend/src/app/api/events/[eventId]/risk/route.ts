import { estimateHistoricalReaction } from "@/lib/historicalEstimate";
import { getStoredHistoricalIssueAnalysisByEventId } from "@/lib/historicalIssueRepository";
import type {
  EventRiskApiResponse,
  EventRiskForecast,
  ForecastHorizon,
} from "@/lib/riskForecasts";
import { getEventRiskForecast } from "@/lib/riskRepository";

export const dynamic = "force-dynamic";

function isHorizon(value: string | null): value is ForecastHorizon {
  return value === "d1" || value === "d5" || value === "d20";
}

async function getExploratoryFallback(
  eventId: string,
  horizon: ForecastHorizon,
): Promise<EventRiskForecast | null> {
  const analysis = await getStoredHistoricalIssueAnalysisByEventId(eventId);
  if (!analysis) return null;
  const estimate = estimateHistoricalReaction(analysis.events, horizon);
  if (estimate.status !== "available") return null;
  const asOf = analysis.createdAt;
  const staleAfter = new Date(
    new Date(asOf).getTime() + analysis.search.cacheTtlHours * 60 * 60 * 1000,
  ).toISOString();
  return {
    eventId,
    stockCode: analysis.target.stockCode,
    horizon,
    asOf,
    staleAfter,
    stale: new Date(staleAfter).getTime() <= Date.now(),
    forecast: {
      lossProbability: estimate.lossProbability,
      returnPercentiles: {
        p10: estimate.returnRange.p10,
        p50: estimate.expectedReturnPercent,
        p90: estimate.returnRange.p90,
      },
      observedEventCount: estimate.observedEventCount,
      effectiveSampleSize: estimate.effectiveSampleSize,
      confidence: estimate.confidence,
      productionEligible: false,
      returnBasis: estimate.returnBasis,
      modelVersion: estimate.method,
      datasetVersion: analysis.cacheKey,
    },
    observedHistory: {
      sampleCount: estimate.observedEventCount,
      events: analysis.events,
    },
    limitations: [
      "저장된 화면 사례에서 즉시 계산한 탐색적 추정치입니다.",
      "운영 표본 gate를 통과하지 않았으며 자동 리밸런싱에는 사용하지 않습니다.",
    ],
  };
}

export async function GET(
  request: Request,
  context: { params: Promise<{ eventId: string }> },
) {
  const { eventId } = await context.params;
  const horizonValue = new URL(request.url).searchParams.get("horizon") ?? "d5";
  if (!eventId || eventId.length > 200 || !isHorizon(horizonValue)) {
    return Response.json(
      { success: false, error: "올바른 Event ID와 horizon이 필요합니다." } satisfies EventRiskApiResponse,
      { status: 400 },
    );
  }
  try {
    const stored = await getEventRiskForecast(eventId, horizonValue);
    const data = stored ?? await getExploratoryFallback(eventId, horizonValue);
    if (!data) {
      console.info("[event-risk] Forecast not ready.", {
        eventId,
        horizon: horizonValue,
      });
      return Response.json(
        {
          success: false,
          errorCode: "forecast_not_ready",
          error: "저장된 위험 분석 결과가 아직 없습니다.",
        } satisfies EventRiskApiResponse,
        { status: 404 },
      );
    }
    console.info("[event-risk] Forecast loaded.", {
      eventId,
      horizon: horizonValue,
      confidence: data.forecast.confidence,
      productionEligible: data.forecast.productionEligible,
      observedEventCount: data.forecast.observedEventCount,
      source: stored ? "materialized" : "stored_historical_analysis",
    });
    return Response.json({ success: true, data } satisfies EventRiskApiResponse);
  } catch (error) {
    console.error("[event-risk] Stored forecast lookup failed.", {
      eventId,
      errorName: error instanceof Error ? error.name : "unknown",
    });
    return Response.json(
      { success: false, error: "위험 분석 결과를 불러오지 못했습니다." } satisfies EventRiskApiResponse,
      { status: 503 },
    );
  }
}
