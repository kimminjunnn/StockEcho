import fs from 'fs';
import path from 'path';

function getEnv(key: string) {
  if (process.env[key]) return process.env[key];
  try {
    const pathsToTry = [
      path.resolve(process.cwd(), '.env'),
      path.resolve(process.cwd(), '../.env'),
      path.resolve(process.cwd(), '../../.env'),
      '/Users/seojieun/Desktop/StockEcho/.env'
    ];
    
    let envFile = '';
    for (const p of pathsToTry) {
      if (fs.existsSync(p)) {
        envFile = fs.readFileSync(p, 'utf8');
        break;
      }
    }
    
    const match = envFile.match(new RegExp(`^${key}=(.*)$`, 'm'));
    return match ? match[1].trim() : undefined;
  } catch (e) {
    return undefined;
  }
}

const KIS_ENV = getEnv('KIS_ENV') || 'paper';
const APP_KEY = getEnv('KIS_APP_KEY') || '';
const APP_SECRET = getEnv('KIS_APP_SECRET') || '';

const DOMAIN = KIS_ENV === 'real' 
  ? 'https://openapi.koreainvestment.com:9443' 
  : 'https://openapivts.koreainvestment.com:29443';

let cachedToken = '';
let tokenExpiration = 0;

export async function getAccessToken() {
  if (!APP_KEY || !APP_SECRET) {
    throw new Error('API 키 또는 시크릿이 설정되지 않았습니다.');
  }

  if (cachedToken && Date.now() < tokenExpiration) {
    return cachedToken;
  }

  const res = await fetch(`${DOMAIN}/oauth2/tokenP`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      grant_type: 'client_credentials',
      appkey: APP_KEY,
      appsecret: APP_SECRET,
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
  tokenExpiration = Date.now() + 12 * 60 * 60 * 1000; 

  return cachedToken;
}

export async function getStockPrice(stockCode: string) {
  const token = await getAccessToken();
  
  const res = await fetch(`${DOMAIN}/uapi/domestic-stock/v1/quotations/inquire-price?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': APP_KEY,
      'appsecret': APP_SECRET,
      'tr_id': 'FHKST01010100',
    },
    cache: 'no-store',
  });

  if (!res.ok) throw new Error('현재가 조회에 실패했습니다.');

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output;
}

export async function getStockChartData(stockCode: string, period: 'D' | 'W' | 'M' | 'Y' = 'D') {
  const token = await getAccessToken();
  
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

  const res = await fetch(`${DOMAIN}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}&FID_INPUT_DATE_1=${startDt}&FID_INPUT_DATE_2=${endDt}&FID_PERIOD_DIV_CODE=${period}&FID_ORG_ADJ_PRC=0`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': APP_KEY,
      'appsecret': APP_SECRET,
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
  
  return data.output2; 
}

export async function getPastIssueChartData(stockCode: string, startDate: string, endDate: string) {
  const token = await getAccessToken();

  const res = await fetch(`${DOMAIN}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}&FID_INPUT_DATE_1=${startDate}&FID_INPUT_DATE_2=${endDate}&FID_PERIOD_DIV_CODE=D&FID_ORG_ADJ_PRC=0`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': APP_KEY,
      'appsecret': APP_SECRET,
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
  
  return data.output2; 
}

export async function getStockInvestorData(stockCode: string) {
  const token = await getAccessToken();
  
  const res = await fetch(`${DOMAIN}/uapi/domestic-stock/v1/quotations/inquire-investor?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': APP_KEY,
      'appsecret': APP_SECRET,
      'tr_id': 'FHKST01010900',
    },
    cache: 'no-store',
  });

  if (!res.ok) throw new Error('투자자 데이터 조회에 실패했습니다.');

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  return data.output;
}

export async function getStockOrderbook(stockCode: string) {
  const token = await getAccessToken();
  
  const res = await fetch(`${DOMAIN}/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=${stockCode}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'authorization': `Bearer ${token}`,
      'appkey': APP_KEY,
      'appsecret': APP_SECRET,
      'tr_id': 'FHKST01010200',
    },
    cache: 'no-store',
  });

  if (!res.ok) throw new Error('호가 데이터 조회에 실패했습니다.');

  const data = await res.json();
  if (data.rt_cd !== '0') throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  
  // output1 contains the 10-level ask/bid prices and quantities
  return data.output1;
}
