import React from 'react';
import { getStockPrice, getStockMinuteChartData, getStockChartData, getStockInvestorData, getStockOrderbook } from '@/lib/kisApi';
import StockDetailClient from '@/components/StockDetailClient';

export const dynamic = 'force-dynamic';

// MVP: Basic Dictionary for resolving stock names from code
const STOCK_NAMES: Record<string, string> = {
  "005930": "삼성전자",
  "000660": "SK하이닉스",
  "005380": "현대차",
  "373220": "LG에너지솔루션",
  "207940": "삼성바이오로직스",
  "105560": "KB금융",
  "005490": "POSCO홀딩스",
  "012450": "한화에어로스페이스",
  "035420": "NAVER",
  "017670": "SK텔레콤",
  "000270": "기아",
  "068270": "셀트리온",
  "035720": "카카오",
  "055550": "신한지주",
  "329180": "HD현대중공업",
  "034020": "두산에너빌리티",
  "402340": "SK스퀘어",
  "028260": "삼성물산",
  "032830": "삼성생명",
  "009150": "삼성전기"
};

export default async function StockDetailPage({ params }: { params: Promise<{ code: string }> }) {
  const resolvedParams = await params;
  const code = resolvedParams.code;
  const stockName = STOCK_NAMES[code] || "알 수 없는 종목";

  // Fetch initial data in parallel from server (no sequential delays)
  let initialPrice = null;
  let initialChart = null;
  let initialInvestor = null;
  let initialOrderbook = null;

  try {
    const [priceRes, chartRes, investorRes, orderbookRes] = await Promise.allSettled([
      getStockPrice(code),
      getStockChartData(code, 'D'),
      getStockInvestorData(code),
      getStockOrderbook(code)
    ]);

    if (priceRes.status === 'fulfilled') initialPrice = priceRes.value;
    if (chartRes.status === 'fulfilled') initialChart = chartRes.value;
    if (investorRes.status === 'fulfilled') initialInvestor = investorRes.value;
    if (orderbookRes.status === 'fulfilled') initialOrderbook = orderbookRes.value;
  } catch (e: any) {
    console.warn("Server-side fetch failed, falling back to client fetch:", e.message);
  }

  return (
    <StockDetailClient 
      stockCode={code}
      stockName={stockName}
      initialPrice={initialPrice}
      initialChart={initialChart}
      initialInvestor={initialInvestor}
      initialOrderbook={initialOrderbook}
    />
  );
}
