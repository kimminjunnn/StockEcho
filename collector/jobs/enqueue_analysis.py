"""종목 분석 요청을 Supabase Queue에 등록한다."""

from __future__ import annotations

import argparse
import json

from collector.companies import SUPPORTED_COMPANIES
from collector.repositories.supabase import enqueue_stock


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--stock-code", action="append")
    selection.add_argument("--all-supported", action="store_true")
    parser.add_argument("--reason", default="scheduled_refresh")
    parser.add_argument("--priority", type=int, default=100)
    args = parser.parse_args()

    stock_codes = (
        [company.stock_code for company in SUPPORTED_COMPANIES]
        if args.all_supported
        else args.stock_code
    )
    messages = {
        stock_code: enqueue_stock(stock_code, args.reason, args.priority)
        for stock_code in dict.fromkeys(stock_codes)
    }
    print(json.dumps({"messages": messages}, ensure_ascii=False))


if __name__ == "__main__":
    main()
