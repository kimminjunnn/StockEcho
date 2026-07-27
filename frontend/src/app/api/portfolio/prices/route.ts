import {
  areSupportedStockCodes,
  getLatestStoredPrices,
} from "@/lib/riskRepository";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ success: false, error: "올바른 JSON이 필요합니다." }, { status: 400 });
  }
  const codes = (
    body && typeof body === "object" && Array.isArray((body as { codes?: unknown }).codes)
      ? (body as { codes: unknown[] }).codes
      : []
  );
  if (
    codes.length < 1
    || codes.length > 10
    || !codes.every((code) => typeof code === "string" && /^\d{6}$/.test(code))
  ) {
    return Response.json({ success: false, error: "1~10개 지원 종목 코드가 필요합니다." }, { status: 400 });
  }
  const stockCodes = codes as string[];
  if (!await areSupportedStockCodes(stockCodes)) {
    return Response.json({ success: false, error: "StockEcho 지원 종목만 조회할 수 있습니다." }, { status: 400 });
  }
  try {
    return Response.json({
      success: true,
      data: await getLatestStoredPrices(stockCodes),
    });
  } catch (error) {
    console.error("[portfolio-prices] Stored price lookup failed.", {
      errorName: error instanceof Error ? error.name : "unknown",
    });
    return Response.json({ success: false, error: "저장된 현재가를 불러오지 못했습니다." }, { status: 503 });
  }
}
