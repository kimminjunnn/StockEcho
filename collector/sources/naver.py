"""NAVER API HUB를 공통 NewsSource 계약에 연결한다."""

from __future__ import annotations

from collector.clients.naver import NaverNewsClient
from collector.sources.base import SourceSearchResult


class NaverNewsSource:
    name = "naver"

    def __init__(self, client: NaverNewsClient) -> None:
        self._client = client

    def search(self, query: str, *, limit: int = 100) -> SourceSearchResult:
        payload = self._client.search_news(query, display=limit)
        return SourceSearchResult(
            source=self.name,
            payload=payload,
            items=payload.get("items", []),
        )
