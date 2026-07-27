from __future__ import annotations

import unittest
from datetime import date, timedelta

from collector.risk_model.validation import (
    leave_one_group_out_splits,
    walk_forward_splits,
)


def rows(count: int) -> list[dict]:
    start = date(2020, 1, 1)
    return [
        {
            "event_id": f"event-{index}",
            "event_date": (start + timedelta(days=index)).isoformat(),
            "stock_code": "A" if index % 2 else "B",
            "event_category": "risk" if index % 3 else "growth",
        }
        for index in range(count)
    ]


class RiskValidationTest(unittest.TestCase):
    def test_walk_forward_never_uses_future_in_train(self) -> None:
        splits = walk_forward_splits(
            rows(30),
            minimum_train_events=10,
            validation_events=5,
            test_events=5,
        )
        self.assertEqual(len(splits), 3)
        for split in splits:
            self.assertLess(
                max(row["event_date"] for row in split["train"]),
                min(row["event_date"] for row in split["validation"]),
            )
            self.assertLess(
                max(row["event_date"] for row in split["validation"]),
                min(row["event_date"] for row in split["test"]),
            )

    def test_company_and_category_can_be_held_out(self) -> None:
        for key in ("stock_code", "event_category"):
            splits = leave_one_group_out_splits(rows(12), group_key=key)
            for split in splits:
                self.assertNotIn(
                    split["held_out_group"],
                    {row[key] for row in split["train"]},
                )
