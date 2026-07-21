"""회사명 seed 검색어로 최신 뉴스를 증분 수집한다."""

from __future__ import annotations

import argparse
import json

from collector.companies import get_company
from collector.jobs.collect_news_query import run as collect_query
from collector.query.planner import build_company_query


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", default="005930")
    parser.add_argument("--source", default="naver")
    parser.add_argument("--display", type=int, default=100)
    return parser.parse_args()


def run(*, stock_code: str, display: int = 100, source_name: str = "naver") -> dict:
    company = get_company(stock_code)
    result = collect_query(
        query=build_company_query(company), source_name=source_name, display=display
    )
    return {"stock_code": stock_code, "company_name": company.name, **result}


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            run(
                stock_code=args.stock_code,
                source_name=args.source,
                display=args.display,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
