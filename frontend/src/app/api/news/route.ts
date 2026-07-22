import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const stockName = searchParams.get('stockName');
  const periodStr = searchParams.get('period') || '5'; // default to 5 days
  const period = parseInt(periodStr, 10);

  if (!stockName) {
    return NextResponse.json({ error: 'stockName parameter is required' }, { status: 400 });
  }

  // Calculate dates
  const today = new Date();
  const pastDate = new Date();
  pastDate.setDate(today.getDate() - period);

  const formatDate = (date: Date) => {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const endDate = formatDate(today);
  const startDate = formatDate(pastDate);

  try {
    const response = await fetch('https://www.bigkinds.or.kr/api/news/search.do', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bigkinds.or.kr/v2/news/index.do'
      },
      body: JSON.stringify({
        "indexName": "news",
        "searchKey": stockName,
        "searchKeys": [{}],
        "byLine": "",
        "searchFilterType": "1",
        "searchScopeType": "1",
        "searchSortType": "date", // Sort by latest
        "sortMethod": "date",
        "mainTodayPersonYn": "",
        "startDate": startDate,
        "endDate": endDate,
        "newsIds": [],
        "categoryCodes": [],
        "providerCodes": [],
        "incidentCodes": [],
        "networkNodeType": "",
        "topicType": "",
        "dateCodes": [],
        "startNo": 1,
        "resultNumber": 3, // Fetch 3 articles per stock
        "isTmUsable": false,
        "isNotTmUsable": false
      })
    });

    if (!response.ok) {
      throw new Error(`BigKinds API responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    let articles = [];
    if (data.resultList && Array.isArray(data.resultList)) {
      articles = data.resultList.map((item: any) => ({
        id: item.NEWS_ID,
        title: item.TITLE.replace(/<[^>]*>?/gm, ''), // Remove HTML tags if any
        content: item.CONTENT.replace(/<[^>]*>?/gm, '').substring(0, 100) + '...',
        url: item.PROVIDER_LINK_PAGE,
        date: item.DATE,
        provider: item.PROVIDER
      }));
    }

    return NextResponse.json({ articles });
  } catch (error: any) {
    console.error('Error fetching from BigKinds:', error);
    return NextResponse.json({ error: 'Failed to fetch news data' }, { status: 500 });
  }
}
