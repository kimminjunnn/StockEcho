"""Supabase 최신 주요 이슈 snapshot에 LLM 분류 결과를 채운다."""

from __future__ import annotations

import argparse
import json
from typing import Any

from psycopg.types.json import Jsonb

from collector.repositories.supabase import connect
from collector.topic_modeling.issue_classifier import (
    IssueClassifierConfig,
    OpenAIIssueClassifier,
)


def _to_classifier_article(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": article.get("documentId", ""),
        "title": article.get("title", ""),
        "summary": article.get("summary", ""),
        "published_at": article.get("publishedAt", ""),
        "canonical_url": article.get("canonicalUrl", ""),
        "source_url": article.get("sourceUrl", ""),
    }


def classify_result(
    result: dict[str, Any], classifier: OpenAIIssueClassifier
) -> dict[str, Any]:
    stock_code = result.get("stockCode", "")
    company_name = result.get("companyName", "")
    for issue in result.get("issues", []):
        classification = classifier.classify(
            {
                "stock_code": stock_code,
                "company_name": company_name,
                "event_id": issue.get("eventId", ""),
                "event_date": issue.get("eventDate", ""),
                "name": issue.get("name", ""),
                "topic_name": issue.get("topicLabel", ""),
                "keywords": issue.get("keywords", []),
                "representative_article": _to_classifier_article(
                    issue.get("representativeArticle", {})
                ),
                "articles": [
                    _to_classifier_article(article)
                    for article in issue.get("articles", [])
                ],
            }
        )
        issue.update(
            {
                "category": classification["category"],
                "impact": classification["impact"],
                "impactConfidence": classification["impact_confidence"],
                "impactHorizon": classification["impact_horizon"],
                "impactReason": classification["impact_reason"],
                "impactEvidenceDocumentIds": classification[
                    "impact_evidence_document_ids"
                ],
                "classificationMethod": classification["classification_method"],
                "classificationModel": classification["classification_model"],
            }
        )
    return result


def run(stock_codes: list[str]) -> list[dict[str, Any]]:
    classifier = OpenAIIssueClassifier(IssueClassifierConfig.from_env())
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select distinct on (stock_code) id, stock_code, as_of, result
                from public.stock_analysis_results
                where stock_code = any(%s)
                order by stock_code, analyzed_at desc
                """,
                (stock_codes,),
            )
            rows = cursor.fetchall()

    updates = []
    summary = []
    for row_id, stock_code, as_of, result in rows:
        enriched = classify_result(result, classifier)
        updates.append((Jsonb(enriched), row_id))
        summary.append(
            {
                "stock_code": stock_code,
                "as_of": str(as_of),
                "classified_count": len(enriched.get("issues", [])),
            }
        )

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                update public.stock_analysis_results
                set result = %s, analyzed_at = now()
                where id = %s
                """,
                updates,
            )
        connection.commit()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", action="append", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(list(dict.fromkeys(args.stock_code))),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
