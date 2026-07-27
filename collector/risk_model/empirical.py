"""유사 Event 실제 반응에 기반한 설명 가능한 경험분포."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


RISK_FORECAST_SCHEMA_VERSION = "event-risk-forecast-v1"
SUPPORTED_HORIZONS = ("d1", "d5", "d20")


def _weighted_quantile(
    values: Sequence[tuple[float, float]], quantile: float
) -> float | None:
    usable = sorted((value, weight) for value, weight in values if weight > 0)
    if not usable:
        return None
    total = sum(weight for _value, weight in usable)
    threshold = quantile * total
    cumulative = 0.0
    for value, weight in usable:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return usable[-1][0]


def _effective_sample_size(weights: Sequence[float]) -> float:
    total = sum(weights)
    denominator = sum(weight * weight for weight in weights)
    return total * total / denominator if denominator else 0.0


def _confidence(effective_n: float, source_events: int) -> str:
    if source_events >= 20 and effective_n >= 12:
        return "high"
    if source_events >= 8 and effective_n >= 5:
        return "medium"
    if source_events >= 3:
        return "low"
    return "insufficient"


def empirical_risk_forecast(
    similar_events: Sequence[Mapping[str, Any]],
    *,
    horizons: Sequence[str] = SUPPORTED_HORIZONS,
    prior_loss_probability: float = 0.5,
    prior_strength: float = 2.0,
    model_version: str = "similarity-weighted-empirical-v1",
) -> dict[str, Any]:
    """유사도 가중 실제 abnormal return으로 확률과 분위수를 계산한다."""

    if not 0.0 <= prior_loss_probability <= 1.0:
        raise ValueError("prior_loss_probability는 0과 1 사이여야 합니다.")
    if prior_strength < 0:
        raise ValueError("prior_strength는 0 이상이어야 합니다.")
    invalid = set(horizons) - set(SUPPORTED_HORIZONS)
    if invalid:
        raise ValueError(f"지원하지 않는 horizon입니다: {sorted(invalid)}")

    forecasts: dict[str, Any] = {}
    for horizon in horizons:
        observations: list[tuple[float, float, str]] = []
        for event in similar_events:
            reaction = event.get("price_reaction") or event.get("priceReaction") or {}
            abnormal = reaction.get("abnormal_returns") or reaction.get("abnormalReturns") or {}
            raw = reaction.get("returns") or {}
            value = abnormal.get(horizon)
            return_basis = "abnormal"
            if value is None:
                value = raw.get(horizon)
                return_basis = "raw"
            if value is None:
                continue
            similarity = max(float(event.get("similarity_score") or event.get("similarityScore") or 0.0), 0.0)
            source_count = max(int(event.get("source_count") or event.get("sourceCount") or 1), 1)
            evidence_weight = min(math.log1p(source_count) / math.log(6), 1.0)
            weight = max(similarity * evidence_weight, 0.01)
            observations.append((float(value), weight, return_basis))

        weights = [weight for _value, weight, _basis in observations]
        weighted_losses = sum(
            weight for value, weight, _basis in observations if value < 0
        )
        weighted_total = sum(weights)
        probability = (
            weighted_losses + prior_loss_probability * prior_strength
        ) / (weighted_total + prior_strength) if weighted_total + prior_strength else None
        weighted_values = [(value, weight) for value, weight, _basis in observations]
        effective_n = _effective_sample_size(weights)
        confidence = _confidence(effective_n, len(observations))
        forecasts[horizon] = {
            "status": "available" if observations else "unavailable",
            "loss_probability": (
                round(float(probability), 6) if probability is not None else None
            ),
            "return_percentiles": {
                "p10": _weighted_quantile(weighted_values, 0.10),
                "p50": _weighted_quantile(weighted_values, 0.50),
                "p90": _weighted_quantile(weighted_values, 0.90),
            },
            "observed_event_count": len(observations),
            "effective_sample_size": round(effective_n, 4),
            "confidence": confidence,
            "production_eligible": confidence in {"medium", "high"},
            "return_basis": (
                "abnormal"
                if observations and all(basis == "abnormal" for *_rest, basis in observations)
                else "mixed_or_raw"
            ),
        }

    return {
        "schema_version": RISK_FORECAST_SCHEMA_VERSION,
        "method": "similarity-weighted-empirical",
        "model_version": model_version,
        "horizons": forecasts,
        "disclaimer": "과거 유사 사건의 분포이며 확정적 주가 전망이 아닙니다.",
    }
