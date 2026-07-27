"""릴리스에 필요한 코드·문서·저장 결과의 추적 가능성을 확인한다."""

from __future__ import annotations

import json
from pathlib import Path

from collector.jobs.monitor_product_health import health_snapshot
from collector.repositories.supabase import PROJECT_ROOT


REQUIRED_FILES = (
    "docs/research/DATASET_CARD_event_study_v1.md",
    "docs/research/MODEL_CARD_event_risk_v1.md",
    "docs/research/RELEASE_REPORT_v1.md",
    "docs/runbooks/risk-model-rollback.md",
    "notebooks/StockEcho_Event_Risk_Colab.ipynb",
    "supabase/migrations/202607270007_event_risk_forecasts.sql",
)


def verify() -> dict[str, object]:
    missing = [
        path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()
    ]
    health = health_snapshot()
    critical = []
    if missing:
        critical.append("required_files_missing")
    if int(health["forecasts"]["total"]) == 0:  # type: ignore[index]
        critical.append("forecast_rows_missing")
    if int(health["marketDailyRows"]) == 0:
        critical.append("stock_market_history_missing")
    if int(health["marketIndexDailyRows"]) == 0:
        critical.append("benchmark_history_missing")
    current_issues = health["currentIssues"]
    if float(current_issues["analysisCoverageRatio"]) < 0.8:  # type: ignore[index]
        critical.append("current_issue_analysis_coverage_low")
    if float(current_issues["evidenceCoverageRatio"]) < 0.5:  # type: ignore[index]
        critical.append("current_issue_evidence_coverage_low")
    if float(current_issues["d5ForecastCoverageRatio"]) < 0.5:  # type: ignore[index]
        critical.append("current_issue_d5_forecast_coverage_low")
    return {
        "schemaVersion": "production-artifact-verification-v1",
        "passed": not critical,
        "criticalFailures": critical,
        "missingFiles": missing,
        "health": health,
        "productionModelPolicy": {
            "selected": "similarity-weighted-empirical-v1",
            "embeddingSearchPromoted": False,
            "logisticPromoted": False,
            "mlpPromoted": False,
            "reason": (
                "embedding은 실제 사람평가 검색셋이 없고, ML/DL은 D+5 train "
                "16건으로 최소 학습표본 gate를 충족하지 못했으며 Brier/ECE도 "
                "경험 기준선보다 악화됨"
            ),
        },
    }


def main() -> int:
    result = verify()
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
