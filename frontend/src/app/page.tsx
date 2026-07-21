import { Suspense } from 'react';
import { getStockPrice } from '../lib/kisApi';

export const dynamic = 'force-dynamic';

async function StockData() {
  try {
    const stockCode = '005930';
    const data = await getStockPrice(stockCode);
    
    const price = parseInt(data.stck_prpr).toLocaleString();
    const diff = parseInt(data.prdy_vrss);
    const diffRate = data.prdy_ctrt;
    const isUp = diff > 0;
    const isDown = diff < 0;
    const colorClass = isUp ? 'text-red-500' : isDown ? 'text-blue-500' : 'text-gray-500';
    const sign = isUp ? '▲' : isDown ? '▼' : '-';

    return (
      <div className="flex flex-col gap-4 text-center">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">삼성전자</h2>
          <p className="text-gray-500 dark:text-gray-400">{stockCode}</p>
        </div>
        
        <div className="mt-4">
          <p className={`text-5xl font-extrabold tracking-tight ${colorClass}`}>
            {price}원
          </p>
          <div className={`mt-2 text-lg font-medium flex items-center justify-center gap-2 ${colorClass}`}>
            <span>전일대비 {sign} {Math.abs(diff).toLocaleString()}원</span>
            <span>({diffRate}%)</span>
          </div>
        </div>
      </div>
    );
  } catch (error: any) {
    return (
      <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
        <p className="font-semibold">오류가 발생했습니다.</p>
        <p className="text-sm mt-1">{error.message}</p>
      </div>
    );
  }
}

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 dark:bg-zinc-900 font-sans p-6">
      <main className="w-full max-w-md bg-white dark:bg-zinc-800 rounded-3xl shadow-xl overflow-hidden p-8 border border-gray-100 dark:border-zinc-700">
        <header className="mb-8 text-center">
          <h1 className="text-xl font-bold text-gray-800 dark:text-zinc-200">한국투자증권 API 연동</h1>
          <p className="text-sm text-gray-500 dark:text-zinc-400 mt-1">실시간 현재가 조회</p>
        </header>

        <Suspense fallback={
          <div className="flex flex-col items-center justify-center py-10 space-y-4">
            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin"></div>
            <p className="text-gray-500 font-medium">데이터를 불러오는 중...</p>
          </div>
        }>
          <StockData />
        </Suspense>
      </main>
    </div>
  );
}
