import { NextRequest, NextResponse } from 'next/server';
import { getKospiIndex } from '@/lib/kisApi';

export async function GET(request: NextRequest) {
  try {
    const kospiData = await getKospiIndex();
    
    // bstp_nmix_prpr: 업종 지수 현재가 (e.g. "2581.39")
    // bstp_nmix_prdy_vrss: 업종 지수 전일 대비 (e.g. "-14.21" or "14.21")
    // bstp_nmix_prdy_ctrt: 업종 지수 전일 대비율 (e.g. "0.55" or "-0.55")
    // prdy_vrss_sign: 1:상한, 2:상승, 3:보합, 4:하한, 5:하락
    
    const price = Number(kospiData?.bstp_nmix_prpr || 0);
    const change = Number(kospiData?.bstp_nmix_prdy_vrss || 0);
    const changeRate = Number(kospiData?.bstp_nmix_prdy_ctrt || 0);
    const sign = kospiData?.prdy_vrss_sign || '5';

    return NextResponse.json({
      success: true,
      data: {
        price,
        change,
        changeRate,
        sign,
        raw: kospiData,
      },
    });
  } catch (error: any) {
    console.error('KOSPI API Route Error:', error);
    // Return fallback KOSPI index matching the screenshot design if API rate limit occurs
    return NextResponse.json({
      success: false,
      error: error.message || 'Failed to fetch KOSPI index',
      data: {
        price: 2581.39,
        change: -14.21,
        changeRate: 0.55,
        sign: '5',
      }
    });
  }
}
