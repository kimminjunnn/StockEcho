"""현재 주요 이슈의 실제 과거 Event와 거래일 가격 반응을 계산한다."""

from __future__ import annotations

import argparse
import json
from datetime import date

from collector.historical_events.service import (
    HistoricalIssueRequest,
    analyze_historical_issue,
)


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
    except Exception:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "과거 유사 이슈 분석을 완료하지 못했습니다.",
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(1)
    print(json.dumps({"success": True, "data": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
