from __future__ import annotations

import unittest

from collector.portfolio.impact import calculate_portfolio_impact


class PortfolioImpactTest(unittest.TestCase):
    def test_weighted_downside_contributions_sum_to_portfolio_scenario(self) -> None:
        holdings = [
            {"stock_code": "A", "name": "A", "market_value": 600},
            {"stock_code": "B", "name": "B", "market_value": 400},
        ]
        forecasts = {
            "A": {"horizons": {"d5": {"status": "available", "loss_probability": 0.7, "return_percentiles": {"p10": -10}}}},
            "B": {"horizons": {"d5": {"status": "available", "loss_probability": 0.25, "return_percentiles": {"p10": -2}}}},
        }

        result = calculate_portfolio_impact(holdings, forecasts)

        self.assertEqual(result["coverage_status"], "complete")
        self.assertAlmostEqual(result["portfolio_downside_scenario_percent"], -6.8)
        self.assertAlmostEqual(
            sum(row["downside_contribution_percent"] for row in result["contributions"]),
            result["portfolio_downside_scenario_percent"],
        )

    def test_missing_forecast_is_reported_as_partial_coverage(self) -> None:
        result = calculate_portfolio_impact(
            [
                {"stock_code": "A", "market_value": 50},
                {"stock_code": "B", "market_value": 50},
            ],
            {
                "A": {"horizons": {"d5": {"status": "available", "loss_probability": 0.5, "return_percentiles": {"p10": -3}}}},
            },
        )
        self.assertEqual(result["coverage_status"], "partial")
        self.assertEqual(result["covered_weight"], 0.5)
