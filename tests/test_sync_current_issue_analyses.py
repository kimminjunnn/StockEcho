from __future__ import annotations

import unittest

from collector.jobs.sync_current_issue_analyses import (
    request_from_issue,
    requests_from_snapshots,
)


class CurrentIssueAnalysisSyncTest(unittest.TestCase):
    def test_maps_current_snapshot_issue_to_analysis_request(self) -> None:
        request = request_from_issue(
            "005930",
            {
                "topicId": "topic",
                "eventId": "event",
                "eventDate": "2026-07-27",
                "name": "히트펌프 실증",
                "topicLabel": "에너지",
                "keywords": ["히트펌프", " 실증 "],
                "category": None,
                "impact": None,
            },
        )

        self.assertEqual(request.stock_code, "005930")
        self.assertEqual(request.keywords, ("히트펌프", "실증"))
        self.assertEqual(request.category, "")
        self.assertEqual(request.impact, "unknown")

    def test_limits_each_stock_without_mixing_snapshots(self) -> None:
        snapshots = [
            {
                "stock_code": "005930",
                "result": {
                    "issues": [
                        {
                            "topicId": f"topic-{index}",
                            "eventId": f"event-{index}",
                            "eventDate": "2026-07-27",
                            "name": f"사건 {index}",
                            "keywords": [f"키워드 {index}"],
                        }
                        for index in range(3)
                    ]
                },
            },
            {
                "stock_code": "000660",
                "result": {
                    "issues": [
                        {
                            "topicId": "topic-sk",
                            "eventId": "event-sk",
                            "eventDate": "2026-07-27",
                            "name": "반도체 사건",
                            "keywords": ["반도체"],
                        }
                    ]
                },
            },
        ]

        requests = requests_from_snapshots(snapshots, limit_per_stock=2)

        self.assertEqual(
            [(request.stock_code, request.event_id) for request in requests],
            [
                ("005930", "event-0"),
                ("005930", "event-1"),
                ("000660", "event-sk"),
            ],
        )

    def test_uses_name_when_snapshot_keywords_are_missing(self) -> None:
        request = request_from_issue(
            "005930",
            {
                "topicId": "topic",
                "eventId": "event",
                "eventDate": "2026-07-27",
                "name": "수주 계약",
                "keywords": [],
            },
        )

        self.assertEqual(request.keywords, ("수주 계약",))
