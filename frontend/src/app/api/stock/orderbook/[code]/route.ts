import { NextRequest, NextResponse } from 'next/server';
import { getStockOrderbook } from '@/lib/kisApi';
import { errorMessage } from '@/lib/errors';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ code: string }> }
) {
  try {
    const { code } = await params;
    const data = await getStockOrderbook(code);
    return NextResponse.json({ success: true, data });
  } catch (error: unknown) {
    return NextResponse.json(
      { success: false, message: errorMessage(error, 'Failed to fetch orderbook') },
      { status: 500 }
    );
  }
}
