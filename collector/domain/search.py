"""검색어와 종목 연결 domain model."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any


QUERY_TYPES = {"company", "product", "industry", "event"}


def normalize_query_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def make_query_id(query: str, query_type: str) -> str:
    normalized = normalize_query_text(query).casefold()
    digest = hashlib.sha256(f"{query_type}:{normalized}".encode("utf-8")).hexdigest()
    return f"query_{digest[:20]}"


@dataclass(frozen=True)
class QueryCompanyLink:
    stock_code: str
    weight: float
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SearchQuery:
    query_id: str
    text: str
    query_type: str
    status: str
    company_links: tuple[QueryCompanyLink, ...]
    sources: tuple[str, ...] = ("naver",)

    @classmethod
    def create(
        cls,
        text: str,
        query_type: str,
        company_links: tuple[QueryCompanyLink, ...],
        *,
        status: str = "active",
        sources: tuple[str, ...] = ("naver",),
    ) -> "SearchQuery":
        normalized = normalize_query_text(text)
        if not normalized:
            raise ValueError("검색어는 비어 있을 수 없습니다.")
        if query_type not in QUERY_TYPES:
            raise ValueError(f"지원하지 않는 query_type입니다: {query_type}")
        return cls(
            query_id=make_query_id(normalized, query_type),
            text=normalized,
            query_type=query_type,
            status=status,
            company_links=company_links,
            sources=sources,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "text": self.text,
            "query_type": self.query_type,
            "status": self.status,
            "company_links": [link.to_dict() for link in self.company_links],
            "sources": list(self.sources),
        }
