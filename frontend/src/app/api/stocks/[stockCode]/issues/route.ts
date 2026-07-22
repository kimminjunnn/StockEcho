import { getStockIssues } from "@/lib/issueRepository";
import type { StockIssuesApiResponse } from "@/lib/issues";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: RouteContext<"/api/stocks/[stockCode]/issues">,
) {
  const { stockCode } = await context.params;
  if (!/^\d{6}$/.test(stockCode)) {
    return Response.json(
      { success: false, error: "올바른 6자리 종목 코드가 필요합니다." } satisfies StockIssuesApiResponse,
      { status: 400 },
    );
  }

  try {
    const data = await getStockIssues(stockCode);
    if (!data) {
      return Response.json(
        { success: true, data: undefined } satisfies StockIssuesApiResponse,
        { status: 200 },
      );
    }
    return Response.json({ success: true, data } satisfies StockIssuesApiResponse);
  } catch (error) {
    console.error(`Issue repository failed for ${stockCode}:`, error);
    return Response.json(
      { success: false, error: "이슈 분석 결과를 불러오지 못했습니다." } satisfies StockIssuesApiResponse,
      { status: 500 },
    );
  }
}
