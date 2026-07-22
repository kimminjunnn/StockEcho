"""자사 → 공통 → 동종기업 순서의 과거 이슈 뉴스 검색 계획."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from collector.companies import Company, SUPPORTED_COMPANIES
from collector.domain.search import QueryCompanyLink, SearchQuery, normalize_query_text


SYNONYM_REPLACEMENTS = (
    ("규제", "통제"),
    ("통제", "규제"),
    ("제한", "통제"),
    ("파업", "쟁의"),
    ("소송", "법적 분쟁"),
    ("리콜", "회수"),
)
SECTOR_TOKEN_PATTERN = re.compile(r"[가-힣a-z0-9]+", re.IGNORECASE)


@dataclass(frozen=True)
class IssueNewsQueryPlan:
    target_stock_code: str
    keywords: tuple[str, ...]
    phrases: tuple[str, ...]
    peer_stock_codes: tuple[str, ...]
    own_queries: tuple[SearchQuery, ...]
    common_queries: tuple[SearchQuery, ...]
    peer_queries: tuple[SearchQuery, ...]

    def to_dict(self) -> dict:
        return {
            "target_stock_code": self.target_stock_code,
            "keywords": list(self.keywords),
            "phrases": list(self.phrases),
            "peer_stock_codes": list(self.peer_stock_codes),
            "own_queries": [query.to_dict() for query in self.own_queries],
            "common_queries": [query.to_dict() for query in self.common_queries],
            "peer_queries": [query.to_dict() for query in self.peer_queries],
        }


def _issue_phrases(
    company: Company,
    keywords: Sequence[str],
    *,
    extra_variants: Sequence[str],
    max_variants: int,
) -> tuple[str, ...]:
    cleaned = [
        normalize_query_text(keyword)
        for keyword in keywords
        if normalize_query_text(keyword)
        and normalize_query_text(keyword).casefold() != company.name.casefold()
    ]
    if not cleaned:
        raise ValueError("회사명을 제외한 이슈 키워드가 하나 이상 필요합니다.")

    base = normalize_query_text(" ".join(cleaned))
    candidates = [base]
    for source, replacement in SYNONYM_REPLACEMENTS:
        if source in base:
            candidates.append(normalize_query_text(base.replace(source, replacement, 1)))
            break
    candidates.extend(normalize_query_text(value) for value in extra_variants)
    unique = tuple(dict.fromkeys(value for value in candidates if value))
    return unique[:max_variants]


def _sector_tokens(company: Company) -> set[str]:
    return {token.casefold() for token in SECTOR_TOKEN_PATTERN.findall(company.sector)}


def _peer_companies(company: Company, *, limit: int) -> tuple[Company, ...]:
    target_tokens = _sector_tokens(company)
    peers = [
        candidate
        for candidate in SUPPORTED_COMPANIES
        if candidate.stock_code != company.stock_code
        and target_tokens.intersection(_sector_tokens(candidate))
    ]
    peers.sort(key=lambda candidate: (candidate.tier, candidate.stock_code))
    return tuple(peers[:limit])


def _company_query(company: Company, phrase: str, *, evidence: str) -> SearchQuery:
    return SearchQuery.create(
        text=f"{company.name} {phrase}",
        query_type="event",
        company_links=(
            QueryCompanyLink(
                stock_code=company.stock_code,
                weight=0.9,
                evidence=(evidence,),
            ),
        ),
    )


def build_issue_news_query_plan(
    company: Company,
    keywords: Sequence[str],
    *,
    extra_variants: Sequence[str] = (),
    max_variants: int = 2,
    max_peers: int = 3,
) -> IssueNewsQueryPlan:
    """호출량을 제한한 3단계 과거 뉴스 검색 계획을 만든다."""

    if max_variants < 1:
        raise ValueError("max_variants는 1 이상이어야 합니다.")
    if max_peers < 0:
        raise ValueError("max_peers는 0 이상이어야 합니다.")

    phrases = _issue_phrases(
        company,
        keywords,
        extra_variants=extra_variants,
        max_variants=max_variants,
    )
    peers = _peer_companies(company, limit=max_peers)
    common_links = tuple(
        QueryCompanyLink(
            stock_code=candidate.stock_code,
            weight=0.7,
            evidence=("issue_history_common_query",),
        )
        for candidate in SUPPORTED_COMPANIES
    )
    own_queries = tuple(
        _company_query(company, phrase, evidence="issue_history_own_query")
        for phrase in phrases
    )
    common_queries = tuple(
        SearchQuery.create(
            text=phrase,
            query_type="industry",
            company_links=common_links,
        )
        for phrase in phrases
    )
    peer_queries = tuple(
        _company_query(peer, phrase, evidence="issue_history_peer_query")
        for peer in peers
        for phrase in phrases
    )
    return IssueNewsQueryPlan(
        target_stock_code=company.stock_code,
        keywords=tuple(normalize_query_text(keyword) for keyword in keywords if keyword.strip()),
        phrases=phrases,
        peer_stock_codes=tuple(peer.stock_code for peer in peers),
        own_queries=own_queries,
        common_queries=common_queries,
        peer_queries=peer_queries,
    )
