"""현재 Event보다 과거인 후보만 대상으로 하는 embedding 검색."""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Mapping, Sequence


RETRIEVAL_SCHEMA_VERSION = "event-embedding-retrieval-v1"


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("비교할 embedding은 같은 양의 차원이어야 합니다.")
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _esg_subtypes(event: Mapping[str, Any]) -> set[str]:
    payload = event.get("esg_classification") or {}
    labels = payload.get("labels") if isinstance(payload, Mapping) else []
    return {
        str(label.get("subtype"))
        for label in labels or []
        if isinstance(label, Mapping) and label.get("subtype")
    }


def _diverse_top_k(
    candidates: Sequence[dict[str, Any]], *, limit: int
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    companies: set[str] = set()
    for candidate in candidates:
        stock_code = str(candidate.get("stock_code") or "")
        if stock_code in companies:
            continue
        selected.append(candidate)
        selected_ids.add(str(candidate["event_id"]))
        companies.add(stock_code)
        if len(selected) == limit:
            return selected
    for candidate in candidates:
        if str(candidate["event_id"]) in selected_ids:
            continue
        selected.append(candidate)
        if len(selected) == limit:
            break
    return selected


def search_similar_events(
    current_event: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    before: date,
    limit: int = 3,
    minimum_sources: int = 2,
    minimum_semantic_similarity: float = 0.0,
) -> dict[str, Any]:
    """시간·동일 Event 누수를 제거하고 의미/사건속성 유사도를 반환한다."""

    if limit < 1:
        raise ValueError("limit은 1 이상이어야 합니다.")
    query_embedding = current_event.get("embedding")
    if not isinstance(query_embedding, Sequence) or isinstance(query_embedding, str):
        raise ValueError("현재 Event embedding이 필요합니다.")
    current_id = str(current_event.get("event_id") or "")
    current_category = str(current_event.get("category") or "")
    current_sector = str(current_event.get("sector") or "")
    current_esg = _esg_subtypes(current_event)

    matches: list[dict[str, Any]] = []
    excluded = {"same_or_future": 0, "same_event": 0, "insufficient_sources": 0, "missing_embedding": 0}
    for source in candidates:
        event_id = str(source.get("event_id") or "")
        if current_id and event_id == current_id:
            excluded["same_event"] += 1
            continue
        try:
            event_date = date.fromisoformat(str(source.get("event_date") or ""))
        except ValueError:
            excluded["same_or_future"] += 1
            continue
        if event_date >= before:
            excluded["same_or_future"] += 1
            continue
        source_count = int(source.get("source_count") or 0)
        if source_count < minimum_sources:
            excluded["insufficient_sources"] += 1
            continue
        embedding = source.get("embedding")
        if not isinstance(embedding, Sequence) or isinstance(embedding, str):
            excluded["missing_embedding"] += 1
            continue
        semantic = _cosine(query_embedding, embedding)
        if semantic < minimum_semantic_similarity:
            continue

        candidate_category = str(source.get("category") or "")
        candidate_sector = str(source.get("sector") or "")
        candidate_esg = _esg_subtypes(source)
        category_affinity = float(
            bool(current_category) and current_category == candidate_category
        )
        sector_affinity = float(bool(current_sector) and current_sector == candidate_sector)
        esg_union = current_esg | candidate_esg
        esg_affinity = (
            len(current_esg & candidate_esg) / len(esg_union)
            if esg_union
            else 0.0
        )
        score = (
            0.80 * semantic
            + 0.10 * category_affinity
            + 0.05 * sector_affinity
            + 0.05 * esg_affinity
        )
        matches.append(
            {
                **dict(source),
                "semantic_similarity": round(semantic, 6),
                "similarity_score": round(score, 6),
                "similarity_components": {
                    "semantic": round(semantic, 6),
                    "categoryAffinity": category_affinity,
                    "sectorAffinity": sector_affinity,
                    "esgAffinity": round(esg_affinity, 6),
                },
                "similarity_reasons": [
                    f"Event 문장 의미 유사도 {semantic:.1%}",
                    f"서로 다른 원문 출처 {source_count}곳",
                ],
            }
        )
    matches.sort(
        key=lambda row: (
            -float(row["similarity_score"]),
            -int(row.get("source_count") or 0),
            str(row.get("event_date") or ""),
            str(row["event_id"]),
        )
    )
    return {
        "schema_version": RETRIEVAL_SCHEMA_VERSION,
        "retrieval_method": "embedding-rerank-v1",
        "query_event_id": current_id,
        "before": before.isoformat(),
        "matches": _diverse_top_k(matches, limit=limit),
        "eligible_candidate_count": len(matches),
        "excluded_candidate_counts": excluded,
    }
