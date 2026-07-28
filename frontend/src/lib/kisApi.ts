export type KisRecord = Record<string, string>;

interface KisConfig {
  appKey: string;
  appSecret: string;
  domain: string;
  cacheKey: string;
}

function getKisConfig(): KisConfig {
  const appKey = process.env.KIS_APP_KEY?.trim() ?? '';
  const appSecret = process.env.KIS_APP_SECRET?.trim() ?? '';
  if (!appKey || !appSecret) {
    throw new Error('KIS API 키 또는 시크릿이 설정되지 않았습니다.');
  }
  const environment = process.env.KIS_ENV === 'real' ? 'real' : 'paper';
  return {
    appKey,
    appSecret,
    domain: environment === 'real'
      ? 'https://openapi.koreainvestment.com:9443'
      : 'https://openapivts.koreainvestment.com:29443',
    cacheKey: `${environment}:${appKey}`,
  };
}

let cachedToken = '';
let tokenExpiration = 0;
let tokenRequest: Promise<string> | null = null;
let cachedConfigKey = '';
let kisMarketDataQueue = Promise.resolve();
let nextKisMarketDataRequestAt = 0;

const KIS_MARKET_DATA_REQUEST_INTERVAL_MS = 1_100;

async function fetchKisMarketData(
  input: string | URL,
  init: RequestInit,
): Promise<Response> {
  const previousRequest = kisMarketDataQueue;
  let releaseRequest: () => void = () => undefined;
  kisMarketDataQueue = new Promise<void>((resolve) => {
    releaseRequest = resolve;
  });

  await previousRequest;
  try {
    const waitMs = Math.max(0, nextKisMarketDataRequestAt - Date.now());
    if (waitMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, waitMs));
    }
    nextKisMarketDataRequestAt = Date.now() + KIS_MARKET_DATA_REQUEST_INTERVAL_MS;
    return await fetch(input, init);
  } finally {
    releaseRequest();
  }
}

async function issueAccessToken(config: KisConfig) {
  const res = await fetch(`${config.domain}/oauth2/tokenP`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      grant_type: 'client_credentials',
      appkey: config.appKey,
      appsecret: config.appSecret,
    }),
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorText = await res.text();
    console.error("Token API Error:", res.status, errorText);
    throw new Error(`액세스 토큰 발급에 실패했습니다: ${errorText}`);
  }

  const data = await res.json();
  cachedToken = data.access_token;
  cachedConfigKey = config.cacheKey;
  tokenExpiration = Date.now() + 12 * 60 * 60 * 1000; 

  return cachedToken;
}

export async function getAccessToken() {
  return getAccessTokenFor(getKisConfig());
}

async function getAccessTokenFor(config: KisConfig) {
  if (
    cachedToken
    && cachedConfigKey === config.cacheKey
    && Date.now() < tokenExpiration
  ) {
    return cachedToken;
  }

  if (tokenRequest) {
    return tokenRequest;
  }

  tokenRequest = issueAccessToken(config);
  try {
    return await tokenRequest;
  } finally {
    tokenRequest = null;
  }
}

export async function getStockPrice(stockCode: string): Promise<KisRecord> {
  const config = getKisConfig();
  const token = await getAccessTokenFor(config);
  
  const res = await fetchKisMarketData(`${config.domain}/uapi/domestic-stock/v1/quotations/inquire-price?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': config.appKey,
      'appsecret': config.appSecret,
      'tr_id': 'FHKST01010100',
    },
    cache: 'no-store',
  });

  if (!res.ok) throw new Error('현재가 조회에 실패했습니다.');

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output as KisRecord;
}

export async function getStockChartData(
  stockCode: string,
  period: 'D' | 'W' | 'M' | 'Y' = 'D',
): Promise<KisRecord[]> {
  const config = getKisConfig();
  const token = await getAccessTokenFor(config);
  
  const today = new Date();
  const pastDate = new Date();
  
  if (period === 'D') pastDate.setDate(today.getDate() - 100);
  else if (period === 'W') pastDate.setFullYear(today.getFullYear() - 1);
  else if (period === 'M') pastDate.setFullYear(today.getFullYear() - 5);
  else if (period === 'Y') pastDate.setFullYear(today.getFullYear() - 20);
  
  const formatDate = (date: Date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}${m}${d}`;
  };

  const endDt = formatDate(today);
  const startDt = formatDate(pastDate);

  const res = await fetchKisMarketData(`${config.domain}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}&FID_INPUT_DATE_1=${startDt}&FID_INPUT_DATE_2=${endDt}&FID_PERIOD_DIV_CODE=${period}&FID_ORG_ADJ_PRC=0`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': config.appKey,
      'appsecret': config.appSecret,
      'tr_id': 'FHKST03010100',
    },
    cache: 'no-store',
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`차트 데이터 조회에 실패했습니다. HTTP: ${res.status}, Body: ${text}`);
  }

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output2 as KisRecord[];
}

export async function getStockMinuteChartData(stockCode: string): Promise<KisRecord[]> {
  const config = getKisConfig();
  const token = await getAccessTokenFor(config);
  
  // Use a fixed hour or current time? 
  // For VTS and after hours, using "153000" (market close) is safer to get the whole day.
  const time = "153000";

  const res = await fetchKisMarketData(`${config.domain}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice?FID_ETC_CLS_CODE=&FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}&FID_INPUT_HOUR_1=${time}&FID_PW_DATA_INCU_YN=N`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': config.appKey,
      'appsecret': config.appSecret,
      'tr_id': 'FHKST03010200',
    },
    cache: 'no-store',
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`분봉 데이터 조회에 실패했습니다. HTTP: ${res.status}, Body: ${text}`);
  }

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output2 as KisRecord[];
}

export async function getPastIssueChartData(
  stockCode: string,
  startDate: string,
  endDate: string,
): Promise<KisRecord[]> {
  const config = getKisConfig();
  const token = await getAccessTokenFor(config);

  const res = await fetchKisMarketData(`${config.domain}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}&FID_INPUT_DATE_1=${startDate}&FID_INPUT_DATE_2=${endDate}&FID_PERIOD_DIV_CODE=D&FID_ORG_ADJ_PRC=0`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': config.appKey,
      'appsecret': config.appSecret,
      'tr_id': 'FHKST03010100',
    },
    cache: 'no-store',
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`과거 차트 데이터 조회에 실패했습니다. HTTP: ${res.status}, Body: ${text}`);
  }

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output2 as KisRecord[];
}

export async function getStockInvestorData(stockCode: string): Promise<KisRecord[]> {
  const config = getKisConfig();
  const token = await getAccessTokenFor(config);
  
  const res = await fetchKisMarketData(`${config.domain}/uapi/domestic-stock/v1/quotations/inquire-investor?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': config.appKey,
      'appsecret': config.appSecret,
      'tr_id': 'FHKST01010900',
    },
    cache: 'no-store',
  });

  if (!res.ok) throw new Error('투자자 데이터 조회에 실패했습니다.');

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output as KisRecord[];
}

export async function getStockOrderbook(stockCode: string): Promise<KisRecord> {
  const config = getKisConfig();
  const token = await getAccessTokenFor(config);
  
  const res = await fetchKisMarketData(`${config.domain}/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': config.appKey,
      'appsecret': config.appSecret,
      'tr_id': 'FHKST01010200',
    },
    cache: 'no-store',
  });

  if (!res.ok) throw new Error('호가 데이터 조회에 실패했습니다.');

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output1 as KisRecord;
}

export async function getKospiIndex(): Promise<KisRecord> {
  const config = getKisConfig();
  const token = await getAccessTokenFor(config);
  
  const res = await fetchKisMarketData(`${config.domain}/uapi/domestic-stock/v1/quotations/inquire-index-price?FID_COND_MRKT_DIV_CODE=U&FID_INPUT_ISCD=0001`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': config.appKey,
      'appsecret': config.appSecret,
      'tr_id': 'FHPUP02100000',
    },
    cache: 'no-store',
  });

  if (!res.ok) throw new Error('KOSPI 지수 조회에 실패했습니다.');

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output as KisRecord;
}
