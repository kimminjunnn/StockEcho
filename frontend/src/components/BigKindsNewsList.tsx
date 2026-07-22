"use client";

import React, { useEffect, useState } from 'react';

interface Article {
  id: string;
  title: string;
  content: string;
  url: string;
  date: string;
  provider: string;
}

export default function BigKindsNewsList({ stockName }: { stockName: string }) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [period, setPeriod] = useState(5); // default 5 days

  useEffect(() => {
    let active = true;
    const fetchNews = async () => {
      setLoading(true);
      setError(false);
      try {
        const res = await fetch(`/api/news?stockName=${encodeURIComponent(stockName)}&period=${period}`);
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        if (active) setArticles(data.articles || []);
      } catch (err) {
        if (active) setError(true);
      } finally {
        if (active) setLoading(false);
      }
    };
    fetchNews();
    return () => { active = false; };
  }, [stockName, period]);

  const formatDate = (dateString: string) => {
    if (dateString.length === 8) {
      return `${dateString.substring(0,4)}.${dateString.substring(4,6)}.${dateString.substring(6,8)}`;
    }
    return dateString;
  };

  return (
    <div className="mt-lg border-t border-outline-variant pt-lg">
      <div className="flex items-center justify-between mb-md">
        <h4 className="font-title-sm text-sm font-bold text-on-surface">관련 뉴스 기사 (빅카인즈)</h4>
        <select 
          value={period} 
          onChange={(e) => setPeriod(Number(e.target.value))}
          className="text-[11px] bg-surface border border-outline-variant rounded-md px-2 py-1 outline-none"
        >
          <option value={1}>최근 1일</option>
          <option value={5}>최근 5일</option>
          <option value={15}>최근 15일</option>
          <option value={30}>최근 30일</option>
        </select>
      </div>

      {loading && <p className="text-xs text-outline">뉴스를 불러오는 중...</p>}
      {error && <p className="text-xs text-error">뉴스를 불러오지 못했습니다.</p>}
      {!loading && !error && articles.length === 0 && (
        <p className="text-xs text-outline">최근 {period}일간 관련된 주요 기사가 없습니다.</p>
      )}

      {!loading && !error && articles.length > 0 && (
        <div className="space-y-sm">
          {articles.map((article) => (
            <a 
              key={article.id} 
              href={article.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="block bg-surface p-md rounded-xl border border-outline-variant hover:border-primary transition-colors"
            >
              <div className="flex justify-between items-start mb-xs">
                <h5 className="font-title-sm text-sm font-bold text-on-surface line-clamp-1 flex-grow pr-sm" dangerouslySetInnerHTML={{ __html: article.title }} />
                <span className="text-[10px] text-outline whitespace-nowrap">{formatDate(article.date)} | {article.provider}</span>
              </div>
              <p className="text-xs text-on-surface-variant line-clamp-2" dangerouslySetInnerHTML={{ __html: article.content }} />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
