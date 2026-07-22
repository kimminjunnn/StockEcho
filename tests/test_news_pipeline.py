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

    def test_meaningful_company_event_is_eligible(self) -> None:
        article = normalize_item(
            make_item(
                title="삼성전자 노조, 임금협상 결렬로 파업 예고",
                description="삼성전자 노조가 총파업 일정을 논의한다.",
            )
        )
        result = classify_relevance(article, get_company("005930"))
        self.assertEqual(result.status, "eligible")
        self.assertGreaterEqual(result.confidence, 0.65)
        self.assertIn("event_signal:+0.10", result.evidence)

    def test_market_roundup_is_rejected(self) -> None:
        article = normalize_item(
            make_item(
                title="코스피 급등…삼성전자·SK하이닉스 동반 상승",
                description="반도체주가 강세를 보였다.",
            )
        )
        result = classify_relevance(article, get_company("005930"))
        self.assertEqual(result.status, "rejected")
        self.assertIn("market_roundup:-0.35", result.evidence)

    def test_market_slang_and_leverage_product_are_rejected(self) -> None:
        company = get_company("000660")
        market = normalize_item(
            make_item(
                title="SK하이닉스, 장중 200만닉스 탈환…반도체 훈풍",
                description="주가가 동반 강세를 보였다.",
            )
        )
        product = normalize_item(
            make_item(
                title="자산운용사, SK하이닉스 레버리지 상품 출시",
                description="투자 상품이 시장의 주목을 받고 있다.",
                url="https://example.com/news/leverage",
            )
        )
        self.assertEqual(classify_relevance(market, company).status, "rejected")
        self.assertNotEqual(classify_relevance(product, company).status, "eligible")

    def test_commercial_and_ceremonial_articles_are_rejected(self) -> None:
        company = get_company("005930")
        commercial = normalize_item(
            make_item(
                title="삼성전자 감사 할인 페스티벌 진행",
                description="구매 고객에게 사은품을 제공한다.",
            )
        )
        ceremonial = normalize_item(
            make_item(
                title="삼성전자, 8년 연속 에너지대상 수상",
                description="고효율 가전 성과를 인정받았다.",
                url="https://example.com/news/ceremony",
            )
        )
        self.assertEqual(classify_relevance(commercial, company).status, "rejected")
        self.assertEqual(classify_relevance(ceremonial, company).status, "rejected")

    def test_expanded_query_requires_company_and_topic_context(self) -> None:
        company = get_company("005930")
        relevant = normalize_item(
            make_item(
                title="삼성전자, AI 로봇 사업 조직 신설",
                description="피지컬 AI 제품 개발을 확대한다.",
            )
        )
        missing_topic = normalize_item(
            make_item(
                title="삼성전자, 갤럭시 신제품 공개",
                description="모바일 신제품을 선보였다.",
                url="https://example.com/news/missing-topic",
            )
        )
        relevant_result = classify_relevance(
            relevant,
            company,
            query_text="삼성전자 AI",
            query_type="product",
            link_weight=0.8,
        )
        missing_result = classify_relevance(
            missing_topic,
            company,
            query_text="삼성전자 AI",
            query_type="product",
            link_weight=0.8,
        )
        self.assertEqual(relevant_result.status, "eligible")
        self.assertEqual(relevant_result.relation_type, "product")
        self.assertEqual(missing_result.status, "rejected")
        self.assertIn("topic_not_mentioned:-0.45", missing_result.evidence)

    def test_expanded_query_allows_non_contiguous_topic_terms(self) -> None:
        article = normalize_item(
            make_item(
                title="삼성전자, 반도체 장비의 중국 수출을 추가로 규제",
                description="정부 조치에 대응 방안을 마련한다.",
            )
        )

        result = classify_relevance(
            article,
            get_company("005930"),
            query_text="삼성전자 반도체 수출 규제",
            query_type="event",
            link_weight=0.9,
        )

        self.assertEqual(result.status, "eligible")
        self.assertIn("topic_in_title:+0.25", result.evidence)

    def test_mixed_news_roundup_is_not_eligible(self) -> None:
        article = normalize_item(
            make_item(
                title="[비즈&] 삼성전자, 대표 직속 로봇사업 조직 신설 外",
                description="삼성전자가 RX 사업추진실을 신설했다.",
            )
        )
        result = classify_relevance(
            article,
            get_company("005930"),
            query_text="삼성전자 로봇",
            query_type="product",
            link_weight=0.95,
        )
        self.assertNotEqual(result.status, "eligible")
        self.assertIn("news_roundup:-0.45", result.evidence)


if __name__ == "__main__":
    unittest.main()
