import type { IssueArticle } from "@/lib/issues";

export type PriceReactionStatus = "complete" | "partial" | "unavailable";

export interface HistoricalPriceReaction {
  status: PriceReactionStatus;
  reason: string | null;
  baseDate: string | null;
  baseClose: number | null;
  baselinePolicy?: string;
  returns: {
    d1: number | null;
    d5: number | null;
    d15: number | null;
    d30: number | null;
  };
  comparisonDates: {
    d1: string | null;
    d5: string | null;
    d15: string | null;
    d30: string | null;
  };
}

export interface HistoricalIssueEvent {
  rank: number;
  eventId: string;
  topicId: string;
  stockCode: string;
  companyName: string;
  scope: "own_company" | "other_company";
  eventDate: string;
  name: string;
  keywords: string[];
  category: string;
  impact: "positive" | "negative" | "neutral" | "mixed" | "unknown";
  similarityScore: number;
  similarityComponents: {
    primaryCoverage: number;
    eventCoverage: number;
    articleCoverage: number;
    topicContextCoverage: number;
    contextCoverage: number;
    keywordScore: number;
    sectorAffinity: number;
    categoryAffinity: number | null;
    impactAffinity: number | null;
  };
  matchedKeywords: string[];
  similarityReasons: string[];
  articleCount: number;
  sourceCount: number;
  origin: "topic_model" | "analysis_snapshot" | "naver_backfill";
  representativeArticle: IssueArticle;
  articles: IssueArticle[];
  priceReaction: HistoricalPriceReaction;
}

export interface HistoricalIssueAnalysis {
  schemaVersion: string;
  cacheKey: string;
  cacheHit: boolean;
  completeness: "complete" | "partial" | "insufficient";
  target: {
    stockCode: string;
    companyName: string;
    topicId: string;
    eventId: string;
    eventDate: string;
    name: string;
    topicLabel: string;
    keywords: string[];
    coreKeywords: string[];
    searchKeywords: string[];
    category: string;
    impact: "positive" | "negative" | "neutral" | "mixed" | "unknown";
  };
  search: {
    storedEventCount: number;
    storedMatchCount: number;
    naverBackfillUsed: boolean;
    naverCacheHit: boolean;
    naverCallCount: number;
    minimumSources: number;
    minimumSimilarity: number;
    cacheTtlHours: number;
    candidateBefore: string;
    currentEventCooldownDays: number;
  };
  events: HistoricalIssueEvent[];
  dataCoverageNotice: string;
  createdAt: string;
}

export interface HistoricalIssueRequestBody {
  topicId: string;
  eventId: string;
  eventDate: string;
  name: string;
  topicLabel: string;
  keywords: string[];
}

export interface HistoricalIssueApiResponse {
  success: boolean;
  data?: HistoricalIssueAnalysis;
  error?: string;
  errorCode?: string;
}
