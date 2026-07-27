"""long-only, turnover 제약을 지키는 Event-Safety/ESG frontier."""

from __future__ import annotations

from typing import Any, Sequence


TOLERANCE = 1e-6


def _validate_inputs(
    current_weights: Sequence[float],
    covariance: Sequence[Sequence[float]],
    safety_scores: Sequence[float],
    *,
    maximum_weights: Sequence[float],
    cash_index: int | None,
    minimum_cash: float,
) -> None:
    import numpy as np

    size = len(current_weights)
    if size == 0 or len(safety_scores) != size or len(maximum_weights) != size:
        raise ValueError("모든 종목 입력의 길이가 같고 1 이상이어야 합니다.")
    matrix = np.asarray(covariance, dtype=float)
    if matrix.shape != (size, size):
        raise ValueError("covariance는 종목 수와 같은 정방행렬이어야 합니다.")
    if not np.allclose(matrix, matrix.T, atol=1e-10):
        raise ValueError("covariance는 대칭이어야 합니다.")
    if float(np.linalg.eigvalsh(matrix).min()) < -1e-8:
        raise ValueError("covariance는 positive semidefinite여야 합니다.")
    if abs(sum(current_weights) - 1.0) > TOLERANCE:
        raise ValueError("현재 비중 합계는 1이어야 합니다.")
    if any(value < 0 for value in current_weights):
        raise ValueError("현재 비중은 long-only여야 합니다.")
    if any(value <= 0 or value > 1 for value in maximum_weights):
        raise ValueError("종목 상한은 0보다 크고 1 이하여야 합니다.")
    if sum(maximum_weights) < 1 - TOLERANCE:
        raise ValueError("종목 상한 합계로 100% 비중을 구성할 수 없습니다.")
    if any(not 0 <= value <= 1 for value in safety_scores):
        raise ValueError("안전성 점수는 0과 1 사이여야 합니다.")
    if not 0 <= minimum_cash <= 1:
        raise ValueError("minimum_cash는 0과 1 사이여야 합니다.")
    if minimum_cash > 0 and cash_index is None:
        raise ValueError("최소 현금 제약에는 cash_index가 필요합니다.")
    if cash_index is not None and not 0 <= cash_index < size:
        raise ValueError("cash_index가 범위를 벗어났습니다.")
    if cash_index is not None and maximum_weights[cash_index] + TOLERANCE < minimum_cash:
        raise ValueError("현금 상한이 최소 현금 비중보다 작습니다.")


def _portfolio_metrics(
    weights,
    current,
    covariance,
    safety,
    expected_returns,
    *,
    transaction_cost_bps: float,
) -> dict[str, float]:
    import numpy as np

    turnover = 0.5 * float(np.abs(weights - current).sum())
    variance = float(weights @ covariance @ weights)
    return {
        "expected_return": float(weights @ expected_returns),
        "variance": variance,
        "volatility": variance**0.5,
        "preference_score": float(weights @ safety),
        "turnover": turnover,
        "estimated_transaction_cost": turnover * transaction_cost_bps / 10_000,
    }


def optimize_portfolio(
    *,
    asset_ids: Sequence[str],
    current_weights: Sequence[float],
    covariance: Sequence[Sequence[float]],
    safety_scores: Sequence[float],
    expected_returns: Sequence[float] | None = None,
    maximum_weight: float | Sequence[float] = 0.6,
    maximum_turnover: float = 0.3,
    minimum_cash: float = 0.0,
    cash_index: int | None = None,
    risk_aversion: float = 1.0,
    safety_preference: float = 0.0,
    turnover_penalty: float = 0.01,
    transaction_cost_bps: float = 10.0,
    minimum_safety: float | None = None,
    score_kind: str = "event_safety",
) -> dict[str, Any]:
    """제약 위반을 결과 상태로 숨기지 않는 결정적 SLSQP 최적화."""

    import numpy as np
    from scipy.optimize import minimize

    size = len(asset_ids)
    current = np.asarray(current_weights, dtype=float)
    matrix = np.asarray(covariance, dtype=float)
    safety = np.asarray(safety_scores, dtype=float)
    returns = np.asarray(expected_returns or [0.0] * size, dtype=float)
    if len(returns) != size:
        raise ValueError("expected_returns 길이가 종목 수와 같아야 합니다.")
    if isinstance(maximum_weight, (float, int)):
        maxima = np.full(size, float(maximum_weight))
    else:
        maxima = np.asarray(maximum_weight, dtype=float)
    _validate_inputs(
        current,
        matrix,
        safety,
        maximum_weights=maxima,
        cash_index=cash_index,
        minimum_cash=minimum_cash,
    )
    if maximum_turnover < 0 or maximum_turnover > 1:
        raise ValueError("maximum_turnover는 0과 1 사이여야 합니다.")
    if minimum_safety is not None and not 0 <= minimum_safety <= 1:
        raise ValueError("minimum_safety는 0과 1 사이여야 합니다.")
    if score_kind not in {"event_safety", "esg"}:
        raise ValueError("score_kind는 event_safety 또는 esg여야 합니다.")

    constraints: list[dict[str, Any]] = [
        {"type": "eq", "fun": lambda weights: float(weights.sum() - 1.0)},
        {
            "type": "ineq",
            "fun": lambda weights: float(
                maximum_turnover - 0.5 * np.abs(weights - current).sum()
            ),
        },
    ]
    if cash_index is not None:
        constraints.append(
            {
                "type": "ineq",
                "fun": lambda weights: float(weights[cash_index] - minimum_cash),
            }
        )
    if minimum_safety is not None:
        constraints.append(
            {
                "type": "ineq",
                "fun": lambda weights: float(weights @ safety - minimum_safety),
            }
        )

    def objective(weights) -> float:
        turnover = 0.5 * float(np.abs(weights - current).sum())
        return float(
            risk_aversion * (weights @ matrix @ weights)
            - returns @ weights
            - safety_preference * (weights @ safety)
            + turnover_penalty * turnover
        )

    result = minimize(
        objective,
        current,
        method="SLSQP",
        bounds=[(0.0, float(value)) for value in maxima],
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 2_000, "disp": False},
    )
    weights = np.asarray(result.x, dtype=float)
    metrics = _portfolio_metrics(
        weights,
        current,
        matrix,
        safety,
        returns,
        transaction_cost_bps=transaction_cost_bps,
    )
    residuals = {
        "weight_sum": abs(float(weights.sum()) - 1.0),
        "minimum_weight": float(weights.min()),
        "maximum_weight_excess": float(np.max(weights - maxima)),
        "turnover_excess": metrics["turnover"] - maximum_turnover,
        "cash_shortfall": (
            minimum_cash - float(weights[cash_index]) if cash_index is not None else 0.0
        ),
        "safety_shortfall": (
            minimum_safety - metrics["preference_score"]
            if minimum_safety is not None
            else 0.0
        ),
    }
    feasible = bool(
        result.success
        and residuals["weight_sum"] <= TOLERANCE
        and residuals["minimum_weight"] >= -TOLERANCE
        and residuals["maximum_weight_excess"] <= TOLERANCE
        and residuals["turnover_excess"] <= TOLERANCE
        and residuals["cash_shortfall"] <= TOLERANCE
        and residuals["safety_shortfall"] <= TOLERANCE
    )
    current_metrics = _portfolio_metrics(
        current,
        current,
        matrix,
        safety,
        returns,
        transaction_cost_bps=transaction_cost_bps,
    )
    score_metric = "event_safety" if score_kind == "event_safety" else "esg_score"
    metrics[score_metric] = metrics.pop("preference_score")
    current_metrics[score_metric] = current_metrics.pop("preference_score")
    return {
        "schema_version": "constrained-portfolio-optimizer-v1",
        "status": "optimal" if feasible else "infeasible",
        "message": str(result.message),
        "score_kind": score_kind,
        "weights": {
            asset_id: float(weight) for asset_id, weight in zip(asset_ids, weights)
        },
        "current_weights": {
            asset_id: float(weight) for asset_id, weight in zip(asset_ids, current)
        },
        "metrics": metrics,
        "current_metrics": current_metrics,
        "changes": {
            key: metrics[key] - current_metrics[key]
            for key in ("expected_return", "variance", "volatility", score_metric)
        },
        "constraints": {
            "maximum_weights": {
                asset_id: float(value) for asset_id, value in zip(asset_ids, maxima)
            },
            "maximum_turnover": maximum_turnover,
            "minimum_cash": minimum_cash,
            "minimum_safety": minimum_safety,
        },
        "residuals": residuals,
        "method": "SLSQP-long-only",
        "disclaimer": (
            "계산상 비중 시나리오이며 실제 주문 또는 단일 종목 투자 권유가 아닙니다."
        ),
    }


def build_event_safety_frontier(
    *,
    safety_targets: Sequence[float],
    **optimizer_inputs: Any,
) -> dict[str, Any]:
    points = [
        optimize_portfolio(
            **optimizer_inputs,
            minimum_safety=float(target),
            score_kind="event_safety",
        )
        for target in safety_targets
    ]
    return {
        "schema_version": "event-safety-frontier-v1",
        "frontier_kind": "event_safety",
        "points": points,
        "all_feasible": all(point["status"] == "optimal" for point in points),
        "paper_relation": (
            "Pedersen et al.의 선호-효율경계 구조를 참고한 서비스 확장입니다. "
            "논문의 ESG 점수를 사건안전성으로 치환한 재현 결과가 아닙니다."
        ),
    }


def build_esg_efficient_frontier(
    *,
    esg_targets: Sequence[float],
    **optimizer_inputs: Any,
) -> dict[str, Any]:
    """외부 검증 ESG score가 있을 때만 사용하는 논문 재현용 제약 frontier."""

    points = [
        optimize_portfolio(
            **optimizer_inputs,
            minimum_safety=float(target),
            score_kind="esg",
        )
        for target in esg_targets
    ]
    return {
        "schema_version": "constrained-esg-efficient-frontier-v1",
        "frontier_kind": "esg",
        "points": points,
        "all_feasible": all(point["status"] == "optimal" for point in points),
        "paper_relation": (
            "Pedersen et al.의 ESG-efficient frontier를 long-only, 종목상한, "
            "turnover 제약으로 확장한 연구 계약입니다. closed-form four-fund "
            "separation 재현을 주장하지 않습니다."
        ),
    }
