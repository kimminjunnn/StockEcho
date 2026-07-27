import { NextRequest, NextResponse } from 'next/server';
import { getPastIssueChartData } from '@/lib/kisApi';
import { errorMessage } from '@/lib/errors';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ code: string }> }
) {
  try {
    const { code } = await params;
    const searchParams = request.nextUrl.searchParams;
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');

    if (!startDate || !endDate) {
      return NextResponse.json({ success: false, message: 'startDate and endDate are required' }, { status: 400 });
    }

    const data = await getPastIssueChartData(code, startDate, endDate);
    return NextResponse.json({ success: true, data });
  } catch (error: unknown) {
    return NextResponse.json(
      { success: false, message: errorMessage(error, 'Failed to fetch issue chart') },
      { status: 500 }
    );
  }
}
