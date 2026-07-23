"""여러 기업의 Topic/Event 산출물에서 키워드 기반 과거 이슈를 찾는다."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

from collector.repositories.local import read_jsonl


SCHEMA_VERSION = "historical-event-search-v1"
TOKEN_PATTERN = re.compile(r"[가-힣a-z0-9]+")


def _normalize(value: str) -> str:
    return " ".join(TOKEN_PATTERN.findall((value or "").casefold()))


def _tokens(values: Iterable[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        result.update(TOKEN_PATTERN.findall((value or "").casefold()))
    return {token for token in result if len(token) >= 2}


def load_topic_records(directory: Path) -> list[dict[str, Any]]:
    """종목별 ``*_topics.jsonl``을 하나의 검색 corpus로 읽는다."""

    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*_topics.jsonl")):
        records.extend(read_jsonl(path))
    return records


def _score_candidate(
    *,
    query_keywords: Sequence[str],
    query_tokens: set[str],
    topic: dict[str, Any],
    event: dict[str, Any],
) -> tuple[float, list[str]]:
    event_keyword_values = [
        *event.get("keywords", []),
        event.get("name", ""),
    ]
    topic_keyword_values = [
        *topic.get("keywords", []),
        topic.get("name", ""),
    ]
    representative = event.get("representative_article", {})
    article_values = [
        representative.get("title", ""),
        representative.get("summary", ""),
    ]

    event_keyword_tokens = _tokens(event_keyword_values)
    topic_keyword_tokens = _tokens(topic_keyword_values)
    all_tokens = event_keyword_tokens | topic_keyword_tokens | _tokens(article_values)
    matched_tokens = query_tokens & all_tokens
    if not matched_tokens:
        return (0.0, [])

    candidate_text = " ".join(
        _normalize(value)
        for value in [*event_keyword_values, *topic_keyword_values, *article_values]
    )
    matched_phrases = [
        keyword
        for keyword in query_keywords
        if _normalize(keyword) and _normalize(keyword) in candidate_text
    ]

    token_coverage = len(matched_tokens) / len(query_tokens)
    event_keyword_coverage = len(query_tokens & event_keyword_tokens) / len(query_tokens)
    topic_keyword_coverage = len(query_tokens & topic_keyword_tokens) / len(query_tokens)
    phrase_coverage = len(matched_phrases) / len(query_keywords)
    score = (
        0.45 * token_coverage
        + 0.30 * event_keyword_coverage
        + 0.15 * topic_keyword_coverage
        + 0.10 * phrase_coverage
    )
    return (round(score, 6), sorted(matched_tokens))


def _representative_for_query(
    event: dict[str, Any], query_tokens: set[str]
) -> dict[str, Any]:
    articles = list(event.get("articles") or [])
    if not articles:
        return event.get("representative_article", {})
    return max(
        articles,
        key=lambda article: (
            len(
                query_tokens
                & _tokens(
                    [
                        article.get("title", ""),
                        article.get("summary", ""),
                    ]
                )
            ),
            float(article.get("relevance_confidence", 0)),
            article.get("published_at", ""),
            article.get("document_id", ""),
        ),
    )


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -candidate["keyword_score"],
        -candidate["article_count"],
        -candidate["source_count"],
        -date.fromisoformat(candidate["event_date"]).toordinal(),
        candidate["stock_code"],
        candidate["event_id"],
    )


def _select_external_candidates(
    candidates: Sequence[dict[str, Any]], *, limit: int
) -> list[dict[str, Any]]:
    """가능하면 서로 다른 회사를 먼저 골라 비교 사례를 다양화한다."""

    if limit <= 0:
        return []

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    used_companies: set[str] = set()

    for candidate in candidates:
        if candidate["stock_code"] in used_companies:
            continue
        selected.append(candidate)
        selected_ids.add(candidate["event_id"])
        used_companies.add(candidate["stock_code"])
        if len(selected) == limit:
            return selected

    for candidate in candidates:
        if candidate["event_id"] in selected_ids:
            continue
        selected.append(candidate)
        if len(selected) == limit:
            break
    return selected


def search_historical_events(
    topics: Sequence[dict[str, Any]],
    *,
    target_stock_code: str,
    keywords: Sequence[str],
    before: date,
    current_event_id: str | None = None,
    limit: int = 3,
    minimum_score: float = 0.4,
    minimum_sources: int = 2,
) -> dict[str, Any]:
    """키워드로 과거 Event를 찾고 자사 1건을 외부 기업보다 우선한다.

    자사 후보가 있으면 가장 점수가 높은 한 건을 첫 번째로 선택하고 나머지는
    다른 기업으로 채운다. 자사 후보가 없으면 전부 다른 기업 후보에서 고른다.
    같은 날짜와 미래 Event는 검색 대상에 포함하지 않는다.
    """

    if limit < 1:
        raise ValueError("limit은 1 이상이어야 합니다.")
    if not 0.0 <= minimum_score <= 1.0:
        raise ValueError("minimum_score는 0과 1 사이여야 합니다.")
    if minimum_sources < 1:
        raise ValueError("minimum_sources는 1 이상이어야 합니다.")
    normalized_keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
    if not normalized_keywords:
        raise ValueError("검색 키워드가 하나 이상 필요합니다.")
    query_tokens = _tokens(normalized_keywords)
    if not query_tokens:
        raise ValueError("검색 가능한 두 글자 이상의 키워드가 필요합니다.")

    own_candidates: list[dict[str, Any]] = []
    external_candidates: list[dict[str, Any]] = []
    for topic in topics:
        if topic.get("is_outlier"):
            continue
        stock_code = str(topic.get("stock_code", ""))
        for event in topic.get("events", []):
            event_id = str(event.get("event_id", ""))
            event_date_value = str(event.get("event_date", ""))
            if not event_id or not event_date_value:
                continue
            if current_event_id and event_id == current_event_id:
                continue
            if date.fromisoformat(event_date_value) >= before:
                continue
            source_count = int(event.get("source_count", 0))
            if source_count < minimum_sources:
                continue

            representative = _representative_for_query(event, query_tokens)
            event_for_score = {
                **event,
                "representative_article": representative,
            }
            score, matched_keywords = _score_candidate(
                query_keywords=normalized_keywords,
                query_tokens=query_tokens,
                topic=topic,
                event=event_for_score,
            )
            if score < minimum_score:
                continue

            candidate = {
                "stock_code": stock_code,
                "company_name": topic.get("company_name", ""),
                "scope": "own_company" if stock_code == target_stock_code else "other_company",
                "topic_id": topic.get("topic_id", ""),
                "event_id": event_id,
                "event_date": event_date_value,
                "name": event.get("name") or topic.get("name", ""),
                "keywords": event.get("keywords") or topic.get("keywords", []),
                "keyword_score": score,
                "similarity_score": score,
                "matched_keywords": matched_keywords,
                "article_count": int(event.get("article_count", 0)),
                "source_count": source_count,
                "representative_article": representative,
                "articles": event.get("articles", []),
                "origin": event.get("origin", topic.get("origin", "topic_model")),
            }
            candidate["similarity_reasons"] = [
                (
                    "현재 이슈 핵심어 일치: "
                    + ", ".join(matched_keywords)
                ),
                (
                    "같은 종목의 과거 Event"
                    if candidate["scope"] == "own_company"
                    else "동종·지원 종목의 과거 Event"
                ),
                f"서로 다른 원문 출처 {source_count}곳",
            ]
            if candidate["scope"] == "own_company":
                own_candidates.append(candidate)
            else:
                external_candidates.append(candidate)

    own_candidates.sort(key=_candidate_sort_key)
    external_candidates.sort(key=_candidate_sort_key)

    selected: list[dict[str, Any]] = []
    if own_candidates:
        selected.append(own_candidates[0])
    selected.extend(
        _select_external_candidates(
            external_candidates,
            limit=max(limit - len(selected), 0),
        )
    )
    selected = selected[:limit]
    for rank, candidate in enumerate(selected, start=1):
        candidate["rank"] = rank

    return {
        "schema_version": SCHEMA_VERSION,
        "target_stock_code": target_stock_code,
        "keywords": normalized_keywords,
        "before": before.isoformat(),
        "selection_policy": "own_company_first_then_other_companies",
        "minimum_score": minimum_score,
        "minimum_sources": minimum_sources,
        "candidate_count": len(own_candidates) + len(external_candidates),
        "own_company_candidate_count": len(own_candidates),
        "other_company_candidate_count": len(external_candidates),
        "matches": selected,
    }
