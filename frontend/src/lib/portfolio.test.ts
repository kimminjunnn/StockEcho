import { describe, expect, it } from "vitest";
import { INITIAL_HOLDINGS, parseStoredHoldings } from "./portfolio";

describe("default portfolio", () => {
  it("starts all six default stocks with ten shares", () => {
    expect(INITIAL_HOLDINGS).toHaveLength(6);
    expect(INITIAL_HOLDINGS.every((holding) => holding.quantity === 10)).toBe(true);
  });

  it("migrates the legacy one-share demo portfolio to ten shares", () => {
    const legacy = INITIAL_HOLDINGS.map((holding) => ({
      ...holding,
      quantity: 1,
    }));

    const parsed = parseStoredHoldings(JSON.stringify(legacy));

    expect(parsed).not.toBeNull();
    expect(parsed?.every((holding) => holding.quantity === 10)).toBe(true);
  });

  it("does not rewrite a user-created portfolio", () => {
    const custom = [{
      code: "005930",
      name: "삼성전자",
      quantity: 1,
      riskLevel: "pending",
    }];

    expect(parseStoredHoldings(JSON.stringify(custom))?.[0].quantity).toBe(1);
  });
});
