import { NextRequest, NextResponse } from 'next/server';
import { getStockPrice } from '@/lib/kisApi';
import { errorMessage } from '@/lib/errors';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ code: string }> }
) {
  try {
    const { code } = await params;
    
    if (!code) {
      return NextResponse.json(
        { error: 'Stock code is required' },
        { status: 400 }
      );
    }

    const priceData = await getStockPrice(code);
    
    return NextResponse.json({
      success: true,
      data: priceData,
    });
  } catch (error: unknown) {
    console.error('API Route Error:', error);
    return NextResponse.json(
      { error: errorMessage(error, 'Failed to fetch stock price') },
      { status: 500 }
    );
  }
}
