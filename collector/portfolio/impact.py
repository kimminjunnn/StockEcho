"""종목 Event forecast를 보유 비중 기준 포트폴리오 영향으로 변환한다."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def calculate_portfolio_impact(
    holdings: Sequence[Mapping[str, Any]],
    forecasts: Mapping[str, Mapping[str, Any]],
    *,
    horizon: str = "d5",
) -> dict[str, Any]:
    if not holdings:
        raise ValueError("보유 종목이 하나 이상 필요합니다.")
    market_values = [
        float(row.get("market_value") or 0.0)
        for row in holdings
    ]
    if any(value < 0 for value in market_values) or sum(market_values) <= 0:
        raise ValueError("market_value 합계는 양수여야 합니다.")
    total = sum(market_values)
    contributions = []
    covered_weight = 0.0
    scenario_return = 0.0
    probability_score = 0.0
    for holding, market_value in zip(holdings, market_values):
        code = str(holding.get("stock_code") or holding.get("code") or "")
        weight = market_value / total
        payload = forecasts.get(code) or {}
        horizon_forecast = (payload.get("horizons") or {}).get(horizon) or {}
        percentiles = horizon_forecast.get("return_percentiles") or {}
        downside = percentiles.get("p10")
        probability = horizon_forecast.get("loss_probability")
        available = (
            horizon_forecast.get("status") == "available"
            and downside is not None
            and probability is not None
        )
        if available:
            covered_weight += weight
            scenario_return += weight * float(downside)
            probability_score += weight * float(probability)
        contributions.append(
            {
                "stock_code": code,
                "name": str(holding.get("name") or code),
                "market_value": round(market_value, 2),
                "weight": round(weight, 8),
                "forecast_available": available,
                "loss_probability": float(probability) if probability is not None else None,
                "downside_return_percent": float(downside) if downside is not None else None,
                "downside_contribution_percent": (
                    round(weight * float(downside), 6) if downside is not None else None
                ),
            }
        )
    contributions.sort(
        key=lambda row: (
            float(row["downside_contribution_percent"] or 0.0),
            str(row["stock_code"]),
        )
    )
    return {
        "schema_version": "portfolio-event-impact-v1",
        "horizon": horizon,
        "total_market_value": round(total, 2),
        "covered_weight": round(covered_weight, 8),
        "coverage_status": (
            "complete"
            if covered_weight >= 0.999999
            else "partial"
            if covered_weight > 0
            else "unavailable"
        ),
        "portfolio_downside_scenario_percent": round(scenario_return, 6),
        "portfolio_loss_probability_score": round(probability_score, 6),
        "contributions": contributions,
        "limitations": [
            "종목별 하방 분위수의 비중 가중 시나리오이며 공동 꼬리위험 확률은 아닙니다."
        ],
    }
