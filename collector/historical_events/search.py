"""여러 기업의 Topic/Event 산출물에서 키워드 기반 과거 이슈를 찾는다."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

from collector.repositories.local import read_jsonl


SCHEMA_VERSION = "historical-event-search-v2"
TOKEN_PATTERN = re.compile(r"[가-힣a-z0-9]+")


@dataclass(frozen=True)
class CandidateScore:
    keyword_score: float
    matched_keywords: tuple[str, ...]
    matched_context_keywords: tuple[str, ...]
    components: dict[str, float]


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
    query_tokens: set[str],
    context_tokens: set[str],
    topic: dict[str, Any],
    event: dict[str, Any],
) -> CandidateScore:
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
    article_tokens = _tokens(article_values)
    all_tokens = event_keyword_tokens | topic_keyword_tokens | article_tokens
    matched_tokens = query_tokens & all_tokens
    if not matched_tokens:
        return CandidateScore(0.0, (), (), {})

    # 짧은 2~3개 검색어 중 하나만 겹친 후보는 일반어 오탐일 가능성이 높다.
    # 검색 recall은 NAVER와 context 키워드에서 확보하고 최종 선별은 precision을
    # 우선한다.
    required_matches = min(2, len(query_tokens))
    if len(matched_tokens) < required_matches:
        return CandidateScore(0.0, tuple(sorted(matched_tokens)), (), {})

    context_only_tokens = context_tokens - query_tokens
    matched_context_tokens = context_only_tokens & all_tokens
    primary_coverage = len(matched_tokens) / len(query_tokens)
    event_coverage = len(query_tokens & event_keyword_tokens) / len(query_tokens)
    article_coverage = len(query_tokens & article_tokens) / len(query_tokens)

    # historical_events에서 Topic과 Event가 같은 값으로 평탄화된 기존 행은 Topic
    # 근거를 중복 가산하지 않는다. Event에 없고 상위 Topic에만 있는 검색어만
    # 별도의 문맥 근거로 인정한다.
    topic_only_matches = (query_tokens & topic_keyword_tokens) - event_keyword_tokens
    topic_context_coverage = len(topic_only_matches) / len(query_tokens)
    context_coverage = (
        len(matched_context_tokens) / len(context_only_tokens)
        if context_only_tokens
        else 0.0
    )

    weights = {
        "primaryCoverage": 0.40,
        "eventCoverage": 0.30,
        "articleCoverage": 0.15,
        "topicContextCoverage": 0.05,
    }
    if context_only_tokens:
        weights["contextCoverage"] = 0.10
    weighted_score = (
        weights["primaryCoverage"] * primary_coverage
        + weights["eventCoverage"] * event_coverage
        + weights["articleCoverage"] * article_coverage
        + weights["topicContextCoverage"] * topic_context_coverage
        + weights.get("contextCoverage", 0.0) * context_coverage
    )
    score = weighted_score / sum(weights.values())
    return CandidateScore(
        keyword_score=round(score, 6),
        matched_keywords=tuple(sorted(matched_tokens)),
        matched_context_keywords=tuple(sorted(matched_context_tokens)),
        components={
            "primaryCoverage": round(primary_coverage, 6),
            "eventCoverage": round(event_coverage, 6),
            "articleCoverage": round(article_coverage, 6),
            "topicContextCoverage": round(topic_context_coverage, 6),
            "contextCoverage": round(context_coverage, 6),
        },
    )


def _sector_affinity(
    target_sector: str, candidate_sector: str
) -> tuple[float, list[str]]:
    target_tokens = _tokens([target_sector])
    candidate_tokens = _tokens([candidate_sector])
    if not target_tokens or not candidate_tokens:
        return (0.0, [])
    shared = target_tokens & candidate_tokens
    if not shared:
        return (0.0, [])
    affinity = len(shared) / min(len(target_tokens), len(candidate_tokens))
    return (round(affinity, 6), sorted(shared))


def _exact_feature_affinity(
    target: str, candidate: str, *, unknown: str
) -> float | None:
    normalized_target = target.strip().casefold()
    normalized_candidate = candidate.strip().casefold()
    if (
        not normalized_target
        or not normalized_candidate
        or normalized_target == unknown
        or normalized_candidate == unknown
    ):
        return None
    return 1.0 if normalized_target == normalized_candidate else 0.0


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
        -candidate["similarity_score"],
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
    context_keywords: Sequence[str] = (),
    target_sector: str = "",
    target_category: str = "",
    target_impact: str = "unknown",
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
    normalized_context_keywords = [
        keyword.strip() for keyword in context_keywords if keyword.strip()
    ]
    context_tokens = _tokens(normalized_context_keywords)

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
            score = _score_candidate(
                query_tokens=query_tokens,
                context_tokens=context_tokens,
                topic=topic,
                event=event_for_score,
            )
            if score.keyword_score < minimum_score:
                continue

            candidate_sector = str(topic.get("sector", ""))
            sector_affinity, shared_sector_keywords = _sector_affinity(
                target_sector, candidate_sector
            )
            candidate_category = str(event.get("category", ""))
            candidate_impact = str(event.get("impact", "unknown"))
            category_affinity = _exact_feature_affinity(
                target_category,
                candidate_category,
                unknown="unknown",
            )
            impact_affinity = _exact_feature_affinity(
                target_impact,
                candidate_impact,
                unknown="unknown",
            )
            feature_scores: list[tuple[float, float]] = []
            if category_affinity is not None:
                feature_scores.append((0.15, category_affinity))
            if impact_affinity is not None:
                feature_scores.append((0.05, impact_affinity))
            if target_sector.strip() and candidate_sector.strip():
                feature_scores.append((0.05, sector_affinity))
            keyword_weight = 1.0 - sum(
                weight for weight, _ in feature_scores
            )
            similarity_score = round(
                keyword_weight * score.keyword_score
                + sum(weight * value for weight, value in feature_scores),
                6,
            )
            candidate = {
                "stock_code": stock_code,
                "company_name": topic.get("company_name", ""),
                "sector": candidate_sector,
                "category": candidate_category,
                "impact": candidate_impact,
                "scope": "own_company" if stock_code == target_stock_code else "other_company",
                "topic_id": topic.get("topic_id", ""),
                "event_id": event_id,
                "event_date": event_date_value,
                "name": event.get("name") or topic.get("name", ""),
                "keywords": event.get("keywords") or topic.get("keywords", []),
                "keyword_score": score.keyword_score,
                "similarity_score": similarity_score,
                "similarity_components": {
                    **score.components,
                    "keywordScore": score.keyword_score,
                    "sectorAffinity": sector_affinity,
                    "categoryAffinity": category_affinity,
                    "impactAffinity": impact_affinity,
                },
                "matched_keywords": list(score.matched_keywords),
                "matched_context_keywords": list(
                    score.matched_context_keywords
                ),
                "shared_sector_keywords": shared_sector_keywords,
                "article_count": int(event.get("article_count", 0)),
                "source_count": source_count,
                "representative_article": representative,
                "articles": event.get("articles", []),
                "origin": event.get("origin", topic.get("origin", "topic_model")),
            }
            candidate["similarity_reasons"] = [
                (
                    f"사건 핵심어 {len(score.matched_keywords)}/"
                    f"{len(query_tokens)} 일치: "
                    + ", ".join(score.matched_keywords)
                ),
                (
                    "같은 종목의 과거 Event"
                    if candidate["scope"] == "own_company"
                    else (
                        "업종 연관: " + ", ".join(shared_sector_keywords)
                        if shared_sector_keywords
                        else "지원 종목의 과거 Event"
                    )
                ),
                f"서로 다른 원문 출처 {source_count}곳",
            ]
            if score.matched_context_keywords:
                candidate["similarity_reasons"].insert(
                    1,
                    (
                        "추가 문맥어 일치: "
                        + ", ".join(score.matched_context_keywords)
                    ),
                )
            if category_affinity is not None:
                candidate["similarity_reasons"].insert(
                    -1,
                    (
                        f"사건 유형 일치: {candidate_category}"
                        if category_affinity == 1.0
                        else (
                            f"사건 유형 다름: 현재 {target_category}"
                            f" · 과거 {candidate_category}"
                        )
                    ),
                )
            if impact_affinity is not None:
                candidate["similarity_reasons"].insert(
                    -1,
                    (
                        f"영향 방향 일치: {candidate_impact}"
                        if impact_affinity == 1.0
                        else (
                            f"영향 방향 다름: 현재 {target_impact}"
                            f" · 과거 {candidate_impact}"
                        )
                    ),
                )
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
        "context_keywords": normalized_context_keywords,
        "target_sector": target_sector,
        "target_category": target_category,
        "target_impact": target_impact,
        "before": before.isoformat(),
        "selection_policy": "own_company_first_then_other_companies",
        "minimum_score": minimum_score,
        "minimum_sources": minimum_sources,
        "candidate_count": len(own_candidates) + len(external_candidates),
        "own_company_candidate_count": len(own_candidates),
        "other_company_candidate_count": len(external_candidates),
        "matches": selected,
    }
