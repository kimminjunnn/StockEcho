"use client";

import React from 'react';
import Link from 'next/link';

interface RebalancingExecutionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function RebalancingExecutionModal({ isOpen, onClose }: RebalancingExecutionModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex justify-center items-center p-4 bg-gray-900 bg-opacity-40 backdrop-blur-sm">
      <div className="bg-white w-full max-w-[700px] rounded-[16px] shadow-2xl flex flex-col relative animate-fade-in-up">
        
        {/* Header */}
        <div className="px-8 pt-8 pb-4">
          <button 
            onClick={onClose}
            className="absolute top-6 right-6 text-gray-400 hover:text-gray-800 transition-colors"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
          
          <h2 className="text-xl font-bold text-gray-800 mb-2">포트폴리오 리밸런싱 실행</h2>
          <p className="text-gray-600 font-medium">AI 추천 비중에 맞추기 위해 필요한 매수/매도 수량을 확인하세요.</p>
        </div>

        {/* Content */}
        <div className="px-8 pb-8 pt-2">
          {/* Table */}
          <div className="rounded-[12px] border border-gray-200 overflow-hidden mb-6">
            <table className="w-full text-left bg-white">
              <thead className="bg-[#f8f9fa] border-b border-gray-200">
                <tr>
                  <th className="py-4 px-6 text-gray-500 font-bold text-sm">종목명</th>
                  <th className="py-4 px-6 text-gray-500 font-bold text-sm text-center">보유 수량</th>
                  <th className="py-4 px-6 text-gray-500 font-bold text-sm text-center">현재 비중</th>
                  <th className="py-4 px-6 text-gray-500 font-bold text-sm text-center">목표 비중</th>
                  <th className="py-4 px-6 text-gray-500 font-bold text-sm text-center">추천 액션</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {/* NAVER */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="py-5 px-6">
                    <Link href="/stock/035420" className="text-primary font-bold text-[15px] hover:underline" onClick={onClose}>
                      NAVER
                    </Link>
                  </td>
                  <td className="py-5 px-6 text-center font-medium text-gray-800">336주</td>
                  <td className="py-5 px-6 text-center text-gray-600">20%</td>
                  <td className="py-5 px-6 text-center font-bold text-primary">12%</td>
                  <td className="py-5 px-6 text-center flex justify-center">
                    <span className="inline-block bg-[#ffeef0] text-[#e55039] font-bold py-1.5 px-4 rounded-[6px] text-sm">
                      134주 판매
                    </span>
                  </td>
                </tr>
                {/* 라인 */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="py-5 px-6">
                    <Link href="/stock/4689" className="text-primary font-bold text-[15px] hover:underline" onClick={onClose}>
                      라인
                    </Link>
                  </td>
                  <td className="py-5 px-6 text-center font-medium text-gray-800">210주</td>
                  <td className="py-5 px-6 text-center text-gray-600">30%</td>
                  <td className="py-5 px-6 text-center font-bold text-primary">28%</td>
                  <td className="py-5 px-6 text-center flex justify-center">
                    <span className="inline-block bg-[#ffeef0] text-[#e55039] font-bold py-1.5 px-4 rounded-[6px] text-sm">
                      11주 판매
                    </span>
                  </td>
                </tr>
                {/* 삼성전자 */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="py-5 px-6">
                    <Link href="/stock/005930" className="text-primary font-bold text-[15px] hover:underline" onClick={onClose}>
                      삼성전자
                    </Link>
                  </td>
                  <td className="py-5 px-6 text-center font-medium text-gray-800">842주</td>
                  <td className="py-5 px-6 text-center text-gray-600">50%</td>
                  <td className="py-5 px-6 text-center font-bold text-primary">60%</td>
                  <td className="py-5 px-6 text-center flex justify-center">
                    <span className="inline-block bg-[#3182f6] text-white font-bold py-1.5 px-4 rounded-[6px] text-sm shadow-sm">
                      64주 구매
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Fee Information Panel */}
          <div className="bg-[#f8f9fa] border border-gray-200 rounded-[12px] p-5 flex items-start gap-3">
            <div className="text-primary mt-0.5">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 className="text-gray-800 font-bold mb-1">리밸런싱 예상 수수료</h3>
              <p className="text-gray-600 text-[15px]">
                현재 시장가 기준으로 약 <span className="font-bold text-gray-900">12,450원</span>의 거래 수수료와 세금이 발생할 것으로 예상됩니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
