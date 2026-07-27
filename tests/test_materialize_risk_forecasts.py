from __future__ import annotations

import unittest
from datetime import date

from collector.jobs.materialize_risk_forecasts import (
    _dataset_version,
    _enrich_abnormal_returns,
    _forecast_evidence_events,
)


class MaterializeRiskForecastTest(unittest.TestCase):
    def test_dataset_version_is_deterministic_and_evidence_sensitive(self) -> None:
        events = [
            {
                "eventId": "one",
                "eventDate": "2024-01-01",
                "similarityScore": 0.8,
                "priceReaction": {"returns": {"d5": -2}},
            }
        ]
        self.assertEqual(_dataset_version(events), _dataset_version(events))
        changed = [{**events[0], "similarityScore": 0.9}]
        self.assertNotEqual(_dataset_version(events), _dataset_version(changed))

    def test_enriches_market_adjusted_returns(self) -> None:
        dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09"]
        stock = [
            {"trading_date": value, "close_price": 100 + index * 2}
            for index, value in enumerate(dates)
        ]
        benchmark = [
            {"trading_date": value, "close_price": 100 + index}
            for index, value in enumerate(dates)
        ]
        events = [{
            "eventId": "one",
            "stockCode": "005930",
            "eventDate": "2024-01-02",
            "representativeArticle": {"publishedAt": "2024-01-02T10:00:00+09:00"},
            "priceReaction": {"returns": {"d1": 2.0}},
        }]

        result = _enrich_abnormal_returns(
            events,
            stock_prices={"005930": stock},
            benchmark_prices=benchmark,
        )

        self.assertIn("abnormalReturns", result[0]["priceReaction"])
        self.assertAlmostEqual(result[0]["priceReaction"]["abnormalReturns"]["d1"], 1.0)

    def test_forecast_pool_can_exceed_four_ui_events(self) -> None:
        topics = []
        for index in range(10):
            article = {
                "document_id": f"doc-{index}",
                "title": "반도체 수출 규제 강화",
                "summary": "",
                "published_at": f"2024-01-{index + 1:02d}T00:00:00+09:00",
            }
            topics.append({
                "stock_code": f"{index:06d}",
                "company_name": f"회사{index}",
                "sector": "반도체",
                "topic_id": f"topic-{index}",
                "name": "반도체 수출 규제",
                "keywords": ["반도체", "수출", "규제"],
                "is_outlier": False,
                "events": [{
                    "event_id": f"event-{index}",
                    "event_date": f"2024-01-{index + 1:02d}",
                    "name": "반도체 수출 규제",
                    "keywords": ["반도체", "수출", "규제"],
                    "article_count": 2,
                    "source_count": 2,
                    "representative_article": article,
                    "articles": [article],
                }],
            })
        result = {
            "target": {
                "stockCode": "005930",
                "eventId": "current",
                "eventDate": "2026-01-01",
                "searchKeywords": ["반도체", "수출", "규제"],
            },
            "events": [],
        }

        evidence = _forecast_evidence_events(
            result,
            saved_topics=topics,
            minimum_event_date=date(2020, 1, 1),
        )

        self.assertGreater(len(evidence), 4)
