"""동일한 순방향 분할에서 Logistic/MLP를 학습하고 calibration한다."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from collector.risk_model.metrics import probability_metrics


NUMERIC_FEATURES = ("source_count", "article_count")
CATEGORICAL_FEATURES = ("event_category", "impact_direction", "stock_code")


def _records(rows: Sequence[Mapping[str, Any]]):
    import pandas as pd

    values = [
        {
            "feature_text": str(row.get("feature_text") or ""),
            **{
                key: float(row.get(key) or 0.0)
                for key in NUMERIC_FEATURES
            },
            **{
                key: str(row.get(key) or "unknown")
                for key in CATEGORICAL_FEATURES
            },
        }
        for row in rows
    ]
    return pd.DataFrame.from_records(values)


def _logit(value: float) -> float:
    clipped = min(max(float(value), 1e-6), 1 - 1e-6)
    return math.log(clipped / (1 - clipped))


def _labels(rows: Sequence[Mapping[str, Any]], label_key: str) -> list[int]:
    labels = [row.get(label_key) for row in rows]
    if any(value not in (0, 1) for value in labels):
        raise ValueError(f"{label_key}에는 0/1 label만 있어야 합니다.")
    return [int(value) for value in labels]


def _feature_transformer():
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    return ColumnTransformer(
        [
            (
                "text",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=512,
                    sublinear_tf=True,
                ),
                "feature_text",
            ),
            (
                "category",
                OneHotEncoder(handle_unknown="ignore"),
                list(CATEGORICAL_FEATURES),
            ),
            ("numeric", StandardScaler(), list(NUMERIC_FEATURES)),
        ]
    )


def _base_estimator(kind: str, random_state: int):
    if kind == "logistic":
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(
            max_iter=1_000,
            class_weight="balanced",
            random_state=random_state,
        )
    if kind == "mlp":
        from sklearn.neural_network import MLPClassifier

        return MLPClassifier(
            hidden_layer_sizes=(32,),
            alpha=0.01,
            early_stopping=False,
            max_iter=500,
            random_state=random_state,
        )
    raise ValueError("kind는 logistic 또는 mlp여야 합니다.")


@dataclass
class CalibratedRiskModel:
    pipeline: Any
    calibrator: Any | None
    model_kind: str
    label_key: str

    def predict_proba(self, rows: Sequence[Mapping[str, Any]]) -> list[float]:
        raw = self.pipeline.predict_proba(_records(rows))[:, 1]
        if self.calibrator is None:
            return [float(value) for value in raw]
        logits = [[_logit(float(value))] for value in raw]
        values = self.calibrator.predict_proba(logits)[:, 1]
        return [float(value) for value in values]


def train_calibrated_model(
    train_rows: Sequence[Mapping[str, Any]],
    validation_rows: Sequence[Mapping[str, Any]],
    *,
    kind: str,
    label_key: str,
    random_state: int = 42,
) -> CalibratedRiskModel:
    """train 학습 후, 시간상 뒤인 validation으로 Platt calibration한다."""

    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    train_labels = _labels(train_rows, label_key)
    validation_labels = _labels(validation_rows, label_key)
    if len(set(train_labels)) < 2:
        raise ValueError("train에는 양·음 class가 모두 필요합니다.")
    pipeline = Pipeline(
        [
            ("features", _feature_transformer()),
            ("classifier", _base_estimator(kind, random_state)),
        ]
    )
    pipeline.fit(_records(train_rows), train_labels)
    calibrator = None
    if len(set(validation_labels)) == 2:
        raw = pipeline.predict_proba(_records(validation_rows))[:, 1]
        logits = [[_logit(float(value))] for value in raw]
        calibrator = LogisticRegression(random_state=random_state)
        calibrator.fit(logits, validation_labels)
    return CalibratedRiskModel(
        pipeline=pipeline,
        calibrator=calibrator,
        model_kind=kind,
        label_key=label_key,
    )


def evaluate_model(
    model: CalibratedRiskModel,
    test_rows: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    return probability_metrics(
        _labels(test_rows, model.label_key),
        model.predict_proba(test_rows),
    )
