"use client";

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, Time, CandlestickSeries } from 'lightweight-charts';

interface StockChartProps {
  data: any[]; // Data from KIS output2 array
  currentPrice?: number;
  period?: 'min' | 'D' | 'W' | 'M' | 'Y';
}

export default function StockChart({ data, currentPrice, period = 'min' }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#f3f4f6' },
        horzLines: { color: '#f3f4f6' },
      },
      timeScale: {
        timeVisible: period === 'min',
        secondsVisible: false,
        borderVisible: false,
        tickMarkFormatter: (time: any, tickMarkType: number) => {
          if (typeof time === 'number') {
            const date = new Date(time * 1000);
            if (tickMarkType === 3 || tickMarkType === 4) {
              const hours = String(date.getHours()).padStart(2, '0');
              const minutes = String(date.getMinutes()).padStart(2, '0');
              return `${hours}:${minutes}`;
            }
            if (tickMarkType === 0) return `${date.getFullYear()}`;
            if (tickMarkType === 1) return `${date.getMonth() + 1}월`;
            if (tickMarkType === 2) return `${date.getDate()}일`;
          }

          if (typeof time === 'string') {
            const parts = time.split('-');
            if (tickMarkType === 0) return parts[0];
            if (tickMarkType === 1) return `${parseInt(parts[1], 10)}월`;
            if (tickMarkType === 2) return `${parseInt(parts[2], 10)}일`;
            return parts[0];
          }

          if (time && typeof time === 'object' && 'year' in time) {
            if (tickMarkType === 0) return `${time.year}`;
            if (tickMarkType === 1) return `${time.month}월`;
            if (tickMarkType === 2) return `${time.day}일`;
            return `${time.year}`;
          }

          return String(time);
        },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      crosshair: {
        mode: 1,
      },
    });

    chartRef.current = chart;

    // Add candlestick series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#ef4444',
      downColor: '#3b82f6',
      borderVisible: false,
      wickUpColor: '#ef4444',
      wickDownColor: '#3b82f6',
    });
    seriesRef.current = candlestickSeries;

    // Format data
    const isMinute = period === 'min';
    const formattedData = [...data].reverse().map((item: any) => {
      let timestamp: Time;
      
      if (isMinute) {
        // item.stck_bsop_date: YYYYMMDD, item.stck_cntg_hour: HHMMSS
        const dateStr = item.stck_bsop_date || '';
        const timeStr = item.stck_cntg_hour || '153000';
        if (dateStr.length === 8 && timeStr.length >= 6) {
          const y = parseInt(dateStr.substring(0, 4), 10);
          const m = parseInt(dateStr.substring(4, 6), 10) - 1;
          const d = parseInt(dateStr.substring(6, 8), 10);
          const h = parseInt(timeStr.substring(0, 2), 10);
          const min = parseInt(timeStr.substring(2, 4), 10);
          const dt = new Date(y, m, d, h, min, 0);
          timestamp = (dt.getTime() / 1000) as Time;
        } else {
          // fallback
          timestamp = (new Date().getTime() / 1000) as Time;
        }
      } else {
        // item.stck_bsop_date: YYYYMMDD
        const dateStr = item.stck_bsop_date;
        const y = parseInt(dateStr.substring(0, 4), 10);
        const m = parseInt(dateStr.substring(4, 6), 10);
        const d = parseInt(dateStr.substring(6, 8), 10);
        timestamp = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}` as Time;
      }

      return {
        time: timestamp,
        open: parseInt(item.stck_oprc, 10),
        high: parseInt(item.stck_hgpr, 10),
        low: parseInt(item.stck_lwpr, 10),
        close: parseInt(item.stck_clpr || item.stck_prpr, 10),
      };
    });

    // Remove duplicates or invalid times which lightweight-charts throws errors for
    const uniqueData = [];
    const seenTimes = new Set();
    for (const d of formattedData) {
      if (!seenTimes.has(d.time) && !isNaN(d.open) && !isNaN(d.high) && !isNaN(d.low) && !isNaN(d.close)) {
        seenTimes.add(d.time);
        uniqueData.push(d);
      }
    }

    // Sort by time just in case
    uniqueData.sort((a, b) => {
      if (typeof a.time === 'number' && typeof b.time === 'number') {
        return a.time - b.time;
      }
      if (typeof a.time === 'string' && typeof b.time === 'string') {
        return a.time.localeCompare(b.time);
      }
      return 0;
    });

    try {
      candlestickSeries.setData(uniqueData);
    } catch (e) {
      console.error("Chart data error:", e, uniqueData);
    }

    if (currentPrice) {
      candlestickSeries.createPriceLine({
        price: currentPrice,
        color: '#9ca3af',
        lineWidth: 1,
        lineStyle: 3, // dashed
        axisLabelVisible: true,
        title: '현재가',
      });
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, currentPrice, period]);

  if (!data || data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50 text-gray-400">
        차트 데이터를 불러올 수 없습니다.
      </div>
    );
  }

  return <div ref={chartContainerRef} className="w-full h-full" />;
}
