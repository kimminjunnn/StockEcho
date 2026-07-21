import React from 'react';

interface AddStockModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const STOCK_LIST = {
  "005930": ["삼성전자"],
  "000660": ["SK하이닉스"],
  "005380": ["현대차", "현대자동차"],
  "373220": ["LG에너지솔루션", "LG엔솔"],
  "207940": ["삼성바이오로직스"],
  "105560": ["KB금융", "KB금융지주"],
  "005490": ["POSCO홀딩스"],
  "012450": ["한화에어로스페이스"],
  "035420": ["NAVER", "네이버"],
  "017670": ["SK텔레콤"]
};

export default function AddStockModal({ isOpen, onClose }: AddStockModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4">
      <div className="bg-surface rounded-2xl max-w-md w-full p-lg shadow-xl relative border border-outline-variant">
        <button 
          onClick={onClose}
          className="absolute top-md right-md material-symbols-outlined text-outline hover:text-on-surface transition-colors"
        >
          close
        </button>
        <h2 className="font-title-sm text-xl font-bold mb-md">종목 추가하기</h2>
        <p className="font-body-sm text-on-surface-variant mb-lg">MVP 단계에서 지원되는 종목 목록입니다.</p>
        
        <div className="space-y-sm max-h-[400px] overflow-y-auto">
          {Object.entries(STOCK_LIST).map(([code, names]) => (
            <div key={code} className="flex justify-between items-center p-md bg-surface-container-low rounded-xl border border-outline-variant hover:border-primary cursor-pointer transition-colors">
              <div className="flex flex-col">
                <span className="font-bold">{names[0]}</span>
                <span className="text-xs text-outline">{code}</span>
              </div>
              <button className="text-primary font-bold text-sm bg-primary/10 px-md py-sm rounded-lg hover:bg-primary/20 transition-colors" onClick={() => {
                  alert(names[0] + ' 추가 기능은 아직 준비 중입니다.');
              }}>
                추가
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
