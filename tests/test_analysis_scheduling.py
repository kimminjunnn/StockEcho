from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from collector.repositories.supabase import _to_corpus_row, decide_analysis_schedule


class AnalysisSchedulingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 7, 22, 12, tzinfo=timezone.utc)

    def test_enqueues_after_five_new_articles(self) -> None:
        decision = decide_analysis_schedule(
            pending_article_count=5,
            last_analyzed_at=self.now - timedelta(hours=1),
            has_urgent_event=False,
            now=self.now,
        )
        self.assertTrue(decision.should_enqueue)
        self.assertEqual(decision.reason, "new_articles_threshold")

    def test_enqueues_stale_stock_with_one_new_article(self) -> None:
        decision = decide_analysis_schedule(
            pending_article_count=1,
            last_analyzed_at=self.now - timedelta(hours=24),
            has_urgent_event=False,
            now=self.now,
        )
        self.assertTrue(decision.should_enqueue)
        self.assertEqual(decision.reason, "stale_with_new_articles")

    def test_urgent_event_bypasses_article_threshold(self) -> None:
        decision = decide_analysis_schedule(
            pending_article_count=1,
            last_analyzed_at=self.now,
            has_urgent_event=True,
            now=self.now,
        )
        self.assertTrue(decision.should_enqueue)
        self.assertEqual(decision.priority, 10)

    def test_waits_when_initial_corpus_is_too_small(self) -> None:
        decision = decide_analysis_schedule(
            pending_article_count=4,
            last_analyzed_at=None,
            has_urgent_event=False,
            now=self.now,
        )
        self.assertFalse(decision.should_enqueue)
        self.assertEqual(decision.reason, "waiting_for_initial_articles")

    def test_does_nothing_without_new_articles(self) -> None:
        decision = decide_analysis_schedule(
            pending_article_count=0,
            last_analyzed_at=self.now - timedelta(days=10),
            has_urgent_event=True,
            now=self.now,
        )
        self.assertFalse(decision.should_enqueue)

    def test_builds_topic_corpus_row_from_supabase_article(self) -> None:
        row = _to_corpus_row(
            {
                "document_id": "news_1",
                "source": "naver",
                "title": "삼성전자, HBM 공급 확대",
                "summary": "신규 계약을 체결했다.",
                "published_at": self.now,
                "canonical_url": "https://example.com/1",
                "original_url": "https://example.com/1",
                "source_url": "https://example.com/1",
                "content_hash": "hash",
                "confidence": 0.91,
                "evidence": ["company_in_title:+0.65"],
                "matched_queries": ["삼성전자", "삼성전자 HBM"],
                "rule_version": "relevance-v2",
            },
            stock_code="005930",
            company_name="삼성전자",
        )
        self.assertEqual(row["published_at"], self.now.isoformat())
        self.assertEqual(row["stock_code"], "005930")
        self.assertEqual(row["relevance_confidence"], 0.91)
        self.assertIn("HBM 공급 확대", row["text"])


if __name__ == "__main__":
    unittest.main()
