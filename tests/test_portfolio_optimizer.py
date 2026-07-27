from __future__ import annotations

import unittest

from collector.portfolio.optimizer import (
    build_esg_efficient_frontier,
    build_event_safety_frontier,
    optimize_portfolio,
)


INPUTS = {
    "asset_ids": ["risky", "safe", "cash"],
    "current_weights": [0.5, 0.4, 0.1],
    "covariance": [
        [0.09, 0.01, 0.0],
        [0.01, 0.04, 0.0],
        [0.0, 0.0, 0.0],
    ],
    "safety_scores": [0.2, 0.85, 1.0],
    "maximum_weight": [0.6, 0.7, 0.4],
    "maximum_turnover": 0.3,
    "minimum_cash": 0.1,
    "cash_index": 2,
}


class PortfolioOptimizerTest(unittest.TestCase):
    def test_solution_satisfies_all_constraints_and_is_deterministic(self) -> None:
        first = optimize_portfolio(
            **INPUTS,
            safety_preference=0.05,
            minimum_safety=0.55,
        )
        second = optimize_portfolio(
            **INPUTS,
            safety_preference=0.05,
            minimum_safety=0.55,
        )

        self.assertEqual(first["status"], "optimal")
        self.assertEqual(first["weights"], second["weights"])
        self.assertAlmostEqual(sum(first["weights"].values()), 1.0)
        self.assertLessEqual(first["metrics"]["turnover"], 0.3 + 1e-6)
        self.assertGreaterEqual(first["weights"]["cash"], 0.1 - 1e-6)
        self.assertGreaterEqual(first["metrics"]["event_safety"], 0.55 - 1e-6)

    def test_infeasible_target_is_not_hidden(self) -> None:
        result = optimize_portfolio(
            **INPUTS,
            minimum_safety=0.99,
        )
        self.assertEqual(result["status"], "infeasible")
        self.assertGreater(result["residuals"]["safety_shortfall"], 0)

    def test_event_safety_frontier_is_separate_from_esg(self) -> None:
        result = build_event_safety_frontier(
            **INPUTS,
            safety_targets=[0.45, 0.55, 0.65],
        )
        self.assertEqual(result["frontier_kind"], "event_safety")
        self.assertIn("논문의 ESG 점수", result["paper_relation"])
        safety = [
            round(point["metrics"]["event_safety"], 8)
            for point in result["points"]
            if point["status"] == "optimal"
        ]
        self.assertEqual(safety, sorted(safety))

    def test_esg_score_kind_remains_explicit(self) -> None:
        result = optimize_portfolio(
            **INPUTS,
            score_kind="esg",
            minimum_safety=0.55,
        )
        self.assertEqual(result["score_kind"], "esg")
        self.assertIn("esg_score", result["metrics"])
        self.assertNotIn("event_safety", result["metrics"])

    def test_esg_frontier_has_a_separate_contract(self) -> None:
        result = build_esg_efficient_frontier(
            **INPUTS,
            esg_targets=[0.45, 0.55],
        )
        self.assertEqual(result["frontier_kind"], "esg")
        self.assertIn("four-fund", result["paper_relation"])
