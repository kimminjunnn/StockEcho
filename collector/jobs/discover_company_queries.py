"""회사 직접 기사 corpus에서 확장 검색어를 발견하고 선택적으로 수집한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from collector.companies import get_company
from collector.jobs.collect_news_query import run as collect_query
from collector.query.keywords import KiwiKeywordExtractor
from collector.query.planner import build_query_plan
from collector.repositories.local import read_jsonl, write_json_atomic


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_company_articles(stock_code: str) -> list[dict]:
    processed_root = PROJECT_ROOT / "data" / "processed" / "news"
    articles = {
        row["document_id"]: row for row in read_jsonl(processed_root / "articles.jsonl")
    }
    links = read_jsonl(processed_root / "article_companies.jsonl")
    ids = {
        row["document_id"]
        for row in links
        if row.get("stock_code") == stock_code
        and row.get("relation_type") == "direct"
        and float(row.get("confidence", 0)) >= 0.9
    }
    selected = [articles[document_id] for document_id in ids if document_id in articles]
    if selected:
        return selected
    # 이전 수집 결과를 한 번의 마이그레이션 없이도 seed corpus로 사용할 수 있다.
    return read_jsonl(
        PROJECT_ROOT / "data" / "processed" / "naver" / f"{stock_code}_articles.jsonl"
    )


def run(
    *,
    stock_code: str,
    max_active: int = 5,
    sources: tuple[str, ...] = ("naver",),
    collect_active: bool = False,
    display: int = 100,
) -> dict:
    company = get_company(stock_code)
    articles = _load_company_articles(stock_code)
    candidates = KiwiKeywordExtractor(max_active=max_active).extract(company, articles)
    queries = build_query_plan(company, candidates, sources=sources)
    keyword_path = PROJECT_ROOT / "data" / "processed" / "keywords" / f"{stock_code}.json"
    query_path = PROJECT_ROOT / "data" / "processed" / "queries" / f"{stock_code}.json"
    write_json_atomic(keyword_path, [candidate.to_dict() for candidate in candidates])
    write_json_atomic(query_path, [query.to_dict() for query in queries])

    collection_results = []
    if collect_active:
        for query in queries[1:]:
            for source_name in query.sources:
                collection_results.append(
                    collect_query(query=query, source_name=source_name, display=display)
                )
    return {
        "stock_code": stock_code,
        "company_name": company.name,
        "corpus_count": len(articles),
        "candidate_count": len(candidates),
        "active_keywords": [
            candidate.keyword for candidate in candidates if candidate.status == "active"
        ],
        "queries": [query.to_dict() for query in queries],
        "keyword_path": str(keyword_path.relative_to(PROJECT_ROOT)),
        "query_path": str(query_path.relative_to(PROJECT_ROOT)),
        "collection_results": collection_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", default="005930")
    parser.add_argument("--max-active", type=int, default=5)
    parser.add_argument("--source", action="append", default=None)
    parser.add_argument("--collect-active", action="store_true")
    parser.add_argument("--display", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            run(
                stock_code=args.stock_code,
                max_active=args.max_active,
                sources=tuple(args.source or ["naver"]),
                collect_active=args.collect_active,
                display=args.display,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
