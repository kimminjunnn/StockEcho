"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  HistoricalIssueAnalysis,
  HistoricalIssueApiResponse,
  HistoricalIssueEvent,
} from "@/lib/historicalIssues";
import type { StockIssue } from "@/lib/issues";

interface IssueAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  stockCode: string;
  issue: StockIssue;
}

type AnalysisState =
  | { status: "idle" | "loading"; data: null; error: null }
  | { status: "ready"; data: HistoricalIssueAnalysis; error: null }
  | { status: "error"; data: null; error: string };

type HorizonKey = "d1" | "d5" | "d15" | "d30";

const horizonOptions: ReadonlyArray<{
  key: HorizonKey;
  label: string;
  points: ReadonlyArray<HorizonKey>;
}> = [
  { key: "d1", label: "1일", points: ["d1"] },
  { key: "d5", label: "5일", points: ["d1", "d5"] },
  { key: "d15", label: "15일", points: ["d1", "d5", "d15"] },
  { key: "d30", label: "30일", points: ["d1", "d5", "d15", "d30"] },
];

const seriesColors = ["#3182F6", "#8B95A1", "#B0B8C1", "#D1D6DB"];

function formatPercent(value: number | null): string {
  if (value === null) return "관측값 없음";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatDate(value: string): string {
  const [year, month, day] = value.split("-");
  return `${year}.${month}.${day}`;
}

function returnColor(value: number | null): string {
  if (value === null) return "text-outline";
  if (value > 0) return "text-chart-up";
  if (value < 0) return "text-chart-down";
  return "text-on-surface";
}

function articleUrl(event: HistoricalIssueEvent): string | null {
  return (
    event.representativeArticle.canonicalUrl
    || event.representativeArticle.sourceUrl
    || null
  );
}

function EventEvidence({
  event,
  selected,
  onSelect,
  variant,
}: {
  event: HistoricalIssueEvent;
  selected: boolean;
  onSelect: () => void;
  variant: "timeline" | "card";
}) {
  const url = articleUrl(event);

  if (variant === "timeline") {
    return (
      <article className="relative border-l-2 border-primary-fixed pb-md pl-md last:pb-0">
        <span
          aria-hidden="true"
          className="absolute -left-[7px] top-1 h-3 w-3 rounded-full border-2 border-surface-container-low bg-primary"
        />
        <button
          type="button"
          onClick={onSelect}
          aria-pressed={selected}
          className={`w-full rounded-xl px-sm py-xs text-left transition-colors ${
            selected ? "bg-primary-fixed/70" : "hover:bg-surface-container"
          }`}
        >
          <div className="flex items-start justify-between gap-sm">
            <div className="min-w-0">
              <p className="text-xs font-bold text-outline">
                {formatDate(event.eventDate)}
              </p>
              <p className="mt-xs text-sm font-bold leading-snug text-on-surface">
                {event.name}
              </p>
            </div>
            <span className="shrink-0 text-base font-extrabold text-primary">
              {Math.round(event.similarityScore * 100)}%
            </span>
          </div>
          <p className="mt-xs line-clamp-2 text-xs leading-relaxed text-on-surface-variant">
            {event.similarityReasons.join(" · ")}
          </p>
          <p className="mt-xs text-[11px] text-outline">
            원문 {event.sourceCount}곳 · 관련 기사 {event.articleCount}건
          </p>
        </button>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="ml-sm mt-xs block truncate text-[11px] font-bold text-primary hover:underline"
          >
            대표 기사 보기
          </a>
        )}
      </article>
    );
  }

  return (
    <article
      className={`rounded-xl border bg-surface transition-colors ${
        selected
          ? "border-primary ring-1 ring-primary/20"
          : "border-outline-variant hover:border-primary/40"
      }`}
    >
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        className="w-full p-md text-left"
      >
        <div className="flex items-start gap-sm">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-fixed text-primary">
            <span className="material-symbols-outlined text-xl" aria-hidden="true">
              factory
            </span>
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-sm">
              <div className="min-w-0">
                <p className="truncate text-sm font-extrabold text-on-surface">
                  {event.companyName}
                </p>
                <p className="mt-0.5 text-[11px] text-outline">
                  {formatDate(event.eventDate)} · 원문 {event.sourceCount}곳
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-xl font-extrabold text-primary">
                  {Math.round(event.similarityScore * 100)}%
                </p>
                <p className="text-[10px] text-outline">유사도</p>
              </div>
            </div>
            <p className="mt-sm line-clamp-2 text-xs font-bold leading-relaxed text-on-surface-variant">
              {event.name}
            </p>
            <p className="mt-xs line-clamp-2 text-[11px] leading-relaxed text-outline">
              {event.similarityReasons.join(" · ")}
            </p>
          </div>
        </div>
      </button>
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="mx-md mb-sm block truncate border-t border-outline-variant pt-sm text-[11px] font-bold text-primary hover:underline"
        >
          대표 기사: {event.representativeArticle.title}
        </a>
      )}
    </article>
  );
}

function ResultLayout({
  analysis,
  issue,
  selectedHorizon,
  setSelectedHorizon,
  selectedEventId,
  setSelectedEventId,
  onClose,
}: {
  analysis: HistoricalIssueAnalysis;
  issue: StockIssue;
  selectedHorizon: HorizonKey;
  setSelectedHorizon: (value: HorizonKey) => void;
  selectedEventId: string;
  setSelectedEventId: (value: string) => void;
  onClose: () => void;
}) {
  const ownEvents = analysis.events.filter(
    (event) => event.scope === "own_company",
  );
  const otherEvents = analysis.events.filter(
    (event) => event.scope === "other_company",
  );
  const activeHorizon = horizonOptions.find(
    (option) => option.key === selectedHorizon,
  ) ?? horizonOptions[0];

  const chartData = useMemo(() => {
    const points = [
      { key: "base", label: "D-0 (발생일)" },
      ...activeHorizon.points.map((key) => ({
        key,
        label: `D+${key.slice(1)}`,
      })),
    ];
    return points.map((point) => {
      const row: Record<string, string | number | null> = {
        period: point.label,
      };
      analysis.events.forEach((event, index) => {
        row[`event${index}`] =
          point.key === "base"
            ? 0
            : event.priceReaction.returns[point.key as HorizonKey];
      });
      return row;
    });
  }, [activeHorizon.points, analysis.events]);

  const selectedValues = analysis.events
    .map((event) => event.priceReaction.returns[selectedHorizon])
    .filter((value): value is number => value !== null);
  const averageReturn =
    selectedValues.length > 0
      ? selectedValues.reduce((sum, value) => sum + value, 0)
        / selectedValues.length
      : null;

  return (
    <div className="relative block lg:grid lg:min-h-0 lg:flex-1 lg:grid-cols-[42%_58%]">
      <button
        type="button"
        onClick={onClose}
        aria-label="과거 유사 이슈 분석 닫기"
        className="absolute right-md top-md z-10 rounded-full p-xs text-outline transition-colors hover:bg-surface-container hover:text-on-surface lg:hidden"
      >
        <span className="material-symbols-outlined text-3xl">close</span>
      </button>

      <aside className="bg-[#F8F9FD] px-lg py-xl lg:min-h-0 lg:overflow-y-auto lg:border-r lg:border-outline-variant">
        <p className="text-[11px] font-extrabold tracking-[0.12em] text-[#F04452]">
          AI ISSUE ANALYSIS
        </p>
        <h2
          id="historical-analysis-title"
          className="mt-xs text-3xl font-black leading-tight tracking-tight text-on-surface"
        >
          {issue.name}
        </h2>
        <div className="mt-md flex flex-wrap gap-sm">
          <span className="rounded-full bg-surface-container px-sm py-xs text-xs text-on-surface-variant">
            사건 발생일: {formatDate(issue.eventDate)}
          </span>
          <span className="rounded-full bg-primary-fixed px-sm py-xs text-xs font-bold text-on-primary-fixed-variant">
            {issue.topicLabel}
          </span>
        </div>

        <section className="mt-xl">
          <h3 className="text-xl font-black text-on-surface">자사 과거 유사 이슈</h3>
          <div className="mt-md">
            {ownEvents.length > 0 ? (
              <div className="space-y-sm">
                {ownEvents.map((event) => (
                  <EventEvidence
                    key={event.eventId}
                    event={event}
                    selected={selectedEventId === event.eventId}
                    onSelect={() => setSelectedEventId(event.eventId)}
                    variant="timeline"
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-outline-variant bg-surface/70 p-md text-xs leading-relaxed text-outline">
                관련도·유사도·복수 출처 기준을 통과한 자사 과거 사례가 없습니다.
              </div>
            )}
          </div>
        </section>

        <section className="mt-xl">
          <div className="flex items-end justify-between gap-sm">
            <h3 className="text-xl font-black leading-tight text-on-surface">
              유사 종목의
              <br />
              비슷한 과거 이슈
            </h3>
            <span className="pb-1 text-xs text-outline">
              {otherEvents.length}건 분석
            </span>
          </div>
          <div className="mt-md space-y-sm">
            {otherEvents.length > 0 ? (
              otherEvents.map((event) => (
                <EventEvidence
                  key={event.eventId}
                  event={event}
                  selected={selectedEventId === event.eventId}
                  onSelect={() => setSelectedEventId(event.eventId)}
                  variant="card"
                />
              ))
            ) : (
              <div className="rounded-xl border border-dashed border-outline-variant bg-surface/70 p-md text-xs leading-relaxed text-outline">
                품질 기준을 통과한 다른 종목의 과거 사례가 없습니다.
              </div>
            )}
          </div>
        </section>
      </aside>

      <main className="relative bg-surface px-lg py-xl lg:min-h-0 lg:overflow-y-auto">
        <button
          type="button"
          onClick={onClose}
          aria-label="과거 유사 이슈 분석 닫기"
          className="absolute right-lg top-lg hidden rounded-full p-xs text-outline transition-colors hover:bg-surface-container hover:text-on-surface lg:block"
        >
          <span className="material-symbols-outlined text-3xl">close</span>
        </button>

        <div className="pr-12">
          <h3 className="text-xl font-black text-on-surface">
            과거 이슈 · 주가 변동 비교
          </h3>
          <div className="mt-md flex flex-wrap gap-xs" role="tablist" aria-label="비교 거래일">
            {horizonOptions.map((option) => (
              <button
                key={option.key}
                type="button"
                role="tab"
                aria-selected={selectedHorizon === option.key}
                onClick={() => setSelectedHorizon(option.key)}
                className={`rounded-lg px-md py-sm text-sm font-bold transition-colors ${
                  selectedHorizon === option.key
                    ? "bg-primary text-on-primary shadow-sm"
                    : "text-on-surface-variant hover:bg-surface-container"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {analysis.completeness !== "complete" && (
          <div className="mt-md rounded-xl border border-warning/25 bg-warning/10 px-md py-sm text-xs leading-relaxed text-on-surface-variant">
            품질 기준을 통과한 사례와 실제 관측 가격만 표시합니다. 부족한 값은
            추정하지 않았습니다.
          </div>
        )}

        <div className="mt-lg grid min-h-[390px] grid-cols-1 gap-md sm:grid-cols-[88px_minmax(0,1fr)]">
          <div className="grid grid-cols-2 gap-xs sm:flex sm:flex-col sm:justify-center">
            <button
              type="button"
              onClick={() => setSelectedEventId("all")}
              aria-pressed={selectedEventId === "all"}
              className={`rounded-lg border px-sm py-sm text-xs font-bold transition-colors ${
                selectedEventId === "all"
                  ? "border-primary bg-primary text-on-primary shadow-sm"
                  : "border-outline-variant bg-surface text-on-surface-variant"
              }`}
            >
              전체
            </button>
            {analysis.events.map((event, index) => (
              <button
                key={event.eventId}
                type="button"
                onClick={() => setSelectedEventId(event.eventId)}
                aria-pressed={selectedEventId === event.eventId}
                title={`${event.companyName} · ${event.name}`}
                className={`truncate rounded-lg border px-sm py-sm text-xs font-bold transition-colors ${
                  selectedEventId === event.eventId
                    ? "border-primary bg-primary text-on-primary shadow-sm"
                    : "border-outline-variant bg-surface text-on-surface-variant hover:border-primary/40"
                }`}
              >
                {event.scope === "own_company"
                  ? "자사"
                  : event.companyName || `사례 ${index + 1}`}
              </button>
            ))}
          </div>

          <div className="min-w-0">
            <ResponsiveContainer width="100%" height={360}>
              <LineChart
                data={chartData}
                margin={{ top: 30, right: 18, bottom: 16, left: 0 }}
              >
                <CartesianGrid
                  stroke="#E5E8EB"
                  strokeDasharray="4 5"
                  vertical={false}
                />
                <XAxis
                  dataKey="period"
                  tick={{ fill: "#6B7684", fontSize: 11 }}
                  axisLine={{ stroke: "#B0B8C1" }}
                  tickLine={false}
                  interval={0}
                />
                <YAxis
                  tick={{ fill: "#8B95A1", fontSize: 11 }}
                  tickFormatter={(value: number) => `${value}%`}
                  axisLine={false}
                  tickLine={false}
                  width={46}
                />
                <Tooltip
                  formatter={(value) =>
                    typeof value === "number"
                      ? [`${value > 0 ? "+" : ""}${value.toFixed(2)}%`, "수익률"]
                      : ["관측값 없음", "수익률"]
                  }
                  contentStyle={{
                    borderRadius: 12,
                    border: "1px solid #D1D6DB",
                    boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
                    fontSize: 12,
                  }}
                />
                <ReferenceLine y={0} stroke="#8B95A1" />
                {analysis.events.map((event, index) => {
                  const isSelected =
                    selectedEventId === "all"
                    || selectedEventId === event.eventId;
                  const color =
                    selectedEventId === "all"
                      ? seriesColors[index % seriesColors.length]
                      : isSelected
                        ? "#3182F6"
                        : "#D1D6DB";
                  return (
                    <Line
                      key={event.eventId}
                      type="linear"
                      dataKey={`event${index}`}
                      name={`${event.companyName} · ${formatDate(event.eventDate)}`}
                      stroke={color}
                      strokeWidth={isSelected ? 3 : 1.5}
                      strokeOpacity={isSelected ? 1 : 0.55}
                      dot={{ r: isSelected ? 4 : 2, fill: color }}
                      activeDot={{ r: 6 }}
                      connectNulls={false}
                      isAnimationActive={false}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
            <div className="mt-sm flex flex-wrap justify-center gap-x-md gap-y-xs">
              {analysis.events.map((event, index) => (
                <span
                  key={event.eventId}
                  className="inline-flex items-center gap-xs text-[11px] text-outline"
                >
                  <span
                    className="h-0.5 w-4 rounded-full"
                    style={{
                      backgroundColor:
                        selectedEventId === "all"
                          ? seriesColors[index % seriesColors.length]
                          : selectedEventId === event.eventId
                            ? "#3182F6"
                            : "#D1D6DB",
                    }}
                  />
                  {event.companyName} {formatDate(event.eventDate)}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-lg grid gap-sm sm:grid-cols-3">
          <div className="rounded-xl border border-outline-variant bg-[#FAFAFE] px-md py-md text-center">
            <p className="text-xs font-bold text-outline">
              {activeHorizon.label} 평균 수익률
            </p>
            <p className={`mt-xs text-2xl font-black ${returnColor(averageReturn)}`}>
              {formatPercent(averageReturn)}
            </p>
          </div>
          <div className="rounded-xl border border-outline-variant bg-[#FAFAFE] px-md py-md text-center">
            <p className="text-xs font-bold text-outline">가격 관측 사례</p>
            <p className="mt-xs text-2xl font-black text-on-surface">
              {selectedValues.length}
              <span className="text-base text-outline">/{analysis.events.length}건</span>
            </p>
          </div>
          <div className="rounded-xl border border-outline-variant bg-[#FAFAFE] px-md py-md text-center">
            <p className="text-xs font-bold text-outline">복수 출처 검증 사례</p>
            <p className="mt-xs text-2xl font-black text-primary">
              {analysis.events.filter((event) => event.sourceCount >= 2).length}건
            </p>
          </div>
        </div>

        <div className="mt-md rounded-xl bg-surface-container-low px-md py-sm text-[11px] leading-relaxed text-on-surface-variant">
          {analysis.cacheHit
            ? "동일 요청의 저장된 분석 결과를 사용했습니다."
            : analysis.search.naverBackfillUsed
              ? `저장 Event가 부족해 NAVER 보충 검색을 ${analysis.search.naverCallCount}회 실행했습니다.`
              : "Supabase에 저장된 Event에서 품질 기준을 통과한 사례를 찾았습니다."}
          <span className="ml-1">
            NAVER 검색어: {analysis.target.searchKeywords.join(" · ")}
          </span>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="mt-md w-full rounded-xl bg-primary px-md py-md text-lg font-black text-on-primary shadow-[0_10px_24px_rgba(49,130,246,0.22)] transition-colors hover:bg-primary-container"
        >
          현재 주식 상황 보러 가기
        </button>

        <div className="mt-md border-t border-outline-variant pt-sm">
          <p className="text-[11px] leading-relaxed text-on-surface-variant">
            {analysis.dataCoverageNotice}
          </p>
          <p className="mt-1 text-[10px] leading-relaxed text-outline">
            그래프는 실제로 확보된 거래일 관측점만 연결합니다. 과거 수익률은
            미래 수익률을 보장하거나 매수·매도를 권유하지 않습니다.
          </p>
        </div>
      </main>
    </div>
  );
}

function LoadingLayout({
  issue,
  onClose,
}: {
  issue: StockIssue;
  onClose: () => void;
}) {
  return (
    <div className="relative block min-h-[620px] flex-1 lg:grid lg:grid-cols-[42%_58%]">
      <button
        type="button"
        onClick={onClose}
        aria-label="과거 유사 이슈 분석 닫기"
        className="absolute right-lg top-lg z-10 rounded-full p-xs text-outline transition-colors hover:bg-surface-container hover:text-on-surface"
      >
        <span className="material-symbols-outlined text-3xl">close</span>
      </button>

      <aside className="bg-[#F8F9FD] px-lg py-xl lg:border-r lg:border-outline-variant">
        <p className="text-[11px] font-extrabold tracking-[0.12em] text-[#F04452]">
          AI ISSUE ANALYSIS
        </p>
        <h2
          id="historical-analysis-title"
          className="mt-xs w-full break-keep pr-xl text-3xl font-black leading-tight tracking-tight text-on-surface"
        >
          {issue.name}
        </h2>
        <div className="mt-md flex w-full flex-wrap gap-sm">
          <span className="rounded-full bg-surface-container px-sm py-xs text-xs text-on-surface-variant">
            사건 발생일: {formatDate(issue.eventDate)}
          </span>
          <span className="rounded-full bg-primary-fixed px-sm py-xs text-xs font-bold text-on-primary-fixed-variant">
            {issue.topicLabel}
          </span>
        </div>

        <div className="mt-xl space-y-xl" aria-hidden="true">
          <section>
            <div className="h-6 w-40 animate-pulse rounded-md bg-surface-container-high" />
            <div className="mt-md border-l-2 border-primary-fixed pl-md">
              <div className="h-3 w-24 animate-pulse rounded bg-surface-container-high" />
              <div className="mt-sm h-4 w-4/5 animate-pulse rounded bg-surface-container-high" />
              <div className="mt-xs h-3 w-full animate-pulse rounded bg-surface-container" />
              <div className="mt-xs h-3 w-3/4 animate-pulse rounded bg-surface-container" />
            </div>
          </section>
          <section>
            <div className="h-6 w-52 animate-pulse rounded-md bg-surface-container-high" />
            <div className="mt-md space-y-sm">
              {[0, 1].map((item) => (
                <div
                  key={item}
                  className="rounded-xl border border-outline-variant bg-surface p-md"
                >
                  <div className="flex items-center gap-sm">
                    <div className="h-10 w-10 shrink-0 animate-pulse rounded-lg bg-primary-fixed" />
                    <div className="min-w-0 flex-1">
                      <div className="h-4 w-24 animate-pulse rounded bg-surface-container-high" />
                      <div className="mt-sm h-3 w-full animate-pulse rounded bg-surface-container" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </aside>

      <main className="flex min-h-[420px] min-w-0 items-center justify-center bg-surface px-lg py-xl">
        <div className="flex w-full max-w-[520px] flex-col items-center text-center">
          <div
            aria-hidden="true"
            className="h-12 w-12 shrink-0 animate-spin rounded-full border-4 border-primary-fixed border-t-primary"
          />
          <p className="mt-lg w-full break-keep text-lg font-black text-on-surface">
            저장된 Event를 먼저 확인하고 있습니다
          </p>
          <p className="mt-sm w-full break-keep text-sm leading-relaxed text-outline">
            저장된 사례가 부족한 경우에만 NAVER 유사도순 검색을 진행하고,
            실제 거래일 가격을 연결합니다.
          </p>
          <div className="mt-lg flex w-full flex-wrap items-center justify-center gap-xs text-[11px] font-bold text-on-surface-variant">
            <span className="rounded-full bg-surface-container-low px-sm py-xs">
              저장 Event 확인
            </span>
            <span aria-hidden="true" className="text-outline">→</span>
            <span className="rounded-full bg-surface-container-low px-sm py-xs">
              필요 시 NAVER 보충
            </span>
            <span aria-hidden="true" className="text-outline">→</span>
            <span className="rounded-full bg-surface-container-low px-sm py-xs">
              거래일 가격 연결
            </span>
          </div>
          <p className="mt-lg w-full break-keep text-[11px] leading-relaxed text-outline">
            첫 요청은 잠시 걸릴 수 있으며, 동일 요청은 저장된 결과를 사용합니다.
          </p>
        </div>
      </main>
    </div>
  );
}

export default function IssueAnalysisModal({
  isOpen,
  onClose,
  stockCode,
  issue,
}: IssueAnalysisModalProps) {
  const [state, setState] = useState<AnalysisState>({
    status: "loading",
    data: null,
    error: null,
  });
  const [requestVersion, setRequestVersion] = useState(0);
  const [selectedHorizon, setSelectedHorizon] = useState<HorizonKey>("d1");
  const [selectedEventId, setSelectedEventId] = useState("all");

  const loadAnalysis = useCallback(
    async (signal: AbortSignal): Promise<AnalysisState | null> => {
      try {
        const response = await fetch(
          `/api/stocks/${stockCode}/historical-issues`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              topicId: issue.topicId,
              eventId: issue.eventId,
              eventDate: issue.eventDate,
              name: issue.name,
              topicLabel: issue.topicLabel,
              keywords: issue.keywords,
            }),
            cache: "no-store",
            signal,
          },
        );
        const payload = (await response.json()) as HistoricalIssueApiResponse;
        if (!response.ok || !payload.success || !payload.data) {
          throw new Error(payload.error || "과거 유사 이슈를 불러오지 못했습니다.");
        }
        return { status: "ready", data: payload.data, error: null };
      } catch (error) {
        if (signal.aborted) return null;
        return {
          status: "error",
          data: null,
          error:
            error instanceof Error
              ? error.message
              : "과거 유사 이슈를 불러오지 못했습니다.",
        };
      }
    },
    [issue, stockCode],
  );

  useEffect(() => {
    if (!isOpen) return;
    const controller = new AbortController();
    void loadAnalysis(controller.signal).then((nextState) => {
      if (nextState) setState(nextState);
    });
    return () => controller.abort();
  }, [isOpen, loadAnalysis, requestVersion]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="historical-analysis-title"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-[#17191F]/55 p-sm backdrop-blur-[2px] sm:p-lg"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="flex max-h-[94vh] min-h-[620px] w-full max-w-[1320px] flex-col overflow-y-auto rounded-[28px] bg-surface shadow-[0_32px_90px_rgba(0,0,0,0.25)] lg:overflow-hidden">
        {state.status === "loading" ? (
          <LoadingLayout issue={issue} onClose={onClose} />
        ) : state.status === "ready" && state.data.events.length > 0 ? (
          <ResultLayout
            analysis={state.data}
            issue={issue}
            selectedHorizon={selectedHorizon}
            setSelectedHorizon={setSelectedHorizon}
            selectedEventId={selectedEventId}
            setSelectedEventId={setSelectedEventId}
            onClose={onClose}
          />
        ) : (
          <div className="relative flex min-h-[620px] flex-1 flex-col items-center justify-center px-lg py-xl text-center">
            <button
              type="button"
              onClick={onClose}
              aria-label="과거 유사 이슈 분석 닫기"
              className="absolute right-lg top-lg rounded-full p-xs text-outline hover:bg-surface-container"
            >
              <span className="material-symbols-outlined text-3xl">close</span>
            </button>

            <p className="text-[11px] font-extrabold tracking-[0.12em] text-[#F04452]">
              AI ISSUE ANALYSIS
            </p>
            <h2
              id="historical-analysis-title"
              className="mt-xs w-full max-w-[672px] break-keep text-3xl font-black text-on-surface"
            >
              {issue.name}
            </h2>

            {state.status === "error" && (
              <>
                <span className="material-symbols-outlined mt-xl text-4xl text-error">
                  error
                </span>
                <p className="mt-md font-bold text-on-surface">분석에 실패했습니다</p>
                <p className="mt-xs w-full max-w-[448px] break-keep text-sm text-outline">
                  {state.error}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setState({ status: "loading", data: null, error: null });
                    setRequestVersion((version) => version + 1);
                  }}
                  className="mt-md rounded-lg bg-primary px-md py-sm text-sm font-bold text-on-primary"
                >
                  다시 시도
                </button>
              </>
            )}

            {state.status === "ready" && state.data.events.length === 0 && (
              <>
                <span className="material-symbols-outlined mt-xl text-4xl text-outline">
                  search_off
                </span>
                <p className="mt-md font-bold text-on-surface">
                  충분한 과거 사례가 없습니다
                </p>
                <p className="mt-xs w-full max-w-[448px] break-keep text-sm leading-relaxed text-outline">
                  관련도·유사도·서로 다른 원문 출처 2곳 기준을 낮춰 억지로
                  사례 수를 채우지 않았습니다.
                </p>
                <p className="mt-md w-full max-w-[512px] break-keep text-[11px] leading-relaxed text-outline">
                  {state.data.dataCoverageNotice}
                </p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
