"""고정 fixture 또는 JSON judgment로 Event 검색 품질을 비교한다."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from collector.event_retrieval.evaluation import evaluate_rankings


TOKEN_PATTERN = re.compile(r"[가-힣a-z0-9]+")


def _keyword_rank(
    query: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> list[str]:
    query_tokens = set(TOKEN_PATTERN.findall(str(query["text"]).casefold()))
    ranked = sorted(
        candidates,
        key=lambda row: (
            -len(
                query_tokens
                & set(TOKEN_PATTERN.findall(str(row["text"]).casefold()))
            ),
            str(row["event_id"]),
        ),
    )
    return [str(row["event_id"]) for row in ranked]


def _embedding_rank(
    query: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> list[str]:
    vector = list(query["embedding"])
    ranked = sorted(
        candidates,
        key=lambda row: (
            -sum(
                float(left) * float(right)
                for left, right in zip(vector, row["embedding"])
            ),
            str(row["event_id"]),
        ),
    )
    return [str(row["event_id"]) for row in ranked]


def fixture_payload() -> dict[str, Any]:
    """배선 검증용 소형 fixture. 실제 운영 승격 근거로 사용할 수 없다."""

    return {
        "queries": [
            {
                "query_id": "q-recall",
                "text": "고객 정보가 외부로 새어 나간 보안 사고",
                "embedding": [1.0, 0.0, 0.0],
            },
            {
                "query_id": "q-environment",
                "text": "공장 유해 물질 방류",
                "embedding": [0.0, 1.0, 0.0],
            },
        ],
        "candidates": [
            {
                "event_id": "privacy-breach",
                "text": "대규모 개인정보 유출",
                "embedding": [0.98, 0.02, 0.0],
            },
            {
                "event_id": "factory-pollution",
                "text": "사업장 폐수 오염 적발",
                "embedding": [0.0, 0.97, 0.03],
            },
            {
                "event_id": "new-product",
                "text": "신제품 외부 공개",
                "embedding": [0.0, 0.0, 1.0],
            },
        ],
        "judgments": {
            "q-recall": {"privacy-breach": 3},
            "q-environment": {"factory-pollution": 3},
        },
    }


def evaluate_payload(payload: Mapping[str, Any], *, k: int = 3) -> dict[str, Any]:
    queries = list(payload.get("queries") or [])
    candidates = list(payload.get("candidates") or [])
    judgments = dict(payload.get("judgments") or {})
    keyword_rankings = {
        str(query["query_id"]): _keyword_rank(query, candidates) for query in queries
    }
    embedding_rankings = {
        str(query["query_id"]): _embedding_rank(query, candidates) for query in queries
    }
    keyword_metrics = evaluate_rankings(keyword_rankings, judgments, k=k)
    embedding_metrics = evaluate_rankings(embedding_rankings, judgments, k=k)
    metric = f"ndcg@{k}"
    delta = float(embedding_metrics[metric]) - float(keyword_metrics[metric])
    is_fixture = bool(payload.get("is_fixture"))
    return {
        "schema_version": "event-retrieval-evaluation-v1",
        "evaluation_kind": "fixture" if is_fixture else "labeled-corpus",
        "keyword_baseline": keyword_metrics,
        "embedding_candidate": embedding_metrics,
        "ndcg_delta": round(delta, 6),
        "production_gate": {
            "passed": bool(not is_fixture and len(queries) >= 30 and delta > 0),
            "requirements": [
                "사람이 판정한 query 30개 이상",
                f"embedding {metric}가 keyword 기준선보다 높음",
                "시간 누수 및 동일 Event 제외 테스트 통과",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    if args.fixture == bool(args.input):
        parser.error("--fixture 또는 --input 중 하나만 지정해야 합니다.")
    if args.fixture:
        payload = {**fixture_payload(), "is_fixture": True}
    else:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(evaluate_payload(payload, k=args.k), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
