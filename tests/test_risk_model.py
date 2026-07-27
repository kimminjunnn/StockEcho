from __future__ import annotations

import unittest

from collector.risk_model.empirical import empirical_risk_forecast
from collector.risk_model.metrics import expected_calibration_error
from collector.risk_model.training import evaluate_model, train_calibrated_model
from collector.jobs.evaluate_risk_models import evaluate_rows, fixture_rows


def rows(count: int, offset: int = 0) -> list[dict]:
    values = []
    for index in range(offset, offset + count):
        loss = int(index % 3 == 0 or index % 7 == 0)
        values.append(
            {
                "feature_text": "리콜 안전 결함" if loss else "신제품 수주 성장",
                "event_category": "사고·분쟁" if loss else "수주·계약",
                "impact_direction": "negative" if loss else "positive",
                "stock_code": f"{index % 4:06d}",
                "source_count": 2 + index % 3,
                "article_count": 3 + index % 5,
                "material_downside_label_d5": loss,
            }
        )
    return values


class RiskModelTest(unittest.TestCase):
    def test_empirical_forecast_returns_probability_and_range(self) -> None:
        events = [
            {
                "event_id": f"e{index}",
                "similarity_score": 0.9 - index * 0.05,
                "source_count": 3,
                "price_reaction": {
                    "abnormal_returns": {"d1": value, "d5": value * 1.5, "d20": value * 2}
                },
            }
            for index, value in enumerate([-5.0, -2.0, 1.0, 3.0])
        ]

        result = empirical_risk_forecast(events)
        d5 = result["horizons"]["d5"]

        self.assertEqual(d5["observed_event_count"], 4)
        self.assertGreater(d5["loss_probability"], 0.4)
        self.assertLess(d5["loss_probability"], 0.7)
        self.assertLessEqual(
            d5["return_percentiles"]["p10"], d5["return_percentiles"]["p90"]
        )
        self.assertEqual(d5["confidence"], "low")

    def test_sparse_evidence_is_not_production_eligible(self) -> None:
        result = empirical_risk_forecast([])
        self.assertFalse(result["horizons"]["d20"]["production_eligible"])
        self.assertEqual(result["horizons"]["d20"]["status"], "unavailable")

    def test_ece_for_perfect_probabilities_is_zero(self) -> None:
        self.assertEqual(expected_calibration_error([0, 1], [0.0, 1.0]), 0.0)

    def test_logistic_and_mlp_share_temporal_contract(self) -> None:
        train = rows(36)
        validation = rows(12, 36)
        test = rows(12, 48)
        for kind in ("logistic", "mlp"):
            model = train_calibrated_model(
                train,
                validation,
                kind=kind,
                label_key="material_downside_label_d5",
            )
            metrics = evaluate_model(model, test)
            self.assertEqual(set(metrics), {"pr_auc", "brier", "ece"})
            self.assertGreaterEqual(metrics["pr_auc"], 0.0)
            self.assertLessEqual(metrics["brier"], 1.0)

    def test_fixture_is_evaluated_but_never_promoted(self) -> None:
        report, _models = evaluate_rows(
            fixture_rows(),
            label_key="material_downside_label_d5",
            fixture=True,
        )

        self.assertEqual(report["split"]["strategy"], "chronological-holdout")
        self.assertFalse(report["production_gate"]["passed"])
        self.assertEqual(report["production_gate"]["selected_model"], "empirical")
