from __future__ import annotations

import unittest

from collector.companies import get_company
from collector.normalize.news import normalize_item, normalize_items, normalize_url
from collector.relevance.rules import classify_relevance
from collector.repositories.local import (
    NaverCheckpoint,
    select_new_articles,
    updated_checkpoint,
)


def make_item(
    *,
    title: str = "<b>삼성전자</b>, 신제품 공개",
    description: str = "삼성전자가 신제품을 공개했다.",
    url: str = "https://example.com/news/1?utm_source=test",
) -> dict:
    return {
        "title": title,
        "description": description,
        "originallink": url,
        "link": url,
        "pubDate": "Tue, 21 Jul 2026 09:00:00 +0900",
    }


class NewsNormalizationTest(unittest.TestCase):
    def test_normalize_url_removes_tracking_and_fragment(self) -> None:
        actual = normalize_url(
            "HTTPS://Example.COM/news/1?utm_source=test&id=7#section"
        )
        self.assertEqual(actual, "https://example.com/news/1?id=7")

    def test_normalize_items_removes_duplicate_url(self) -> None:
        articles = normalize_items([make_item(), make_item()])
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "삼성전자, 신제품 공개")
        self.assertEqual(articles[0].published_at, "2026-07-21T00:00:00+00:00")


class IncrementalCollectionTest(unittest.TestCase):
    def test_known_url_is_not_selected_again(self) -> None:
        article = normalize_item(make_item())
        checkpoint = NaverCheckpoint(recent_urls=[article.canonical_url])
        self.assertEqual(select_new_articles([article], checkpoint), [])

    def test_checkpoint_keeps_current_and_previous_urls(self) -> None:
        article = normalize_item(make_item())
        previous = NaverCheckpoint(recent_urls=["https://example.com/old"])
        current = updated_checkpoint([article], previous, "payload-hash")
        self.assertEqual(current.recent_urls[0], article.canonical_url)
        self.assertIn("https://example.com/old", current.recent_urls)
        self.assertEqual(current.payload_hash, "payload-hash")


class RelevanceRuleTest(unittest.TestCase):
    def test_title_mention_has_stronger_confidence(self) -> None:
        company = get_company("005930")
        title_article = normalize_item(make_item())
        summary_article = normalize_item(
            make_item(
                title="신제품 공개",
                description="삼성전자가 신제품을 공개했다.",
                url="https://example.com/news/2",
            )
        )

        title_result = classify_relevance(title_article, company)
        summary_result = classify_relevance(summary_article, company)

        self.assertEqual(title_result.relation_type, "direct")
        self.assertGreater(title_result.confidence, summary_result.confidence)

    def test_no_company_name_is_irrelevant(self) -> None:
        article = normalize_item(
            make_item(
                title="지역 청년 취업 지원",
                description="지역 청년을 위한 지원 사업이다.",
            )
        )
        result = classify_relevance(article, get_company("005930"))
        self.assertEqual(result.relation_type, "irrelevant")


if __name__ == "__main__":
    unittest.main()
