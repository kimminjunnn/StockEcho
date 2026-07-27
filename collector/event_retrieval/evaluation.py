"""Event 검색의 고정 relevance judgment 평가."""

from __future__ import annotations

import math
from typing import Mapping, Sequence


def precision_at_k(
    ranked_event_ids: Sequence[str],
    relevance: Mapping[str, int],
    *,
    k: int,
) -> float:
    if k < 1:
        raise ValueError("k는 1 이상이어야 합니다.")
    values = ranked_event_ids[:k]
    return sum(int(relevance.get(event_id, 0) > 0) for event_id in values) / k


def ndcg_at_k(
    ranked_event_ids: Sequence[str],
    relevance: Mapping[str, int],
    *,
    k: int,
) -> float:
    if k < 1:
        raise ValueError("k는 1 이상이어야 합니다.")

    def dcg(grades: Sequence[int]) -> float:
        return sum(
            (2**grade - 1) / math.log2(index + 2)
            for index, grade in enumerate(grades)
        )

    actual = [int(relevance.get(event_id, 0)) for event_id in ranked_event_ids[:k]]
    ideal = sorted((int(value) for value in relevance.values()), reverse=True)[:k]
    ideal_score = dcg(ideal)
    return dcg(actual) / ideal_score if ideal_score else 0.0


def evaluate_rankings(
    rankings: Mapping[str, Sequence[str]],
    judgments: Mapping[str, Mapping[str, int]],
    *,
    k: int = 3,
) -> dict[str, object]:
    query_ids = sorted(set(rankings) & set(judgments))
    if not query_ids:
        raise ValueError("평가 가능한 query가 없습니다.")
    per_query = {
        query_id: {
            f"precision@{k}": round(
                precision_at_k(rankings[query_id], judgments[query_id], k=k), 6
            ),
            f"ndcg@{k}": round(
                ndcg_at_k(rankings[query_id], judgments[query_id], k=k), 6
            ),
        }
        for query_id in query_ids
    }
    return {
        "query_count": len(query_ids),
        f"precision@{k}": round(
            sum(float(row[f"precision@{k}"]) for row in per_query.values())
            / len(per_query),
            6,
        ),
        f"ndcg@{k}": round(
            sum(float(row[f"ndcg@{k}"]) for row in per_query.values())
            / len(per_query),
            6,
        ),
        "per_query": per_query,
    }
