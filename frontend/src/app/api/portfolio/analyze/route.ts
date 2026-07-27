import {
  analyzePortfolio,
  validatePortfolioHoldings,
  type PortfolioHoldingInput,
} from "@/lib/portfolioEngine";
import type { ForecastHorizon } from "@/lib/riskForecasts";
import {
  areSupportedStockCodes,
  getLatestStockRiskForecasts,
} from "@/lib/riskRepository";

export const dynamic = "force-dynamic";

interface AnalyzeRequest {
  holdings: PortfolioHoldingInput[];
  horizon?: ForecastHorizon;
}

function isRequest(value: unknown): value is AnalyzeRequest {
  if (!value || typeof value !== "object") return false;
  const request = value as Partial<AnalyzeRequest>;
  return Array.isArray(request.holdings)
    && (request.horizon === undefined || ["d1", "d5", "d20"].includes(request.horizon));
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ success: false, error: "올바른 JSON이 필요합니다." }, { status: 400 });
  }
  if (!isRequest(body)) {
    return Response.json({ success: false, error: "보유 종목 입력이 필요합니다." }, { status: 400 });
  }
  const validationError = validatePortfolioHoldings(body.holdings);
  if (validationError) {
    return Response.json({ success: false, error: validationError }, { status: 400 });
  }
  const codes = body.holdings.map((holding) => holding.code);
  if (!await areSupportedStockCodes(codes)) {
    return Response.json({ success: false, error: "StockEcho 지원 종목만 분석할 수 있습니다." }, { status: 400 });
  }
  try {
    const horizon = body.horizon ?? "d5";
    const forecasts = await getLatestStockRiskForecasts(codes, horizon);
    return Response.json({
      success: true,
      data: analyzePortfolio(body.holdings, forecasts, horizon),
    });
  } catch (error) {
    console.error("[portfolio-analyze] Failed.", {
      errorName: error instanceof Error ? error.name : "unknown",
    });
    return Response.json({ success: false, error: "포트폴리오 분석을 완료하지 못했습니다." }, { status: 503 });
  }
}
