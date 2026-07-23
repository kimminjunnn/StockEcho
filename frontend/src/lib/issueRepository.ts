import { readFile } from "node:fs/promises";
import path from "node:path";
import type { StockIssue, StockIssuesResult } from "@/lib/issues";

interface MajorIssueRow {
  model_version: string;
  stock_code: string;
  company_name: string;
  topic_id: string;
  event_id?: string;
  event_date?: string;
  name: string;
  topic_name?: string;
  keywords: string[];
  as_of: string;
  selection_window_days: number;
  score: number;
  article_count_in_window: number;
  source_count_in_window: number;
  rank: number;
  category?: string;
  impact?: "positive" | "negative" | "neutral" | "mixed" | "unknown";
  impact_confidence?: number;
  impact_horizon?: "short_term" | "medium_term" | "long_term" | "unclear";
  impact_reason?: string;
  impact_evidence_document_ids?: string[];
  classification_method?: string;
  classification_model?: string;
  representative_article: {
    document_id: string;
    source?: string;
    title: string;
    summary?: string;
    published_at: string;
    canonical_url: string;
    source_url: string;
    relevance_confidence: number;
  };
  articles?: ArticleRow[];
}

interface ArticleRow {
  document_id: string;
  source?: string;
  title: string;
  summary?: string;
  published_at: string;
  canonical_url: string;
  source_url: string;
  relevance_confidence: number;
}

interface TopicRow {
  topic_id: string;
  events: Array<{
    event_id: string;
    event_date: string;
    articles?: ArticleRow[];
  }>;
}

function getTopicsDirectory(): string {
  const configuredRoot = process.env.STOCKECHO_DATA_ROOT;
  const dataRoot = configuredRoot
    ? path.resolve(configuredRoot)
    : path.resolve(process.cwd(), "..", "data");
  return path.join(dataRoot, "processed", "topics");
}

async function readJsonl<T>(filePath: string): Promise<T[]> {
  const content = await readFile(filePath, "utf8");
  return content
    .split("\n")
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line) as T);
}

function sourceName(urlValue: string): string {
  try {
    const hostname = new URL(urlValue).hostname.replace(/^www\./, "");
    const publishers: Array<[string, string]> = [
      ["hankyung.com", "한국경제"],
      ["yna.co.kr", "연합뉴스"],
      ["mk.co.kr", "매일경제"],
      ["donga.com", "동아일보"],
      ["chosun.com", "조선일보"],
      ["joongang.co.kr", "중앙일보"],
      ["sbs.co.kr", "SBS"],
      ["kbs.co.kr", "KBS"],
      ["mbc.co.kr", "MBC"],
      ["etnews.com", "전자신문"],
      ["zdnet.co.kr", "지디넷코리아"],
    ];
    return publishers.find(([domain]) => hostname.endsWith(domain))?.[1] ?? hostname;
  } catch {
    return "원문 기사";
  }
}

function toArticle(article: ArticleRow) {
  const articleUrl = article.canonical_url || article.source_url;
  return {
    documentId: article.document_id,
    source: article.source ?? "",
    title: article.title,
    summary: article.summary ?? "",
    publishedAt: article.published_at,
    canonicalUrl: article.canonical_url,
    sourceUrl: article.source_url,
    sourceName: sourceName(articleUrl),
    relevanceConfidence: article.relevance_confidence,
  };
}

function toIssue(row: MajorIssueRow, topic?: TopicRow): StockIssue {
  const article = row.representative_article;
  const event = topic?.events.find((candidate) => candidate.event_id === row.event_id)
    ?? topic?.events[0];
  const articleRows = row.articles ?? event?.articles ?? [article];
  const articles = articleRows.map(toArticle);
  return {
    topicId: row.topic_id,
    eventId: row.event_id ?? event?.event_id ?? `${row.topic_id}:${row.as_of}`,
    name: row.name,
    topicLabel: row.topic_name ?? row.keywords.slice(0, 2).join(" · "),
    keywords: row.keywords,
    eventDate: row.event_date ?? event?.event_date ?? article.published_at.slice(0, 10),
    articleCount: row.article_count_in_window,
    sourceCount: row.source_count_in_window,
    selectionWindowDays: row.selection_window_days,
    rank: row.rank,
    score: row.score,
    category: row.category,
    impact: row.impact ?? "unknown",
    impactConfidence: row.impact_confidence ?? 0,
    impactHorizon: row.impact_horizon ?? "unclear",
    impactReason: row.impact_reason ?? "",
    impactEvidenceDocumentIds: row.impact_evidence_document_ids ?? [],
    classificationMethod: row.classification_method ?? "rule-fallback-v1",
    classificationModel: row.classification_model ?? "",
    representativeArticle: articles[0],
    articles,
  };
}

export async function getStockIssues(
  stockCode: string,
): Promise<StockIssuesResult | null> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (supabaseUrl && publishableKey) {
    try {
      const query = new URL("/rest/v1/stock_analysis_results", supabaseUrl);
      query.searchParams.set("select", "result");
      query.searchParams.set("stock_code", `eq.${stockCode}`);
      query.searchParams.set("order", "analyzed_at.desc");
      query.searchParams.set("limit", "1");
      const response = await fetch(query, {
        headers: { apikey: publishableKey },
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Supabase returned ${response.status}`);
      }
      const rows = await response.json() as Array<{ result: StockIssuesResult }>;
      if (rows[0]?.result) return rows[0].result;
    } catch (error) {
      console.warn(`Supabase issue lookup failed for ${stockCode}; using local fallback.`, error);
    }
  }

  const directory = getTopicsDirectory();
  const issuesPath = path.join(directory, `${stockCode}_major_issues.jsonl`);
  const topicsPath = path.join(directory, `${stockCode}_topics.jsonl`);

  try {
    const [issueRows, topicRows] = await Promise.all([
      readJsonl<MajorIssueRow>(issuesPath),
      readJsonl<TopicRow>(topicsPath),
    ]);
    if (issueRows.length === 0) return null;

    const topicsById = new Map(topicRows.map((topic) => [topic.topic_id, topic]));
    const first = issueRows[0];
    return {
      stockCode: first.stock_code,
      companyName: first.company_name,
      asOf: first.as_of,
      modelVersion: first.model_version,
      issues: issueRows
        .sort((left, right) => left.rank - right.rank)
        .map((row) => toIssue(row, topicsById.get(row.topic_id))),
    };
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") return null;
    throw error;
  }
}
