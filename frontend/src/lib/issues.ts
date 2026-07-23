export interface IssueArticle {
  documentId: string;
  source: string;
  title: string;
  summary: string;
  publishedAt: string;
  canonicalUrl: string;
  sourceUrl: string;
  sourceName: string;
  relevanceConfidence: number;
}

export interface StockIssue {
  topicId: string;
  eventId: string;
  name: string;
  topicLabel: string;
  keywords: string[];
  eventDate: string;
  articleCount: number;
  sourceCount: number;
  selectionWindowDays: number;
  rank: number;
  score: number;
  category?: string;
  impact?: "positive" | "negative" | "neutral" | "mixed" | "unknown";
  impactConfidence?: number;
  impactHorizon?: "short_term" | "medium_term" | "long_term" | "unclear";
  impactReason?: string;
  impactEvidenceDocumentIds?: string[];
  classificationMethod?: string;
  classificationModel?: string;
  representativeArticle: IssueArticle;
  articles: IssueArticle[];
}

export interface StockIssuesResult {
  stockCode: string;
  companyName: string;
  asOf: string;
  modelVersion: string;
  issues: StockIssue[];
}

export interface StockIssuesApiResponse {
  success: boolean;
  data?: StockIssuesResult;
  error?: string;
}

export type StockIssuesState =
  | { status: "loading"; data: null }
  | { status: "ready"; data: StockIssuesResult }
  | { status: "empty"; data: null }
  | { status: "error"; data: null };
