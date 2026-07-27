from __future__ import annotations

import unittest
from datetime import date

from collector.event_retrieval.evaluation import evaluate_rankings
from collector.event_retrieval.search import search_similar_events
from collector.jobs.evaluate_event_retrieval import evaluate_payload, fixture_payload


class EventRetrievalTest(unittest.TestCase):
    def test_future_same_event_and_single_source_are_excluded(self) -> None:
        current = {
            "event_id": "current",
            "embedding": [1.0, 0.0],
            "category": "사고·분쟁",
            "sector": "반도체",
        }
        candidates = [
            {"event_id": "current", "event_date": "2024-01-01", "source_count": 2, "embedding": [1.0, 0.0]},
            {"event_id": "future", "event_date": "2026-08-01", "source_count": 2, "embedding": [1.0, 0.0]},
            {"event_id": "weak-source", "event_date": "2024-01-01", "source_count": 1, "embedding": [1.0, 0.0]},
            {
                "event_id": "valid",
                "stock_code": "000660",
                "event_date": "2024-01-01",
                "source_count": 3,
                "embedding": [0.9, 0.1],
                "category": "사고·분쟁",
                "sector": "반도체",
            },
        ]

        result = search_similar_events(
            current, candidates, before=date(2026, 7, 27)
        )

        self.assertEqual([row["event_id"] for row in result["matches"]], ["valid"])
        self.assertEqual(result["excluded_candidate_counts"]["same_event"], 1)
        self.assertEqual(result["excluded_candidate_counts"]["same_or_future"], 1)
        self.assertEqual(result["excluded_candidate_counts"]["insufficient_sources"], 1)

    def test_results_prefer_company_diversity(self) -> None:
        current = {"event_id": "q", "embedding": [1.0, 0.0]}
        candidates = [
            {"event_id": "a", "stock_code": "A", "event_date": "2024-01-01", "source_count": 3, "embedding": [1.0, 0.0]},
            {"event_id": "b", "stock_code": "A", "event_date": "2023-01-01", "source_count": 3, "embedding": [0.99, 0.01]},
            {"event_id": "c", "stock_code": "B", "event_date": "2022-01-01", "source_count": 3, "embedding": [0.8, 0.2]},
        ]

        result = search_similar_events(
            current, candidates, before=date(2026, 1, 1), limit=2
        )

        self.assertEqual([row["event_id"] for row in result["matches"]], ["a", "c"])

    def test_ranking_metrics(self) -> None:
        result = evaluate_rankings(
            {"q": ["best", "irrelevant", "related"]},
            {"q": {"best": 3, "related": 1}},
            k=3,
        )

        self.assertEqual(result["precision@3"], 0.666667)
        self.assertGreater(result["ndcg@3"], 0.9)

    def test_fixture_cannot_pass_production_gate(self) -> None:
        result = evaluate_payload(
            {**fixture_payload(), "is_fixture": True},
            k=3,
        )

        self.assertFalse(result["production_gate"]["passed"])
        self.assertEqual(result["evaluation_kind"], "fixture")
