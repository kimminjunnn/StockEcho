import { describe, expect, it } from "vitest";
import { estimateHistoricalReaction } from "./historicalEstimate";
import type { HistoricalIssueEvent } from "./historicalIssues";

function event(
  eventId: string,
  d5: number | null,
  {
    similarityScore = 0.8,
    sourceCount = 2,
    abnormalD5,
  }: {
    similarityScore?: number;
    sourceCount?: number;
    abnormalD5?: number;
  } = {},
): HistoricalIssueEvent {
  return {
    rank: 1,
    eventId,
    topicId: `topic-${eventId}`,
    stockCode: "005930",
    companyName: "삼성전자",
    scope: "own_company",
    eventDate: "2025-01-01",
    name: "테스트 사건",
    keywords: ["테스트"],
    category: "기타",
    impact: "unknown",
    similarityScore,
    similarityComponents: {
      primaryCoverage: 1,
      eventCoverage: 1,
      articleCoverage: 1,
      topicContextCoverage: 1,
      contextCoverage: 1,
      keywordScore: 1,
      sectorAffinity: 1,
      categoryAffinity: null,
      impactAffinity: null,
    },
    matchedKeywords: ["테스트"],
    similarityReasons: ["테스트"],
    articleCount: 2,
    sourceCount,
    origin: "analysis_snapshot",
    representativeArticle: {
      documentId: "document",
      source: "source",
      title: "title",
      summary: "",
      publishedAt: "2025-01-01T00:00:00Z",
      canonicalUrl: "https://example.com",
      sourceUrl: "https://example.com",
      sourceName: "example",
      relevanceConfidence: 1,
    },
    articles: [],
    priceReaction: {
      status: d5 === null ? "unavailable" : "complete",
      reason: null,
      baseDate: "2025-01-01",
      baseClose: 100,
      returns: { d1: null, d5, d20: null },
      abnormalReturns: {
        d1: null,
        d5: abnormalD5 ?? null,
        d20: null,
      },
      comparisonDates: { d1: null, d5: "2025-01-08", d20: null },
    },
  };
}

describe("historical reaction estimate", () => {
  it("returns an explicit unavailable state without observed prices", () => {
    const result = estimateHistoricalReaction([event("one", null)], "d5");

    expect(result.status).toBe("unavailable");
    expect(result.expectedReturnPercent).toBeNull();
    expect(result.direction).toBe("unknown");
  });

  it("uses the weighted median and exposes low-sample uncertainty", () => {
    const result = estimateHistoricalReaction([
      event("negative", -8, { similarityScore: 0.4 }),
      event("positive", 5, { similarityScore: 0.9, sourceCount: 4 }),
    ], "d5");

    expect(result.status).toBe("available");
    expect(result.expectedReturnPercent).toBe(5);
    expect(result.returnRange.p10).toBe(-8);
    expect(result.returnRange.p90).toBe(5);
    expect(result.confidence).toBe("insufficient");
    expect(result.lossProbability).toBeGreaterThan(0);
    expect(result.lossProbability).toBeLessThan(1);
  });

  it("prefers market-adjusted returns when present", () => {
    const result = estimateHistoricalReaction([
      event("one", 8, { abnormalD5: 3 }),
    ], "d5");

    expect(result.expectedReturnPercent).toBe(3);
    expect(result.returnBasis).toBe("abnormal");
  });
});
