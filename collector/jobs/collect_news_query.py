"""소스와 종목을 분리해 SearchQuery 단위로 뉴스를 증분 수집한다."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from collector.clients.naver import NaverCredentials, NaverNewsClient
from collector.companies import get_company
from collector.domain.search import QueryCompanyLink, SearchQuery
from collector.normalize.news import normalize_items
from collector.relevance.rules import classify_relevance
from collector.repositories.local import (
    load_checkpoint,
    merge_jsonl,
    payload_items_hash,
    save_checkpoint,
    select_new_articles,
    updated_checkpoint,
    write_raw_gzip,
)
from collector.sources.base import NewsSource
from collector.sources.naver import NaverNewsSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_source(name: str) -> NewsSource:
    load_dotenv(PROJECT_ROOT / ".env")
    if name != "naver":
        raise ValueError(f"지원하지 않는 뉴스 소스입니다: {name}")
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            ".env에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 설정해 주세요."
        )
    return NaverNewsSource(NaverNewsClient(NaverCredentials(client_id, client_secret)))


def run(
    *,
    query: SearchQuery,
    source_name: str = "naver",
    display: int = 100,
    source: NewsSource | None = None,
) -> dict:
    source = source or load_source(source_name)
    if source.name not in query.sources:
        raise ValueError(f"{query.query_id} 검색어는 {source.name} 소스를 허용하지 않습니다.")

    result = source.search(query.text, limit=display)
    articles = normalize_items(result.items, source=result.source)
    checkpoint_path = (
        PROJECT_ROOT
        / "data"
        / "state"
        / "news"
        / result.source
        / f"{query.query_id}.json"
    )
    checkpoint = load_checkpoint(checkpoint_path)
    current_payload_hash = payload_items_hash(result.payload)
    new_articles = select_new_articles(articles, checkpoint)
    collected_at = datetime.now(timezone.utc)

    raw_path: Path | None = None
    if new_articles or current_payload_hash != checkpoint.payload_hash:
        raw_path = (
            PROJECT_ROOT
            / "data"
            / "raw"
            / "news"
            / result.source
            / collected_at.strftime("%Y-%m-%d")
            / query.query_id
            / f"{collected_at.strftime('%H%M%S')}_{current_payload_hash[:12]}.json.gz"
        )
        write_raw_gzip(raw_path, result.payload)

    article_rows = [article.to_dict() for article in new_articles]
    query_rows = [
        {
            "document_id": article.document_id,
            "query_id": query.query_id,
            "source": result.source,
            "query_text": query.text,
            "query_type": query.query_type,
            "collected_at": collected_at.isoformat(),
        }
        for article in new_articles
    ]
    company_rows = []
    relevance_rows = []
    for article in new_articles:
        for link in query.company_links:
            company = get_company(link.stock_code)
            relevance = classify_relevance(
                article,
                company,
                query_text=query.text,
                query_type=query.query_type,
                link_weight=link.weight,
            )
            assessment = {
                "document_id": article.document_id,
                "stock_code": company.stock_code,
                "company_name": company.name,
                "query_id": query.query_id,
                "query_text": query.text,
                "query_type": query.query_type,
                "relation_type": relevance.relation_type,
                "confidence": relevance.confidence,
                "status": relevance.status,
                "evidence": [*relevance.evidence, *link.evidence],
                "rule_version": relevance.rule_version,
                "evaluated_at": collected_at.isoformat(),
            }
            relevance_rows.append(assessment)
            if relevance.status != "eligible":
                continue
            company_rows.append({**assessment, "collected_at": collected_at.isoformat()})

    processed_root = PROJECT_ROOT / "data" / "processed" / "news"
    articles_added = merge_jsonl(
        processed_root / "articles.jsonl", article_rows, key_fields=("document_id",)
    )
    query_links_added = merge_jsonl(
        processed_root / "article_queries.jsonl",
        query_rows,
        key_fields=("document_id", "query_id"),
    )
    company_links_added = merge_jsonl(
        processed_root / "article_companies.jsonl",
        company_rows,
        key_fields=("document_id", "stock_code", "query_id"),
    )
    relevance_rows_added = merge_jsonl(
        processed_root / "article_relevance.jsonl",
        relevance_rows,
        key_fields=("document_id", "stock_code", "query_id", "rule_version"),
    )
    merge_jsonl(
        PROJECT_ROOT / "data" / "processed" / "queries" / "registry.jsonl",
        [{**query.to_dict(), "updated_at": collected_at.isoformat()}],
        key_fields=("query_id",),
    )
    save_checkpoint(
        checkpoint_path,
        updated_checkpoint(articles, checkpoint, current_payload_hash),
    )
    return {
        "query": query.to_dict(),
        "source": result.source,
        "received_count": len(result.items),
        "normalized_count": len(articles),
        "new_count": len(new_articles),
        "articles_added": articles_added,
        "query_links_added": query_links_added,
        "company_links_added": company_links_added,
        "relevance_rows_added": relevance_rows_added,
        "raw_path": str(raw_path.relative_to(PROJECT_ROOT)) if raw_path else None,
        "checkpoint_path": str(checkpoint_path.relative_to(PROJECT_ROOT)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument(
        "--query-type", choices=("company", "product", "industry", "event"), required=True
    )
    parser.add_argument("--stock-code", action="append", required=True)
    parser.add_argument("--source", default="naver")
    parser.add_argument("--display", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weight = 1.0 if args.query_type == "company" else 0.75
    query = SearchQuery.create(
        text=args.query,
        query_type=args.query_type,
        company_links=tuple(
            QueryCompanyLink(stock_code=code, weight=weight, evidence=("cli_input",))
            for code in args.stock_code
        ),
        sources=(args.source,),
    )
    print(
        json.dumps(
            run(query=query, source_name=args.source, display=args.display),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
