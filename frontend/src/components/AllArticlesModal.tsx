"use client";

import { useEffect } from "react";
import type { StockIssue } from "@/lib/issues";
import IssueArticleRow from "@/components/IssueArticleRow";

interface AllArticlesModalProps {
  isOpen: boolean;
  issue: StockIssue;
  onClose: () => void;
}

export default function AllArticlesModal({ isOpen, issue, onClose }: AllArticlesModalProps) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center p-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="all-articles-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/55 backdrop-blur-sm"
        onClick={onClose}
        aria-label="전체 기사 모달 닫기"
      />
      <div className="relative z-10 flex max-h-[88vh] w-full max-w-[720px] flex-col overflow-hidden rounded-2xl bg-surface shadow-2xl">
        <header className="flex items-start justify-between gap-lg border-b border-outline-variant px-xl py-lg">
          <div>
            <p className="mb-1 text-xs font-bold text-primary">관련 기사 전체</p>
            <h2 id="all-articles-title" className="text-xl font-bold text-on-surface">{issue.name}</h2>
            <p className="mt-2 text-xs text-outline">관련 기사 {issue.articleCount}건 · 언론사 {issue.sourceCount}곳</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-surface-container text-outline hover:text-on-surface"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </header>
        <div className="space-y-sm overflow-y-auto bg-surface-container-low p-lg">
          {issue.articles.map((article, index) => (
            <IssueArticleRow
              key={article.documentId}
              article={article}
              label={index === 0 ? "대표 기사" : `추가 기사 ${index}`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
