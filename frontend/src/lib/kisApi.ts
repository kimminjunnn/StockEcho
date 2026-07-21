import fs from 'fs';
import path from 'path';

function getEnv(key: string) {
  if (process.env[key]) return process.env[key];
  try {
    const envPath = path.resolve(process.cwd(), '../.env');
    const envFile = fs.readFileSync(envPath, 'utf8');
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
    throw new Error('액세스 토큰 발급에 실패했습니다.');
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

  if (!res.ok) {
    throw new Error('현재가 조회에 실패했습니다.');
  }

  const data = await res.json();
  if (data.rt_cd !== '0') {
    throw new Error(data.msg1 || 'API 오류가 발생했습니다.');
  }
  
  return data.output;
}
