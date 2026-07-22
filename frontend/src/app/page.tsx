"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import AddStockModal from '@/components/AddStockModal';
import StockIssueCard from '@/components/StockIssueCard';
import type { StockIssuesApiResponse, StockIssuesState } from '@/lib/issues';
import { HOLDINGS_STORAGE_KEY, INITIAL_HOLDINGS, parseStoredHoldings, type Holding } from '@/lib/portfolio';

const ALLOCATION_COLORS = ['#0059b9', '#2d6fe5', '#acc7ff'];

function analysisPresentation(state: StockIssuesState | undefined, isDomestic: boolean) {
  if (!isDomestic) {
    return { label: '지원 대상 아님', className: 'bg-surface-container-highest text-outline' };
  }
  if (!state || state.status === 'loading') {
    return { label: '분석 중', className: 'bg-primary-fixed text-on-primary-fixed-variant' };
  }
  if (state.status === 'ready') {
    return { label: `주요 이슈 ${state.data.issues.length}건`, className: 'bg-primary-fixed text-on-primary-fixed-variant' };
  }
  if (state.status === 'error') {
    return { label: '조회 실패', className: 'bg-error-container text-on-error-container' };
  }
  return { label: '분석 데이터 없음', className: 'bg-surface-container-highest text-on-surface-variant' };
}

function formatCurrentPrice(holding: Holding) {
  const price = holding.currentPrice || 0;
  if (holding.code.endsWith('.T')) {
    return `${price.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} JPY`;
  }
  return `${price.toLocaleString('ko-KR')}원`;
}

function formatChangeRate(changeRate?: number) {
  if (changeRate === undefined) return '—';
  const sign = changeRate > 0 ? '+' : '';
  return `${sign}${changeRate.toFixed(2)}%`;
}

function getChangeRateClass(changeRate?: number) {
  if (changeRate === undefined || changeRate === 0) return 'text-outline';
  return changeRate > 0 ? 'text-chart-up' : 'text-chart-down';
}

function formatPortfolioValue(value: number) {
  if (value >= 100_000_000) {
    const eok = Math.floor(value / 100_000_000);
    const man = Math.floor((value % 100_000_000) / 10_000);
    return man > 0 ? `${eok.toLocaleString('ko-KR')}억 ${man.toLocaleString('ko-KR')}만원` : `${eok.toLocaleString('ko-KR')}억원`;
  }
  return `${Math.floor(value).toLocaleString('ko-KR')}원`;
}

export default function HomePage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [expandedStock, setExpandedStock] = useState<string | null>('035420');
  const [holdings, setHoldings] = useState<Holding[]>(INITIAL_HOLDINGS);
  const [storageReady, setStorageReady] = useState(false);
  const [issuesByCode, setIssuesByCode] = useState<Record<string, StockIssuesState>>({});
  const marketCodes = holdings
    .filter((holding) => /^\d{6}$/.test(holding.code))
    .map((holding) => holding.code)
    .join(',');
  const missingMarketCodes = holdings
    .filter((holding) => /^\d{6}$/.test(holding.code) && holding.changeRate === undefined)
    .map((holding) => holding.code)
    .join(',');

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (!active) return;
      const stored = parseStoredHoldings(window.localStorage.getItem(HOLDINGS_STORAGE_KEY));
      if (stored) setHoldings(stored);
      setStorageReady(true);
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    window.localStorage.setItem(HOLDINGS_STORAGE_KEY, JSON.stringify(holdings));
  }, [holdings, storageReady]);

  useEffect(() => {
    if (!missingMarketCodes) return;

    const abortController = new AbortController();

    const refreshMarketData = async () => {
      const updates = new Map<string, { currentPrice: number; changeRate: number }>();

      // KIS token issuance is rate-limited, so request holdings sequentially.
      for (const code of missingMarketCodes.split(',')) {
        try {
          const response = await fetch(`/api/stock/price/${code}`, { signal: abortController.signal });
          if (!response.ok) continue;

          const result = await response.json();
          const currentPrice = Number(result.data?.stck_prpr);
          const changeRate = Number(result.data?.prdy_ctrt);
          if (result.success && Number.isFinite(currentPrice) && Number.isFinite(changeRate)) {
            updates.set(code, { currentPrice, changeRate });
          }
        } catch (error) {
          if (abortController.signal.aborted) return;
          console.error(`Failed to refresh market data for ${code}:`, error);
        }
      }

      if (abortController.signal.aborted || updates.size === 0) return;
      setHoldings((currentHoldings) => currentHoldings.map((holding) => {
        const update = updates.get(holding.code);
        return update ? { ...holding, ...update } : holding;
      }));
    };

    refreshMarketData();
    return () => abortController.abort();
  }, [missingMarketCodes]);

  useEffect(() => {
    if (!marketCodes) return;

    const codes = marketCodes.split(',');
    const abortController = new AbortController();

    const refreshIssues = async () => {
      const entries = await Promise.all(codes.map(async (code): Promise<[string, StockIssuesState]> => {
        try {
          const response = await fetch(`/api/stocks/${code}/issues`, {
            signal: abortController.signal,
          });
          if (!response.ok) return [code, { status: 'error', data: null }];
          const payload = await response.json() as StockIssuesApiResponse;
          if (!payload.success) return [code, { status: 'error', data: null }];
          if (!payload.data) return [code, { status: 'empty', data: null }];
          return [code, { status: 'ready', data: payload.data }];
        } catch {
          return [code, { status: 'error', data: null }];
        }
      }));

      if (!abortController.signal.aborted) {
        setIssuesByCode(Object.fromEntries(entries));
      }
    };

    refreshIssues();
    return () => abortController.abort();
  }, [marketCodes]);

  const totalValuation = holdings.reduce((sum, holding) => sum + (holding.currentPrice || 0) * holding.quantity, 0);
  const analyzedHoldings = holdings.filter((holding) => issuesByCode[holding.code]?.status === 'ready');
  const allocationBase = [...holdings]
    .sort((a, b) => (b.currentPrice || 0) * b.quantity - (a.currentPrice || 0) * a.quantity)
    .slice(0, 3)
    .map((holding, index) => {
      const value = (holding.currentPrice || 0) * holding.quantity;
      const percentage = totalValuation > 0 ? (value / totalValuation) * 100 : 0;
      return { holding, percentage, color: ALLOCATION_COLORS[index] };
    });
  const allocationItems = allocationBase.map((item, index) => ({
    ...item,
    offset: allocationBase.slice(0, index).reduce((sum, previousItem) => sum + previousItem.percentage, 0),
  }));

  const toggleExpand = (stockId: string) => {
    setExpandedStock(prev => prev === stockId ? null : stockId);
  };

  return (
    <>
      <main className="max-w-container-max mx-auto px-gutter py-2xl w-full flex-grow">
        <div className="flex flex-col lg:flex-row gap-2xl">
          {/* Left Main Area */}
          <div className="w-full lg:w-2/3">
            <div className="mb-2xl">
              <h1 className="font-display-lg text-[38px] font-bold tracking-tight mb-xs">내 포트폴리오</h1>
              <p className="font-body-md text-on-surface-variant">보유한 종목의 현황과 주요 위험 요인을 분석합니다.</p>
            </div>
            
            <div className="flex justify-start mb-xl">
              <button 
                onClick={() => setIsModalOpen(true)}
                className="bg-primary text-white font-title-sm text-sm px-lg py-md rounded-2xl flex items-center gap-xs hover:bg-primary-container transition-all active:scale-95 shadow-sm"
              >
                <span className="material-symbols-outlined text-[20px]">add</span>
                종목 편집하기
              </button>
            </div>
            
            {/* Stock List Header */}
            <div className="grid grid-cols-12 px-lg py-sm font-label-caps text-outline mb-sm">
              <div className="col-span-4">종목명</div>
              <div className="col-span-3 text-right">현재가</div>
              <div className="col-span-2 text-right">등락률</div>
              <div className="col-span-3 text-right">상태</div>
            </div>
            
            {/* Stock List Items */}
            <div className="space-y-md">
              
              {holdings.length === 0 && (
                <div className="rounded-2xl border border-dashed border-outline-variant bg-surface py-2xl text-center text-sm text-outline">
                  보유 중인 종목이 없습니다. 종목 편집하기에서 추가해 주세요.
                </div>
              )}

              {holdings.map((holding) => {
                const isDomestic = /^\d{6}$/.test(holding.code);
                const issueState = issuesByCode[holding.code];
                const presentation = analysisPresentation(issueState, isDomestic);

                return (
                  <div key={holding.code} className={`bg-surface border border-outline-variant rounded-2xl transition-all hover:border-primary group ${expandedStock === holding.code ? 'expanded' : ''}`}>
                    <div
                      className="grid cursor-pointer grid-cols-12 items-center px-lg py-lg"
                      onClick={() => toggleExpand(holding.code)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          toggleExpand(holding.code);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      aria-expanded={expandedStock === holding.code}
                      aria-label={`${holding.name} 상세 ${expandedStock === holding.code ? '접기' : '펼치기'}`}
                    >
                      <div className="col-span-4 flex items-center gap-md">
                        <div className="h-10 w-10 rounded-lg bg-surface-container-low flex items-center justify-center font-bold text-primary">
                          {holding.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          {isDomestic ? (
                            <Link
                              href={`/stock/${holding.code}`}
                              onClick={(event) => event.stopPropagation()}
                              onKeyDown={(event) => event.stopPropagation()}
                              className="hover:underline"
                            >
                              <h3 className="font-title-sm text-md font-bold">{holding.name}</h3>
                            </Link>
                          ) : (
                            <h3 className="font-title-sm text-md font-bold">{holding.name}</h3>
                          )}
                          <span className="text-xs text-outline font-body-sm">{holding.code}</span>
                        </div>
                      </div>
                      <div className="col-span-3 text-right font-title-sm text-sm font-bold">{formatCurrentPrice(holding)}</div>
                      <div className={`col-span-2 text-right font-title-sm text-sm ${getChangeRateClass(holding.changeRate)}`}>{formatChangeRate(holding.changeRate)}</div>
                      <div className="col-span-3 flex justify-end items-center gap-md">
                        <span className={`${presentation.className} text-[11px] font-bold px-sm py-xs rounded-lg tracking-wider`}>{presentation.label}</span>
                        <span className="material-symbols-outlined text-outline transition-transform expand-icon">expand_more</span>
                      </div>
                    </div>
                    <div className="expandable-content border-t border-outline-variant bg-surface-container-low rounded-b-2xl">
                      <div className="expandable-inner">
                        {issueState?.status === 'ready' ? (
                          <div className="p-lg">
                            <div className="mb-md flex items-center justify-between gap-md">
                              <h4 className="font-title-sm text-sm font-bold text-on-surface">분석된 주요 이슈</h4>
                              <span className="text-[11px] text-outline">기준일 {issueState.data.asOf}</span>
                            </div>
                            <div className="space-y-sm">
                              {issueState.data.issues.map((issue) => (
                                <StockIssueCard key={issue.eventId} issue={issue} stockCode={holding.code} />
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="p-lg">
                            <p className="text-sm text-outline">
                              {!isDomestic
                                ? '현재 국내 KOSPI 지원 종목만 뉴스 분석을 제공합니다.'
                                : issueState?.status === 'loading' || !issueState
                                  ? '최신 이슈 분석 결과를 불러오는 중입니다.'
                                  : issueState.status === 'error'
                                    ? '이슈 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'
                                    : '아직 이 종목의 검증된 이슈 분석 데이터가 없습니다.'}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              
            </div>
          </div>

          {/* Right Side Panel */}
          <div className="w-full lg:w-1/3">
            <div className="sticky top-[112px] space-y-lg">
              <div className="bg-surface border border-outline-variant rounded-2xl p-lg shadow-sm">
                <h2 className="font-title-sm text-md font-bold mb-lg flex items-center gap-xs">
                  <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>analytics</span>
                  포트폴리오 요약
                </h2>
                
                {/* Mini Chart */}
                <div className="bg-surface-container-low rounded-xl h-32 mb-lg overflow-hidden relative border border-outline-variant">
                  <div className="absolute inset-x-0 bottom-4 h-full flex items-end">
                    <svg className="w-full h-full preserve-3d" preserveAspectRatio="none" viewBox="0 0 100 40">
                      <path d="M0,35 L10,30 L25,32 L40,20 L55,25 L70,10 L85,8 L100,5" fill="none" stroke="#3182F6" strokeWidth="2" vectorEffect="non-scaling-stroke"></path>
                      <path d="M0,35 L10,30 L25,32 L40,20 L55,25 L70,10 L85,8 L100,5 L100,40 L0,40 Z" fill="url(#grad)" opacity="0.1"></path>
                      <defs>
                        <linearGradient id="grad" x1="0%" x2="0%" y1="0%" y2="100%">
                          <stop offset="0%" style={{ stopColor: '#3182F6', stopOpacity: 1 }}></stop>
                          <stop offset="100%" style={{ stopColor: '#3182F6', stopOpacity: 0 }}></stop>
                        </linearGradient>
                      </defs>
                    </svg>
                  </div>
                  <div className="absolute top-md left-md flex flex-col">
                    <span className="font-label-caps text-[10px] text-outline">수익률 추이</span>
                    <span className="font-title-sm text-xs font-bold text-outline">가격 반응 분석 준비 중</span>
                  </div>
                </div>

                {/* Main Stats */}
                <div className="space-y-md mb-xl">
                  <div className="flex justify-between items-center py-xs border-b border-surface-container-high">
                    <span className="text-sm font-body-sm text-on-surface-variant">총 평가 금액</span>
                    <span className="text-sm font-bold">{formatPortfolioValue(totalValuation)}</span>
                  </div>
                  <div className="flex justify-between items-center py-xs border-b border-surface-container-high">
                    <span className="text-sm font-body-sm text-on-surface-variant">보유 종목</span>
                    <span className="text-sm font-bold">{holdings.length}개</span>
                  </div>
                  <div className="flex justify-between items-center py-xs">
                    <span className="text-sm font-body-sm text-on-surface-variant">이슈 분석 완료</span>
                    <span className="text-sm font-bold text-primary">
                      {analyzedHoldings.length}개{analyzedHoldings.length > 0 ? ` (${analyzedHoldings.map((holding) => holding.name).join(', ')})` : ''}
                    </span>
                  </div>
                </div>

                {/* Asset Allocation */}
                <div className="mb-xl">
                  <div className="flex items-center justify-between mb-sm">
                    <span className="font-label-caps text-[11px] text-outline">자산 배분</span>
                    <span className="text-xs font-bold text-primary cursor-pointer">상세보기</span>
                  </div>
                  <div className="flex items-center gap-lg">
                    <div className="relative w-24 h-24 flex-shrink-0">
                      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                        <circle cx="18" cy="18" fill="none" r="16" stroke="#f2f3fd" strokeWidth="4"></circle>
                        {allocationItems.map(({ holding, percentage, offset, color }) => (
                          <circle
                            key={holding.code}
                            cx="18"
                            cy="18"
                            fill="none"
                            r="16"
                            stroke={color}
                            strokeDasharray={`${percentage} 100`}
                            strokeDashoffset={-offset}
                            strokeWidth="4"
                          />
                        ))}
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-[10px] font-bold text-outline">Allocation</span>
                      </div>
                    </div>
                    <div className="flex-grow space-y-xs">
                      {allocationItems.length === 0 && <span className="text-xs text-outline">데이터 없음</span>}
                      {allocationItems.map(({ holding, percentage, color }) => (
                        <div key={holding.code} className="flex items-center justify-between">
                          <div className="flex min-w-0 items-center gap-xs">
                            <div className="h-2 w-2 flex-shrink-0 rounded-full" style={{ backgroundColor: color }}></div>
                            <span className="truncate text-xs font-body-sm">{holding.name}</span>
                          </div>
                          <span className="text-xs font-bold">{Math.round(percentage)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <Link href="/rebalancing" className="w-full bg-on-surface text-white font-title-sm text-sm py-md rounded-2xl hover:bg-on-surface-variant transition-all active:scale-[0.98] flex items-center justify-center text-center">
                  리밸런싱 제안 보기
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
      {isModalOpen && (
        <AddStockModal
          isOpen
          savedHoldings={holdings}
          onClose={() => setIsModalOpen(false)}
          onSave={(nextHoldings) => {
            setHoldings(nextHoldings);
            setIsModalOpen(false);
          }}
        />
      )}
    </>
  );
}
