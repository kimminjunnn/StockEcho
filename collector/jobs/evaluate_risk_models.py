"""시간순 holdout에서 경험 기준선·Logistic·MLP를 비교한다."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from collector.risk_model.metrics import probability_metrics
from collector.risk_model.training import evaluate_model, train_calibrated_model


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _split_rows(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    groups = {
        name: [dict(row) for row in rows if row.get("split") == name]
        for name in ("train", "validation", "test")
    }
    if any(not groups[name] for name in groups):
        raise ValueError("train/validation/test가 모두 비어 있지 않아야 합니다.")
    boundaries = {
        name: [
            date.fromisoformat(str(row["event_date"])) for row in groups[name]
        ]
        for name in groups
    }
    if max(boundaries["train"]) >= min(boundaries["validation"]):
        raise ValueError("train과 validation 시간 순서가 겹칩니다.")
    if max(boundaries["validation"]) >= min(boundaries["test"]):
        raise ValueError("validation과 test 시간 순서가 겹칩니다.")
    return groups["train"], groups["validation"], groups["test"]


def _empirical_probabilities(
    train_rows: Sequence[Mapping[str, Any]],
    test_rows: Sequence[Mapping[str, Any]],
    *,
    label_key: str,
) -> list[float]:
    global_rate = sum(int(row[label_key]) for row in train_rows) / len(train_rows)
    category_counts: dict[str, Counter[int]] = {}
    for row in train_rows:
        category = str(row.get("event_category") or "unknown")
        category_counts.setdefault(category, Counter())[int(row[label_key])] += 1
    probabilities = []
    for row in test_rows:
        counts = category_counts.get(str(row.get("event_category") or "unknown"), Counter())
        # Beta prior로 작은 category의 과신을 막는다.
        probability = (counts[1] + 5 * global_rate) / (sum(counts.values()) + 5)
        probabilities.append(probability)
    return probabilities


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    label_key: str,
    fixture: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    usable_rows = [row for row in rows if row.get(label_key) in (0, 1)]
    train, validation, test = _split_rows(usable_rows)
    test_labels = [int(row[label_key]) for row in test]
    baseline = probability_metrics(
        test_labels,
        _empirical_probabilities(train, test, label_key=label_key),
    )
    models: dict[str, Any] = {}
    fitted: dict[str, Any] = {}
    for kind in ("logistic", "mlp"):
        model = train_calibrated_model(
            train,
            validation,
            kind=kind,
            label_key=label_key,
        )
        metrics = evaluate_model(model, test)
        models[kind] = metrics
        fitted[kind] = model

    eligible = [
        name
        for name, metrics in models.items()
        if (
            not fixture
            and len(train) >= 100
            and len(validation) >= 30
            and len(test) >= 100
            and metrics["pr_auc"] > baseline["pr_auc"]
            and metrics["brier"] < baseline["brier"]
            and metrics["ece"] <= 0.10
        )
    ]
    selected = min(
        eligible,
        key=lambda name: (models[name]["brier"], -models[name]["pr_auc"]),
        default="empirical",
    )
    report = {
        "schema_version": "risk-model-evaluation-v1",
        "label_key": label_key,
        "split": {
            "strategy": "chronological-holdout",
            "train_count": len(train),
            "validation_count": len(validation),
            "test_count": len(test),
            "train_end": max(str(row["event_date"]) for row in train),
            "validation_end": max(str(row["event_date"]) for row in validation),
            "test_start": min(str(row["event_date"]) for row in test),
        },
        "empirical": baseline,
        "candidates": models,
        "production_gate": {
            "passed": selected != "empirical",
            "selected_model": selected,
            "requirements": [
                "실제 train Event 100건 및 validation Event 30건 이상",
                "실제 test Event 100건 이상",
                "경험 기준선 대비 PR-AUC 상승 및 Brier 감소",
                "ECE 0.10 이하",
            ],
        },
    }
    return report, fitted


def fixture_rows() -> list[dict[str, Any]]:
    result = []
    start = date(2020, 1, 1)
    for index in range(90):
        loss = int(index % 3 == 0 or index % 11 == 0)
        split = "train" if index < 54 else "validation" if index < 72 else "test"
        result.append(
            {
                "event_id": f"fixture-{index}",
                "event_date": (start + timedelta(days=index)).isoformat(),
                "split": split,
                "feature_text": "리콜 제품 결함 안전 사고" if loss else "수주 신제품 매출 성장",
                "event_category": "사고·분쟁" if loss else "수주·계약",
                "impact_direction": "negative" if loss else "positive",
                "stock_code": f"{index % 6:06d}",
                "source_count": 2 + index % 3,
                "article_count": 3 + index % 4,
                "material_downside_label_d5": loss,
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--label-key", default="material_downside_label_d5")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    if args.fixture == bool(args.dataset):
        parser.error("--fixture 또는 --dataset 중 하나만 지정해야 합니다.")
    rows = fixture_rows() if args.fixture else _load_jsonl(args.dataset)
    report, fitted = evaluate_rows(
        rows,
        label_key=args.label_key,
        fixture=args.fixture,
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    selected = str(report["production_gate"]["selected_model"])
    if args.artifact_dir and selected != "empirical":
        import joblib

        args.artifact_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(fitted[selected], args.artifact_dir / "risk_model.joblib")
        (args.artifact_dir / "manifest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
