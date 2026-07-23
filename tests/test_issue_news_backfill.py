from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from collector.clients.naver import NaverCredentials, NaverNewsClient
from collector.companies import get_company
from collector.historical_news.planner import build_issue_news_query_plan
from collector.jobs.backfill_issue_news import _cache_is_fresh, run
from collector.sources.base import SourceSearchResult


def news_item(company: str, number: int, *, event_date: str = "2024-03-01") -> dict:
    return {
        "title": f"{company}, 반도체 수출 규제 대응 {number}",
        "description": f"{company}가 반도체 수출 규제에 대응한다.",
        "originallink": f"https://source{number}.example/news/{company}/{number}",
        "link": f"https://source{number}.example/news/{company}/{number}",
        "pubDate": f"Fri, {event_date[-2:]} Mar 2024 09:00:00 +0900",
    }


class FakeNewsSource:
    name = "naver"

    def __init__(self, responses: dict[tuple[str, int], list[dict]]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def search(
        self,
        query: str,
        *,
        limit: int = 100,
        start: int = 1,
        sort: str = "date",
    ) -> SourceSearchResult:
        self.calls.append(
            {"query": query, "limit": limit, "start": start, "sort": sort}
        )
        items = self.responses.get((query, start), [])[:limit]
        return SourceSearchResult(
            source=self.name,
            payload={"total": len(items), "start": start, "display": len(items), "items": items},
            items=items,
        )


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"items": []}


class FakeSession:
    def __init__(self) -> None:
        self.params: dict | None = None

    def get(self, _url: str, *, headers: dict, params: dict, timeout: float) -> FakeResponse:
        self.params = params
        return FakeResponse()


class IssueNewsPlannerTest(unittest.TestCase):
    def test_builds_own_common_and_semiconductor_peer_queries(self) -> None:
        plan = build_issue_news_query_plan(
            get_company("005930"),
            ["반도체", "수출", "규제"],
        )

        self.assertEqual(plan.phrases, ("반도체 수출 규제", "반도체 수출 통제"))
        self.assertEqual(plan.own_queries[0].text, "삼성전자 반도체 수출 규제")
        self.assertEqual(plan.common_queries[0].text, "반도체 수출 규제")
        self.assertIn("000660", plan.peer_stock_codes)
        self.assertTrue(
            all(
                query.text.split()[0] != "삼성전자"
                for query in plan.peer_queries
            )
        )

    def test_naver_client_forwards_similarity_sort_and_start(self) -> None:
        session = FakeSession()
        client = NaverNewsClient(
            NaverCredentials("id", "secret"),
            session=session,
        )

        client.search_news("반도체 수출 규제", display=50, start=101, sort="sim")

        self.assertEqual(session.params["display"], 50)
        self.assertEqual(session.params["start"], 101)
        self.assertEqual(session.params["sort"], "sim")


class IssueNewsBackfillTest(unittest.TestCase):
    def test_cache_expires_after_quality_refresh_window(self) -> None:
        now = datetime.now(timezone.utc)

        self.assertTrue(_cache_is_fresh({"created_at": now.isoformat()}))
        self.assertFalse(
            _cache_is_fresh(
                {"created_at": (now - timedelta(hours=25)).isoformat()}
            )
        )
        self.assertFalse(_cache_is_fresh({"created_at": "invalid"}))

    def test_stops_after_one_own_and_three_external_company_proxies(self) -> None:
        responses = {
            ("삼성전자 반도체 수출 규제", 1): [
                news_item("삼성전자", 1),
                news_item("삼성전자", 2),
            ],
            ("반도체 수출 규제", 1): [
                news_item("SK하이닉스", 3),
                news_item("SK하이닉스", 4),
                news_item("한미반도체", 5),
                news_item("한미반도체", 6),
                news_item("NAVER", 7),
                news_item("NAVER", 8),
            ],
        }
        source = FakeNewsSource(responses)

        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            result = run(
                stock_code="005930",
                keywords=["반도체", "수출", "규제"],
                before=date(2026, 7, 22),
                result_limit=4,
                external_result_limit=3,
                source=source,
                project_root=project_root,
            )

            self.assertTrue(result["goal_met"])
            self.assertTrue(result["own_company_ready"])
            self.assertEqual(result["other_company_count"], 3)
            self.assertEqual(result["call_count"], 2)
            self.assertEqual(
                [call["phase"] for call in result["calls"]],
                ["own_company", "common_industry"],
            )
            self.assertTrue(all(call["sort"] == "sim" for call in source.calls))
            self.assertTrue(
                all(
                    event["representative_article"]
                    and event["articles"]
                    and event["keywords"]
                    for event in result["qualifying_event_proxies"]
                )
            )

            cached = run(
                stock_code="005930",
                keywords=["반도체", "수출", "규제"],
                before=date(2026, 7, 22),
                result_limit=4,
                external_result_limit=3,
                source=source,
                project_root=project_root,
            )
            self.assertTrue(cached["cache_hit"])
            self.assertEqual(len(source.calls), 2)

            refreshed = run(
                stock_code="005930",
                keywords=["반도체", "수출", "규제"],
                before=date(2026, 7, 22),
                refresh=True,
                source=source,
                project_root=project_root,
            )
            self.assertFalse(refreshed["cache_hit"])
            self.assertTrue(refreshed["goal_met"])
            self.assertEqual(len(source.calls), 4)

    def test_uses_peer_queries_only_when_common_search_is_insufficient(self) -> None:
        responses = {
            ("삼성전자 반도체 수출 규제", 1): [
                news_item("삼성전자", 1),
                news_item("삼성전자", 2),
            ],
            ("SK하이닉스 반도체 수출 규제", 1): [
                news_item("SK하이닉스", 3),
                news_item("SK하이닉스", 4),
            ],
        }
        source = FakeNewsSource(responses)

        with TemporaryDirectory() as directory:
            result = run(
                stock_code="005930",
                keywords=["반도체", "수출", "규제"],
                before=date(2026, 7, 22),
                result_limit=2,
                source=source,
                project_root=Path(directory),
            )

        self.assertTrue(result["goal_met"])
        self.assertEqual(result["other_company_count"], 1)
        self.assertEqual(result["calls"][-1]["phase"], "peer_company")
        self.assertEqual(result["calls"][-1]["query"], "SK하이닉스 반도체 수출 규제")


if __name__ == "__main__":
    unittest.main()
