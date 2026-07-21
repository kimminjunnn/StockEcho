# StockEcho Frontend

한국투자증권 Open API를 활용한 주식 현재가 조회 애플리케이션입니다. 
Next.js 16.2.10 (App Router), React 19, Tailwind CSS를 기반으로 구축되었습니다.

## 환경변수 설정 (.env)

이 프로젝트를 실행하기 위해 루트 디렉토리(또는 상위 디렉토리)에 `.env` 파일이 필요합니다. 아래의 환경 변수를 설정해야 합니다:

```env
# KIS API 환경 (paper: 모의투자, real: 실전투자)
KIS_ENV=paper

# KIS API 앱 키
KIS_APP_KEY=여러분의_APP_KEY

# KIS API 앱 시크릿
KIS_APP_SECRET=여러분의_APP_SECRET
```

- 본 프로젝트는 상위 디렉토리(`../.env`)에 위치한 `.env` 파일을 읽을 수 있도록 구현되어 있습니다.

## 실행 방법

1. 의존성 설치:
```bash
npm install
```

2. 개발 서버 실행:
```bash
npm run dev
```

3. 결과 확인:
브라우저를 열고 [http://localhost:3000](http://localhost:3000) 주소로 이동하면 삼성전자(005930)의 실시간 주가 정보를 확인할 수 있습니다.

## 기술 스택
- **프레임워크**: Next.js 16 (App Router)
- **언어**: TypeScript
- **스타일링**: Tailwind CSS
- **API 연동**: 한국투자증권 Open API (서버 컴포넌트 환경에서 직접 호출하여 API Key 노출 방지)
