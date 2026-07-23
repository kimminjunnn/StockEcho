from __future__ import annotations

import unittest
from datetime import date

from collector.historical_events.search import search_historical_events


def topic(
    stock_code: str,
    company_name: str,
    *,
    topic_id: str,
    event_id: str,
    event_date: str,
    keywords: list[str],
    title: str,
    article_count: int = 2,
    sector: str = "",
    category: str = "",
    impact: str = "unknown",
) -> dict:
    article = {
        "document_id": f"doc-{event_id}",
        "title": title,
        "summary": "",
        "published_at": f"{event_date}T00:00:00+09:00",
    }
    return {
        "stock_code": stock_code,
        "company_name": company_name,
        "sector": sector,
        "topic_id": topic_id,
        "name": " · ".join(keywords),
        "keywords": keywords,
        "is_outlier": False,
        "events": [
            {
                "event_id": event_id,
                "event_date": event_date,
                "name": " · ".join(keywords),
                "keywords": keywords,
                "category": category,
                "impact": impact,
                "article_count": article_count,
                "source_count": 2,
                "representative_article": article,
                "articles": [article],
            }
        ],
    }


class HistoricalEventSearchTest(unittest.TestCase):
    def test_own_company_is_first_then_other_companies(self) -> None:
        topics = [
            topic(
                "005930",
                "삼성전자",
                topic_id="topic-own",
                event_id="event-own",
                event_date="2023-10-17",
                keywords=["반도체", "수출", "규제"],
                title="삼성전자 반도체 수출 규제 영향",
            ),
            topic(
                "000660",
                "SK하이닉스",
                topic_id="topic-sk",
                event_id="event-sk",
                event_date="2024-03-01",
                keywords=["반도체", "수출", "규제", "강화"],
                title="SK하이닉스 수출 규제 강화",
            ),
            topic(
                "035420",
                "NAVER",
                topic_id="topic-naver",
                event_id="event-naver",
                event_date="2022-06-01",
                keywords=["수출", "규제"],
                title="플랫폼 기업 수출 규제 검토",
            ),
        ]

        result = search_historical_events(
            topics,
            target_stock_code="005930",
            keywords=["반도체", "수출", "규제", "강화"],
            before=date(2026, 7, 22),
        )

        self.assertEqual(
            [match["event_id"] for match in result["matches"]],
            ["event-own", "event-sk", "event-naver"],
        )
        self.assertEqual(result["matches"][0]["scope"], "own_company")
        self.assertTrue(
            all(match["scope"] == "other_company" for match in result["matches"][1:])
        )

    def test_all_matches_can_be_other_companies_when_no_own_history_exists(self) -> None:
        topics = [
            topic(
                code,
                name,
                topic_id=f"topic-{code}",
                event_id=f"event-{code}",
                event_date=f"202{index}-01-01",
                keywords=["반도체", "수출", "규제"],
                title=f"{name} 반도체 수출 규제",
            )
            for index, (code, name) in enumerate(
                [("000660", "SK하이닉스"), ("005380", "현대차"), ("035420", "NAVER")],
                start=2,
            )
        ]

        result = search_historical_events(
            topics,
            target_stock_code="005930",
            keywords=["반도체", "수출", "규제"],
            before=date(2026, 7, 22),
        )

        self.assertEqual(len(result["matches"]), 3)
        self.assertTrue(all(match["scope"] == "other_company" for match in result["matches"]))
        self.assertEqual(result["own_company_candidate_count"], 0)

    def test_same_day_future_outlier_and_unmatched_events_are_excluded(self) -> None:
        valid = topic(
            "000660",
            "SK하이닉스",
            topic_id="topic-valid",
            event_id="event-valid",
            event_date="2025-01-01",
            keywords=["반도체", "규제"],
            title="반도체 규제 대응",
        )
        same_day = topic(
            "005930",
            "삼성전자",
            topic_id="topic-today",
            event_id="event-today",
            event_date="2026-07-22",
            keywords=["반도체", "규제"],
            title="현재 반도체 규제",
        )
        unmatched = topic(
            "005380",
            "현대차",
            topic_id="topic-car",
            event_id="event-car",
            event_date="2024-01-01",
            keywords=["전기차", "판매"],
            title="전기차 판매 확대",
        )
        outlier = topic(
            "035420",
            "NAVER",
            topic_id="topic-outlier",
            event_id="event-outlier",
            event_date="2023-01-01",
            keywords=["반도체", "규제"],
            title="반도체 규제",
        )
        outlier["is_outlier"] = True

        result = search_historical_events(
            [valid, same_day, unmatched, outlier],
            target_stock_code="005930",
            keywords=["반도체", "수출", "규제"],
            before=date(2026, 7, 22),
        )

        self.assertEqual([match["event_id"] for match in result["matches"]], ["event-valid"])

    def test_external_results_prefer_different_companies(self) -> None:
        topics = [
            topic(
                "000660",
                "SK하이닉스",
                topic_id="topic-sk-1",
                event_id="event-sk-1",
                event_date="2025-01-01",
                keywords=["반도체", "수출", "규제"],
                title="SK하이닉스 반도체 수출 규제",
                article_count=5,
            ),
            topic(
                "000660",
                "SK하이닉스",
                topic_id="topic-sk-2",
                event_id="event-sk-2",
                event_date="2024-01-01",
                keywords=["반도체", "수출", "규제"],
                title="SK하이닉스 과거 수출 규제",
                article_count=4,
            ),
            topic(
                "005380",
                "현대차",
                topic_id="topic-car",
                event_id="event-car",
                event_date="2023-01-01",
                keywords=["수출", "규제"],
                title="현대차 수출 규제",
            ),
        ]

        result = search_historical_events(
            topics,
            target_stock_code="005930",
            keywords=["반도체", "수출", "규제"],
            before=date(2026, 7, 22),
            limit=2,
        )

        self.assertEqual(
            [match["stock_code"] for match in result["matches"]],
            ["000660", "005380"],
        )

    def test_single_broad_keyword_does_not_pass_default_threshold(self) -> None:
        unrelated = topic(
            "000660",
            "SK하이닉스",
            topic_id="topic-bonus",
            event_id="event-bonus",
            event_date="2025-01-01",
            keywords=["반도체", "성과급", "노사"],
            title="반도체 기업 성과급 교섭",
        )

        result = search_historical_events(
            [unrelated],
            target_stock_code="005930",
            keywords=["반도체", "수출", "규제"],
            before=date(2026, 7, 22),
        )

        self.assertEqual(result["matches"], [])
        self.assertEqual(result["candidate_count"], 0)

    def test_requires_two_primary_keywords_for_multi_term_query(self) -> None:
        unrelated = topic(
            "000660",
            "SK하이닉스",
            topic_id="topic-bonus",
            event_id="event-bonus",
            event_date="2025-01-01",
            keywords=["성과급", "지급", "확대"],
            title="SK하이닉스 성과급 지급 확대",
        )

        result = search_historical_events(
            [unrelated],
            target_stock_code="005930",
            keywords=["성과급", "협상"],
            before=date(2026, 7, 22),
        )

        self.assertEqual(result["matches"], [])

    def test_context_keywords_break_primary_keyword_tie(self) -> None:
        generic = topic(
            "000270",
            "기아",
            topic_id="topic-generic",
            event_id="event-generic",
            event_date="2025-01-01",
            keywords=["성과급", "협상"],
            title="기아 성과급 협상",
        )
        contextual = topic(
            "005380",
            "현대차",
            topic_id="topic-context",
            event_id="event-context",
            event_date="2025-01-01",
            keywords=["성과급", "협상", "노사", "결렬"],
            title="현대차 노사 성과급 협상 결렬",
        )

        result = search_historical_events(
            [generic, contextual],
            target_stock_code="005930",
            keywords=["성과급", "협상"],
            context_keywords=["성과급", "협상", "노사", "결렬"],
            before=date(2026, 7, 22),
            limit=2,
        )

        self.assertEqual(result["matches"][0]["event_id"], "event-context")
        self.assertEqual(
            result["matches"][0]["matched_context_keywords"],
            ["결렬", "노사"],
        )

    def test_sector_affinity_is_a_weak_ranking_prior(self) -> None:
        unrelated = topic(
            "000270",
            "기아",
            topic_id="topic-car",
            event_id="event-car",
            event_date="2025-01-01",
            keywords=["수출", "규제"],
            title="기아 수출 규제",
            sector="자동차",
        )
        related = topic(
            "042700",
            "한미반도체",
            topic_id="topic-semiconductor",
            event_id="event-semiconductor",
            event_date="2025-01-01",
            keywords=["수출", "규제"],
            title="한미반도체 수출 규제",
            sector="반도체 장비",
        )

        result = search_historical_events(
            [unrelated, related],
            target_stock_code="005930",
            keywords=["수출", "규제"],
            target_sector="반도체 전자",
            before=date(2026, 7, 22),
            limit=2,
        )

        self.assertEqual(
            [match["event_id"] for match in result["matches"]],
            ["event-semiconductor", "event-car"],
        )
        self.assertGreater(
            result["matches"][0]["similarity_score"],
            result["matches"][1]["similarity_score"],
        )

    def test_event_category_reranks_lexically_equal_candidates(self) -> None:
        different_type = topic(
            "000270",
            "기아",
            topic_id="topic-product",
            event_id="event-product",
            event_date="2025-01-01",
            keywords=["배터리", "화재"],
            title="기아 배터리 화재",
            category="신제품·출시",
        )
        same_type = topic(
            "373220",
            "LG에너지솔루션",
            topic_id="topic-incident",
            event_id="event-incident",
            event_date="2025-01-01",
            keywords=["배터리", "화재"],
            title="LG에너지솔루션 배터리 화재",
            category="사고·분쟁",
        )

        result = search_historical_events(
            [different_type, same_type],
            target_stock_code="005930",
            keywords=["배터리", "화재"],
            target_category="사고·분쟁",
            before=date(2026, 7, 22),
            limit=2,
        )

        self.assertEqual(result["matches"][0]["event_id"], "event-incident")
        self.assertEqual(
            result["matches"][0]["similarity_components"]["categoryAffinity"],
            1.0,
        )

    def test_known_impact_direction_reranks_same_category(self) -> None:
        opposite = topic(
            "000270",
            "기아",
            topic_id="topic-positive",
            event_id="event-positive",
            event_date="2025-01-01",
            keywords=["공급", "계약"],
            title="기아 공급 계약",
            category="수주·계약",
            impact="positive",
        )
        same_direction = topic(
            "005380",
            "현대차",
            topic_id="topic-negative",
            event_id="event-negative",
            event_date="2025-01-01",
            keywords=["공급", "계약"],
            title="현대차 공급 계약",
            category="수주·계약",
            impact="negative",
        )

        result = search_historical_events(
            [opposite, same_direction],
            target_stock_code="005930",
            keywords=["공급", "계약"],
            target_category="수주·계약",
            target_impact="negative",
            before=date(2026, 7, 22),
            limit=2,
        )

        self.assertEqual(result["matches"][0]["event_id"], "event-negative")
        self.assertEqual(
            result["matches"][0]["similarity_components"]["impactAffinity"],
            1.0,
        )

    def test_representative_article_is_reselected_for_current_keywords(self) -> None:
        candidate = topic(
            "000660",
            "SK하이닉스",
            topic_id="topic-bonus",
            event_id="event-bonus",
            event_date="2025-01-01",
            keywords=["성과급", "노사", "협상"],
            title="SK하이닉스 실적 전망",
        )
        candidate["events"][0]["articles"].append(
            {
                "document_id": "doc-relevant",
                "title": "SK하이닉스 성과급 노사 협상 재개",
                "summary": "성과급 제도 이견을 논의한다.",
                "published_at": "2025-01-01T01:00:00+09:00",
                "relevance_confidence": 0.8,
            }
        )

        result = search_historical_events(
            [candidate],
            target_stock_code="005930",
            keywords=["성과급", "노사", "협상"],
            before=date(2026, 7, 22),
        )

        self.assertEqual(
            result["matches"][0]["representative_article"]["document_id"],
            "doc-relevant",
        )

    def test_requires_searchable_keywords(self) -> None:
        with self.assertRaises(ValueError):
            search_historical_events(
                [],
                target_stock_code="005930",
                keywords=[""],
                before=date(2026, 7, 22),
            )


if __name__ == "__main__":
    unittest.main()
