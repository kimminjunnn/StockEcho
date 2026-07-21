from __future__ import annotations

import unittest

from collector.companies import get_company
from collector.domain.search import QueryCompanyLink, SearchQuery
from collector.jobs.collect_news_query import _query_presence
from collector.normalize.news import normalize_item
from collector.query.keywords import KiwiKeywordExtractor
from collector.query.planner import build_query_plan
from collector.repositories.local import merge_jsonl, read_jsonl


def article(number: int, host: str, title: str, summary: str = ""):
    return normalize_item(
        {
            "title": title,
            "description": summary,
            "originallink": f"https://{host}/news/{number}",
            "link": f"https://{host}/news/{number}",
            "pubDate": "Tue, 21 Jul 2026 09:00:00 +0900",
        }
    )


class SearchQueryTest(unittest.TestCase):
    def test_query_id_is_stable_after_whitespace_normalization(self) -> None:
        links = (QueryCompanyLink("005930", 0.8, ("test",)),)
        left = SearchQuery.create("HBM   공급 부족", "event", links)
        right = SearchQuery.create("HBM 공급 부족", "event", links)
        self.assertEqual(left.query_id, right.query_id)
        self.assertEqual(left.text, "HBM 공급 부족")


class KeywordDiscoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.company = get_company("005930")
        cls.articles = [
            article(1, "one.example", "삼성전자 HBM 공급 부족 우려"),
            article(2, "two.example", "HBM 공급 부족, 반도체 업계 긴장", "삼성전자 대응"),
            article(3, "three.example", "삼성전자 HBM 신제품 양산", "반도체 공급 부족 지속"),
            article(4, "one.example", "삼성전자 갤럭시 신제품 출시"),
        ]
        cls.candidates = KiwiKeywordExtractor(max_active=5).extract(
            cls.company, cls.articles
        )

    def test_specific_keyword_can_be_active_but_broad_term_cannot(self) -> None:
        by_keyword = {candidate.keyword: candidate for candidate in self.candidates}
        self.assertEqual(by_keyword["HBM"].status, "active")
        self.assertNotEqual(by_keyword["반도체"].status, "active")

    def test_event_query_requires_observed_cooccurrence(self) -> None:
        by_keyword = {candidate.keyword: candidate for candidate in self.candidates}
        self.assertEqual(by_keyword["HBM 공급 부족"].kind, "event")
        self.assertEqual(by_keyword["HBM 공급 부족"].status, "active")
        self.assertGreaterEqual(by_keyword["HBM 공급 부족"].source_count, 2)

    def test_plan_contains_direct_query_and_at_most_five_expansions(self) -> None:
        plan = build_query_plan(self.company, self.candidates)
        self.assertEqual(plan[0].text, "삼성전자")
        self.assertEqual(plan[0].query_type, "company")
        self.assertLessEqual(len(plan[1:]), 5)
        self.assertNotIn("삼성", [query.text for query in plan])
        self.assertTrue(all(query.text.startswith("삼성전자 ") for query in plan[1:]))

    def test_ambiguous_group_alias_is_not_enough_for_company_link(self) -> None:
        ambiguous = article(9, "one.example", "삼성 로봇 사업 확대")
        confidence, evidence = _query_presence(
            ambiguous, "삼성전자 로봇", self.company
        )
        self.assertEqual(confidence, 0.2)
        self.assertEqual(evidence, "missing_company_or_topic_context")


class JsonlRepositoryTest(unittest.TestCase):
    def test_composite_key_prevents_duplicate_relation(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            first = {"document_id": "d1", "query_id": "q1", "value": 1}
            second = {"document_id": "d1", "query_id": "q1", "value": 2}
            self.assertEqual(
                merge_jsonl(path, [first], key_fields=("document_id", "query_id")), 1
            )
            self.assertEqual(
                merge_jsonl(path, [second], key_fields=("document_id", "query_id")), 0
            )
            self.assertEqual(read_jsonl(path)[0]["value"], 2)


if __name__ == "__main__":
    unittest.main()
