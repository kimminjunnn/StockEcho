"use client";

import React from 'react';

export default function CriteriaPage() {
  return (
    <main className="max-w-[1400px] mx-auto px-8 py-10 w-full flex-grow">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        {/* Samsung Card */}
        <section className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 flex flex-col gap-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 mb-1">종목 분석</p>
              <h2 className="text-3xl font-bold text-gray-900">삼성전자</h2>
              <p className="text-lg font-bold text-gray-500 mt-1">(005930)</p>
            </div>
            <div className="bg-green-50 text-positive px-4 py-3 rounded-lg flex flex-col items-center">
              <span className="font-bold flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                </svg>
                +10.0%
              </span>
              <span className="text-xs font-medium mt-1">예상 성장률</span>
            </div>
          </div>
          
          <ul className="space-y-4">
            <li className="flex items-start gap-3">
              <div className="mt-1 w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-3 h-3 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path></svg>
              </div>
              <span className="text-gray-700 leading-relaxed font-medium text-[15px]">글로벌 GPU 리더들과의 HBM4 공급망 통합 가속화.</span>
            </li>
            <li className="flex items-start gap-3">
              <div className="mt-1 w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-3 h-3 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path></svg>
              </div>
              <span className="text-gray-700 leading-relaxed font-medium text-[15px]">2nm 공정 파운드리 노드에서의 기술 리더십 강화.</span>
            </li>
            <li className="flex items-start gap-3">
              <div className="mt-1 w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-3 h-3 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path></svg>
              </div>
              <span className="text-gray-700 leading-relaxed font-medium text-[15px]">고용량 AI 서버용 DRAM 모듈의 강력한 수요.</span>
            </li>
          </ul>

          <div className="mt-auto bg-gray-50 rounded-xl p-6 border border-gray-100">
            <p className="text-xs text-gray-500 font-bold mb-3">시장 센티먼트</p>
            <div className="flex items-center gap-2 text-positive font-bold mb-3">
              <span className="w-2.5 h-6 rounded-full bg-positive"></span>
              긍정적인 뉴스 톤
            </div>
            <p className="text-sm text-gray-600 leading-relaxed">
              기관 보고서들은 파운드리 턴어라운드와 메모리 사이클 회복을 매우 긍정적으로 평가하고 있습니다. 최근 기사의 82%가 기술적 회복 탄력성을 강조합니다.
            </p>
          </div>
        </section>

        {/* Naver Card */}
        <section className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 flex flex-col gap-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 mb-1">종목 분석</p>
              <h2 className="text-3xl font-bold text-gray-900">네이버</h2>
              <p className="text-lg font-bold text-gray-500 mt-1">(035420)</p>
            </div>
            <div className="bg-red-50 text-negative px-4 py-3 rounded-lg flex flex-col items-center">
              <span className="font-bold flex items-center gap-1 text-sm">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>
                핵심 리스크 요인
              </span>
            </div>
          </div>
          
          <div className="border-l-4 border-negative pl-4 py-1">
            <h4 className="text-negative font-bold text-lg mb-3">노동 분쟁 영향</h4>
            <p className="text-gray-700 leading-relaxed font-medium text-[15px]">
              노조의 파업 계획으로 인해 서비스 안정성 점수가 <span className="text-negative font-bold">-14%</span> 하락할 것으로 예상되며, 이는 핵심 검색 및 커머스 인프라에 차질을 빚을 가능성이 있습니다.
            </p>
          </div>

          <div className="mt-auto bg-gray-50 rounded-xl p-6 border border-gray-100">
            <p className="text-xs text-gray-500 font-bold mb-3">시장 센티먼트</p>
            <div className="flex items-center gap-2 text-negative font-bold mb-3">
              <span className="w-2.5 h-2.5 rounded-full bg-negative"></span>
              부정적인 뉴스 톤
            </div>
            <p className="text-sm text-gray-600 leading-relaxed">
              경영권 분쟁과 관련된 소셜 미디어 언급량이 많아 AI 확장 소식이 가려지고 있습니다. 중립 또는 하향 조정된 애널리스트 등급이 증가하는 추세입니다.
            </p>
          </div>
        </section>

        {/* Line Card */}
        <section className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 flex flex-col gap-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 mb-1">종목 분석</p>
              <h2 className="text-3xl font-bold text-gray-900">라인</h2>
              <p className="text-lg font-bold text-gray-500 mt-1">(LYCorp)</p>
            </div>
            <div className="bg-red-50 text-negative px-4 py-3 rounded-lg flex flex-col items-center">
              <span className="font-bold flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path>
                </svg>
                -2.0%
              </span>
              <span className="text-xs font-medium mt-1">예상 하락률</span>
            </div>
          </div>
          
          <div className="border-l-4 border-negative pl-4 py-1">
            <h4 className="text-negative font-bold text-lg mb-3">지배구조 리스크</h4>
            <p className="text-gray-700 leading-relaxed font-medium text-[15px]">
              자본 관계 재검토 및 플랫폼 연결성 약화 우려로 인해 시장 불확실성이 증대되고 있으며, 이는 장기적인 성장 동력에 부정적인 영향을 미칠 수 있습니다.
            </p>
          </div>

          <div className="mt-auto bg-gray-50 rounded-xl p-6 border border-gray-100">
            <p className="text-xs text-gray-500 font-bold mb-3">시장 센티먼트</p>
            <div className="flex items-center gap-2 text-negative font-bold mb-3">
              <span className="w-2.5 h-2.5 rounded-full bg-negative"></span>
              부정적인 뉴스 톤
            </div>
            <p className="text-sm text-gray-600 leading-relaxed">
              규제 환경 변화와 관련된 보도가 주를 이루고 있으며, 투자자들의 관망세가 뚜렷해지고 있습니다.
            </p>
          </div>
        </section>

      </div>

      {/* Bottom Area (Placeholders for Charts) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 col-span-1 min-h-[300px] flex flex-col">
          <h3 className="font-bold mb-4">상대강도지수 (RSI)</h3>
          <div className="flex-1 flex items-end justify-between px-4 pb-4 mt-8 relative">
             {/* RSI Mock Chart Lines */}
             <div className="w-full absolute inset-0 bottom-8 flex flex-col justify-end opacity-20">
               <div className="border-b border-gray-400 h-1/3 w-full"></div>
               <div className="border-b border-gray-400 h-1/3 w-full"></div>
             </div>
             <div className="text-xs text-gray-400 font-bold flex flex-col items-center z-10"><span className="text-primary text-2xl font-black mb-2">.</span>SAMSUNG</div>
             <div className="text-xs text-gray-400 font-bold flex flex-col items-center z-10"><span className="text-primary text-2xl font-black mb-6">.</span>SK HYNIX</div>
             <div className="text-xs text-gray-400 font-bold flex flex-col items-center z-10"><span className="text-primary text-2xl font-black mb-10">.</span>SECTOR AVG</div>
             <div className="text-xs text-gray-400 font-bold flex flex-col items-center z-10"><span className="text-negative text-2xl font-black mb-4">.</span>NAVER</div>
          </div>
        </section>

        <section className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 col-span-1 lg:col-span-2 min-h-[300px] flex flex-col">
          <h3 className="font-bold mb-4">리스크 확산 시각화</h3>
          <div className="flex-1 bg-gray-50 rounded-xl flex items-center justify-center border border-gray-100">
            <div className="text-center">
              <h4 className="font-bold text-gray-700 text-lg mb-2">섹터 히트맵 안정성</h4>
              <p className="text-gray-500 text-sm">플랫폼 서비스 섹터에서 시장 변동성 클러스터가 확인되었습니다.</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
