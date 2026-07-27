export type RiskLevel = "critical" | "caution" | "good" | "pending";

export interface Holding {
  code: string;
  name: string;
  quantity: number;
  currentPrice?: number;
  changeRate?: number;
  riskLevel: RiskLevel;
}

export const HOLDINGS_STORAGE_KEY = "stockecho.holdings.v2";

const DEFAULT_HOLDING_CODES = new Set([
  "005930",
  "000660",
  "042700",
  "005380",
  "035420",
  "035720",
]);

export function parseStoredHoldings(value: string | null): Holding[] | null {
  if (!value) return null;
  try {
    const parsed: unknown = JSON.parse(value);
    if (!Array.isArray(parsed)) return null;
    const holdings = parsed.filter((item): item is Partial<Holding> & Pick<Holding, "code" | "name" | "quantity"> => {
      if (!item || typeof item !== "object") return false;
      const candidate = item as Partial<Holding>;
      return (
        typeof candidate.code === "string" &&
        typeof candidate.name === "string" &&
        typeof candidate.quantity === "number" &&
        candidate.quantity > 0 &&
        ["critical", "caution", "good", "pending"].includes(
          candidate.riskLevel ?? "pending",
        )
      );
    }).map((holding): Holding => ({
      code: holding.code,
      name: holding.name,
      quantity: holding.quantity,
      currentPrice: typeof holding.currentPrice === "number" ? holding.currentPrice : undefined,
      changeRate: typeof holding.changeRate === "number" ? holding.changeRate : undefined,
      riskLevel: holding.riskLevel ?? "pending",
    }));
    if (holdings.length === 0) return null;
    const isLegacyDefaultPortfolio = (
      holdings.length >= 5
      && holdings.every(
        (holding) => holding.quantity === 1 && DEFAULT_HOLDING_CODES.has(holding.code),
      )
    );
    return isLegacyDefaultPortfolio
      ? holdings.map((holding) => ({ ...holding, quantity: 10 }))
      : holdings;
  } catch {
    return null;
  }
}

export const INITIAL_HOLDINGS: Holding[] = [
  {
    code: "005930",
    name: "삼성전자",
    quantity: 10,
    riskLevel: "pending",
  },
  {
    code: "000660",
    name: "SK하이닉스",
    quantity: 10,
    riskLevel: "pending",
  },
  {
    code: "042700",
    name: "한미반도체",
    quantity: 10,
    riskLevel: "pending",
  },
  {
    code: "005380",
    name: "현대차",
    quantity: 10,
    riskLevel: "pending",
  },
  {
    code: "035420",
    name: "네이버",
    quantity: 10,
    riskLevel: "pending",
  },
  {
    code: "035720",
    name: "카카오",
    quantity: 10,
    riskLevel: "pending",
  },
];
