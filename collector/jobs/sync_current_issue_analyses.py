"""최신 주요 이슈 전체의 과거 유사사건 분석을 선계산해 제품 공백을 막는다."""

from __future__ import annotations

import argparse
import json
from datetime import date
from typing import Any, Iterable

from psycopg.rows import dict_row

from collector.companies import SUPPORTED_COMPANIES
from collector.historical_events.service import (
    SCHEMA_VERSION,
    HistoricalIssueRequest,
    analyze_historical_issue,
)
from collector.repositories.supabase import connect
from collector.topic_modeling.issue_classifier import CATEGORIES


VALID_IMPACTS = {"positive", "negative", "neutral", "mixed", "unknown"}


def request_from_issue(
    stock_code: str,
    issue: dict[str, Any],
) -> HistoricalIssueRequest:
    keywords = tuple(
        str(value).strip()
        for value in issue.get("keywords") or []
        if str(value).strip()
    )
    if not keywords and str(issue.get("name") or "").strip():
        keywords = (str(issue["name"]).strip(),)
    category = str(issue.get("category") or "")
    impact = str(issue.get("impact") or "unknown")
    return HistoricalIssueRequest(
        stock_code=stock_code,
        topic_id=str(issue.get("topicId") or ""),
        event_id=str(issue.get("eventId") or ""),
        event_date=date.fromisoformat(str(issue.get("eventDate") or "")),
        name=str(issue.get("name") or ""),
        topic_label=str(issue.get("topicLabel") or ""),
        keywords=keywords,
        category=category if category in CATEGORIES else "",
        impact=impact if impact in VALID_IMPACTS else "unknown",
    )


def requests_from_snapshots(
    snapshots: Iterable[dict[str, Any]],
    *,
    limit_per_stock: int,
) -> list[HistoricalIssueRequest]:
    if limit_per_stock < 1:
        raise ValueError("limit_per_stock은 1 이상이어야 합니다.")
    requests: list[HistoricalIssueRequest] = []
    for snapshot in snapshots:
        stock_code = str(snapshot["stock_code"])
        result = dict(snapshot.get("result") or {})
        for issue in list(result.get("issues") or [])[:limit_per_stock]:
            request = request_from_issue(stock_code, dict(issue))
            request.validate()
            requests.append(request)
    return requests


def _load_latest_snapshots(stock_codes: list[str]) -> list[dict[str, Any]]:
    with connect() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                select distinct on (stock_code)
                       stock_code, result, analyzed_at
                from public.stock_analysis_results
                where stock_code = any(%s)
                order by stock_code, analyzed_at desc
                """,
                (stock_codes,),
            )
            return [dict(row) for row in cursor.fetchall()]


def _ready_current_schema_event_ids(event_ids: list[str]) -> set[str]:
    if not event_ids:
        return set()
    with connect() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                select distinct current_event_id
                from public.historical_issue_analyses
                where current_event_id = any(%s)
                  and status = 'ready'
                  and result->>'schemaVersion' = %s
                """,
                (event_ids, SCHEMA_VERSION),
            )
            return {str(row["current_event_id"]) for row in cursor.fetchall()}


def sync_current_issue_analyses(
    *,
    stock_codes: list[str],
    limit_per_stock: int = 3,
) -> dict[str, Any]:
    snapshots = _load_latest_snapshots(stock_codes)
    requests = requests_from_snapshots(
        snapshots,
        limit_per_stock=limit_per_stock,
    )
    already_ready = _ready_current_schema_event_ids(
        [request.event_id for request in requests]
    )
    ready = 0
    with_events = 0
    empty = 0
    failures: list[dict[str, str]] = []
    processed_event_ids: list[str] = []
    for request in requests:
        if request.event_id in already_ready:
            continue
        try:
            result = analyze_historical_issue(request)
            event_count = len(result.get("events") or [])
            ready += 1
            with_events += int(event_count > 0)
            empty += int(event_count == 0)
            processed_event_ids.append(request.event_id)
            print(
                json.dumps(
                    {
                        "event": "current_issue_analysis_ready",
                        "stockCode": request.stock_code,
                        "eventId": request.event_id,
                        "evidenceEventCount": event_count,
                        "completeness": result.get("completeness"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        except Exception as error:
            failure = {
                "stockCode": request.stock_code,
                "eventId": request.event_id,
                "errorType": type(error).__name__,
            }
            failures.append(failure)
            print(
                json.dumps(
                    {"event": "current_issue_analysis_failed", **failure},
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return {
        "schemaVersion": "current-issue-analysis-sync-v1",
        "requestedStockCount": len(stock_codes),
        "snapshotCount": len(snapshots),
        "currentIssueCount": len(requests),
        "skippedReadyCount": len(already_ready),
        "processedCount": ready,
        "withEvidenceCount": with_events,
        "emptyCount": empty,
        "processedEventIds": processed_event_ids,
        "failureCount": len(failures),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--stock-code", action="append")
    selection.add_argument("--all-supported", action="store_true")
    parser.add_argument("--limit-per-stock", type=int, default=3)
    args = parser.parse_args()
    stock_codes = (
        [company.stock_code for company in SUPPORTED_COMPANIES]
        if args.all_supported
        else list(dict.fromkeys(args.stock_code))
    )
    result = sync_current_issue_analyses(
        stock_codes=stock_codes,
        limit_per_stock=args.limit_per_stock,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failureCount"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
