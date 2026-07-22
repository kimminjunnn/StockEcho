"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

interface IssueAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  stockCode?: string;
}

interface IssueChartPoint {
  stck_clpr: string;
}

interface IssueChartResponse {
  success: boolean;
  data?: IssueChartPoint[];
}

export default function IssueAnalysisModal({ isOpen, onClose, stockCode = "035420" }: IssueAnalysisModalProps) {
  const [chartPeriod, setChartPeriod] = useState<1 | 5 | 15 | 30>(15);
  const [issueData, setIssueData] = useState<IssueChartPoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !stockCode) return;
    
    // KIS API fetching logic for past issue
    const startDt = new Date("2024-05-20");
    const endDt = new Date(startDt);
    endDt.setDate(startDt.getDate() + chartPeriod);

    const formatDate = (date: Date) => {
      const y = date.getFullYear();
      const m = String(date.getMonth() + 1).padStart(2, '0');
      const d = String(date.getDate()).padStart(2, '0');
      return `${y}${m}${d}`;
    };

    const fetchIssueData = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`/api/stock/issue-chart/${stockCode}?startDate=${formatDate(startDt)}&endDate=${formatDate(endDt)}`);
        if (res.ok) {
          const data = await res.json() as IssueChartResponse;
          if (data.success && data.data) {
            // KIS API returns data from most recent to oldest. We want chronologically from oldest (start) to newest (end)
            setIssueData([...data.data].reverse());
          }
        }
      } catch (e) {
        console.error("Issue chart fetch error:", e);
      } finally {
        setIsLoading(false);
      }
    };

    fetchIssueData();
  }, [isOpen, stockCode, chartPeriod]);

  if (!isOpen) return null;

  // Render variables for dynamic chart
  let polylinePoints = "";
  let circles: React.ReactNode[] = [];
  let endY = 70;
  let dropRateStr = "-7.47%"; 

  if (issueData.length > 0) {
    const prices = issueData.map(d => parseInt(d.stck_clpr, 10));
    const maxP = Math.max(...prices);
    const minP = Math.min(...prices);
    
    const range = (maxP - minP) || 1;
    const yMax = maxP + range * 0.1;
    const yMin = minP - range * 0.1;

    // Y maps to 20 ~ 110
    const mapY = (val: number) => 110 - ((val - yMin) / (yMax - yMin)) * 90;
    
    // X maps to 0 ~ 360
    const stepX = prices.length > 1 ? 360 / (prices.length - 1) : 360;

    const points = prices.map((p, i) => `${i * stepX},${mapY(p)}`);
    polylinePoints = points.join(" ");

    circles = prices.map((p, i) => (
      <circle key={i} cx={i * stepX} cy={mapY(p)} r="2.5" fill="#3182f6"/>
    ));
    
    endY = mapY(prices[prices.length - 1]);
    
    const dropRate = ((prices[prices.length - 1] - prices[0]) / prices[0] * 100).toFixed(2);
    dropRateStr = `${dropRate}%`;
  } else {
    polylinePoints = "0,20 50,65 90,100 150,85 210,95 270,105 360,70"; // Mock fallback
    endY = 70;
  }

  return (
    <div className="fixed inset-0 z-[100] flex justify-center items-center p-4 bg-gray-900 bg-opacity-60 backdrop-blur-sm">
      <div className="bg-white w-full max-w-[920px] rounded-[24px] shadow-2xl overflow-hidden flex flex-col relative max-h-[90vh] overflow-y-auto hide-scrollbar">
        
        <div className="flex flex-col md:flex-row w-full">
          {/* Left Column */}
          <section className="w-full md:w-[43%] p-8 md:p-9 border-b md:border-b-0 md:border-r border-gray-100 flex flex-col">
            <p className="text-[#ff3b30] font-bold text-[11px] tracking-wider mb-1">AI ISSUE ANALYSIS</p>
            <h1 className="text-[28px] font-extrabold text-[#191f28] tracking-tight mb-4">파업 선언</h1>
            
            <div className="flex items-center gap-2 mb-8">
              <span className="bg-[#f2f4f6] px-3 py-1.5 rounded-full text-[12px] text-[#6b7684] font-medium">
                사건 발생일: 2024.05.20
              </span>
              <span className="bg-[#fff0f0] px-3 py-1.5 rounded-full text-[12px] text-[#ff3b30] font-bold">
                심각도: High
              </span>
            </div>

            <div className="mb-8">
              <h2 className="text-[17px] font-bold text-[#191f28] mb-3">자사 과거 유사 이슈</h2>
              <div className="relative pl-4">
                <div className="absolute left-0 top-1.5 w-[7px] h-[7px] bg-primary rounded-full"></div>
                <p className="text-[12px] text-[#8b95a1] font-semibold mb-1">2022년 11월 14일</p>
                <p className="text-[13px] leading-relaxed text-[#4e5968]">
                  노조 전면 파업 선언에 따른 생산 라인 중단. 당시 공급망 차질 우려로 주가 급락 및 14일간의 회복기 소요.
                </p>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-3">
                <h2 className="text-[17px] font-bold text-[#191f28] leading-tight">유사 종목의<br/>비슷한 과거 이슈</h2>
                <span className="text-[11px] text-[#b0b8c1]">총 12건 분석</span>
              </div>

              <div className="space-y-2.5">
                <div className="border border-[#e5e8eb] bg-[#f9fafb] rounded-[14px] p-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-[#e8f3ff] rounded-lg flex items-center justify-center text-primary flex-shrink-0">
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[14px] text-[#191f28]">기업 A</span>
                        <span className="text-[11px] text-[#8b95a1]">반도체 부문</span>
                      </div>
                      <p className="text-[12px] text-[#4e5968] mt-0.5">‘반도체 생산 라인 가동 중단 사고’</p>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-2">
                    <p className="text-primary text-[19px] font-extrabold leading-none">92%</p>
                    <p className="text-[10px] text-[#8b95a1] mt-0.5">유사도</p>
                  </div>
                </div>

                <div className="border border-[#e5e8eb] bg-[#f9fafb] rounded-[14px] p-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-[#e8f3ff] rounded-lg flex items-center justify-center text-primary flex-shrink-0">
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[14px] text-[#191f28]">기업 B</span>
                        <span className="text-[11px] text-[#8b95a1]">디스플레이 부문</span>
                      </div>
                      <p className="text-[12px] text-[#4e5968] mt-0.5">‘공급망 차질로 인한 실적 악화 우려’</p>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-2">
                    <p className="text-primary text-[19px] font-extrabold leading-none">87%</p>
                    <p className="text-[10px] text-[#8b95a1] mt-0.5">유사도</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Right Column */}
          <section className="w-full md:w-[57%] p-8 md:p-9 flex flex-col justify-between relative">
            <button onClick={onClose} className="absolute top-6 right-6 text-[#8b95a1] hover:text-[#191f28] transition-colors">
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>

            <div>
              <div className="flex justify-between items-center mb-6 pr-8">
                <h2 className="text-[20px] font-bold text-[#191f28]">과거 이슈 - 주가 변동 비교</h2>
                <div className="flex bg-[#f2f4f6] p-1 rounded-lg">
                  <button onClick={() => setChartPeriod(1)} className={`px-3 py-1 text-[12px] font-bold rounded-md shadow-sm transition-colors ${chartPeriod === 1 ? 'bg-primary text-white' : 'text-[#6b7684] hover:bg-gray-200'}`}>1일</button>
                  <button onClick={() => setChartPeriod(5)} className={`px-3 py-1 text-[12px] font-bold rounded-md shadow-sm transition-colors ${chartPeriod === 5 ? 'bg-primary text-white' : 'text-[#6b7684] hover:bg-gray-200'}`}>5일</button>
                  <button onClick={() => setChartPeriod(15)} className={`px-3 py-1 text-[12px] font-bold rounded-md shadow-sm transition-colors ${chartPeriod === 15 ? 'bg-primary text-white' : 'text-[#6b7684] hover:bg-gray-200'}`}>15일</button>
                  <button onClick={() => setChartPeriod(30)} className={`px-3 py-1 text-[12px] font-bold rounded-md shadow-sm transition-colors ${chartPeriod === 30 ? 'bg-primary text-white' : 'text-[#6b7684] hover:bg-gray-200'}`}>30일</button>
                </div>
              </div>

              <div className="flex gap-3 items-center mb-3">
                <div className="flex flex-col gap-1.5 flex-shrink-0">
                  <span className="px-2.5 py-1 text-[10px] border border-[#e5e8eb] rounded text-[#8b95a1] text-center bg-white">Total</span>
                  <span className="px-2.5 py-1 text-[10px] bg-primary text-white font-bold rounded text-center">자사</span>
                  <span className="px-2.5 py-1 text-[10px] text-[#b0b8c1] text-center">기업 A</span>
                  <span className="px-2.5 py-1 text-[10px] text-[#b0b8c1] text-center">기업 B</span>
                  <span className="px-2.5 py-1 text-[10px] text-[#b0b8c1] text-center">기업 C</span>
                </div>

                <div className="flex-grow relative h-[160px]">
                  {isLoading && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/60 backdrop-blur-[1px]">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  )}
                  <svg className="w-full h-full" viewBox="0 0 360 140" preserveAspectRatio="none">
                    <line x1="0" y1="20" x2="360" y2="20" stroke="#f2f4f6" strokeWidth="1"/>
                    <line x1="0" y1="50" x2="360" y2="50" stroke="#f2f4f6" strokeWidth="1"/>
                    <line x1="0" y1="80" x2="360" y2="80" stroke="#f2f4f6" strokeWidth="1"/>
                    <line x1="0" y1="110" x2="360" y2="110" stroke="#e5e8eb" strokeDasharray="3,3" strokeWidth="1"/>

                    {/* MOCK background curves for other companies */}
                    <path d="M 0 20 Q 80 15, 180 35 T 360 20" fill="none" stroke="#e5e8eb" strokeWidth="1.5"/>
                    <path d="M 0 20 Q 100 55, 200 40 T 360 50" fill="none" stroke="#e5e8eb" strokeWidth="1.5"/>
                    <path d="M 0 20 Q 70 70, 180 80 T 360 65" fill="none" stroke="#e5e8eb" strokeWidth="1.5"/>

                    <polyline points={polylinePoints} fill="none" stroke="#3182f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                    {circles}

                    <text x="355" y={endY - 10} textAnchor="end" fill="#3182f6" fontSize="10" fontWeight="bold">자사</text>
                  </svg>

                  <div className="flex justify-between text-[10px] text-[#b0b8c1] font-medium pt-1">
                    <span>D-0 (발생일)</span>
                    <span>D+{chartPeriod}</span>
                  </div>
                </div>
              </div>

              <div className="flex justify-center items-center gap-5 mb-6 text-[11px] text-[#6b7684]">
                <div className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-primary rounded-full"></span><span>자사</span></div>
                <div className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-[#b0b8c1] rounded-full"></span><span>유사 기업 A, B, C</span></div>
                <div className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-[#e5e8eb] rounded-full"></span><span>전체 평균</span></div>
              </div>

              <div className="grid grid-cols-3 gap-2.5 mb-6">
                <div className="border border-[#e5e8eb] bg-[#f9fafb] rounded-[12px] py-3.5 px-2 text-center">
                  <p className="text-[10px] text-[#8b95a1] font-medium mb-1">평균 하락률</p>
                  <p className={`text-[20px] font-extrabold leading-none ${dropRateStr.startsWith('-') ? 'text-blue-500' : 'text-red-500'}`}>{dropRateStr}</p>
                </div>
                <div className="border border-[#e5e8eb] bg-[#f9fafb] rounded-[12px] py-3.5 px-2 text-center">
                  <p className="text-[10px] text-[#8b95a1] font-medium mb-1">평균 회복 기간</p>
                  <p className="text-[20px] font-extrabold text-[#191f28] leading-none">12일</p>
                </div>
                <div className="border border-[#e5e8eb] bg-[#f9fafb] rounded-[12px] py-3.5 px-2 text-center">
                  <p className="text-[10px] text-[#8b95a1] font-medium mb-1">데이터 신뢰도</p>
                  <p className="text-[20px] font-extrabold text-primary leading-none">High</p>
                </div>
              </div>
            </div>

            <Link href={`/stock/${stockCode}`} className="w-full bg-primary hover:bg-blue-600 text-white font-bold py-4 rounded-[14px] text-[16px] transition-all flex justify-center text-center mt-4">
              현재 주식 상황 보러 가기
            </Link>
          </section>
        </div>

        <footer className="w-full bg-[#f2f4f6] px-6 py-4 text-center border-t border-[#e5e8eb]">
          <p className="text-[11px] text-[#6b7684] leading-relaxed">
            ‘노조 / 파업’ 관련 이슈로 ‘반도체/SI’ 기업 관련 주가가 일 평균 <span className="text-primary font-bold">“6.31%”</span> 하락했습니다. 예상되는 ‘라인’의 주가 변동은 <span className="text-primary font-bold">“-4.5%”</span> 입니다.
          </p>
          <p className="text-[10px] text-[#b0b8c1] mt-1">
            *본 분석은 과거 유사 사건 데이터 기반의 시뮬레이션이며, 확정된 미래 주가 예측이나 매수·매도 투자 권유가 아닙니다.
          </p>
        </footer>
      </div>
    </div>
  );
}
