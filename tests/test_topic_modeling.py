from __future__ import annotations

import unittest
from datetime import date

from collector.topic_modeling.event_labeling import (
    _candidate_phrases,
    _headline_clauses,
)
from collector.topic_modeling.results import (
    _same_issue_title,
    annotate_major_issues,
    build_topic_records,
    select_major_issues,
)
from collector.topic_modeling.tokenizer import KiwiTokenizer


def article(
    number: int,
    published_at: str,
    *,
    stock_code: str = "005930",
    title: str | None = None,
) -> dict:
    return {
        "document_id": f"doc-{number}",
        "stock_code": stock_code,
        "company_name": "삼성전자",
        "title": title or f"삼성전자 HBM 공급 계약 {number}",
        "published_at": published_at,
        "canonical_url": f"https://source{number % 3}.example/news/{number}",
        "source_url": "",
        "relevance_confidence": 0.8 + number / 100,
        "matched_queries": ["삼성전자 HBM"],
    }


class KiwiTokenizerTest(unittest.TestCase):
    def test_keeps_korean_content_words_and_removes_stopwords(self) -> None:
        tokens = KiwiTokenizer()("삼성전자가 올해 HBM 공급 계약을 확대했다")
        self.assertIn("삼성전자", tokens)
        self.assertIn("hbm", tokens)
        self.assertIn("공급", tokens)
        self.assertNotIn("올해", tokens)

    def test_event_candidates_include_multiword_phrases(self) -> None:
        tokenizer = KiwiTokenizer()
        candidates, coverage = _candidate_phrases(
            [
                {"title": "삼성전자 로봇 사업 조직 신설"},
                {"title": "삼성전자 로봇 사업 본격 추진"},
            ],
            tokenizer,
            "삼성전자",
        )
        self.assertIn("로봇 사업", candidates)
        self.assertEqual(coverage["로봇 사업"], 1.0)

    def test_headline_clause_removes_company_and_editorial_prefix(self) -> None:
        clauses = _headline_clauses(
            "[단독] 삼성전자, 대표이사 직속 RX사업추진실 신설…로봇사업 본격화",
            "삼성전자",
        )
        self.assertIn("대표이사 직속 RX사업추진실 신설", clauses)
        self.assertIn("로봇사업 본격화", clauses)

    def test_headline_clause_drops_truncated_tail_and_neutralizes_denial(self) -> None:
        self.assertNotIn(
            "폴더블폰 공개 준비 막",
            _headline_clauses("갤럭시 언팩…폴더블폰 공개 준비 막...", "삼성전자"),
        )
        self.assertIn(
            "인텔 오하이오 공장 인수설",
            _headline_clauses(
                "SK하이닉스, 인텔 오하이오 공장 인수설 사실무근",
                "SK하이닉스",
            ),
        )


class TopicResultTest(unittest.TestCase):
    def test_duplicate_headlines_for_the_same_event_are_detected(self) -> None:
        self.assertTrue(
            _same_issue_title(
                "삼성전자, 대표이사 직속 RX사업추진실 신설…로봇사업 본격화",
                "삼성전자, 대표이사 직속 RX사업추진실 신설…로봇 사업 본격 육성",
                "삼성전자",
            )
        )
        self.assertFalse(
            _same_issue_title(
                "삼성전자, 대표이사 직속 RX사업추진실 신설…로봇사업 본격화",
                "삼성전자 갤럭시 카드 공개, 금융 플랫폼 진출",
                "삼성전자",
            )
        )

    def test_stable_topic_uuid_does_not_depend_on_input_order(self) -> None:
        rows = [
            article(1, "2026-07-21T15:30:00+00:00"),
            article(2, "2026-07-21T16:30:00+00:00"),
        ]
        first = build_topic_records(rows, [4, 4], {4: ["HBM", "공급"]}, model_version="v1")
        second = build_topic_records(list(reversed(rows)), [9, 9], {9: ["HBM", "공급"]}, model_version="v1")
        self.assertEqual(first[0]["topic_id"], second[0]["topic_id"])
        self.assertNotEqual(first[0]["runtime_topic_id"], second[0]["runtime_topic_id"])

    def test_events_are_split_by_korean_calendar_date(self) -> None:
        rows = [
            article(1, "2026-07-21T14:59:00+00:00"),  # KST 7/21
            article(2, "2026-07-21T15:01:00+00:00"),  # KST 7/22
        ]
        topics = build_topic_records(rows, [1, 1], {1: ["HBM"]}, model_version="v1")
        self.assertEqual(
            [event["event_date"] for event in topics[0]["events"]],
            ["2026-07-22", "2026-07-21"],
        )

    def test_event_name_uses_keywords_instead_of_representative_headline(self) -> None:
        rows = [
            article(1, "2026-07-22T00:00:00+00:00", title="삼성전자 로봇 사업 조직 신설"),
            article(2, "2026-07-22T01:00:00+00:00", title="삼성전자 로봇 사업 본격 추진"),
        ]
        topics = build_topic_records(
            rows,
            [1, 1],
            {1: ["사업", "신설"]},
            model_version="v1",
            event_keyword_tokenizer=KiwiTokenizer(),
        )
        event = topics[0]["events"][0]
        self.assertEqual(event["name"], "로봇 · 사업 · 조직")
        self.assertNotEqual(event["name"], event["representative_article"]["title"])

    def test_outliers_are_not_merged_into_a_fake_topic(self) -> None:
        rows = [
            article(1, "2026-07-21T00:00:00+00:00"),
            article(2, "2026-07-21T00:00:00+00:00"),
        ]
        topics = build_topic_records(rows, [-1, -1], {}, model_version="v1")
        self.assertEqual(len(topics), 2)
        self.assertTrue(all(topic["is_outlier"] for topic in topics))

    def test_major_issues_expand_7_then_14_then_30_days(self) -> None:
        rows = [
            article(1, "2026-07-22T00:00:00+00:00", title="삼성전자 HBM 공급 계약"),
            article(2, "2026-07-22T01:00:00+00:00", title="HBM 장기 공급 확대"),
            article(3, "2026-07-12T00:00:00+00:00", title="삼성전자 로봇 조직 신설"),
            article(4, "2026-07-12T01:00:00+00:00", title="휴머노이드 사업 확대"),
            article(5, "2026-07-02T00:00:00+00:00", title="삼성전자 임금 교섭 시작"),
            article(6, "2026-07-02T01:00:00+00:00", title="노사 협상 일정 발표"),
        ]
        topics = build_topic_records(
            rows,
            [1, 1, 2, 2, 3, 3],
            {1: ["최근"], 2: ["중기"], 3: ["장기"]},
            model_version="v1",
        )
        issues, used_window = select_major_issues(
            topics, as_of=date(2026, 7, 22), min_articles=2
        )
        self.assertEqual([issue["selection_window_days"] for issue in issues], [7, 14, 30])
        self.assertEqual(used_window, 30)
        self.assertTrue(all(issue["model_version"] == "v1" for issue in issues))
        self.assertTrue(all(issue["as_of"] == "2026-07-22" for issue in issues))
        annotate_major_issues(topics, issues)
        self.assertEqual(
            sorted(topic["major_issue"]["rank"] for topic in topics), [1, 2, 3]
        )


if __name__ == "__main__":
    unittest.main()
