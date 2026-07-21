"use client";

import React from 'react';
import Link from 'next/link';

export default function RebalancingPage() {
  return (
    <main className="max-w-[1400px] mx-auto px-8 py-10 w-full flex-grow">
      {/* TitleSection */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="bg-green-100 text-green-600 text-xs font-bold px-2 py-1 rounded uppercase tracking-wider">Simulation Mode</span>
            <span className="text-sm text-gray-400">Last updated: 2024.05.20 14:30</span>
          </div>
          <h1 className="text-4xl font-bold text-gray-900">포트폴리오 리밸런싱 시뮬레이션</h1>
        </div>
        <Link 
          href="/criteria"
          className="px-6 py-3 border-2 border-gray-800 rounded-lg font-bold text-gray-800 hover:bg-gray-50 transition-colors"
        >
          비율 산정 기준 알아보기
        </Link>
      </div>

      {/* DashboardGrid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
        {/* Comparison Card */}
        <section className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-10">
            <h2 className="text-2xl font-bold">자산 배분 비교 (현재 vs 제안)</h2>
            <div className="flex items-center gap-4 text-xs font-medium text-gray-500">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-gray-200 rounded-sm"></span> 현재
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-navy rounded-sm"></span> 제안
              </div>
            </div>
          </div>

          <div className="space-y-10">
            {/* Item 1 */}
            <div>
              <div className="flex justify-between text-sm font-bold mb-3">
                <span className="text-gray-400 uppercase tracking-wide">NAVER</span>
                <span className="text-gray-900">20% <span className="mx-1 text-gray-300">→</span> 12%</span>
              </div>
              <div className="space-y-3">
                <div className="w-full h-4 bg-gray-50 rounded-full overflow-hidden">
                  <div className="h-full bg-gray-200 rounded-full" style={{ width: '20%' }}></div>
                </div>
                <div className="w-full h-4 bg-gray-50 rounded-full overflow-hidden">
                  <div className="h-full bg-navy rounded-full" style={{ width: '12%' }}></div>
                </div>
              </div>
            </div>

            {/* Item 2 */}
            <div>
              <div className="flex justify-between text-sm font-bold mb-3">
                <span className="text-gray-400 uppercase tracking-wide">라인</span>
                <span className="text-gray-900">30% <span className="mx-1 text-gray-300">→</span> 28%</span>
              </div>
              <div className="space-y-3">
                <div className="w-full h-4 bg-gray-50 rounded-full overflow-hidden">
                  <div className="h-full bg-gray-200 rounded-full" style={{ width: '30%' }}></div>
                </div>
                <div className="w-full h-4 bg-gray-50 rounded-full overflow-hidden">
                  <div className="h-full bg-navy rounded-full" style={{ width: '28%' }}></div>
                </div>
              </div>
            </div>

            {/* Item 3 */}
            <div>
              <div className="flex justify-between text-sm font-bold mb-3">
                <span className="text-gray-400 uppercase tracking-wide">삼성전자</span>
                <span className="text-gray-900">50% <span className="mx-1 text-gray-300">→</span> 60%</span>
              </div>
              <div className="space-y-3">
                <div className="w-full h-4 bg-gray-50 rounded-full overflow-hidden">
                  <div className="h-full bg-gray-200 rounded-full" style={{ width: '50%' }}></div>
                </div>
                <div className="w-full h-4 bg-gray-50 rounded-full overflow-hidden">
                  <div className="h-full bg-navy rounded-full" style={{ width: '60%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Metrics Card */}
        <section className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 flex flex-col">
          <h2 className="text-2xl font-bold mb-8">리스크 개선 지표</h2>
          <div className="space-y-6 flex-grow">
            {/* Volatility Metric */}
            <div className="bg-surface-container-low p-6 rounded-xl border-l-4 border-positive">
              <p className="text-sm font-medium text-gray-500 mb-2">포트폴리오 변동성</p>
              <div className="flex items-baseline gap-3">
                <span className="text-3xl font-bold">18.5% → 14.2%</span>
                <span className="text-positive font-bold flex items-center gap-1">
                  ▼ 4.3%p
                </span>
              </div>
            </div>

            {/* Downside Risk Metric */}
            <div className="bg-surface-container-low p-6 rounded-xl border-l-4 border-positive">
              <p className="text-sm font-medium text-gray-500 mb-2">하락 위험 가중합</p>
              <div className="flex items-baseline gap-3">
                <span className="text-3xl font-bold">61점 → 42점</span>
                <span className="text-positive font-bold flex items-center gap-1">
                  ▼ 19점
                </span>
              </div>
            </div>
          </div>

          {/* Summary Recommendation */}
          <div className="mt-8 pt-8 border-t border-gray-100 flex items-start gap-4">
            <div className="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-positive mb-1">안정형 목표 달성 가능</h3>
              <p className="text-gray-500 text-sm leading-relaxed">
                ai 제안 비중 적용 시 변동성이 23% 개선될 것으로 예측됩니다.
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* DetailedTable */}
      <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-8 py-6 flex justify-between items-center border-b border-gray-50">
          <h2 className="text-2xl font-bold">비중 조정 세부 제안</h2>
          <button className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-surface-container-low text-gray-500 text-xs font-bold uppercase tracking-wider">
              <tr>
                <th className="px-8 py-4">종목명</th>
                <th className="px-8 py-4 text-center">현재 비중</th>
                <th className="px-8 py-4 text-center">제안 비중</th>
                <th className="px-8 py-4 text-center">비중 변화</th>
                <th className="px-8 py-4">위험 원인 요약</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {/* Row 1 */}
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-8 py-6 font-bold flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  NAVER
                </td>
                <td className="px-8 py-6 text-center text-gray-500 font-medium">20%</td>
                <td className="px-8 py-6 text-center font-bold text-navy">12%</td>
                <td className="px-8 py-6 text-center text-negative font-bold">▼ -8%p</td>
                <td className="px-8 py-6">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-50 text-red-500 rounded border border-red-100 text-sm font-medium">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" clipRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"></path>
                    </svg>
                    위험 종목 (파업 이슈)
                  </span>
                </td>
              </tr>
              {/* Row 2 */}
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-8 py-6 font-bold flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-amber-600"></span>
                  라인
                </td>
                <td className="px-8 py-6 text-center text-gray-500 font-medium">30%</td>
                <td className="px-8 py-6 text-center font-bold text-navy">28%</td>
                <td className="px-8 py-6 text-center text-negative font-bold">▼ -2%p</td>
                <td className="px-8 py-6 text-sm text-gray-600 font-medium">플랫폼 규제 이슈</td>
              </tr>
              {/* Row 3 */}
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-8 py-6 font-bold flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  삼성전자
                </td>
                <td className="px-8 py-6 text-center text-gray-500 font-medium">50%</td>
                <td className="px-8 py-6 text-center font-bold text-navy">60%</td>
                <td className="px-8 py-6 text-center text-positive font-bold">▲ +10%p</td>
                <td className="px-8 py-6 text-sm text-gray-600 font-medium">상대적 위험 안정</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <footer className="mt-8 text-center text-sm text-gray-400">
        *본 분석은 과거 유사 사건 데이터 기반의 시뮬레이션이며, 확정된 미래 주가 예측이나 매수·매도 투자 권유가 아닙니다.
      </footer>
    </main>
  );
}
