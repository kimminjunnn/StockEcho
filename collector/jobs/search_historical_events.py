"""저장된 종목별 Topic/Event에서 키워드 기반 과거 이슈를 검색한다."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from collector.historical_events.search import (
    load_topic_records,
    search_historical_events,
)
from collector.repositories.local import write_json_atomic


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", required=True, help="현재 이슈의 종목 코드")
    parser.add_argument("--keyword", action="append", required=True)
    parser.add_argument(
        "--before",
        type=date.fromisoformat,
        required=True,
        help="이 날짜보다 과거인 Event만 검색 (YYYY-MM-DD)",
    )
    parser.add_argument("--current-event-id")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--minimum-score", type=float, default=0.4)
    parser.add_argument(
        "--topics-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "topics",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = search_historical_events(
        load_topic_records(args.topics_dir),
        target_stock_code=args.stock_code,
        keywords=args.keyword,
        before=args.before,
        current_event_id=args.current_event_id,
        limit=args.limit,
        minimum_score=args.minimum_score,
    )
    if args.output:
        write_json_atomic(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
