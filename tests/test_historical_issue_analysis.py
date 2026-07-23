from __future__ import annotations

import unittest
from datetime import date, timedelta

from collector.historical_events.keywords import (
    extract_core_keywords,
    extract_search_keywords,
)
from collector.historical_events.price_reaction import calculate_trading_day_returns


def weekday_prices(start: date, count: int) -> list[dict]:
    rows = []
    cursor = start
    close = 100
    while len(rows) < count:
        if cursor.weekday() < 5:
            rows.append({"trading_date": cursor, "close_price": close})
            close += 1
        cursor += timedelta(days=1)
    return rows


class HistoricalIssueKeywordTests(unittest.TestCase):
    def test_extracts_event_terms_without_company_or_generic_words(self) -> None:
        keywords = extract_core_keywords(
            name="삼성전자 갤럭시 폴더블 라인업 공개",
            topic_label="갤럭시 신제품 출시",
            keywords=["갤럭시 폴드", "라인업 확대", "폴더블 공개"],
            company_name="삼성전자",
        )

        self.assertEqual(keywords[0], "갤럭시")
        self.assertIn("폴더블", keywords)
        self.assertNotIn("삼성전자", keywords)
        self.assertNotIn("공개", keywords)

    def test_uses_first_representative_keyphrase_for_naver_query(self) -> None:
        search_keywords = extract_search_keywords(
            keywords=["성과급 협상", "성과급 갈등 점화", "노사 임단협"],
            core_keywords=["성과급", "재협상", "갈등", "노사"],
            company_name="SK하이닉스",
        )

        self.assertEqual(search_keywords, ["성과급", "협상"])


class TradingDayReturnTests(unittest.TestCase):
    def test_uses_trading_day_offsets_instead_of_calendar_days(self) -> None:
        rows = weekday_prices(date(2024, 5, 17), 40)
        result = calculate_trading_day_returns(
            rows,
            event_date=date(2024, 5, 20),
            representative_published_at="2024-05-20T09:00:00+09:00",
        )

        self.assertEqual(result["baseDate"], "2024-05-20")
        self.assertEqual(result["comparisonDates"]["d1"], "2024-05-21")
        self.assertEqual(result["comparisonDates"]["d5"], "2024-05-27")
        self.assertEqual(result["comparisonDates"]["d30"], "2024-07-01")
        self.assertEqual(result["status"], "complete")

    def test_weekend_event_uses_next_trading_day_as_base(self) -> None:
        rows = weekday_prices(date(2024, 5, 20), 35)
        result = calculate_trading_day_returns(
            rows,
            event_date=date(2024, 5, 18),
            representative_published_at="2024-05-18T09:00:00+09:00",
        )

        self.assertEqual(result["baseDate"], "2024-05-20")
        self.assertEqual(result["comparisonDates"]["d1"], "2024-05-21")

    def test_after_close_event_uses_next_trading_day(self) -> None:
        rows = weekday_prices(date(2024, 5, 20), 35)
        result = calculate_trading_day_returns(
            rows,
            event_date=date(2024, 5, 20),
            representative_published_at="2024-05-20T16:10:00+09:00",
        )

        self.assertEqual(result["baseDate"], "2024-05-21")

    def test_missing_future_prices_are_partial_not_fabricated(self) -> None:
        rows = weekday_prices(date(2024, 5, 20), 7)
        result = calculate_trading_day_returns(
            rows,
            event_date=date(2024, 5, 20),
            representative_published_at=None,
        )

        self.assertEqual(result["status"], "partial")
        self.assertIsNotNone(result["returns"]["d1"])
        self.assertIsNone(result["returns"]["d15"])
        self.assertIsNone(result["returns"]["d30"])


if __name__ == "__main__":
    unittest.main()
