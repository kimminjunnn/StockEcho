"""KIS Open API의 국내 주식 일봉 client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class KisApiError(RuntimeError):
    """인증정보를 노출하지 않는 KIS API 오류."""


@dataclass(frozen=True)
class KisCredentials:
    app_key: str
    app_secret: str
    environment: str = "paper"


class KisDailyPriceClient:
    def __init__(
        self,
        credentials: KisCredentials,
        *,
        timeout_seconds: float = 15,
        session: requests.Session | None = None,
    ) -> None:
        if credentials.environment not in {"paper", "real"}:
            raise ValueError("KIS 환경은 paper 또는 real이어야 합니다.")
        self._credentials = credentials
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()
        self._access_token = ""
        self._token_expires_at = datetime.min.replace(tzinfo=timezone.utc)

    @property
    def _domain(self) -> str:
        if self._credentials.environment == "real":
            return "https://openapi.koreainvestment.com:9443"
        return "https://openapivts.koreainvestment.com:29443"

    def _token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._access_token and now < self._token_expires_at:
            return self._access_token
        response = self._session.post(
            f"{self._domain}/oauth2/tokenP",
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": self._credentials.app_key,
                "appsecret": self._credentials.app_secret,
            },
            timeout=self._timeout_seconds,
        )
        if not response.ok:
            raise KisApiError(f"KIS 토큰 발급 실패(HTTP {response.status_code})")
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise KisApiError("KIS 토큰 응답에 access_token이 없습니다.")
        self._access_token = str(token)
        self._token_expires_at = now + timedelta(hours=11, minutes=50)
        return self._access_token

    def daily_closes(
        self,
        stock_code: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        if not stock_code.isdigit() or len(stock_code) != 6:
            raise ValueError("종목 코드는 6자리 숫자여야 합니다.")
        if start_date > end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")

        response = self._session.get(
            (
                f"{self._domain}/uapi/domestic-stock/v1/quotations/"
                "inquire-daily-itemchartprice"
            ),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self._token()}",
                "appkey": self._credentials.app_key,
                "appsecret": self._credentials.app_secret,
                "tr_id": "FHKST03010100",
            },
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": stock_code,
                "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0",
            },
            timeout=self._timeout_seconds,
        )
        if not response.ok:
            raise KisApiError(f"KIS 일봉 조회 실패(HTTP {response.status_code})")
        payload = response.json()
        if payload.get("rt_cd") != "0":
            code = payload.get("msg_cd") or "unknown"
            raise KisApiError(f"KIS 일봉 조회 실패({code})")

        rows: list[dict[str, Any]] = []
        for item in payload.get("output2") or []:
            value = str(item.get("stck_bsop_date", ""))
            close_value = str(item.get("stck_clpr", "")).replace(",", "")
            if len(value) != 8 or not close_value.isdigit():
                continue
            close_price = int(close_value)
            if close_price <= 0:
                continue
            rows.append(
                {
                    "trading_date": date(
                        int(value[:4]), int(value[4:6]), int(value[6:])
                    ),
                    "close_price": close_price,
                }
            )
        rows.sort(key=lambda row: row["trading_date"])
        return rows


def load_kis_client() -> KisDailyPriceClient:
    """서버 환경을 우선하고 로컬 개발용 env 파일을 보조로 읽는다."""

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "frontend" / ".env.local")
    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    if not app_key or not app_secret:
        raise KisApiError("KIS 일봉 API 설정이 없습니다.")
    return KisDailyPriceClient(
        KisCredentials(
            app_key=app_key,
            app_secret=app_secret,
            environment=os.getenv("KIS_ENV", "paper"),
        )
    )
