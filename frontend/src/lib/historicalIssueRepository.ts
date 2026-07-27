import type { HistoricalIssueAnalysis } from "@/lib/historicalIssues";

async function queryStoredHistoricalIssueAnalysis(
  filters: ReadonlyArray<[string, string]>,
): Promise<HistoricalIssueAnalysis | null> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();
  if (!supabaseUrl || !key) return null;
  const query = new URL("/rest/v1/historical_issue_analyses", supabaseUrl);
  query.searchParams.set("select", "result");
  filters.forEach(([name, value]) => query.searchParams.set(name, value));
  query.searchParams.set("status", "eq.ready");
  query.searchParams.set("order", "updated_at.desc");
  query.searchParams.set("limit", "1");
  const response = await fetch(query, {
    headers: { apikey: key },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Supabase historical issue lookup failed (${response.status})`);
  }
  const rows = await response.json() as Array<{ result: HistoricalIssueAnalysis }>;
  return rows[0]?.result ?? null;
}

export async function getStoredHistoricalIssueAnalysis(
  stockCode: string,
  eventId: string,
): Promise<HistoricalIssueAnalysis | null> {
  return queryStoredHistoricalIssueAnalysis([
    ["stock_code", `eq.${stockCode}`],
    ["current_event_id", `eq.${eventId}`],
  ]);
}

export async function getStoredHistoricalIssueAnalysisByEventId(
  eventId: string,
): Promise<HistoricalIssueAnalysis | null> {
  return queryStoredHistoricalIssueAnalysis([
    ["current_event_id", `eq.${eventId}`],
  ]);
}
