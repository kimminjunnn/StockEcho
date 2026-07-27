"""KIS Open API의 국내 주식 일봉 client."""

from __future__ import annotations

import os
import time
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
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ) -> None:
        if credentials.environment not in {"paper", "real"}:
            raise ValueError("KIS 환경은 paper 또는 real이어야 합니다.")
        self._credentials = credentials
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()
        self._max_retries = max(max_retries, 0)
        self._retry_backoff_seconds = max(retry_backoff_seconds, 0.0)
        self._access_token = ""
        self._token_expires_at = datetime.min.replace(tzinfo=timezone.utc)

    def _get(self, url: str, **kwargs: Any):
        """429/5xx와 일시 네트워크 오류만 제한적으로 재시도한다."""

        last_error: requests.RequestException | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(url, **kwargs)
            except requests.RequestException as error:
                last_error = error
                retryable = True
            else:
                retryable = response.status_code == 429 or response.status_code >= 500
                if not retryable or attempt == self._max_retries:
                    return response
            if attempt < self._max_retries and retryable:
                time.sleep(self._retry_backoff_seconds * (2**attempt))
        raise KisApiError(
            f"KIS 요청 실패({type(last_error).__name__ if last_error else 'unknown'})"
        )

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
        """기존 호출부와 호환되는 종가 전용 응답."""

        return [
            {
                "trading_date": row["trading_date"],
                "close_price": row["close_price"],
            }
            for row in self.daily_prices(
                stock_code,
                start_date=start_date,
                end_date=end_date,
            )
        ]

    def daily_prices(
        self,
        stock_code: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """수정주가 기준 일봉 OHLCV를 반환한다."""

        if not stock_code.isdigit() or len(stock_code) != 6:
            raise ValueError("종목 코드는 6자리 숫자여야 합니다.")
        if start_date > end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")

        response = self._get(
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
            numeric_values = {
                "open_price": str(item.get("stck_oprc", "")).replace(",", ""),
                "high_price": str(item.get("stck_hgpr", "")).replace(",", ""),
                "low_price": str(item.get("stck_lwpr", "")).replace(",", ""),
                "close_price": str(item.get("stck_clpr", "")).replace(",", ""),
                "volume": str(item.get("acml_vol", "")).replace(",", ""),
            }
            if (
                len(value) != 8
                or not numeric_values["close_price"].isdigit()
            ):
                continue
            close_price = int(numeric_values["close_price"])
            if close_price <= 0:
                continue
            parsed_values = {
                key: int(number)
                if number.isdigit() and int(number) >= 0
                else None
                for key, number in numeric_values.items()
            }
            rows.append(
                {
                    "trading_date": date(
                        int(value[:4]), int(value[4:6]), int(value[6:])
                    ),
                    "close_price": close_price,
                    "open_price": parsed_values["open_price"],
                    "high_price": parsed_values["high_price"],
                    "low_price": parsed_values["low_price"],
                    "volume": parsed_values["volume"],
                    # FID_ORG_ADJ_PRC=0 요청값은 수정주가를 의미한다.
                    "adjusted": True,
                }
            )
        rows.sort(key=lambda row: row["trading_date"])
        return rows

    def daily_index_prices(
        self,
        *,
        index_code: str = "0001",
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """국내업종 기간별시세 API로 KOSPI 등 지수 OHLCV를 조회한다."""

        if not index_code.isdigit() or len(index_code) != 4:
            raise ValueError("지수 코드는 4자리 숫자여야 합니다.")
        if start_date > end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        response = self._get(
            (
                f"{self._domain}/uapi/domestic-stock/v1/quotations/"
                "inquire-daily-indexchartprice"
            ),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self._token()}",
                "appkey": self._credentials.app_key,
                "appsecret": self._credentials.app_secret,
                "tr_id": "FHKUP03500100",
            },
            params={
                "FID_COND_MRKT_DIV_CODE": "U",
                "FID_INPUT_ISCD": index_code,
                "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",
            },
            timeout=self._timeout_seconds,
        )
        if not response.ok:
            raise KisApiError(
                f"KIS 지수 일봉 조회 실패(HTTP {response.status_code})"
            )
        payload = response.json()
        if payload.get("rt_cd") != "0":
            code = payload.get("msg_cd") or "unknown"
            raise KisApiError(f"KIS 지수 일봉 조회 실패({code})")

        rows: list[dict[str, Any]] = []
        for item in payload.get("output2") or []:
            value = str(item.get("stck_bsop_date", ""))
            numeric_values = {
                "open_price": str(
                    item.get("bstp_nmix_oprc", "")
                ).replace(",", ""),
                "high_price": str(
                    item.get("bstp_nmix_hgpr", "")
                ).replace(",", ""),
                "low_price": str(
                    item.get("bstp_nmix_lwpr", "")
                ).replace(",", ""),
                "close_price": str(
                    item.get("bstp_nmix_prpr", "")
                ).replace(",", ""),
                "volume": str(item.get("acml_vol", "")).replace(",", ""),
            }
            try:
                close_price = float(numeric_values["close_price"])
            except ValueError:
                continue
            if len(value) != 8 or close_price <= 0:
                continue
            parsed_values: dict[str, float | int | None] = {}
            for key, number in numeric_values.items():
                try:
                    parsed_values[key] = (
                        int(number) if key == "volume" else float(number)
                    )
                except ValueError:
                    parsed_values[key] = None
            rows.append(
                {
                    "trading_date": date(
                        int(value[:4]), int(value[4:6]), int(value[6:])
                    ),
                    "open_price": parsed_values["open_price"],
                    "high_price": parsed_values["high_price"],
                    "low_price": parsed_values["low_price"],
                    "close_price": close_price,
                    "volume": parsed_values["volume"],
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
