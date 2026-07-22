"""지원 종목 뉴스를 수집하고 변경량에 따라 분석 작업을 자동 등록한다."""

from __future__ import annotations

import argparse
import json

from collector.companies import SUPPORTED_COMPANIES
from collector.jobs.collect_company_news import run as collect_company_news
from collector.jobs.discover_company_queries import run as discover_company_queries
from collector.jobs.reevaluate_company_news import run as reevaluate_company_news
from collector.repositories.supabase import schedule_stock_if_changed, sync_stock_news


def collect_and_schedule(*, stock_code: str, display: int = 100) -> dict:
    collection = collect_company_news(stock_code=stock_code, display=display)
    initial_relevance = reevaluate_company_news(stock_code=stock_code)
    query_discovery = discover_company_queries(
        stock_code=stock_code,
        collect_active=True,
        display=display,
    )
    relevance = reevaluate_company_news(stock_code=stock_code)
    sync = sync_stock_news(stock_code)
    scheduling = schedule_stock_if_changed(stock_code)
    return {
        "stock_code": stock_code,
        "collection": collection,
        "initial_relevance": initial_relevance,
        "query_discovery": query_discovery,
        "relevance": relevance,
        "sync": sync,
        "scheduling": scheduling,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--stock-code", action="append")
    selection.add_argument("--all-supported", action="store_true")
    parser.add_argument("--display", type=int, default=100)
    args = parser.parse_args()
    stock_codes = (
        [company.stock_code for company in SUPPORTED_COMPANIES]
        if args.all_supported
        else args.stock_code
    )
    results = []
    failures = []
    for stock_code in dict.fromkeys(stock_codes):
        try:
            results.append(collect_and_schedule(stock_code=stock_code, display=args.display))
        except Exception as error:
            failures.append(
                {
                    "stock_code": stock_code,
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
    print(json.dumps({"results": results, "failures": failures}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
