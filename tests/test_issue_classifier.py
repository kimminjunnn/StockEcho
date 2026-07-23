from __future__ import annotations

import json
import unittest

from collector.jobs.backfill_issue_classifications import classify_result
from collector.topic_modeling.issue_classifier import (
    IssueClassifierConfig,
    OpenAIIssueClassifier,
    classify_major_issues,
    fallback_category,
    select_evidence_articles,
    strong_category_hint,
)


def article(number: int, *, host: str, title: str) -> dict:
    return {
        "document_id": f"doc-{number}",
        "title": title,
        "summary": f"기사 요약 {number}",
        "published_at": "2026-07-23T00:00:00+00:00",
        "canonical_url": f"https://{host}/news/{number}",
        "source_url": "",
    }


def issue() -> dict:
    articles = [
        article(1, host="a.example", title="삼성전자 신규 HBM 공급 계약"),
        article(2, host="a.example", title="삼성전자 HBM 장기 공급 확대"),
        article(3, host="b.example", title="삼성전자 HBM 고객사 확대"),
    ]
    return {
        "stock_code": "005930",
        "company_name": "삼성전자",
        "event_id": "event-1",
        "event_date": "2026-07-23",
        "name": "HBM 공급 계약 확대",
        "topic_name": "HBM 공급 계약 확대",
        "keywords": ["HBM", "공급", "계약"],
        "representative_article": articles[0],
        "articles": articles,
    }


class FakeResponse:
    def __init__(self, result: dict) -> None:
        self._result = result

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(self._result, ensure_ascii=False),
                        }
                    ],
                }
            ]
        }


class FakeSession:
    def __init__(self, result: dict) -> None:
        self._result = result
        self.request: dict | None = None

    def post(self, url: str, **kwargs):
        self.request = {"url": url, **kwargs}
        return FakeResponse(self._result)


class IssueClassifierTests(unittest.TestCase):
    def test_selects_representative_then_diverse_sources(self) -> None:
        selected = select_evidence_articles(issue(), limit=2)
        self.assertEqual([row["document_id"] for row in selected], ["doc-1", "doc-3"])

    def test_fallback_category_uses_fixed_taxonomy(self) -> None:
        self.assertEqual(fallback_category(issue()), "수주·계약")

    def test_labor_negotiation_is_classified_as_dispute(self) -> None:
        labor_issue = issue()
        labor_issue["name"] = "성과급 협상 결렬"
        labor_issue["topic_name"] = "노사 갈등"
        labor_issue["keywords"] = ["성과급 협상", "노조 쟁의"]

        self.assertEqual(fallback_category(labor_issue), "사고·분쟁")

    def test_strong_category_hint_uses_central_issue_name(self) -> None:
        value = issue()
        value["name"] = "노조 파업 장기화"
        value["topic_name"] = "노조 파업 장기화"
        value["keywords"] = ["공급", "계약"]
        self.assertEqual(strong_category_hint(value), "사고·분쟁")

    def test_without_api_key_keeps_pipeline_ready_with_unknown_impact(self) -> None:
        enriched, summary = classify_major_issues(
            [issue()], config=IssueClassifierConfig(api_key="")
        )
        self.assertEqual(enriched[0]["category"], "수주·계약")
        self.assertEqual(enriched[0]["impact"], "unknown")
        self.assertEqual(enriched[0]["classification_method"], "rule-fallback-v1")
        self.assertEqual(summary["fallback_count"], 1)
        self.assertFalse(summary["enabled"])

    def test_openai_structured_result_is_validated_and_mapped(self) -> None:
        session = FakeSession(
            {
                "category": "수주·계약",
                "impact": "positive",
                "confidence": 0.86,
                "horizon": "medium_term",
                "reason": "장기 공급 확대는 매출 가시성을 높이지만 계약 규모는 확인이 필요합니다.",
                "evidence_document_ids": ["doc-1", "not-provided"],
            }
        )
        classifier = OpenAIIssueClassifier(
            IssueClassifierConfig(api_key="test-key", model="test-model"),
            session=session,
        )

        result = classifier.classify(issue())

        self.assertEqual(result["impact"], "positive")
        self.assertEqual(result["impact_confidence"], 0.86)
        self.assertEqual(result["impact_evidence_document_ids"], ["doc-1"])
        self.assertEqual(result["classification_model"], "test-model")
        self.assertIsNotNone(session.request)
        request_json = session.request["json"]
        self.assertTrue(request_json["text"]["format"]["strict"])
        self.assertEqual(request_json["text"]["format"]["type"], "json_schema")
        self.assertNotIn("test-key", json.dumps(request_json))

    def test_backfill_maps_camel_case_snapshot_to_classifier(self) -> None:
        class FakeClassifier:
            received: dict | None = None

            def classify(self, value: dict) -> dict:
                self.received = value
                return {
                    "category": "사고·분쟁",
                    "impact": "negative",
                    "impact_confidence": 0.9,
                    "impact_horizon": "short_term",
                    "impact_reason": "파업으로 생산 차질이 예상됩니다.",
                    "impact_evidence_document_ids": ["doc-1"],
                    "classification_method": "test-v1",
                    "classification_model": "test-model",
                }

        classifier = FakeClassifier()
        result = {
            "stockCode": "000660",
            "companyName": "SK하이닉스",
            "issues": [
                {
                    "eventId": "event-1",
                    "eventDate": "2026-07-23",
                    "name": "노조 파업",
                    "topicLabel": "노조 파업",
                    "keywords": ["파업"],
                    "representativeArticle": {
                        "documentId": "doc-1",
                        "title": "노조 파업 장기화",
                        "summary": "생산 차질이 발생했다.",
                        "publishedAt": "2026-07-23T00:00:00+00:00",
                        "canonicalUrl": "https://example.com/1",
                        "sourceUrl": "",
                    },
                    "articles": [],
                }
            ],
        }

        enriched = classify_result(result, classifier)

        self.assertEqual(classifier.received["stock_code"], "000660")
        self.assertEqual(
            classifier.received["representative_article"]["document_id"], "doc-1"
        )
        self.assertEqual(enriched["issues"][0]["impact"], "negative")
        self.assertEqual(enriched["issues"][0]["classificationModel"], "test-model")


if __name__ == "__main__":
    unittest.main()
