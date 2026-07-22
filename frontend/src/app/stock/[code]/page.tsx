import React from 'react';
import Link from 'next/link';
import { getStockPrice, getStockChartData, getStockInvestorData } from '@/lib/kisApi';
import StockChart from '@/components/StockChart';

export const dynamic = 'force-dynamic';

// Mapping for standard MVP stocks since KIS API requires precise codes
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
  "017670": "SK텔레콤"
};

export default async function StockDetailPage({ params }: { params: Promise<{ code: string }> }) {
  const resolvedParams = await params;
  const code = resolvedParams.code;
  const stockName = (STOCK_NAMES[code] || "알 수 없는 종목") + ` (DEBUG code: ${code}, raw: ${JSON.stringify(resolvedParams)})`;

  // Fetch real data from KIS API
  let priceData = null;
  let chartData = null;
  let investorData = null;
  let error = null;

  try {
    const delay = (ms: number) => new Promise(res => setTimeout(res, ms));
    
    const pData = await getStockPrice(code);
    await delay(200); // 초당 거래건수 제한(Rate Limit) 방지
    const cData = await getStockChartData(code);
    await delay(200);
    const iData = await getStockInvestorData(code);
    
    priceData = pData;
    chartData = cData;
    investorData = iData;
  } catch (e: any) {
    error = e.message;
  }

  // HTS 링크 - 한국투자증권 웹 트레이딩 시스템 (가상 링크)
  const htsLink = "https://securities.koreainvestment.com/main/Main.jsp";

  // Format numbers safely
  const formatNum = (numStr: string | undefined) => {
    if (!numStr) return '-';
    return parseInt(numStr, 10).toLocaleString();
  };

  const formatSign = (signStr: string | undefined) => {
    if (!signStr) return '';
    if (signStr === '1' || signStr === '2') return '▲';
    if (signStr === '4' || signStr === '5') return '▼';
    return '-';
  };

  const getSignColor = (signStr: string | undefined) => {
    if (!signStr) return 'text-gray-500';
    if (signStr === '1' || signStr === '2') return 'text-chart-up';
    if (signStr === '4' || signStr === '5') return 'text-chart-down';
    return 'text-gray-500';
  };

  // Safe variables for UI
  const currentPrice = priceData ? parseInt(priceData.stck_prpr, 10) : 0;
  const changeValue = priceData ? priceData.prdy_vrss : '0';
  const changeRate = priceData ? priceData.prdy_ctrt : '0';
  const signColor = getSignColor(priceData?.prdy_vrss_sign);
  const signIcon = formatSign(priceData?.prdy_vrss_sign);

  const high52w = priceData ? priceData.w52_hgpr : '0';
  const low52w = priceData ? priceData.w52_lwpr : '0';
  const dayHigh = priceData ? priceData.stck_hgpr : '0';
  const dayLow = priceData ? priceData.stck_lwpr : '0';
  const tradeVol = priceData ? priceData.acml_vol : '0';

  // Extract investor data
  const individualNet = investorData && investorData.length > 0 ? investorData[0].prsn_ntby_qty : '0';
  const foreignNet = investorData && investorData.length > 0 ? investorData[0].frgn_ntby_qty : '0';
  const instNet = investorData && investorData.length > 0 ? investorData[0].orgn_ntby_qty : '0';
  
  const getInvestorColor = (valStr: string) => {
    if (!valStr || valStr === '0') return 'bg-gray-300 text-gray-500';
    return parseInt(valStr, 10) > 0 ? 'bg-chart-up text-chart-up' : 'bg-chart-down text-chart-down';
  };

  return (
    <main className="max-w-[1440px] mx-auto px-6 py-4 w-full flex-grow">
      {error && (
        <div className="bg-red-50 text-red-500 p-4 rounded-[8px] mb-6 font-bold">
          API 데이터를 불러오는데 실패했습니다: {error}
        </div>
      )}

      {/* StockInfoSummaryBar */}
      <section className="bg-white rounded-[8px] border border-gray-100 shadow-sm mb-6 flex items-center p-4 gap-8">
        <div className="flex flex-col">
          <span className="text-xl font-bold">종목명</span>
          <span className="text-2xl font-extrabold mt-1">{stockName}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-xl font-bold">현재가 <span className="text-sm font-normal text-gray-500">(전일 기준 등락폭)</span></span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-extrabold">{currentPrice.toLocaleString()}</span>
            <span className={`${signColor} font-bold text-lg`}>
              {signIcon} {formatNum(changeValue)} ({changeRate}%)
            </span>
          </div>
        </div>

        {/* Quick Metrics Grid */}
        <div className="flex-1 grid grid-cols-4 gap-4 px-6 border-l border-gray-100">
          <div className="flex flex-col justify-center">
            <div className="flex justify-between text-[10px] text-gray-400"><span className="">1일 범위</span> <span className="">{formatNum(dayHigh)}원</span></div>
            <div className="w-full h-1 bg-gray-100 rounded-full my-1 relative">
              <div className="absolute h-full bg-green-500 rounded-full left-[20%] right-[20%]"></div>
              <div className="absolute w-2 h-2 bg-green-600 rounded-full -top-0.5 left-[50%] border border-white"></div>
            </div>
            <div className="flex justify-between text-[10px] text-gray-400"><span className="">52주 범위</span> <span className="">{formatNum(high52w)}원</span></div>
          </div>
          <div className="flex flex-col justify-center text-[11px] leading-relaxed">
            <div className="flex justify-between">
              <span className="text-gray-400">당일 거래량</span>
              <span className="font-bold">{formatNum(tradeVol)}주</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">체결강도</span>
              <span className="font-bold">100.00%</span>
            </div>
          </div>
          <div className="flex flex-col justify-center text-[11px] leading-relaxed">
            <div className="flex justify-between">
              <span className="text-gray-400">외국인 순매수</span>
              <span className={`font-bold ${parseInt(foreignNet) > 0 ? 'text-chart-up' : 'text-chart-down'}`}>
                {parseInt(foreignNet) > 0 ? formatNum(foreignNet) : '0'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">외국인 순매도</span>
              <span className={`font-bold ${parseInt(foreignNet) < 0 ? 'text-chart-down' : 'text-gray-400'}`}>
                {parseInt(foreignNet) < 0 ? formatNum(Math.abs(parseInt(foreignNet)).toString()) : '0'}
              </span>
            </div>
          </div>
          <div className="flex flex-col justify-center text-[11px] leading-relaxed">
            <div className="flex justify-between">
              <span className="text-gray-400">기관 순매수</span>
              <span className={`font-bold ${parseInt(instNet) > 0 ? 'text-chart-up' : 'text-chart-down'}`}>
                {parseInt(instNet) > 0 ? formatNum(instNet) : '0'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">기관 순매도</span>
              <span className={`font-bold ${parseInt(instNet) < 0 ? 'text-chart-down' : 'text-gray-400'}`}>
                {parseInt(instNet) < 0 ? formatNum(Math.abs(parseInt(instNet)).toString()) : '0'}
              </span>
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
                <button className="px-3 py-1 text-sm font-bold hover:bg-gray-50 rounded">60분</button>
                <button className="px-3 py-1 text-sm font-bold bg-gray-100 text-slate-800 rounded">일</button>
                <button className="px-3 py-1 text-sm font-bold hover:bg-gray-50 rounded">주</button>
                <button className="px-3 py-1 text-sm font-bold hover:bg-gray-50 rounded">월</button>
                <button className="px-3 py-1 text-sm font-bold hover:bg-gray-50 rounded">년</button>
              </div>
            </div>
          </div>
          
          {/* Main Chart Container */}
          <div className="relative border border-gray-100 rounded-lg overflow-hidden bg-white">
            <div className="p-4 border-b border-gray-50">
              <div className="flex items-center gap-4 text-[11px] font-bold">
                <span className="text-gray-400">일별 종가 추이 (최근 100일)</span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">×</span>
                  <span className="">이동평균선 <span className="text-green-500">5</span> <span className="text-chart-up">20</span> <span className="text-orange-500">60</span></span>
                </div>
              </div>
            </div>
            <div className="relative h-[450px] flex flex-col p-4">
              <StockChart data={chartData || []} currentPrice={currentPrice} />
              
              <div className="absolute right-4 top-[32%] w-16 h-6 bg-chart-up flex items-center justify-center text-white text-[11px] font-bold rounded-l z-10 pointer-events-none opacity-90">
                {currentPrice.toLocaleString()}
              </div>
            </div>
          </div>
        </section>

        {/* SidePanel */}
        <aside className="col-span-12 lg:col-span-3 flex flex-col gap-6">
          {/* Real-time Price Widget Dummy (Keep it similar for layout) */}
          <div className="bg-white rounded-[8px] border border-gray-100 shadow-sm flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg>
                <div className="flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-primary text-[10px] font-bold rounded">시세 <span className="ml-1">×</span></div>
              </div>
            </div>
            <div className="p-4 text-center text-gray-400 text-sm font-bold bg-gray-50 h-32 flex items-center justify-center">
              실시간 시세 호가 데이터<br/>(API 미제공)
            </div>
          </div>
          
          {/* Purchase Button */}
          <Link href={htsLink} target="_blank" rel="noopener noreferrer" className="w-full bg-primary text-white font-black py-5 rounded-[8px] text-xl shadow-lg hover:bg-blue-600 transition-all flex justify-center items-center">
            구매하기
          </Link>
          
          {/* Investor Sentiment Widget (Real Data) */}
          <div className="bg-white rounded-[8px] border border-gray-100 shadow-sm flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg>
                <div className="flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 text-[10px] font-bold rounded">개인·외국인·기관 <span className="ml-1">×</span></div>
              </div>
            </div>
            <div className="p-4 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500 w-12">개인</span>
                <span className={`text-xs font-bold flex-1 text-right pr-4 ${getInvestorColor(individualNet).split(' ')[1]}`}>
                  {formatNum(individualNet)}
                </span>
                <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden flex justify-end">
                  <div className={`h-full ${getInvestorColor(individualNet).split(' ')[0]} ${parseInt(individualNet) > 0 ? 'w-2/3' : 'w-1/4'}`}></div>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500 w-12">외국인</span>
                <span className={`text-xs font-bold flex-1 text-right pr-4 ${getInvestorColor(foreignNet).split(' ')[1]}`}>
                  {formatNum(foreignNet)}
                </span>
                <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden flex justify-end">
                  <div className={`h-full ${getInvestorColor(foreignNet).split(' ')[0]} ${parseInt(foreignNet) > 0 ? 'w-2/3' : 'w-1/4'}`}></div>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500 w-12">기관</span>
                <span className={`text-xs font-bold flex-1 text-right pr-4 ${getInvestorColor(instNet).split(' ')[1]}`}>
                  {formatNum(instNet)}
                </span>
                <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden flex justify-end">
                  <div className={`h-full ${getInvestorColor(instNet).split(' ')[0]} ${parseInt(instNet) > 0 ? 'w-2/3' : 'w-1/4'}`}></div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
