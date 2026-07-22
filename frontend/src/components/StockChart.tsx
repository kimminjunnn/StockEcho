"use client";

import React, { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface ChartDataPoint {
  date: string;
  close: number;
}

interface StockChartProps {
  data: any[]; // Data from KIS output2 array
  currentPrice?: number;
}

export default function StockChart({ data, currentPrice }: StockChartProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    // KIS API returns data in descending date order, so we need to reverse it for the chart
    return [...data].reverse().map((item: any) => ({
      date: item.stck_bsop_date.replace(/(\d{4})(\d{2})(\d{2})/, '$2.$3'),
      close: parseInt(item.stck_clpr, 10)
    }));
  }, [data]);

  if (chartData.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50 text-gray-400">
        차트 데이터를 불러올 수 없습니다.
      </div>
    );
  }

  // Calculate domain for Y axis to make chart look better
  const minPrice = Math.min(...chartData.map(d => d.close));
  const maxPrice = Math.max(...chartData.map(d => d.close));
  const padding = (maxPrice - minPrice) * 0.1;
  
  // Decide color based on start vs end price (or current vs previous)
  const isUp = chartData[chartData.length - 1].close >= chartData[0].close;
  const strokeColor = isUp ? '#ef4444' : '#3b82f6'; // red for up, blue for down (Korean stock convention)
  const fillColor = isUp ? 'url(#colorUp)' : 'url(#colorDown)';

  return (
    <div className="w-full h-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 0, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorUp" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorDown" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 10, fill: '#9ca3af' }} 
            tickLine={false}
            axisLine={false}
            minTickGap={30}
          />
          <YAxis 
            domain={[Math.max(0, minPrice - padding), maxPrice + padding]} 
            hide={true} 
          />
          <Tooltip 
            formatter={(value: any) => [`${Number(value).toLocaleString()}원`, '종가']}
            labelFormatter={(label) => `${label}`}
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          />
          {currentPrice && (
            <ReferenceLine 
              y={currentPrice} 
              stroke="#9ca3af" 
              strokeDasharray="3 3" 
            />
          )}
          <Area 
            type="monotone" 
            dataKey="close" 
            stroke={strokeColor} 
            strokeWidth={2}
            fillOpacity={1} 
            fill={fillColor} 
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
