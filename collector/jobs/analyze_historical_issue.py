"""현재 주요 이슈의 실제 과거 Event와 거래일 가격 반응을 계산한다."""

from __future__ import annotations

import argparse
import json
from datetime import date

from collector.historical_events.service import (
    HistoricalIssueRequest,
    analyze_historical_issue,
)


def _failure_payload(error: Exception) -> dict[str, object]:
    message = str(error)
    if "SUPABASE_DB_URL" in message:
        return {
            "success": False,
            "errorCode": "collector_configuration_missing",
            "error": "루트 .env에 SUPABASE_DB_URL 설정이 필요합니다.",
        }
    if "NAVER_CLIENT_ID" in message or "NAVER_CLIENT_SECRET" in message:
        return {
            "success": False,
            "errorCode": "collector_configuration_missing",
            "error": (
                "NAVER 보충 검색을 사용하려면 루트 .env에 "
                "NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 설정이 필요합니다."
            ),
        }
    return {
        "success": False,
        "errorCode": "analysis_failed",
        "error": "과거 유사 이슈 분석을 완료하지 못했습니다.",
    }


def _json_output(payload: dict[str, object]) -> str:
    """Windows cp949 콘솔에서도 안전하게 전달되는 단일 행 JSON을 만든다."""

    return json.dumps(payload, ensure_ascii=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", required=True)
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--event-date", type=date.fromisoformat, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--topic-label", default="")
    parser.add_argument("--keyword", action="append", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = analyze_historical_issue(
            HistoricalIssueRequest(
                stock_code=args.stock_code,
                topic_id=args.topic_id,
                event_id=args.event_id,
                event_date=args.event_date,
                name=args.name,
                topic_label=args.topic_label,
                keywords=tuple(args.keyword),
            )
        )
    except Exception as error:
        print(_json_output(_failure_payload(error)))
        raise SystemExit(1)
    print(_json_output({"success": True, "data": result}))


if __name__ == "__main__":
    main()
