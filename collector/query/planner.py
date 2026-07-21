"""회사 seed와 발견 키워드를 실행 가능한 SearchQuery로 변환한다."""

from __future__ import annotations

from collector.companies import Company
from collector.domain.search import QueryCompanyLink, SearchQuery
from collector.query.keywords import KeywordCandidate


def build_company_query(company: Company, *, sources: tuple[str, ...] = ("naver",)) -> SearchQuery:
    return SearchQuery.create(
        text=company.name,
        query_type="company",
        company_links=(
            QueryCompanyLink(
                stock_code=company.stock_code,
                weight=1.0,
                evidence=("official_company_name",),
            ),
        ),
        sources=sources,
    )


def build_expanded_queries(
    company: Company,
    candidates: list[KeywordCandidate],
    *,
    sources: tuple[str, ...] = ("naver",),
) -> list[SearchQuery]:
    active = [candidate for candidate in candidates if candidate.status == "active"]
    max_score = max((candidate.score for candidate in active), default=1.0)
    queries = []
    for candidate in active:
        weight = round(0.65 + 0.3 * (candidate.score / max_score), 4)
        queries.append(
            SearchQuery.create(
                # 발견어만 단독 검색하면 AI·로봇처럼 범위가 넓어지므로
                # MVP에서는 회사명과 결합해 정밀도를 우선한다.
                text=f"{company.name} {candidate.keyword}",
                query_type="event" if candidate.kind == "event" else "product",
                company_links=(
                    QueryCompanyLink(
                        stock_code=company.stock_code,
                        weight=weight,
                        evidence=(
                            "discovered_from_direct_corpus",
                            f"keyword_rule:{candidate.rule_version}",
                        ),
                    ),
                ),
                sources=sources,
            )
        )
    return queries


def build_query_plan(
    company: Company,
    candidates: list[KeywordCandidate],
    *,
    sources: tuple[str, ...] = ("naver",),
) -> list[SearchQuery]:
    return [
        build_company_query(company, sources=sources),
        *build_expanded_queries(company, candidates, sources=sources),
    ]
