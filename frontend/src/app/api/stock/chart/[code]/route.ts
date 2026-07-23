import { NextRequest, NextResponse } from 'next/server';
import { getStockChartData, getStockMinuteChartData } from '@/lib/kisApi';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ code: string }> }
) {
  try {
    const { code } = await params;
    const searchParams = request.nextUrl.searchParams;
    const period = (searchParams.get('period') as 'min' | 'D' | 'W' | 'M' | 'Y') || 'D';

    let data;
    if (period === 'min') {
      data = await getStockMinuteChartData(code);
    } else {
      data = await getStockChartData(code, period);
    }
    return NextResponse.json({ success: true, data });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, message: error.message },
      { status: 500 }
    );
  }
}
