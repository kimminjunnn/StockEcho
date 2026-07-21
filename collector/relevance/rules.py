"""모든 지원 종목에 공통 적용하는 설명 가능한 관련도 규칙."""

from __future__ import annotations

from collector.companies import Company
from collector.models.news import NormalizedNewsArticle, RelevanceResult


def classify_relevance(
    article: NormalizedNewsArticle,
    company: Company,
) -> RelevanceResult:
    normalized_name = company.name.casefold()
    title = article.title.casefold()
    summary = article.summary.casefold()

    if normalized_name in title:
        return RelevanceResult(
            relation_type="direct",
            confidence=0.95,
            evidence=("title_exact_company_name",),
        )
    if normalized_name in summary:
        return RelevanceResult(
            relation_type="direct",
            confidence=0.65,
            evidence=("summary_exact_company_name",),
        )
    return RelevanceResult(
        relation_type="irrelevant",
        confidence=0.2,
        evidence=("no_exact_company_name",),
    )
