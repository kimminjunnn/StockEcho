import type { IssueArticle } from "@/lib/issues";

interface IssueArticleRowProps {
  article: IssueArticle;
  label?: string;
}

export default function IssueArticleRow({ article, label }: IssueArticleRowProps) {
  const url = article.canonicalUrl || article.sourceUrl;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-xl border border-outline-variant bg-surface p-md transition-colors hover:border-primary hover:bg-primary-fixed/20"
    >
      {label && <p className="mb-1 text-[10px] font-bold tracking-wide text-primary">{label}</p>}
      <p className="text-sm font-bold leading-relaxed text-on-surface">{article.title}</p>
      <div className="mt-2 flex items-center gap-2 text-xs text-outline">
        <span>{article.sourceName}</span>
        <span aria-hidden="true">·</span>
        <time dateTime={article.publishedAt}>{formatRelativeTime(article.publishedAt)}</time>
      </div>
    </a>
  );
}

export function formatRelativeTime(value: string, now = new Date()): string {
  const published = new Date(value);
  const elapsedSeconds = Math.max(0, Math.floor((now.getTime() - published.getTime()) / 1000));
  if (elapsedSeconds < 60) return "방금 전";
  const minutes = Math.floor(elapsedSeconds / 60);
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}일 전`;
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium" }).format(published);
}
