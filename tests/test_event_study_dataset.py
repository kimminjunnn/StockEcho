from __future__ import annotations

import unittest
from datetime import date, timedelta

from collector.event_study.dataset import (
    build_event_study_rows,
    dataset_hash,
    temporal_split,
)


def price_rows(start: date, closes: list[int]) -> list[dict]:
    rows = []
    cursor = start
    for close in closes:
        while cursor.weekday() >= 5:
            cursor += timedelta(days=1)
        rows.append({"trading_date": cursor, "close_price": close})
        cursor += timedelta(days=1)
    return rows


def event(event_id: str, event_date: str, published_values: list[str]) -> dict:
    articles = [
        {
            "document_id": f"{event_id}-{index}",
            "title": f"기사 {index}",
            "summary": "사건 설명",
            "published_at": published_at,
        }
        for index, published_at in enumerate(published_values)
    ]
    return {
        "event_id": event_id,
        "stock_code": "005930",
        "event_date": event_date,
        "name": "공급 계약",
        "category": "계약·수주",
        "source_count": 2,
        "article_count": len(articles),
        "representative_article": articles[0],
        "articles": articles,
    }


class EventStudyDatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stock = price_rows(
            date(2024, 1, 2),
            [100 + index for index in range(30)],
        )
        self.benchmark = price_rows(
            date(2024, 1, 2),
            [200 + index for index in range(30)],
        )

    def test_uses_only_documents_available_at_first_detection(self) -> None:
        rows = build_event_study_rows(
            [
                event(
                    "event-1",
                    "2024-01-02",
                    [
                        "2024-01-02T09:00:00+09:00",
                        "2024-01-02T13:00:00+09:00",
                    ],
                )
            ],
            stock_prices={"005930": self.stock},
            benchmark_prices=self.benchmark,
        )

        self.assertEqual(rows[0]["feature_document_ids"], ["event-1-0"])
        self.assertNotIn("기사 1", rows[0]["feature_text"])
        self.assertIsNotNone(rows[0]["return_d20"])
        self.assertIsNotNone(rows[0]["abnormal_return_d20"])

    def test_dataset_hash_is_independent_of_input_order(self) -> None:
        events = [
            event("event-2", "2024-01-03", ["2024-01-03T09:00:00+09:00"]),
            event("event-1", "2024-01-02", ["2024-01-02T09:00:00+09:00"]),
        ]
        first = build_event_study_rows(
            events,
            stock_prices={"005930": self.stock},
            benchmark_prices=self.benchmark,
        )
        second = build_event_study_rows(
            list(reversed(events)),
            stock_prices={"005930": self.stock},
            benchmark_prices=self.benchmark,
        )

        self.assertEqual(dataset_hash(first), dataset_hash(second))

    def test_temporal_split_never_reuses_an_event(self) -> None:
        rows = [
            {"event_id": "train", "event_date": "2023-12-31"},
            {"event_id": "validation", "event_date": "2024-06-30"},
            {"event_id": "test", "event_date": "2025-01-01"},
        ]

        split = temporal_split(
            rows,
            train_end=date(2023, 12, 31),
            validation_end=date(2024, 12, 31),
        )

        self.assertEqual([row["event_id"] for row in split["train"]], ["train"])
        self.assertEqual(
            [row["event_id"] for row in split["validation"]],
            ["validation"],
        )
        self.assertEqual([row["event_id"] for row in split["test"]], ["test"])

    def test_rejects_duplicate_event_ids(self) -> None:
        duplicate = event(
            "same",
            "2024-01-02",
            ["2024-01-02T09:00:00+09:00"],
        )
        with self.assertRaisesRegex(ValueError, "중복 Event ID"):
            build_event_study_rows(
                [duplicate, duplicate],
                stock_prices={"005930": self.stock},
                benchmark_prices=self.benchmark,
            )


if __name__ == "__main__":
    unittest.main()
