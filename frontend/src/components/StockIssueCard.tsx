"use client";

import { useState } from "react";
import type { StockIssue } from "@/lib/issues";
import AllArticlesModal from "@/components/AllArticlesModal";
import IssueAnalysisModal from "@/components/IssueAnalysisModal";
import IssueArticleRow, {
  formatRelativeTime,
} from "@/components/IssueArticleRow";

interface StockIssueCardProps {
  issue: StockIssue;
  stockCode: string;
}

const impactPresentation = {
  positive: {
    label: "호재",
    className: "border-chart-up/30 bg-chart-up/10 text-chart-up",
  },
  negative: {
    label: "악재",
    className: "border-chart-down/30 bg-chart-down/10 text-chart-down",
  },
  neutral: {
    label: "중립",
    className: "border-outline-variant bg-surface-container text-on-surface-variant",
  },
  mixed: {
    label: "혼재",
    className: "border-outline-variant bg-surface-container text-on-surface-variant",
  },
  unknown: {
    label: "판단 유보",
    className: "border-outline-variant bg-surface-container text-on-surface-variant",
  },
} as const;

const IMPACT_COLOR_CONFIDENCE_THRESHOLD = 70;

const categoryKeywords = [
  ["사고·분쟁", ["리콜", "소송", "분쟁", "사고", "화재", "파업", "해킹"]],
  ["정책·규제", ["규제", "정책", "정부", "관세", "법안", "과징금"]],
  ["실적·전망", ["실적", "매출", "영업이익", "적자", "흑자", "전망", "목표가"]],
  ["수주·계약", ["수주", "계약", "공급", "납품", "파트너십", "협약"]],
  ["투자·M&A", ["투자", "인수", "합병", "지분", "매각", "유상증자"]],
  ["신제품·출시", ["출시", "공개", "신제품", "신작", "언팩", "신모델"]],
  ["경영·지배구조", ["대표이사", "임원", "이사회", "주주", "지배구조"]],
  ["기술·생산", ["기술", "개발", "생산", "공장", "공정", "양산", "hbm"]],
  ["시장·업황", ["시장", "업황", "가격", "수요", "점유율", "경쟁"]],
] as const;

function issueCategory(issue: StockIssue): string {
  if (issue.category) return issue.category;
  const searchable = [issue.name, issue.topicLabel, ...issue.keywords]
    .join(" ")
    .toLocaleLowerCase();
  return categoryKeywords.find(([, keywords]) =>
    keywords.some((keyword) => searchable.includes(keyword)),
  )?.[0] ?? "사업·전략";
}

export default function StockIssueCard({
  issue,
  stockCode,
}: StockIssueCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isAllArticlesOpen, setIsAllArticlesOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const visibleArticles = issue.articles.slice(0, 3);
  const category = issueCategory(issue);
  const confidence = Math.round((issue.impactConfidence ?? 0) * 100);
  const rawImpact = issue.impact ?? "unknown";
  const displayedImpact =
    (rawImpact === "positive" || rawImpact === "negative") &&
    confidence < IMPACT_COLOR_CONFIDENCE_THRESHOLD
      ? "unknown"
      : rawImpact;
  const impact = impactPresentation[displayedImpact];
  const badgeDescription = [
    impact.label,
    confidence > 0 ? `신뢰도 ${confidence}%` : null,
    issue.impactReason || null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <article className="rounded-xl border border-outline-variant bg-surface p-md">
      <div className="flex flex-col gap-md sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-md">
            <span
              aria-label={`${impact.label} 카테고리 ${category}`}
              title={badgeDescription}
              className={`mt-0.5 inline-flex whitespace-nowrap rounded-full border px-sm py-1 text-[11px] font-bold ${impact.className}`}
            >
              {category}
            </span>
            <div className="min-w-0 flex-1">
              <h5 className="text-sm font-bold leading-relaxed text-on-surface">
                {issue.name}
              </h5>
              <p className="mt-1 text-xs leading-relaxed text-outline">
                {formatRelativeTime(issue.representativeArticle.publishedAt)} ·
                언론사 {issue.sourceCount}곳 · 관련 기사 {issue.articleCount}건
              </p>
            </div>

            {isExpanded && (
              <div className="col-start-2 mt-md space-y-sm">
                {visibleArticles.map((article, index) => (
                  <IssueArticleRow
                    key={article.documentId}
                    article={article}
                    label={index === 0 ? "대표 기사" : `추가 기사 ${index}`}
                  />
                ))}
              </div>
            )}

            <div className="col-start-2 mt-md flex flex-wrap items-center gap-md">
              {visibleArticles.length > 0 && (
                <button
                  type="button"
                  onClick={() => setIsExpanded((current) => !current)}
                  aria-expanded={isExpanded}
                  className="group/article-toggle flex items-center gap-xs text-xs font-bold text-primary"
                >
                  <span className="material-symbols-outlined text-[16px]">
                    {isExpanded ? "expand_less" : "expand_more"}
                  </span>
                  <span className="underline-offset-4 group-hover/article-toggle:underline">
                    {isExpanded ? "관련 기사 접기" : "관련 기사 보기"}
                  </span>
                </button>
              )}
              <button
                type="button"
                onClick={() => setIsAllArticlesOpen(true)}
                className="text-xs font-bold text-on-surface-variant hover:text-primary hover:underline"
              >
                전체 기사 보기
              </button>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsHistoryOpen(true)}
          data-event-id={issue.eventId}
          data-topic-id={issue.topicId}
          className="inline-flex flex-shrink-0 self-center items-center gap-xs rounded-lg border border-primary px-sm py-xs text-xs font-bold text-primary transition-colors hover:bg-primary-fixed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          <span
            className="material-symbols-outlined text-[16px]"
            aria-hidden="true"
          >
            history
          </span>
          과거 유사 사례 분석
        </button>
      </div>

      <AllArticlesModal
        isOpen={isAllArticlesOpen}
        issue={issue}
        onClose={() => setIsAllArticlesOpen(false)}
      />
      {isHistoryOpen && (
        <IssueAnalysisModal
          isOpen
          stockCode={stockCode}
          issue={issue}
          onClose={() => setIsHistoryOpen(false)}
        />
      )}
    </article>
  );
}
