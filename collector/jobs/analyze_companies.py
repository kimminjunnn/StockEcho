"""종목별 뉴스 수집부터 주요 이슈 생성까지 한 번에 실행한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from collector.companies import SUPPORTED_COMPANIES
from collector.jobs.collect_company_news import run as collect_company_news
from collector.jobs.discover_company_queries import run as discover_company_queries
from collector.jobs.reevaluate_company_news import run as reevaluate_company_news
from collector.topic_modeling.pipeline import TopicModelConfig, run_topic_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--stock-code", action="append")
    selection.add_argument(
        "--all-supported",
        action="store_true",
        help="지원 종목 전체를 분석한다.",
    )
    parser.add_argument("--display", type=int, default=100)
    parser.add_argument("--device", help="예: cpu, cuda, mps")
    return parser.parse_args()


def analyze_company(*, stock_code: str, display: int, device: str | None) -> dict:
    collection = collect_company_news(stock_code=stock_code, display=display)
    initial_relevance = reevaluate_company_news(stock_code=stock_code)
    query_discovery = discover_company_queries(
        stock_code=stock_code,
        collect_active=True,
        display=display,
    )
    relevance = reevaluate_company_news(stock_code=stock_code)
    input_path = (
        PROJECT_ROOT / "data" / "processed" / "bertopic" / f"{stock_code}_articles.jsonl"
    )
    output_dir = PROJECT_ROOT / "data" / "processed" / "topics"
    topic_modeling = run_topic_pipeline(
        input_path=input_path,
        topics_output_path=output_dir / f"{stock_code}_topics.jsonl",
        issues_output_path=output_dir / f"{stock_code}_major_issues.jsonl",
        config=TopicModelConfig(),
        device=device,
    )
    return {
        "stock_code": stock_code,
        "collection": collection,
        "initial_relevance": initial_relevance,
        "query_discovery": query_discovery,
        "relevance": relevance,
        "topic_modeling": topic_modeling,
    }


def main() -> None:
    args = parse_args()
    stock_codes = (
        [company.stock_code for company in SUPPORTED_COMPANIES]
        if args.all_supported
        else args.stock_code
    )
    results = []
    failures = []
    for stock_code in dict.fromkeys(stock_codes):
        try:
            results.append(
                analyze_company(
                    stock_code=stock_code,
                    display=args.display,
                    device=args.device,
                )
            )
        except Exception as error:  # 종목 하나의 실패가 나머지를 막지 않게 한다.
            failures.append(
                {
                    "stock_code": stock_code,
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )

    print(
        json.dumps(
            {"results": results, "failures": failures},
            ensure_ascii=False,
            indent=2,
        )
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
