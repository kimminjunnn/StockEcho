"use client";

import React, { useEffect } from 'react';
import { signIn, useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

export default function OnboardingPage() {
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === 'authenticated') {
      router.replace('/');
    }
  }, [status, router]);

  return (
    <div className="bg-[#F8FAFC] min-h-screen text-slate-900 w-full flex flex-col justify-between font-sans">
      {/* Main Container */}
      <main className="max-w-[1240px] w-full mx-auto px-6 py-10 flex-grow space-y-12">
        
        {/* Top Hero Section (2-Column Grid) */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center pt-4">
          
          {/* Left Column: Value Proposition & CTA */}
          <div className="lg:col-span-6 space-y-6 w-full flex flex-col items-start">
            <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight leading-[1.25] text-left" style={{ wordBreak: 'normal' }}>
              과거의 <span className="text-[#2563EB]">유사 사례</span>로,<br />
              <span className="text-slate-900">주가 흐름</span>을 파악해보세요.
            </h1>
            
            <p className="text-slate-600 text-base md:text-lg leading-relaxed font-medium text-left" style={{ width: '100%', maxWidth: '540px', wordBreak: 'normal' }}>
              StockEcho가 뉴스와 공시에서 핵심 사건을 찾고,<br />
              비슷한 사건 이후의 실제 주가 반응을 분석해<br />
              가능성 있는 시나리오를 보여드리고 리밸런싱 제안을 해드려요.
            </p>

            <div className="pt-2">
              <button
                onClick={() => signIn('google', { callbackUrl: '/' })}
                className="bg-[#0052CC] hover:bg-blue-700 text-white font-bold px-7 py-3.5 rounded-2xl shadow-lg shadow-blue-500/20 hover:shadow-xl transition-all inline-flex items-center gap-2 text-base active:scale-95 cursor-pointer"
              >
                서비스 시작하기
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </button>
            </div>
          </div>

          {/* Right Column: AI Risk Analysis Feature Showcase Card */}
          <div className="lg:col-span-6 w-full">
            <div className="bg-[#EEF4FF] rounded-3xl p-7 md:p-8 flex flex-col sm:flex-row items-center gap-6 border border-blue-100/80 shadow-sm w-full">
              
              {/* Left Intro inside Light Blue Box */}
              <div className="flex-1 space-y-3 w-full" style={{ minWidth: '180px' }}>
                <h3 className="text-xl font-bold text-[#1E3A8A] tracking-tight">
                  AI 기반 투자 위험 분석
                </h3>
                <p className="text-slate-600 text-xs md:text-sm leading-relaxed font-medium" style={{ wordBreak: 'normal' }}>
                  공시와 뉴스를 AI가<br />
                  실시간으로 분석하여<br />
                  보유 종목의 위험 요인을<br />
                  한눈에 확인할 수 있습니다.<br />
                  복잡한 투자 정보를<br />
                  쉽고 빠르게 이해해 보세요.
                </p>
              </div>

              {/* Right Floating Demo Card */}
              <div className="w-full sm:w-[320px] shrink-0 bg-white rounded-2xl p-5 shadow-xl border border-slate-100 space-y-4">
                
                {/* Stock Header */}
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-base">현대차</span>
                    <span className="text-slate-700 font-semibold text-sm">418,000</span>
                    <span className="text-red-500 font-semibold text-xs">+0.58%</span>
                  </div>
                  <span className="bg-[#DBEAFE] text-[#1E40AF] text-[11px] font-bold px-2.5 py-1 rounded-full">
                    주요 이슈 3건
                  </span>
                </div>

                {/* Main Issue Card */}
                <div className="bg-white border border-slate-200 rounded-xl p-3.5 space-y-2 shadow-sm">
                  <div className="flex justify-between items-start">
                    <h4 className="font-bold text-slate-900 text-sm">1. 노동 분쟁</h4>
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium">
                    1시간 전 · 언론사 26곳 · 관련기사 28건
                  </p>

                  {/* News Preview Sub-box */}
                  <div className="bg-[#F8FAFC] border border-slate-100 rounded-lg p-2.5 space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 block">대표 기사</span>
                    <p className="font-bold text-slate-900 text-xs truncate">
                      현대차 노조, 6번째 부분파업 전개...
                    </p>
                    <span className="text-[10px] text-slate-400 block">
                      newsis.com · 1시간 전
                    </span>
                  </div>
                </div>

                {/* CTA inside Card */}
                <button
                  onClick={() => signIn('google', { callbackUrl: '/' })}
                  className="w-full bg-[#4285F4] hover:bg-blue-600 text-white font-bold text-xs py-3 rounded-xl transition-colors shadow-sm text-center cursor-pointer"
                >
                  과거 유사 사례 분석
                </button>

              </div>
            </div>
          </div>
        </section>

        {/* Bottom Section: Mock Dashboard with Glass Lock Overlay */}
        <section className="relative rounded-3xl overflow-hidden bg-[#3A3E45] border border-slate-700/50 shadow-2xl p-6 md:p-10 min-h-[500px] flex items-center justify-center w-full">
          
          {/* Lock & Login Overlay */}
          <div className="absolute inset-0 z-20 bg-slate-900/65 backdrop-blur-md flex flex-col items-center justify-center text-center p-8 w-full">
            <div className="w-16 h-16 rounded-full bg-white/10 flex items-center justify-center backdrop-blur-lg border border-white/20 shadow-inner mb-5 shrink-0">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>

            <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight text-center mb-3" style={{ width: '100%', maxWidth: '800px', wordBreak: 'normal' }}>
              로그인 후 맞춤형 포트폴리오 분석 리포트를 확인하실 수 있습니다.
            </h2>

            <p className="text-slate-300 text-sm md:text-base font-medium leading-relaxed text-center mb-7" style={{ width: '100%', maxWidth: '600px', wordBreak: 'normal' }}>
              실시간 데이터 동기화를 통해<br />
              당신의 자산이 직면한 잠재적 위험 요소를 즉시 진단합니다.
            </p>

            <button
              onClick={() => signIn('google', { callbackUrl: '/' })}
              className="bg-white hover:bg-slate-100 text-slate-900 font-extrabold px-8 py-3.5 rounded-2xl shadow-xl transition-all text-sm md:text-base active:scale-95 cursor-pointer shrink-0"
            >
              로그인하여 분석 시작
            </button>
          </div>

          {/* Background Blurred Content (Simulated Mock Portfolio Screen matching screenshot) */}
          <div className="w-full opacity-35 pointer-events-none select-none grid grid-cols-1 lg:grid-cols-12 gap-6 text-white">
            
            {/* Left Portfolio Section */}
            <div className="lg:col-span-8 space-y-6">
              <div>
                <h2 className="text-3xl font-bold text-slate-200">내 포트폴리오</h2>
                <p className="text-slate-400 text-sm mt-1">보유한 종목의 현황과 주요 위험 요인을 분석합니다.</p>
              </div>

              <div className="inline-block bg-slate-700 text-slate-200 text-xs font-bold px-4 py-2 rounded-xl">
                + 종목 편집하기
              </div>

              {/* Table Mock */}
              <div className="bg-slate-800/80 rounded-2xl border border-slate-700 p-4 space-y-4">
                <div className="grid grid-cols-12 text-xs text-slate-400 px-2 font-bold">
                  <span className="col-span-4">종목명</span>
                  <span className="col-span-3 text-right">현재가</span>
                  <span className="col-span-2 text-right">등락률</span>
                  <span className="col-span-3 text-right">상태</span>
                </div>

                <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/60 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-blue-900/50 text-blue-400 flex items-center justify-center font-bold">N</div>
                    <div>
                      <div className="font-bold">NAVER</div>
                      <div className="text-xs text-slate-400">035420</div>
                    </div>
                  </div>
                  <div className="font-bold">185,200원</div>
                  <div className="text-slate-400 text-sm font-bold">0.00%</div>
                  <div className="bg-slate-700 text-slate-300 text-xs px-3 py-1 rounded-lg font-bold">분석 완료</div>
                </div>
              </div>
            </div>

            {/* Right Summary Section */}
            <div className="lg:col-span-4 bg-slate-800/90 rounded-2xl border border-slate-700 p-5 space-y-5">
              <h3 className="font-bold text-base text-slate-200">포트폴리오 요약</h3>
              
              {/* Mini Chart Mock */}
              <div className="bg-slate-900/60 rounded-xl h-28 border border-slate-700/50 p-3 flex flex-col justify-between">
                <div className="text-xs text-emerald-400 font-bold">+12.4%</div>
                <div className="h-10 w-full bg-gradient-to-r from-blue-500/20 to-blue-500/40 rounded"></div>
              </div>

              <div className="space-y-2 text-xs text-slate-300">
                <div className="flex justify-between py-1 border-b border-slate-700/50">
                  <span>총 평가 금액</span>
                  <span className="font-bold">1억 2,450만원</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-700/50">
                  <span>보유 종목</span>
                  <span className="font-bold">8개</span>
                </div>
                <div className="flex justify-between py-1">
                  <span>위험 종목</span>
                  <span className="font-bold text-red-400">1개 (네이버)</span>
                </div>
              </div>

              <div className="bg-slate-700/50 text-slate-200 font-bold text-xs py-3 rounded-xl text-center">
                리밸런싱 제안 보기
              </div>
            </div>

          </div>

        </section>

      </main>

    </div>
  );
}


