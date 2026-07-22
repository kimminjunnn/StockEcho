"""NAVER API HUB 뉴스 검색 client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


NAVER_NEWS_API_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"


@dataclass(frozen=True)
class NaverCredentials:
    client_id: str
    client_secret: str


class NaverNewsClient:
    def __init__(
        self,
        credentials: NaverCredentials,
        *,
        timeout_seconds: float = 10,
        session: requests.Session | None = None,
    ) -> None:
        self._credentials = credentials
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()

    def search_news(
        self,
        query: str,
        *,
        display: int = 100,
        start: int = 1,
        sort: str = "date",
    ) -> dict[str, Any]:
        if not 1 <= display <= 100:
            raise ValueError("display는 1~100이어야 합니다.")
        if not 1 <= start <= 1000:
            raise ValueError("start는 1~1000이어야 합니다.")
        if sort not in {"date", "sim"}:
            raise ValueError("sort는 date 또는 sim이어야 합니다.")

        response = self._session.get(
            NAVER_NEWS_API_URL,
            headers={
                "X-NCP-APIGW-API-KEY-ID": self._credentials.client_id,
                "X-NCP-APIGW-API-KEY": self._credentials.client_secret,
            },
            params={
                "query": query,
                "display": display,
                "start": start,
                "sort": sort,
                "format": "json",
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("items", []), list):
            raise ValueError("NAVER 뉴스 응답의 items가 배열이 아닙니다.")
        return payload
