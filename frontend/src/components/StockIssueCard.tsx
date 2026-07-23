"use client";

import { useState } from "react";
import type { StockIssue } from "@/lib/issues";
import AllArticlesModal from "@/components/AllArticlesModal";
import IssueAnalysisModal from "@/components/IssueAnalysisModal";
import IssueArticleRow, { formatRelativeTime } from "@/components/IssueArticleRow";

interface StockIssueCardProps {
  issue: StockIssue;
  stockCode: string;
}

export default function StockIssueCard({ issue, stockCode }: StockIssueCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isAllArticlesOpen, setIsAllArticlesOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const visibleArticles = issue.articles.slice(0, 3);

  return (
    <article className="rounded-xl border border-outline-variant bg-surface p-md">
      <div className="flex flex-col gap-md sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-md">
            <span className="mt-0.5 w-7 flex-shrink-0 text-xs font-bold text-primary">#{issue.rank}</span>
            <div className="min-w-0 flex-1">
              <h5 className="text-sm font-bold leading-relaxed text-on-surface">{issue.name}</h5>
              <p className="mt-1 text-xs leading-relaxed text-outline">
                {formatRelativeTime(issue.representativeArticle.publishedAt)} · 언론사 {issue.sourceCount}곳 · 관련 기사 {issue.articleCount}건
              </p>
            </div>
          </div>

          {isExpanded && (
            <div className="ml-10 mt-md space-y-sm">
              {visibleArticles.map((article, index) => (
                <IssueArticleRow
                  key={article.documentId}
                  article={article}
                  label={index === 0 ? "대표 기사" : `추가 기사 ${index}`}
                />
              ))}
            </div>
          )}

          <div className="ml-10 mt-md flex flex-wrap items-center gap-md">
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
