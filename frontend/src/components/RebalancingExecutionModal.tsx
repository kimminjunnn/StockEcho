"use client";

import Link from "next/link";
import type { RebalancingResult } from "@/lib/portfolioEngine";

interface RebalancingExecutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: RebalancingResult | null;
}

function actionText(value: number | undefined): string {
  if (value === undefined || value === 0) return "유지";
  return value > 0 ? `${value.toLocaleString("ko-KR")}주 계산상 매수` : `${Math.abs(value).toLocaleString("ko-KR")}주 계산상 매도`;
}

export default function RebalancingExecutionModal({
  isOpen,
  onClose,
  result,
}: RebalancingExecutionModalProps) {
  if (!isOpen || !result) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-900/40 p-4 backdrop-blur-sm">
      <div className="relative flex w-full max-w-[760px] flex-col rounded-2xl bg-white shadow-2xl">
        <div className="px-8 pb-4 pt-8">
          <button
            type="button"
            onClick={onClose}
            aria-label="계산 내역 닫기"
            className="absolute right-6 top-6 rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-800"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
          <div className="mb-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-primary">
            계산상 수량 · 주문 전송 없음
          </div>
          <h2 className="text-xl font-bold text-gray-900">리밸런싱 계산 내역</h2>
          <p className="mt-2 text-sm text-gray-600">
            현재가와 목표 비중을 기준으로 정수 수량을 반올림한 참고값입니다.
          </p>
        </div>

        <div className="px-8 pb-8 pt-2">
          <div className="mb-6 overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full min-w-[640px] text-left">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs font-bold text-gray-500">
                <tr>
                  <th className="px-5 py-4">종목명</th>
                  <th className="px-5 py-4 text-center">보유 수량</th>
                  <th className="px-5 py-4 text-center">현재 → 목표</th>
                  <th className="px-5 py-4 text-center">계산상 변화</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {result.positions.map((position) => (
                  <tr key={position.code}>
                    <td className="px-5 py-4">
                      <Link href={`/stock/${position.code}`} className="font-bold text-primary hover:underline" onClick={onClose}>
                        {position.name}
                      </Link>
                    </td>
                    <td className="px-5 py-4 text-center">{position.quantity.toLocaleString("ko-KR")}주</td>
                    <td className="px-5 py-4 text-center tabular-nums">
                      {(position.currentWeight * 100).toFixed(1)}% → {((position.targetWeight ?? position.currentWeight) * 100).toFixed(1)}%
                    </td>
                    <td className="px-5 py-4 text-center text-sm font-bold text-gray-800">
                      {actionText(position.estimatedQuantityChange)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-5 text-sm leading-relaxed text-gray-700">
            추정 거래비용은 입력한 현재 평가금액과 {Math.round(result.turnover * 100)}% turnover,
            10bp 가정으로 약 <strong>{Math.round(result.estimatedTransactionCost).toLocaleString("ko-KR")}원</strong>입니다.
            실제 세금·수수료·체결가는 거래 환경에 따라 다릅니다.
          </div>
        </div>
      </div>
    </div>
  );
}
