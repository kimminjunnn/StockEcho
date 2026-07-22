"""기존 수집 기사를 관련도 v2로 재평가해 BERTopic 입력 corpus를 만든다."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from collector.companies import get_company
from collector.models.news import NormalizedNewsArticle
from collector.relevance.rules import RULE_VERSION, classify_relevance
from collector.repositories.local import read_jsonl, write_jsonl_atomic


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _article_from_row(row: dict) -> NormalizedNewsArticle:
    return NormalizedNewsArticle(
        document_id=row["document_id"],
        source=row.get("source", ""),
        title=row.get("title", ""),
        summary=row.get("summary", ""),
        published_at=row.get("published_at", ""),
        canonical_url=row.get("canonical_url", ""),
        original_url=row.get("original_url", ""),
        source_url=row.get("source_url", row.get("naver_url", "")),
        content_hash=row.get("content_hash", ""),
    )


def run(*, stock_code: str) -> dict:
    company = get_company(stock_code)
    processed_root = PROJECT_ROOT / "data" / "processed"
    news_root = processed_root / "news"
    articles = {
        row["document_id"]: row for row in read_jsonl(news_root / "articles.jsonl")
    }
    article_queries = read_jsonl(news_root / "article_queries.jsonl")
    registry_rows = read_jsonl(processed_root / "queries" / "registry.jsonl")
    company_name_folded = company.name.casefold()
    accepted_query_rows = [
        row
        for row in registry_rows
        if row.get("text", "").casefold() == company_name_folded
        or row.get("text", "").casefold().startswith(f"{company_name_folded} ")
        or len(row.get("company_links", [])) >= 2
    ]
    queries = {row["query_id"]: row for row in accepted_query_rows}
    evaluated_at = datetime.now(timezone.utc).isoformat()
    assessments: list[dict] = []
    missing_article_count = 0
    skipped_legacy_query_count = 0

    for article_query in article_queries:
        article_row = articles.get(article_query["document_id"])
        query = queries.get(article_query["query_id"])
        if not article_row:
            missing_article_count += 1
            continue
        if not query:
            skipped_legacy_query_count += 1
            continue
        matching_links = [
            link
            for link in query.get("company_links", [])
            if link.get("stock_code") == stock_code
        ]
        if not matching_links:
            continue
        article = _article_from_row(article_row)
        for company_link in matching_links:
            result = classify_relevance(
                article,
                company,
                query_text=query["text"],
                query_type=query["query_type"],
                link_weight=float(company_link.get("weight", 1.0)),
            )
            assessments.append(
                {
                    "document_id": article.document_id,
                    "stock_code": stock_code,
                    "company_name": company.name,
                    "query_id": query["query_id"],
                    "query_text": query["text"],
                    "query_type": query["query_type"],
                    "relation_type": result.relation_type,
                    "confidence": result.confidence,
                    "status": result.status,
                    "evidence": [*result.evidence, *company_link.get("evidence", [])],
                    "rule_version": result.rule_version,
                    "evaluated_at": evaluated_at,
                }
            )

    assessments.sort(key=lambda row: (row["document_id"], row["query_id"]))
    assessment_path = (
        processed_root / "relevance" / f"{stock_code}_assessments.jsonl"
    )
    write_jsonl_atomic(assessment_path, assessments)

    by_document: dict[str, list[dict]] = defaultdict(list)
    for assessment in assessments:
        by_document[assessment["document_id"]].append(assessment)

    bertopic_rows = []
    keyword_seed_rows = []
    document_statuses = Counter()
    rejected_samples = []
    for document_id, document_assessments in by_document.items():
        best = max(document_assessments, key=lambda row: row["confidence"])
        document_statuses[best["status"]] += 1
        article = articles[document_id]
        eligible = [
            assessment
            for assessment in document_assessments
            if assessment["status"] == "eligible"
        ]
        if not eligible:
            if len(rejected_samples) < 5:
                rejected_samples.append(article["title"])
            continue
        best_eligible = max(eligible, key=lambda row: row["confidence"])
        bertopic_rows.append(
            {
                **article,
                "stock_code": stock_code,
                "company_name": company.name,
                "text": f"{article.get('title', '')}. {article.get('summary', '')}".strip(),
                "relevance_confidence": best_eligible["confidence"],
                "relevance_evidence": best_eligible["evidence"],
                "matched_queries": sorted(
                    {assessment["query_text"] for assessment in eligible}
                ),
                "rule_version": RULE_VERSION,
            }
        )
        direct_eligible = [
            assessment
            for assessment in eligible
            if assessment["query_type"] == "company"
            and assessment["relation_type"] == "direct"
        ]
        if direct_eligible:
            keyword_seed_rows.append(article)

    bertopic_rows.sort(key=lambda row: row.get("published_at", ""), reverse=True)
    keyword_seed_rows.sort(
        key=lambda row: row.get("published_at", ""), reverse=True
    )
    bertopic_path = (
        processed_root / "bertopic" / f"{stock_code}_articles.jsonl"
    )
    keyword_seed_path = (
        processed_root / "keyword_seed" / f"{stock_code}_articles.jsonl"
    )
    write_jsonl_atomic(bertopic_path, bertopic_rows)
    write_jsonl_atomic(keyword_seed_path, keyword_seed_rows)

    relation_statuses = Counter(row["status"] for row in assessments)
    return {
        "stock_code": stock_code,
        "company_name": company.name,
        "rule_version": RULE_VERSION,
        "article_count": len(by_document),
        "assessment_count": len(assessments),
        "relation_status_counts": dict(relation_statuses),
        "document_status_counts": dict(document_statuses),
        "bertopic_eligible_count": len(bertopic_rows),
        "keyword_seed_count": len(keyword_seed_rows),
        "missing_article_count": missing_article_count,
        "skipped_legacy_query_count": skipped_legacy_query_count,
        "eligible_title_samples": [row["title"] for row in bertopic_rows[:5]],
        "rejected_title_samples": rejected_samples,
        "assessment_path": str(assessment_path.relative_to(PROJECT_ROOT)),
        "bertopic_path": str(bertopic_path.relative_to(PROJECT_ROOT)),
        "keyword_seed_path": str(keyword_seed_path.relative_to(PROJECT_ROOT)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", default="005930")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(run(stock_code=args.stock_code), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
