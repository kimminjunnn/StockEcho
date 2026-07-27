import type { EventRiskForecast, ForecastHorizon } from "@/lib/riskForecasts";

interface ForecastRow {
  result: EventRiskForecast;
  stale_after: string;
}

interface AnalysisSnapshotRow {
  result: {
    issues?: Array<{ eventId?: string }>;
  };
}

function supabaseConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();
  return url && key ? { url, key } : null;
}

async function queryForecasts(
  filters: ReadonlyArray<[string, string]>,
  limit: number,
): Promise<EventRiskForecast[]> {
  const config = supabaseConfig();
  if (!config) return [];
  const query = new URL("/rest/v1/event_risk_forecasts", config.url);
  query.searchParams.set("select", "result,stale_after");
  filters.forEach(([key, value]) => query.searchParams.set(key, value));
  query.searchParams.set("order", "as_of.desc");
  query.searchParams.set("limit", String(limit));
  const response = await fetch(query, {
    headers: { apikey: config.key },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Supabase forecast lookup failed (${response.status})`);
  }
  const rows = await response.json() as ForecastRow[];
  const now = Date.now();
  return rows.map((row) => ({
    ...row.result,
    stale: new Date(row.stale_after).getTime() <= now,
  }));
}

export async function getEventRiskForecast(
  eventId: string,
  horizon: ForecastHorizon,
): Promise<EventRiskForecast | null> {
  const values = await queryForecasts(
    [["event_id", `eq.${eventId}`], ["horizon", `eq.${horizon}`]],
    1,
  );
  return values[0] ?? null;
}

export async function getLatestStockRiskForecasts(
  stockCodes: string[],
  horizon: ForecastHorizon,
): Promise<Map<string, EventRiskForecast>> {
  if (stockCodes.length === 0) return new Map();
  const safeCodes = stockCodes.filter((code) => /^\d{6}$/.test(code));
  if (safeCodes.length === 0) return new Map();
  const config = supabaseConfig();
  if (!config) return new Map();
  const currentEventIds = (
    await Promise.all(safeCodes.map(async (stockCode) => {
      const query = new URL("/rest/v1/stock_analysis_results", config.url);
      query.searchParams.set("select", "result");
      query.searchParams.set("stock_code", `eq.${stockCode}`);
      query.searchParams.set("order", "analyzed_at.desc");
      query.searchParams.set("limit", "1");
      const response = await fetch(query, {
        headers: { apikey: config.key },
        cache: "no-store",
      });
      if (!response.ok) return [];
      const rows = await response.json() as AnalysisSnapshotRow[];
      return (rows[0]?.result.issues ?? [])
        .map((issue) => issue.eventId ?? "")
        .filter((eventId) => eventId.length > 0);
    }))
  ).flat();
  if (currentEventIds.length === 0) return new Map();
  const values = await queryForecasts(
    [
      ["event_id", `in.(${currentEventIds.join(",")})`],
      ["horizon", `eq.${horizon}`],
    ],
    currentEventIds.length * 3,
  );
  const latestByEvent = new Map<string, EventRiskForecast>();
  values.forEach((forecast) => {
    if (!latestByEvent.has(forecast.eventId)) {
      latestByEvent.set(forecast.eventId, forecast);
    }
  });
  const confidenceRank = { high: 4, medium: 3, low: 2, insufficient: 1 };
  const priority = (forecast: EventRiskForecast) => {
    const evidenceAvailable = (
      forecast.forecast.lossProbability !== null
      && forecast.forecast.returnPercentiles.p10 !== null
    );
    return (
      (forecast.forecast.productionEligible ? 10_000 : 0)
      + (evidenceAvailable ? 1_000 : 0)
      + confidenceRank[forecast.forecast.confidence] * 100
      + Math.min(forecast.forecast.observedEventCount, 99)
      + (forecast.forecast.lossProbability ?? 0)
    );
  };
  const latest = new Map<string, EventRiskForecast>();
  latestByEvent.forEach((forecast) => {
    const selected = latest.get(forecast.stockCode);
    if (!selected || priority(forecast) > priority(selected)) {
      latest.set(forecast.stockCode, forecast);
    }
  });
  return latest;
}

export async function areSupportedStockCodes(stockCodes: string[]): Promise<boolean> {
  const config = supabaseConfig();
  if (!config || stockCodes.length === 0) return false;
  const unique = [...new Set(stockCodes)];
  const query = new URL("/rest/v1/stocks", config.url);
  query.searchParams.set("select", "stock_code");
  query.searchParams.set("stock_code", `in.(${unique.join(",")})`);
  query.searchParams.set("is_supported", "eq.true");
  const response = await fetch(query, {
    headers: { apikey: config.key },
    cache: "no-store",
  });
  if (!response.ok) return false;
  const rows = await response.json() as Array<{ stock_code: string }>;
  return new Set(rows.map((row) => row.stock_code)).size === unique.length;
}

export async function getLatestStoredPrices(
  stockCodes: string[],
): Promise<Record<string, {
  price: number;
  tradingDate: string;
  changeRate: number | null;
}>> {
  const config = supabaseConfig();
  if (!config) return {};
  const entries = await Promise.all(stockCodes.map(async (stockCode) => {
    const query = new URL("/rest/v1/market_daily", config.url);
    query.searchParams.set("select", "close_price,trading_date");
    query.searchParams.set("stock_code", `eq.${stockCode}`);
    query.searchParams.set("order", "trading_date.desc");
    query.searchParams.set("limit", "2");
    const response = await fetch(query, {
      headers: { apikey: config.key },
      cache: "no-store",
    });
    if (!response.ok) return null;
    const rows = await response.json() as Array<{
      close_price: string | number;
      trading_date: string;
    }>;
    const price = Number(rows[0]?.close_price);
    const previousPrice = Number(rows[1]?.close_price);
    const changeRate = (
      Number.isFinite(previousPrice) && previousPrice > 0
        ? ((price / previousPrice) - 1) * 100
        : null
    );
    return Number.isFinite(price) && price > 0
      ? [
          stockCode,
          {
            price,
            tradingDate: rows[0].trading_date,
            changeRate,
          },
        ] as const
      : null;
  }));
  return Object.fromEntries(entries.filter((entry) => entry !== null));
}
