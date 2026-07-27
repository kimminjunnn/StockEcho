"""확률 예측의 판별력과 calibration 지표."""

from __future__ import annotations

from typing import Sequence


def expected_calibration_error(
    labels: Sequence[int], probabilities: Sequence[float], *, bins: int = 10
) -> float:
    if len(labels) != len(probabilities) or not labels:
        raise ValueError("같은 길이의 비어 있지 않은 label/probability가 필요합니다.")
    if bins < 2:
        raise ValueError("bins는 2 이상이어야 합니다.")
    total = len(labels)
    error = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        selected = [
            position
            for position, value in enumerate(probabilities)
            if lower <= value < upper or (index == bins - 1 and value == 1.0)
        ]
        if not selected:
            continue
        accuracy = sum(labels[position] for position in selected) / len(selected)
        confidence = sum(probabilities[position] for position in selected) / len(selected)
        error += len(selected) / total * abs(accuracy - confidence)
    return error


def probability_metrics(
    labels: Sequence[int], probabilities: Sequence[float]
) -> dict[str, float]:
    from sklearn.metrics import average_precision_score, brier_score_loss

    return {
        "pr_auc": round(float(average_precision_score(labels, probabilities)), 6),
        "brier": round(float(brier_score_loss(labels, probabilities)), 6),
        "ece": round(expected_calibration_error(labels, probabilities), 6),
    }
