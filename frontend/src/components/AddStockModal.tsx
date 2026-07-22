"use client";

import React, { useState, useEffect, useRef } from 'react';
import type { Holding } from '@/lib/portfolio';

interface AddStockModalProps {
  isOpen: boolean;
  savedHoldings: Holding[];
  onClose: () => void;
  onSave: (holdings: Holding[]) => void;
}

const STOCK_DICTIONARY = [
  { code: "005930", name: "삼성전자" },
  { code: "000660", name: "SK하이닉스" },
  { code: "042700", name: "한미반도체" },
  { code: "005380", name: "현대차" },
  { code: "373220", name: "LG에너지솔루션" },
  { code: "207940", name: "삼성바이오로직스" },
  { code: "105560", name: "KB금융" },
  { code: "005490", name: "POSCO홀딩스" },
  { code: "012450", name: "한화에어로스페이스" },
  { code: "035420", name: "NAVER" },
  { code: "017670", name: "SK텔레콤" },
  { code: "000270", name: "기아" },
  { code: "068270", name: "셀트리온" },
  { code: "035720", name: "카카오" },
  { code: "055550", name: "신한지주" },
  { code: "329180", name: "HD현대중공업" },
  { code: "034020", name: "두산에너빌리티" },
  { code: "402340", name: "SK스퀘어" },
  { code: "028260", name: "삼성물산" },
  { code: "032830", name: "삼성생명" },
  { code: "009150", name: "삼성전기" }
];

export default function AddStockModal({ isOpen, savedHoldings, onClose, onSave }: AddStockModalProps) {
  const [holdings, setHoldings] = useState<Holding[]>(() => savedHoldings.map((holding) => ({ ...holding })));
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedQuantity, setSelectedQuantity] = useState<number | ''>(0);
  
  // Search states
  const [searchResults, setSearchResults] = useState<{code: string, name: string}[]>([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [searchedData, setSearchedData] = useState<{code: string, name: string, price: number, changeRate?: number} | null>(null);
  const [isFetchingPrice, setIsFetchingPrice] = useState(false);
  
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Handle Search Input Change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    
    if (query.trim().length > 0) {
      const results = STOCK_DICTIONARY.filter(
        s => s.name.toLowerCase().includes(query.toLowerCase()) || s.code.includes(query)
      );
      setSearchResults(results);
      setIsDropdownOpen(true);
    } else {
      setSearchResults([]);
      setIsDropdownOpen(false);
    }
  };

  // Perform actual KIS API search when a stock is selected
  const executeSearch = async (code: string, name: string) => {
    setIsDropdownOpen(false);
    setSearchQuery(name);
    setSearchedData(null);
    setIsFetchingPrice(true);
    
    try {
      const res = await fetch(`/api/stock/price/${code}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.data && data.data.stck_prpr) {
          const changeRate = Number(data.data.prdy_ctrt);
          setSearchedData({
            code,
            name,
            price: parseInt(data.data.stck_prpr, 10),
            changeRate: Number.isFinite(changeRate) ? changeRate : undefined,
          });
        }
      }
    } catch (error) {
      console.error(`Failed to fetch price for ${code}:`, error);
    } finally {
      setIsFetchingPrice(false);
    }
  };

  const handleSearchIconClick = () => {
    if (searchResults.length > 0) {
      executeSearch(searchResults[0].code, searchResults[0].name);
    }
  };

  if (!isOpen) return null;

  const totalValuation = holdings.reduce((sum, h) => sum + (h.currentPrice || 0) * h.quantity, 0);
  const totalQuantity = holdings.reduce((sum, holding) => sum + holding.quantity, 0);

  const handleAdd = () => {
    if (!searchQuery) return;
    const qty = selectedQuantity === '' ? 0 : selectedQuantity;
    if (qty <= 0) return;

    const existingIndex = holdings.findIndex((holding) =>
      searchedData
        ? holding.code === searchedData.code
        : holding.name === searchQuery || holding.code === searchQuery
    );
    
    // If it exists in holdings, update quantity
    if (existingIndex >= 0) {
      const newHoldings = holdings.map((holding) => ({ ...holding }));
      newHoldings[existingIndex].quantity += qty;
      // If we searched for it and got a fresh price, update it
      if (searchedData && (searchedData.name === newHoldings[existingIndex].name || searchedData.code === newHoldings[existingIndex].code)) {
        newHoldings[existingIndex].currentPrice = searchedData.price;
        newHoldings[existingIndex].changeRate = searchedData.changeRate;
      }
      setHoldings(newHoldings);
    } else {
      // Add new
      setHoldings([...holdings, {
        code: searchedData ? searchedData.code : '000000',
        name: searchedData ? searchedData.name : searchQuery,
        quantity: qty,
        currentPrice: searchedData ? searchedData.price : 0,
        changeRate: searchedData?.changeRate,
        riskLevel: 'pending',
      }]);
    }
    
    setSearchQuery('');
    setSelectedQuantity(0);
    setSearchedData(null);
  };

  const handleRemove = () => {
    if (!searchQuery) return;
    
    const qty = selectedQuantity === '' ? 0 : selectedQuantity;
    const existingIndex = holdings.findIndex((holding) =>
      searchedData
        ? holding.code === searchedData.code
        : holding.name === searchQuery || holding.code === searchQuery
    );
    if (existingIndex >= 0) {
      const newHoldings = holdings.map((holding) => ({ ...holding }));
      if (newHoldings[existingIndex].quantity <= qty || qty === 0) {
        newHoldings.splice(existingIndex, 1);
      } else {
        newHoldings[existingIndex].quantity -= qty;
      }
      setHoldings(newHoldings);
    }
    
    setSearchQuery('');
    setSelectedQuantity(0);
    setSearchedData(null);
  };

  const formatNumber = (num: number) => num.toLocaleString('ko-KR');

  const formatValuationKorean = (num: number) => {
    if (num >= 100000000) {
        const eok = Math.floor(num / 100000000);
        const man = Math.floor((num % 100000000) / 10000);
        if (man > 0) return `${formatNumber(eok)}억 ${formatNumber(man)}만원`;
        return `${formatNumber(eok)}억원`;
    }
    return `${formatNumber(num)}원`;
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center p-md">
      <div className="fixed inset-0 bg-black/50 modal-overlay z-40" onClick={onClose}></div>
      
      <div className="relative z-50 w-full max-w-[1000px] bg-surface-container-lowest rounded-xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
        <header className="flex justify-between items-center px-xl py-lg bg-surface-container-lowest border-b border-surface-variant sticky top-0 z-10">
          <h1 className="font-headline-md text-headline-md text-on-surface">종목 편집하기</h1>
        </header>

        <main className="p-xl space-y-xl overflow-y-auto">
          <section className="grid grid-cols-1 md:grid-cols-3 gap-lg bg-surface border border-outline-variant p-xl rounded-xl">
            <div className="space-y-xs">
              <p className="font-body-sm text-on-surface-variant">총 평가 금액</p>
              <p className="font-headline-md text-headline-md text-on-surface">{formatValuationKorean(totalValuation)}</p>
            </div>
            <div className="space-y-xs">
              <p className="font-body-sm text-on-surface-variant">보유 종목</p>
              <p className="font-headline-md text-headline-md text-on-surface">{holdings.length}개</p>
            </div>
            <div className="space-y-xs">
              <p className="font-body-sm text-on-surface-variant">총 보유 수량</p>
              <p className="font-headline-md text-headline-md text-on-surface">{formatNumber(totalQuantity)}주</p>
            </div>
          </section>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-xl">
            <section className="lg:col-span-8 space-y-lg">
              <h2 className="font-title-sm text-title-sm text-on-surface px-xs">보유 현황</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="border-y border-surface-variant">
                    <tr>
                      <th className="py-md px-md font-label-caps text-label-caps text-on-surface-variant">종목명</th>
                      <th className="py-md px-md font-label-caps text-label-caps text-on-surface-variant text-right">보유 주식 수</th>
                      <th className="py-md px-md font-label-caps text-label-caps text-on-surface-variant text-right">주가</th>
                      <th className="py-md px-md font-label-caps text-label-caps text-on-surface-variant text-right">평가 금액</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-variant">
                    {holdings.map((h) => (
                      <tr key={h.code} className="hover:bg-surface-container transition-colors group cursor-pointer" onClick={() => { setSearchQuery(h.name); setSelectedQuantity(h.quantity); setSearchedData({ code: h.code, name: h.name, price: h.currentPrice || 0, changeRate: h.changeRate }); }}>
                        <td className="py-lg px-md font-body-md text-on-surface font-semibold">{h.name}</td>
                        <td className="py-lg px-md font-body-md text-on-surface text-right">{formatNumber(h.quantity)}주</td>
                        <td className="py-lg px-md font-body-md text-on-surface text-right">₩{formatNumber(h.currentPrice || 0)}</td>
                        <td className="py-lg px-md font-body-md text-on-surface text-right font-bold">₩{formatNumber((h.currentPrice || 0) * h.quantity)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="lg:col-span-4 bg-surface border border-outline-variant rounded-xl p-lg flex flex-col gap-lg min-h-[300px]">
              <div className="space-y-base relative" ref={dropdownRef}>
                <h2 className="font-title-sm text-title-sm text-on-surface">종목 검색</h2>
                <div className="relative">
                  <input 
                    type="text" 
                    value={searchQuery}
                    onChange={handleSearchChange}
                    onFocus={() => { if (searchResults.length > 0) setIsDropdownOpen(true); }}
                    placeholder="종목명을 입력하세요" 
                    className="w-full bg-surface-container-lowest border border-outline-variant rounded-full px-lg py-md pr-3xl font-body-md focus:ring-2 focus:ring-primary focus:border-primary transition-all outline-none" 
                  />
                  <button 
                    onClick={handleSearchIconClick}
                    className="absolute right-md top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-primary transition-colors flex items-center justify-center p-1"
                  >
                    {isFetchingPrice ? (
                      <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <span className="material-symbols-outlined">search</span>
                    )}
                  </button>
                </div>
                
                {/* Autocomplete Dropdown */}
                {isDropdownOpen && searchResults.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-lg z-50 overflow-hidden max-h-48 overflow-y-auto">
                    {searchResults.map((result) => (
                      <div 
                        key={result.code}
                        onClick={() => executeSearch(result.code, result.name)}
                        className="px-lg py-md hover:bg-surface-container cursor-pointer transition-colors flex justify-between items-center"
                      >
                        <span className="font-bold text-sm text-on-surface">{result.name}</span>
                        <span className="text-xs text-outline font-body-sm">{result.code}</span>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Display Fetched Price Result */}
                {searchedData && !isDropdownOpen && (
                  <div className="bg-primary/5 border border-primary/20 rounded-xl p-md mt-md flex justify-between items-center animate-fade-in">
                    <div>
                      <span className="font-bold text-sm text-on-surface block">{searchedData.name}</span>
                      <span className="text-xs text-outline">{searchedData.code}</span>
                    </div>
                    <span className="font-bold text-sm text-primary">₩{formatNumber(searchedData.price)}</span>
                  </div>
                )}
              </div>

              <div className="mt-auto space-y-lg pt-4">
                <div className="flex items-center justify-between bg-surface-container-lowest border border-outline-variant rounded-full px-base py-base">
                  <button 
                    onClick={() => setSelectedQuantity(Math.max(0, (selectedQuantity === '' ? 0 : selectedQuantity) - 1))}
                    className="w-10 h-10 flex items-center justify-center hover:bg-surface-container-high rounded-full transition-colors active:scale-95"
                  >
                    <span className="material-symbols-outlined text-on-surface-variant">remove</span>
                  </button>
                  <input 
                    type="number"
                    min="0"
                    value={selectedQuantity}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === '') setSelectedQuantity('');
                      else setSelectedQuantity(Math.max(0, parseInt(val) || 0));
                    }}
                    className="w-16 text-center font-body-md text-on-surface font-bold bg-transparent border-none focus:ring-0 outline-none p-0 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                  />
                  <button 
                    onClick={() => setSelectedQuantity((selectedQuantity === '' ? 0 : selectedQuantity) + 1)}
                    className="w-10 h-10 flex items-center justify-center hover:bg-surface-container-high rounded-full transition-colors active:scale-95"
                  >
                    <span className="material-symbols-outlined text-on-surface-variant">add</span>
                  </button>
                </div>

                <div className="flex flex-col gap-base">
                  <button 
                    onClick={handleAdd}
                    className="w-full bg-primary text-on-primary py-lg rounded-xl font-body-md font-bold transition-all hover:brightness-110 active:scale-[0.98]"
                  >
                    추가하기
                  </button>
                  <button 
                    onClick={handleRemove}
                    className="w-full bg-error-container text-on-error-container py-lg rounded-xl font-body-md font-bold transition-all hover:bg-error hover:text-on-error active:scale-[0.98]"
                  >
                    삭제하기
                  </button>
                </div>
              </div>
            </section>
          </div>
        </main>

        <footer className="px-xl py-lg bg-surface-container border-t border-surface-variant flex justify-end gap-md">
          <button onClick={onClose} className="px-xl py-md text-on-surface-variant font-body-md font-semibold hover:bg-surface-container-highest rounded-lg transition-colors">닫기</button>
          <button onClick={() => onSave(holdings)} className="px-xl py-md bg-secondary text-on-secondary rounded-lg font-body-md font-bold hover:shadow-lg transition-all active:translate-y-px">수정 사항 저장</button>
        </footer>
      </div>
    </div>
  );
}
