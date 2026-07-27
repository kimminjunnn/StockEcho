import type {
  HistoricalIssueApiResponse,
  HistoricalIssueRequestBody,
} from "@/lib/historicalIssues";
import { getStoredHistoricalIssueAnalysis } from "@/lib/historicalIssueRepository";
import { getStockIssues } from "@/lib/issueRepository";

export const dynamic = "force-dynamic";

function isRequestBody(value: unknown): value is HistoricalIssueRequestBody {
  if (!value || typeof value !== "object") return false;
  const body = value as Partial<HistoricalIssueRequestBody>;
  return (
    typeof body.topicId === "string"
    && typeof body.eventId === "string"
    && typeof body.eventDate === "string"
    && typeof body.name === "string"
    && typeof body.topicLabel === "string"
    && Array.isArray(body.keywords)
    && body.keywords.every((keyword) => typeof keyword === "string")
  );
}

export async function POST(
  request: Request,
  context: RouteContext<"/api/stocks/[stockCode]/historical-issues">,
) {
  const { stockCode } = await context.params;
  if (!/^\d{6}$/.test(stockCode)) {
    return Response.json(
      { success: false, error: "올바른 6자리 종목 코드가 필요합니다." } satisfies HistoricalIssueApiResponse,
      { status: 400 },
    );
  }
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json(
      { success: false, error: "요청 본문이 올바른 JSON이 아닙니다." } satisfies HistoricalIssueApiResponse,
      { status: 400 },
    );
  }
  if (!isRequestBody(body)) {
    return Response.json(
      { success: false, error: "현재 Event 정보와 키워드가 필요합니다." } satisfies HistoricalIssueApiResponse,
      { status: 400 },
    );
  }
  try {
    const stockIssues = await getStockIssues(stockCode);
    const canonicalIssue = stockIssues?.issues.find(
      (issue) => (
        issue.eventId === body.eventId
        && issue.topicId === body.topicId
        && issue.eventDate === body.eventDate
      ),
    );
    if (!canonicalIssue) {
      return Response.json(
        { success: false, error: "현재 저장된 주요 이슈와 일치하지 않는 요청입니다." } satisfies HistoricalIssueApiResponse,
        { status: 409 },
      );
    }
    const data = await getStoredHistoricalIssueAnalysis(stockCode, body.eventId);
    if (!data) {
      console.info("[historical-issues] Analysis not ready.", {
        stockCode,
        eventId: body.eventId,
      });
      return Response.json(
        {
          success: false,
          errorCode: "analysis_not_ready",
          error: "저장된 과거 유사 이슈 분석이 아직 없습니다.",
        } satisfies HistoricalIssueApiResponse,
        { status: 404 },
      );
    }
    console.info("[historical-issues] Analysis loaded.", {
      stockCode,
      eventId: body.eventId,
      schemaVersion: data.schemaVersion,
      evidenceEventCount: data.events.length,
      completeness: data.completeness,
    });
    return Response.json(
      { success: true, data: { ...data, cacheHit: true } } satisfies HistoricalIssueApiResponse,
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    console.error("[historical-issues] Stored result lookup failed.", {
      stockCode,
      errorName: error instanceof Error ? error.name : "unknown",
    });
    return Response.json(
      {
        success: false,
        errorCode: "stored_analysis_lookup_failed",
        error: "저장된 유사 이슈 분석을 불러오지 못했습니다.",
      } satisfies HistoricalIssueApiResponse,
      { status: 503 },
    );
  }
}
