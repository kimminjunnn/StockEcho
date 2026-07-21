"use client";

import React from 'react';
import { useParams } from 'next/navigation';

export default function StockDetailPage() {
  const params = useParams();
  const code = params.code as string;

  // HTS 링크 - 한국투자증권 웹 트레이딩 시스템 (가상 링크)
  const htsLink = "https://securities.koreainvestment.com/main/Main.jsp";

  return (
    <main className="max-w-[1440px] mx-auto px-6 py-4 w-full flex-grow">
      {/* StockInfoSummaryBar */}
      <section className="bg-white rounded-[8px] border border-gray-100 shadow-sm mb-6 flex items-center p-4 gap-8">
        <div className="flex flex-col">
          <span className="text-xl font-bold">종목명</span>
          <span className="text-2xl font-extrabold mt-1">삼성전자</span>
        </div>
        <div className="flex flex-col">
          <span className="text-xl font-bold">현재가 <span className="text-sm font-normal text-gray-500">(전일 기준 등락폭)</span></span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-extrabold">255,000</span>
            <span className="text-chart-up font-bold text-lg">▲ 3,000 (+1.19%)</span>
          </div>
        </div>

        {/* Quick Metrics Grid */}
        <div className="flex-1 grid grid-cols-4 gap-4 px-6 border-l border-gray-100">
          <div className="flex flex-col justify-center">
            <div className="flex justify-between text-[10px] text-gray-400"><span className="">1일 범위</span> <span className="">1,732,000원</span></div>
            <div className="w-full h-1 bg-gray-100 rounded-full my-1 relative">
              <div className="absolute h-full bg-green-500 rounded-full left-[60%] right-[20%]"></div>
              <div className="absolute w-2 h-2 bg-green-600 rounded-full -top-0.5 left-[75%] border border-white"></div>
            </div>
            <div className="flex justify-between text-[10px] text-gray-400"><span className="">52주 범위</span> <span className="">244,000원</span></div>
          </div>
          <div className="flex flex-col justify-center text-[11px] leading-relaxed">
            <div className="flex justify-between">
              <span className="text-gray-400">거래대금</span>
              <span className="font-bold">1위 -</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">체결강도</span>
              <span className="font-bold">100.19%</span>
            </div>
          </div>
          <div className="flex flex-col justify-center text-[11px] leading-relaxed">
            <div className="flex justify-between">
              <span className="text-gray-400">외국인 순매수</span>
              <span className="font-bold text-gray-800">100위 밖</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">외국인 순매도</span>
              <span className="font-bold">1위 -</span>
            </div>
          </div>
          <div className="flex flex-col justify-center text-[11px] leading-relaxed">
            <div className="flex justify-between">
              <span className="text-gray-400">기관 순매수</span>
              <span className="font-bold text-gray-800">100위 밖</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">기관 순매도</span>
              <span className="font-bold">1위 -</span>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <button className="w-10 h-10 bg-gray-50 border border-gray-100 rounded-[8px] flex items-center justify-center hover:bg-gray-100 transition-colors">
            <svg className="w-5 h-5 text-gray-600" fill="currentColor" viewBox="0 0 24 24"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 4.36 6 6.92 6 10v5l-2 2v1h16v-1l-2-2z"></path></svg>
          </button>
          <button className="w-10 h-10 bg-gray-50 border border-gray-100 rounded-[8px] flex items-center justify-center hover:bg-gray-100 transition-colors">
            <svg className="w-5 h-5 text-gray-300" fill="currentColor" viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"></path></svg>
          </button>
        </div>
      </section>

      <div className="grid grid-cols-12 gap-6">
        {/* ChartSection */}
        <section className="col-span-12 lg:col-span-9 bg-white rounded-[8px] border border-gray-100 shadow-sm p-6">
          {/* Chart Header / Toolbar */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="flex p-1 bg-gray-100 rounded-lg">
                <button className="px-4 py-1 bg-white shadow-sm rounded-md text-sm font-bold text-slate-800">차트</button>
                <button className="px-4 py-1 text-sm font-bold text-gray-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg>
                </button>
              </div>
              <div className="h-6 w-px bg-gray-200 mx-2"></div>
              <div className="flex items-center gap-1">
                <button className="px-3 py-1 text-sm font-bold flex items-center gap-1 hover:bg-gray-50 rounded">60분 <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
                <button className="px-3 py-1 text-sm font-bold hover:bg-gray-50 rounded">일</button>
                <button className="px-3 py-1 text-sm font-bold bg-gray-100 text-slate-800 rounded">주</button>
                <button className="px-3 py-1 text-sm font-bold hover:bg-gray-50 rounded">월</button>
                <button className="px-3 py-1 text-sm font-bold hover:bg-gray-50 rounded">년</button>
              </div>
              <div className="h-6 w-px bg-gray-200 mx-2"></div>
              <div className="flex items-center gap-2 text-gray-400">
                <button className="p-1 hover:bg-gray-50 rounded"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
                <button className="p-1 hover:bg-gray-50 rounded"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
                <button className="p-1 hover:bg-gray-50 rounded"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
              </div>
            </div>
            <div className="flex items-center gap-4 text-gray-400">
              <button className="p-1 hover:bg-gray-50 rounded"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
              <button className="p-1 hover:bg-gray-50 rounded"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
              <button className="p-1 hover:bg-gray-50 rounded"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
              <button className="p-1 hover:bg-gray-50 rounded"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
            </div>
          </div>

          {/* Main Chart Container */}
          <div className="relative border border-gray-100 rounded-lg overflow-hidden bg-white">
            <div className="p-4 border-b border-gray-50">
              <div className="flex items-center gap-4 text-[11px] font-bold">
                <span className="text-gray-400">시작 고가 저가 종가</span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">×</span>
                  <span className="">이동평균선 <span className="text-green-500">5</span> <span className="text-chart-up">20</span> <span className="text-orange-500">60</span> <span className="text-purple-500">120</span></span>
                </div>
              </div>
            </div>
            <div className="relative h-[500px] flex flex-col">
              <div className="flex-1 relative">
                <img alt="Financial Chart" className="absolute inset-0 w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBIp4uN7qeT2Uk3KvWTR7JwPYJTgFAmF0wq9cU54ooXTX2SAc4W--1aGKWMxrMjZ7Vq0-drUEO2ELrWwqPFEyuLoleGlr1Ez--fmULbS4THza5oLEjzb6vsrDCPurVHMAbuXb8ryqen_IREbWDaM_wA38IFWW5gxvw4j7tOrGxQ7_sEOMA-1RzZUCh_RYSEfLYYsTOr6z5gCpml3AS3HlnEIll6NQesGb_aoiJ8o6UXuaFVi3-KYvkxYDrNGlGBo2MgNlM" />
                <div className="absolute right-0 top-[32%] w-16 h-6 bg-chart-up flex items-center justify-center text-white text-[11px] font-bold rounded-l">255,000</div>
              </div>
            </div>
          </div>
        </section>

        {/* SidePanel */}
        <aside className="col-span-12 lg:col-span-3 flex flex-col gap-6">
          <div className="bg-white rounded-[8px] border border-gray-100 shadow-sm flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg>
                <div className="flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-primary text-[10px] font-bold rounded">시세 <span className="ml-1">×</span></div>
                <button className="text-gray-300"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
              </div>
            </div>
            <div className="p-2">
              <div className="grid grid-cols-2 gap-px bg-gray-100 rounded-lg overflow-hidden mb-4">
                <button className="py-2 bg-white text-xs font-bold text-gray-800">실시간</button>
                <button className="py-2 bg-gray-50 text-xs font-medium text-gray-400">일별</button>
              </div>
              <div className="text-[11px]">
                <div className="grid grid-cols-4 text-gray-400 mb-2 px-2">
                  <span className="">체결가</span>
                  <span className="text-right">체결량(주)</span>
                  <span className="text-right">등락률</span>
                  <span className="text-right">거래대금</span>
                </div>
                <div className="flex flex-col gap-1">
                  {[
                    { price: "1,827,000원", vol: 9, volColor: "text-chart-up", pct: "+3.57%", pctColor: "text-chart-up" },
                    { price: "1,827,000원", vol: 3, volColor: "text-chart-up", pct: "+3.57%", pctColor: "text-chart-up" },
                    { price: "1,826,000원", vol: 10, volColor: "text-primary", pct: "+3.51%", pctColor: "text-chart-up" },
                    { price: "1,826,000원", vol: 3, volColor: "text-primary", pct: "+3.51%", pctColor: "text-chart-up" },
                    { price: "1,826,000원", vol: 5, volColor: "text-primary", pct: "+3.51%", pctColor: "text-chart-up" },
                    { price: "1,827,000원", vol: 5, volColor: "text-chart-up", pct: "+3.57%", pctColor: "text-chart-up" },
                  ].map((item, idx) => (
                    <div key={idx} className="grid grid-cols-4 px-2 py-1">
                      <span className="font-bold">{item.price}</span>
                      <span className={`text-right font-bold ${item.volColor}`}>{item.vol}</span>
                      <span className={`text-right font-bold ${item.pctColor}`}>{item.pct}</span>
                      <span className="text-right text-gray-400">2.6조</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Purchase Button */}
          <button 
            onClick={() => window.open(htsLink, "_blank")}
            className="w-full bg-primary text-white font-black py-5 rounded-[8px] text-xl shadow-lg hover:bg-blue-600 transition-all cursor-pointer"
          >
            구매하기
          </button>

          {/* Investor Sentiment Widget */}
          <div className="bg-white rounded-[8px] border border-gray-100 shadow-sm flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg>
                <div className="flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 text-[10px] font-bold rounded">개인·외국인·기관 <span className="ml-1">×</span></div>
                <button className="text-gray-300"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg></button>
              </div>
            </div>
            <div className="p-4 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500 w-12">개인</span>
                <span className="text-xs font-bold flex-1 text-right pr-4">-</span>
                <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-gray-300 w-full"></div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500 w-12">외국인</span>
                <span className="text-xs font-bold flex-1 text-right pr-4 text-primary">-88,574</span>
                <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-primary w-2/3"></div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500 w-12">기관</span>
                <span className="text-xs font-bold flex-1 text-right pr-4 text-primary">-17,000</span>
                <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden flex justify-end">
                  <div className="h-full bg-primary w-1/4"></div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
