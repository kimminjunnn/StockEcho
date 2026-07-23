"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';

const StockChart = dynamic(() => import('@/components/StockChart'), { 
  ssr: false, 
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gray-50/50">
      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
    </div>
  ) 
});
interface StockDetailClientProps {
  stockCode: string;
  stockName: string;
  initialPrice: any;
  initialChart: any;
  initialInvestor: any;
  initialOrderbook: any;
}

export default function StockDetailClient({
  stockCode,
  stockName,
  initialPrice,
  initialChart,
  initialInvestor,
  initialOrderbook
}: StockDetailClientProps) {
  const [priceData, setPriceData] = useState<any>(initialPrice);
  const [chartData, setChartData] = useState<any>(initialChart);
  const [investorData, setInvestorData] = useState<any>(initialInvestor);
  const [orderbook, setOrderbook] = useState<any>(initialOrderbook);
  
  const [chartPeriod, setChartPeriod] = useState<'D' | 'W' | 'M' | 'Y'>('D');
  const [isChartLoading, setIsChartLoading] = useState(false);

  // Fetch chart data when period changes or if initialChart is null
  useEffect(() => {
    let isCancelled = false;
    
    const fetchChart = async (retryCount = 0) => {
      if (retryCount === 0) setIsChartLoading(true);
      
      try {
        const res = await fetch(`/api/stock/chart/${stockCode}?period=${chartPeriod}`);
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.data && data.data.length > 0) {
            if (!isCancelled) {
              setChartData(data.data);
              setIsChartLoading(false);
            }
            return; // Success, exit retry loop
          }
        }
      } catch (e) {
        console.error("Chart fetch error:", e);
      }
      
      // If failed or rate limited (empty data), retry up to 5 times
      if (!isCancelled && retryCount < 5) {
        setTimeout(() => fetchChart(retryCount + 1), 1500); // 1.5초 후 재시도
      } else if (!isCancelled) {
        setIsChartLoading(false);
      }
    };

    if (!initialChart || chartPeriod !== 'D') {
      fetchChart(0);
    }

    return () => { isCancelled = true; };
  }, [chartPeriod, stockCode, initialChart]);

  // Polling for real-time price and orderbook (every 5 seconds)
  useEffect(() => {
    const fetchRealtimeData = async () => {
      try {
        const [priceRes, obRes] = await Promise.all([
          fetch(`/api/stock/price/${stockCode}`),
          fetch(`/api/stock/orderbook/${stockCode}`)
        ]);
        
        if (priceRes.ok) {
          const pData = await priceRes.json();
          if (pData.success && pData.data) setPriceData(pData.data);
        }
        
        if (obRes.ok) {
          const oData = await obRes.json();
          if (oData.success && oData.data) setOrderbook(oData.data);
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    };

    if (!initialPrice || !initialOrderbook) {
      fetchRealtimeData();
    }

    const intervalId = setInterval(fetchRealtimeData, 5000);
    return () => clearInterval(intervalId);
  }, [stockCode, initialPrice, initialOrderbook]);

  // Formatters
  const formatNum = (numStr: string | undefined) => {
    if (!numStr) return '0';
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
  
  const getInvestorColor = (valStr: string | undefined) => {
    if (!valStr || valStr === '0') return 'bg-gray-300 text-gray-500';
    return parseInt(valStr, 10) > 0 ? 'bg-chart-up text-chart-up' : 'bg-chart-down text-chart-down';
  };

  // Extract variables
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

  const individualNet = investorData && investorData.length > 0 ? investorData[0].prsn_ntby_qty : '0';
  const foreignNet = investorData && investorData.length > 0 ? investorData[0].frgn_ntby_qty : '0';
  const instNet = investorData && investorData.length > 0 ? investorData[0].orgn_ntby_qty : '0';

  // HTS Link
  const htsLink = "https://securities.koreainvestment.com/main/Main.jsp";

  // Build orderbook arrays (5 levels for MVP UI)
  const asks = [];
  const bids = [];
  if (orderbook) {
    for (let i = 5; i >= 1; i--) {
      asks.push({
        price: orderbook[`askp${i}`],
        vol: orderbook[`askp_rsqn${i}`],
      });
    }
    for (let i = 1; i <= 5; i++) {
      bids.push({
        price: orderbook[`bidp${i}`],
        vol: orderbook[`bidp_rsqn${i}`],
      });
    }
  }

  return (
    <main className="max-w-[1440px] mx-auto px-6 py-4 w-full flex-grow animate-fade-in">
      {/* StockInfoSummaryBar */}
      <section className="bg-white rounded-[8px] border border-gray-100 shadow-sm mb-6 flex items-center p-4 gap-8">
        <div className="flex flex-col">
          <span className="text-xl font-bold">종목명</span>
          <span className="text-2xl font-extrabold mt-1">{stockName}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-xl font-bold">현재가 <span className="text-sm font-normal text-gray-500">(전일 기준 등락폭)</span></span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-extrabold transition-all duration-300">{currentPrice.toLocaleString()}</span>
            <span className={`${signColor} font-bold text-lg transition-colors duration-300`}>
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
                <button onClick={() => setChartPeriod('D')} className={`px-3 py-1 text-sm font-bold rounded transition-colors ${chartPeriod === 'D' ? 'bg-gray-200 text-slate-800' : 'hover:bg-gray-50'}`}>일</button>
                <button onClick={() => setChartPeriod('W')} className={`px-3 py-1 text-sm font-bold rounded transition-colors ${chartPeriod === 'W' ? 'bg-gray-200 text-slate-800' : 'hover:bg-gray-50'}`}>주</button>
                <button onClick={() => setChartPeriod('M')} className={`px-3 py-1 text-sm font-bold rounded transition-colors ${chartPeriod === 'M' ? 'bg-gray-200 text-slate-800' : 'hover:bg-gray-50'}`}>월</button>
                <button onClick={() => setChartPeriod('Y')} className={`px-3 py-1 text-sm font-bold rounded transition-colors ${chartPeriod === 'Y' ? 'bg-gray-200 text-slate-800' : 'hover:bg-gray-50'}`}>년</button>
              </div>
            </div>
          </div>
          
          <div className="relative border border-gray-100 rounded-lg overflow-hidden bg-white">
            <div className="p-4 border-b border-gray-50">
              <div className="flex items-center gap-4 text-[11px] font-bold">
                <span className="text-gray-400">{chartPeriod === 'D' ? '최근 100일' : chartPeriod === 'W' ? '최근 1년(주간)' : chartPeriod === 'M' ? '최근 5년(월간)' : '최근 20년(연간)'} 종가 추이</span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">×</span>
                  <span className="">이동평균선 <span className="text-green-500">5</span> <span className="text-chart-up">20</span> <span className="text-orange-500">60</span></span>
                </div>
              </div>
            </div>
            <div className="relative h-[450px] flex flex-col p-4">
              {isChartLoading ? (
                <div className="absolute inset-0 flex items-center justify-center bg-white/50 z-20">
                  <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : null}
              <StockChart data={chartData || []} currentPrice={currentPrice} period={chartPeriod} />
              <div className="absolute right-4 top-[32%] w-16 h-6 bg-chart-up flex items-center justify-center text-white text-[11px] font-bold rounded-l z-10 pointer-events-none opacity-90 transition-all duration-300">
                {currentPrice.toLocaleString()}
              </div>
            </div>
          </div>
        </section>

        {/* SidePanel */}
        <aside className="col-span-12 lg:col-span-3 flex flex-col gap-6">
          {/* Real-time Orderbook Widget (호가) */}
          <div className="bg-white rounded-[8px] border border-gray-100 shadow-sm flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path></svg>
                <div className="flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-primary text-[10px] font-bold rounded">실시간 5호가 <span className="ml-1">×</span></div>
              </div>
            </div>
            <div className="flex flex-col">
              <div className="grid grid-cols-3 text-[10px] text-gray-400 font-bold bg-gray-50 py-1 px-2 border-b border-gray-100 text-center">
                <div>매도잔량</div>
                <div>호가</div>
                <div>매수잔량</div>
              </div>
              <div className="flex flex-col font-mono text-[11px]">
                {/* Asks (매도) - from highest to lowest */}
                {asks.map((ask, idx) => (
                  <div key={`ask-${idx}`} className="grid grid-cols-3 hover:bg-blue-50/50 cursor-pointer">
                    <div className="py-1 px-2 text-left text-blue-600 bg-blue-50/30 flex items-center justify-start border-r border-white">
                      {formatNum(ask.vol)}
                    </div>
                    <div className="py-1 px-2 text-center font-bold text-blue-600 bg-blue-50/10">
                      {formatNum(ask.price)}
                    </div>
                    <div className="py-1 px-2"></div>
                  </div>
                ))}
                
                <div className="h-px bg-gray-200 my-1 w-full relative">
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white px-2 text-[8px] text-gray-400 rounded-full border border-gray-200">기준</div>
                </div>

                {/* Bids (매수) - from highest to lowest */}
                {bids.map((bid, idx) => (
                  <div key={`bid-${idx}`} className="grid grid-cols-3 hover:bg-red-50/50 cursor-pointer">
                    <div className="py-1 px-2"></div>
                    <div className="py-1 px-2 text-center font-bold text-red-500 bg-red-50/10">
                      {formatNum(bid.price)}
                    </div>
                    <div className="py-1 px-2 text-right text-red-500 bg-red-50/30 flex items-center justify-end border-l border-white">
                      {formatNum(bid.vol)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          <Link href={htsLink} target="_blank" rel="noopener noreferrer" className="w-full bg-primary text-white font-black py-4 rounded-[8px] text-lg shadow-lg hover:bg-blue-600 transition-all flex justify-center items-center">
            구매하기
          </Link>
          
          {/* Investor Sentiment Widget */}
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
