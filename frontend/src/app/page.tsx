"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import AddStockModal from '@/components/AddStockModal';
import IssueAnalysisModal from '@/components/IssueAnalysisModal';

export default function HomePage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isIssueModalOpen, setIsIssueModalOpen] = useState(false);
  const [selectedIssueStock, setSelectedIssueStock] = useState("035420");
  const [expandedStock, setExpandedStock] = useState<string | null>('naver');

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
                종목 추가하기
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
              
              {/* Item 1: NAVER */}
              <div className={`bg-surface border border-outline-variant rounded-2xl transition-all hover:border-primary group ${expandedStock === 'naver' ? 'expanded' : ''}`}>
                <div className="grid grid-cols-12 items-center px-lg py-lg cursor-pointer" onClick={() => toggleExpand('naver')}>
                  <div className="col-span-4 flex items-center gap-md">
                    <div className="h-10 w-10 rounded-lg bg-surface-container-low flex items-center justify-center font-bold text-primary">N</div>
                    <div>
                      <Link href={`/stock/035420`} className="hover:underline">
                        <h3 className="font-title-sm text-md font-bold">NAVER</h3>
                      </Link>
                      <span className="text-xs text-outline font-body-sm">035420</span>
                    </div>
                  </div>
                  <div className="col-span-3 text-right font-title-sm text-sm font-bold">185,200원</div>
                  <div className="col-span-2 text-right font-title-sm text-sm text-error">-1.2%</div>
                  <div className="col-span-3 flex justify-end items-center gap-md">
                    <span className="bg-error-container text-on-error-container text-[11px] font-bold px-sm py-xs rounded-lg uppercase tracking-wider">핵심 위험</span>
                    <span className="material-symbols-outlined text-outline transition-transform expand-icon">expand_more</span>
                  </div>
                </div>
                
                <div className="expandable-content border-t border-outline-variant bg-surface-container-low rounded-b-2xl">
                  <div className="p-lg">
                    <div className="flex justify-between items-center mb-md">
                      <h4 className="font-title-sm text-sm font-bold text-on-surface">분석된 주요 이슈</h4>
                    </div>
                    <div className="space-y-sm">
                      <div className="bg-surface p-md rounded-xl border border-outline-variant flex justify-between items-center">
                        <div className="flex items-center gap-lg">
                          <span className="text-xs font-bold text-outline w-20">노동 분쟁</span>
                          <span className="text-sm font-bold">노조 파업 선언</span>
                        </div>
                        <div className="flex items-center gap-xl">
                          <span className="text-xs text-outline">2024.05.20</span>
                          <span className="text-xs font-bold text-error">High Risk</span>
                        </div>
                        <button onClick={() => { setSelectedIssueStock("035420"); setIsIssueModalOpen(true); }} className="text-primary font-label-caps text-[11px] flex items-center gap-xs hover:underline ml-md">
                          연관 과거 이슈 보기
                          <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                        </button>
                      </div>
                      <div className="bg-surface p-md rounded-xl border border-outline-variant flex justify-between items-center">
                        <div className="flex items-center gap-lg">
                          <span className="text-xs font-bold text-outline w-20">규제 리스크</span>
                          <span className="text-sm font-bold">공정위 플랫폼법 조사</span>
                        </div>
                        <div className="flex items-center gap-xl">
                          <span className="text-xs text-outline">2024.05.18</span>
                          <span className="text-xs font-bold text-tertiary">Medium</span>
                        </div>
                        <button onClick={() => { setSelectedIssueStock("035420"); setIsIssueModalOpen(true); }} className="text-primary font-label-caps text-[11px] flex items-center gap-xs hover:underline ml-md">
                          연관 과거 이슈 보기
                          <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                        </button>
                      </div>
                      <div className="bg-surface p-md rounded-xl border border-outline-variant flex justify-between items-center">
                        <div className="flex items-center gap-lg">
                          <span className="text-xs font-bold text-outline w-20">수익성</span>
                          <span className="text-sm font-bold">광고 부문 성장 둔화 우려</span>
                        </div>
                        <div className="flex items-center gap-xl">
                          <span className="text-xs text-outline">2024.05.15</span>
                          <span className="text-xs font-bold text-tertiary">Medium</span>
                        </div>
                        <button onClick={() => { setSelectedIssueStock("035420"); setIsIssueModalOpen(true); }} className="text-primary font-label-caps text-[11px] flex items-center gap-xs hover:underline ml-md">
                          연관 과거 이슈 보기
                          <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Item 2: 라인 */}
              <div className={`bg-surface border border-outline-variant rounded-2xl transition-all hover:border-primary group ${expandedStock === 'line' ? 'expanded' : ''}`}>
                <div className="grid grid-cols-12 items-center px-lg py-lg cursor-pointer" onClick={() => toggleExpand('line')}>
                  <div className="col-span-4 flex items-center gap-md">
                    <div className="h-10 w-10 rounded-lg bg-[#00C300]/10 flex items-center justify-center font-bold text-[#00C300]">L</div>
                    <div>
                      <h3 className="font-title-sm text-md font-bold">라인 (LYCorp)</h3>
                      <span className="text-xs text-outline font-body-sm">4689.T</span>
                    </div>
                  </div>
                  <div className="col-span-3 text-right font-title-sm text-sm font-bold">2,450.50 JPY</div>
                  <div className="col-span-2 text-right font-title-sm text-sm text-[#00C300]">+0.8%</div>
                  <div className="col-span-3 flex justify-end items-center gap-md">
                    <span className="bg-tertiary-fixed text-on-tertiary-fixed-variant text-[11px] font-bold px-sm py-xs rounded-lg uppercase tracking-wider">주의</span>
                    <span className="material-symbols-outlined text-outline transition-transform expand-icon">expand_more</span>
                  </div>
                </div>
                <div className="expandable-content border-t border-outline-variant bg-surface-container-low rounded-b-2xl">
                  <div className="p-lg text-center text-outline font-body-sm">이슈 상세 정보를 불러오는 중입니다...</div>
                </div>
              </div>

              {/* Item 3: 삼성전자 */}
              <div className={`bg-surface border border-outline-variant rounded-2xl transition-all hover:border-primary group ${expandedStock === 'samsung' ? 'expanded' : ''}`}>
                <div className="grid grid-cols-12 items-center px-lg py-lg cursor-pointer" onClick={() => toggleExpand('samsung')}>
                  <div className="col-span-4 flex items-center gap-md">
                    <div className="h-10 w-10 rounded-lg bg-secondary-container flex items-center justify-center font-bold text-white">S</div>
                    <div>
                      <Link href={`/stock/005930`} className="hover:underline">
                        <h3 className="font-title-sm text-md font-bold">삼성전자</h3>
                      </Link>
                      <span className="text-xs text-outline font-body-sm">005930</span>
                    </div>
                  </div>
                  <div className="col-span-3 text-right font-title-sm text-sm font-bold">78,500원</div>
                  <div className="col-span-2 text-right font-title-sm text-sm text-[#00C300]">+1.5%</div>
                  <div className="col-span-3 flex justify-end items-center gap-md">
                    <span className="bg-surface-container-highest text-on-surface-variant text-[11px] font-bold px-sm py-xs rounded-lg uppercase tracking-wider">양호</span>
                    <span className="material-symbols-outlined text-outline transition-transform expand-icon">expand_more</span>
                  </div>
                </div>
                <div className="expandable-content border-t border-outline-variant bg-surface-container-low rounded-b-2xl">
                  <div className="p-lg text-center text-outline font-body-sm">이슈 상세 정보를 불러오는 중입니다...</div>
                </div>
              </div>
              
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
                    <span className="font-title-sm text-sm font-bold text-[#00C300]">+12.4%</span>
                  </div>
                </div>

                {/* Main Stats */}
                <div className="space-y-md mb-xl">
                  <div className="flex justify-between items-center py-xs border-b border-surface-container-high">
                    <span className="text-sm font-body-sm text-on-surface-variant">총 평가 금액</span>
                    <span className="text-sm font-bold">1억 2,450만원</span>
                  </div>
                  <div className="flex justify-between items-center py-xs border-b border-surface-container-high">
                    <span className="text-sm font-body-sm text-on-surface-variant">보유 종목</span>
                    <span className="text-sm font-bold">8개</span>
                  </div>
                  <div className="flex justify-between items-center py-xs">
                    <span className="text-sm font-body-sm text-on-surface-variant">위험 종목</span>
                    <span className="text-sm font-bold text-error">1개 (네이버)</span>
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
                        <circle cx="18" cy="18" fill="none" r="16" stroke="#0059b9" strokeDasharray="50 100" strokeDashoffset="0" strokeWidth="4"></circle>
                        <circle cx="18" cy="18" fill="none" r="16" stroke="#2d6fe5" strokeDasharray="30 100" strokeDashoffset="-50" strokeWidth="4"></circle>
                        <circle cx="18" cy="18" fill="none" r="16" stroke="#acc7ff" strokeDasharray="20 100" strokeDashoffset="-80" strokeWidth="4"></circle>
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-[10px] font-bold text-outline">Allocation</span>
                      </div>
                    </div>
                    <div className="flex-grow space-y-xs">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-xs">
                          <div className="h-2 w-2 rounded-full bg-[#0059b9]"></div>
                          <span className="text-xs font-body-sm">삼성전자</span>
                        </div>
                        <span className="text-xs font-bold">50%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-xs">
                          <div className="h-2 w-2 rounded-full bg-[#2d6fe5]"></div>
                          <span className="text-xs font-body-sm">라인</span>
                        </div>
                        <span className="text-xs font-bold">30%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-xs">
                          <div className="h-2 w-2 rounded-full bg-[#acc7ff]"></div>
                          <span className="text-xs font-body-sm">네이버</span>
                        </div>
                        <span className="text-xs font-bold">20%</span>
                      </div>
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
      <AddStockModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      <IssueAnalysisModal isOpen={isIssueModalOpen} onClose={() => setIsIssueModalOpen(false)} stockCode={selectedIssueStock} />
    </>
  );
}
