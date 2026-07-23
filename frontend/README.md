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

# 선택: data/가 프로젝트 기본 위치가 아닐 때 지정
STOCKECHO_DATA_ROOT=/absolute/path/to/StockEcho/data
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

홈의 주요 이슈는 `data/processed/topics/<stockCode>_major_issues.jsonl`과
`<stockCode>_topics.jsonl`을 서버의 repository가 읽어
`GET /api/stocks/<stockCode>/issues`로 전달합니다. 현재 실제 분석 데이터가 있는
삼성전자와 SK하이닉스는 Top 3를 표시하고, 다른 종목은 데이터 준비 상태를 표시합니다.
보유 종목과 수량은 브라우저 `localStorage`에만 저장됩니다.

주요 이슈 카드의 `과거 유사 사례 분석`은
`POST /api/stocks/<stockCode>/historical-issues`를 호출합니다. Route Handler는
현재 저장된 Event와 요청을 대조하고 같은 서버의 collector Python을 실행합니다.
프론트엔드만 설치하면 collector 의존성이 없어 `503`이 발생하므로 팀원도
저장소 루트에서 Python 환경을 한 번 준비해야 합니다.

macOS·Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Route Handler는 `.venv`, `venv`의 macOS·Linux·Windows 실행 경로를 자동으로
확인합니다. 다른 Python을 사용하면 서버 전용 `STOCKECHO_PYTHON`에 실행 파일
경로를 지정하고, 별도 실행 디렉터리에서는 `STOCKECHO_REPOSITORY_ROOT`에 저장소
루트를 지정합니다. 화면은 실제 대표 기사,
출처 수, 유사 근거와 D+1·D+5·D+15·D+30 거래일 수익률을 표시하며 부족한
사례나 가격을 임의로 채우지 않습니다.

## 기술 스택
- **프레임워크**: Next.js 16 (App Router)
- **언어**: TypeScript
- **스타일링**: Tailwind CSS
- **API 연동**: 한국투자증권 Open API (서버 컴포넌트 환경에서 직접 호출하여 API Key 노출 방지)
