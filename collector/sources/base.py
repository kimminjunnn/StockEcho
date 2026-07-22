"""뉴스 source가 구현해야 하는 공통 계약."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SourceSearchResult:
    source: str
    payload: dict[str, Any]
    items: list[dict[str, Any]]


class NewsSource(Protocol):
    name: str

    def search(
        self,
        query: str,
        *,
        limit: int = 100,
        start: int = 1,
        sort: str = "date",
    ) -> SourceSearchResult:
        ...
