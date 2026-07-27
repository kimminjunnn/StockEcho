import {
  analyzePortfolio,
  rebalancePortfolio,
  validatePortfolioHoldings,
  type PortfolioHoldingInput,
  type RebalancingRiskMode,
  type RebalancingScenario,
} from "@/lib/portfolioEngine";
import type { ForecastHorizon } from "@/lib/riskForecasts";
import {
  areSupportedStockCodes,
  getLatestStockRiskForecasts,
} from "@/lib/riskRepository";

export const dynamic = "force-dynamic";

interface RebalanceRequest {
  holdings: PortfolioHoldingInput[];
  horizon?: ForecastHorizon;
  riskMode?: RebalancingRiskMode;
  scenario?: RebalancingScenario;
}

function isRequest(value: unknown): value is RebalanceRequest {
  if (!value || typeof value !== "object") return false;
  const request = value as Partial<RebalanceRequest>;
  return Array.isArray(request.holdings)
    && (request.horizon === undefined || ["d1", "d5", "d20"].includes(request.horizon))
    && (request.riskMode === undefined || ["exploratory", "validated"].includes(request.riskMode))
    && (request.scenario === undefined || ["risk_first", "balanced", "safety_first"].includes(request.scenario));
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ success: false, error: "올바른 JSON이 필요합니다." }, { status: 400 });
  }
  if (!isRequest(body)) {
    return Response.json({ success: false, error: "리밸런싱 입력이 필요합니다." }, { status: 400 });
  }
  const validationError = validatePortfolioHoldings(body.holdings);
  if (validationError) {
    return Response.json({ success: false, error: validationError }, { status: 400 });
  }
  const codes = body.holdings.map((holding) => holding.code);
  if (!await areSupportedStockCodes(codes)) {
    return Response.json({ success: false, error: "StockEcho 지원 종목만 계산할 수 있습니다." }, { status: 400 });
  }
  try {
    const horizon = body.horizon ?? "d5";
    const forecasts = await getLatestStockRiskForecasts(codes, horizon);
    const analysis = analyzePortfolio(
      body.holdings,
      forecasts,
      horizon,
      body.riskMode ?? "exploratory",
    );
    const data = rebalancePortfolio(analysis, body.scenario ?? "balanced");
    return Response.json({ success: true, data });
  } catch (error) {
    console.error("[portfolio-rebalance] Failed.", {
      errorName: error instanceof Error ? error.name : "unknown",
    });
    return Response.json({ success: false, error: "리밸런싱 계산을 완료하지 못했습니다." }, { status: 503 });
  }
}
