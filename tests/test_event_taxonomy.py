from __future__ import annotations

import unittest

from collector.event_taxonomy import classify_esg_event


class EventTaxonomyTest(unittest.TestCase):
    def test_multiple_dimensions_keep_evidence(self) -> None:
        result = classify_esg_event(
            {
                "name": "공장 폐수 오염과 내부통제 부실",
                "articles": [
                    {
                        "title": "폐기물 처리 공시 위반도 확인",
                        "summary": "",
                    }
                ],
            }
        )

        self.assertEqual(result["dimensions"], ["E", "G"])
        self.assertTrue(result["is_esg_related"])
        subtypes = {label["subtype"] for label in result["labels"]}
        self.assertIn("pollution_waste", subtypes)
        self.assertIn("board_control", subtypes)
        self.assertIn("accounting_disclosure", subtypes)

    def test_non_esg_product_launch_is_not_forced_into_esg(self) -> None:
        result = classify_esg_event(
            {"name": "신형 스마트폰 공개", "keywords": ["출시", "판매"]}
        )

        self.assertFalse(result["is_esg_related"])
        self.assertEqual(result["labels"], [])
        self.assertIn("주가 방향 예측이 아닙니다", result["disclaimer"])

    def test_invalid_threshold_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            classify_esg_event({}, minimum_matches=0)
