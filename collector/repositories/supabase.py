"""Supabase Postgres에 뉴스와 종목 분석 snapshot을 저장한다."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

from collector.companies import SUPPORTED_COMPANIES
from collector.repositories.local import read_jsonl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUEUE_NAME = "stock_analysis"


@dataclass(frozen=True)
class AnalysisSchedulePolicy:
    article_threshold: int = 5
    max_wait_hours: int = 24


@dataclass(frozen=True)
class AnalysisDecision:
    should_enqueue: bool
    reason: str | None = None
    priority: int = 100


URGENT_EVENT_PATTERNS = (
    "공시",
    "거래정지",
    "상장폐지",
    "유상증자",
    "부도",
    "회생절차",
    "대규모 계약",
    "합병",
)


def decide_analysis_schedule(
    *,
    pending_article_count: int,
    last_analyzed_at: datetime | None,
    has_urgent_event: bool,
    now: datetime | None = None,
    policy: AnalysisSchedulePolicy = AnalysisSchedulePolicy(),
) -> AnalysisDecision:
    """새 기사 수와 마지막 분석 시각으로 큐 등록 여부를 결정한다."""

    if pending_article_count <= 0:
        return AnalysisDecision(False)
    if has_urgent_event:
        return AnalysisDecision(True, "urgent_event", 10)
    if pending_article_count >= policy.article_threshold:
        return AnalysisDecision(True, "new_articles_threshold", 50)
    if last_analyzed_at is None:
        return AnalysisDecision(False, "waiting_for_initial_articles")

    current = now or datetime.now(timezone.utc)
    analyzed_at = last_analyzed_at
    if analyzed_at.tzinfo is None:
        analyzed_at = analyzed_at.replace(tzinfo=timezone.utc)
    if current - analyzed_at >= timedelta(hours=policy.max_wait_hours):
        return AnalysisDecision(True, "stale_with_new_articles", 100)
    return AnalysisDecision(False, "waiting_for_more_articles")


def load_database_url() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.getenv("SUPABASE_DB_URL", "")
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise RuntimeError("SUPABASE_DB_URL에 유효한 Postgres 연결 문자열이 필요합니다.")
    return database_url


def connect():
    return psycopg.connect(load_database_url(), autocommit=False)


def apply_migrations() -> None:
    migration_dir = PROJECT_ROOT / "supabase" / "migrations"
    with connect() as connection:
        with connection.cursor() as cursor:
            for path in sorted(migration_dir.glob("*.sql")):
                cursor.execute(path.read_text(encoding="utf-8"))
        connection.commit()


def upsert_supported_stocks(connection) -> None:
    rows = [
        (
            company.stock_code,
            company.name,
            company.tier,
            company.sector,
            Jsonb(list(company.aliases)),
        )
        for company in SUPPORTED_COMPANIES
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into public.stocks (stock_code, name, tier, sector, aliases)
            values (%s, %s, %s, %s, %s)
            on conflict (stock_code) do update set
              name = excluded.name,
              tier = excluded.tier,
              sector = excluded.sector,
              aliases = excluded.aliases,
              is_supported = true,
              updated_at = now()
            """,
            rows,
        )


def _source_name(url_value: str) -> str:
    publishers = {
        "hankyung.com": "한국경제",
        "yna.co.kr": "연합뉴스",
        "mk.co.kr": "매일경제",
        "donga.com": "동아일보",
        "chosun.com": "조선일보",
        "joongang.co.kr": "중앙일보",
        "sbs.co.kr": "SBS",
        "kbs.co.kr": "KBS",
        "mbc.co.kr": "MBC",
        "etnews.com": "전자신문",
        "zdnet.co.kr": "지디넷코리아",
    }
    hostname = urlparse(url_value).hostname or ""
    hostname = hostname.removeprefix("www.")
    return next(
        (name for domain, name in publishers.items() if hostname.endswith(domain)),
        hostname or "원문 기사",
    )


def _to_article(row: dict[str, Any]) -> dict[str, Any]:
    article_url = row.get("canonical_url") or row.get("source_url", "")
    return {
        "documentId": row["document_id"],
        "source": row.get("source", ""),
        "title": row.get("title", ""),
        "summary": row.get("summary", ""),
        "publishedAt": row.get("published_at", ""),
        "canonicalUrl": row.get("canonical_url", ""),
        "sourceUrl": row.get("source_url", ""),
        "sourceName": _source_name(article_url),
        "relevanceConfidence": float(row.get("relevance_confidence", 0)),
    }


def build_stock_result(stock_code: str) -> tuple[dict[str, Any], int]:
    topics_root = PROJECT_ROOT / "data" / "processed" / "topics"
    issue_rows = read_jsonl(topics_root / f"{stock_code}_major_issues.jsonl")
    if not issue_rows:
        raise ValueError(f"{stock_code}의 주요 이슈 결과가 없습니다.")

    issues = []
    for row in sorted(issue_rows, key=lambda value: value["rank"]):
        articles = [_to_article(article) for article in row.get("articles", [])]
        if not articles:
            articles = [_to_article(row["representative_article"])]
        issues.append(
            {
                "topicId": row["topic_id"],
                "eventId": row.get("event_id") or f"{row['topic_id']}:{row['as_of']}",
                "name": row["name"],
                "topicLabel": row.get("topic_name") or " · ".join(row["keywords"][:2]),
                "keywords": row["keywords"],
                "eventDate": row.get("event_date") or articles[0]["publishedAt"][:10],
                "articleCount": row["article_count_in_window"],
                "sourceCount": row["source_count_in_window"],
                "selectionWindowDays": row["selection_window_days"],
                "rank": row["rank"],
                "score": row["score"],
                "representativeArticle": articles[0],
                "articles": articles,
            }
        )

    first = issue_rows[0]
    article_ids = {
        article["documentId"] for issue in issues for article in issue["articles"]
    }
    return (
        {
            "stockCode": first["stock_code"],
            "companyName": first["company_name"],
            "asOf": first["as_of"],
            "modelVersion": first["model_version"],
            "issues": issues,
        },
        len(article_ids),
    )


def _upsert_news_for_stock(connection, stock_code: str) -> None:
    processed_root = PROJECT_ROOT / "data" / "processed"
    articles_by_id = {
        row["document_id"]: row
        for row in read_jsonl(processed_root / "news" / "articles.jsonl")
    }
    assessments = read_jsonl(
        processed_root / "relevance" / f"{stock_code}_assessments.jsonl"
    )
    referenced_ids = {row["document_id"] for row in assessments}
    article_rows = [articles_by_id[value] for value in referenced_ids if value in articles_by_id]

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into public.news_articles (
              document_id, source, title, summary, published_at, canonical_url,
              original_url, source_url, content_hash
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (document_id) do update set
              title = excluded.title,
              summary = excluded.summary,
              source_url = excluded.source_url,
              updated_at = now()
            """,
            [
                (
                    row["document_id"],
                    row.get("source", ""),
                    row.get("title", ""),
                    row.get("summary", ""),
                    row["published_at"],
                    row.get("canonical_url", ""),
                    row.get("original_url", ""),
                    row.get("source_url", ""),
                    row.get("content_hash", ""),
                )
                for row in article_rows
            ],
        )
        cursor.executemany(
            """
            insert into public.article_stocks (
              document_id, stock_code, query_id, query_text, query_type,
              relation_type, confidence, status, evidence, rule_version, evaluated_at
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (document_id, stock_code, query_id, rule_version) do update set
              confidence = excluded.confidence,
              status = excluded.status,
              evidence = excluded.evidence,
              linked_at = case
                when public.article_stocks.status <> excluded.status
                  and excluded.status = 'eligible' then now()
                else public.article_stocks.linked_at
              end,
              evaluated_at = excluded.evaluated_at
            """,
            [
                (
                    row["document_id"],
                    stock_code,
                    row["query_id"],
                    row.get("query_text", ""),
                    row.get("query_type", "company"),
                    row.get("relation_type", "direct"),
                    float(row.get("confidence", 0)),
                    row["status"],
                    Jsonb(row.get("evidence", [])),
                    row["rule_version"],
                    row["evaluated_at"],
                )
                for row in assessments
                if row["document_id"] in articles_by_id
            ],
        )


def sync_stock_news(stock_code: str) -> dict[str, Any]:
    """로컬 수집·관련도 결과만 Supabase에 반영하고 대기 기사 수를 갱신한다."""

    with connect() as connection:
        upsert_supported_stocks(connection)
        _upsert_news_for_stock(connection, stock_code)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.stock_analysis_state (stock_code, status, updated_at)
                values (%s, 'idle', now())
                on conflict (stock_code) do nothing
                """,
                (stock_code,),
            )
            cursor.execute(
                """
                select count(distinct links.document_id)
                from public.article_stocks links
                join public.stock_analysis_state state
                  on state.stock_code = links.stock_code
                where links.stock_code = %s
                  and links.status = 'eligible'
                  and (
                    state.last_analyzed_at is null
                    or links.linked_at > state.last_analyzed_at
                  )
                """,
                (stock_code,),
            )
            pending_article_count = int(cursor.fetchone()[0])
            cursor.execute(
                """
                update public.stock_analysis_state
                set pending_article_count = %s,
                    status = case
                      when status in ('queued', 'running') then status
                      when last_analyzed_at is null and %s < 5 then 'insufficient_data'
                      else status
                    end,
                    updated_at = now()
                where stock_code = %s
                """,
                (pending_article_count, pending_article_count, stock_code),
            )
        connection.commit()
    return {"stock_code": stock_code, "pending_article_count": pending_article_count}


def schedule_stock_if_changed(
    stock_code: str,
    *,
    policy: AnalysisSchedulePolicy = AnalysisSchedulePolicy(),
) -> dict[str, Any]:
    """변경량을 확인하고 필요한 경우 원자적으로 분석 메시지를 등록한다."""

    with connect() as connection:
        upsert_supported_stocks(connection)
        with connection.cursor() as cursor:
            cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", (stock_code,))
            cursor.execute(
                """
                select status, pending_article_count, last_analyzed_at
                from public.stock_analysis_state
                where stock_code = %s
                for update
                """,
                (stock_code,),
            )
            state = cursor.fetchone()
            if not state:
                connection.commit()
                return {
                    "stock_code": stock_code,
                    "message_id": None,
                    "decision": asdict(AnalysisDecision(False, "no_analysis_state")),
                }
            status, pending_article_count, last_analyzed_at = state
            if status in {"queued", "running"}:
                connection.commit()
                return {
                    "stock_code": stock_code,
                    "message_id": None,
                    "decision": asdict(AnalysisDecision(False, "already_scheduled")),
                }
            urgent_expression = " or ".join(
                ["(article.title ilike %s or article.summary ilike %s)"]
                * len(URGENT_EVENT_PATTERNS)
            )
            urgent_values = [
                value
                for pattern in URGENT_EVENT_PATTERNS
                for value in (f"%{pattern}%", f"%{pattern}%")
            ]
            cursor.execute(
                f"""
                select exists (
                  select 1
                  from public.article_stocks links
                  join public.news_articles article using (document_id)
                  where links.stock_code = %s
                    and links.status = 'eligible'
                    and links.linked_at > coalesce(%s, '-infinity'::timestamptz)
                    and ({urgent_expression})
                )
                """,
                (stock_code, last_analyzed_at, *urgent_values),
            )
            decision = decide_analysis_schedule(
                pending_article_count=int(pending_article_count),
                last_analyzed_at=last_analyzed_at,
                has_urgent_event=bool(cursor.fetchone()[0]),
                policy=policy,
            )
            message_id = None
            if decision.should_enqueue:
                cursor.execute(
                    "select * from pgmq.send(%s, %s)",
                    (
                        QUEUE_NAME,
                        Jsonb(
                            {
                                "stock_code": stock_code,
                                "reason": decision.reason,
                                "priority": decision.priority,
                            }
                        ),
                    ),
                )
                message_id = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    update public.stock_analysis_state
                    set status = 'queued', reason = %s,
                        error_message = null, updated_at = now()
                    where stock_code = %s
                    """,
                    (decision.reason, stock_code),
                )
        connection.commit()
    return {
        "stock_code": stock_code,
        "message_id": message_id,
        "decision": asdict(decision),
    }


def sync_stock_snapshot(stock_code: str) -> dict[str, Any]:
    result, article_count = build_stock_result(stock_code)
    with connect() as connection:
        upsert_supported_stocks(connection)
        _upsert_news_for_stock(connection, stock_code)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.stock_analysis_results (
                  stock_code, model_version, as_of, article_count, issue_count, result
                ) values (%s, %s, %s, %s, %s, %s)
                on conflict (stock_code, model_version, as_of) do update set
                  article_count = excluded.article_count,
                  issue_count = excluded.issue_count,
                  result = excluded.result,
                  analyzed_at = now()
                """,
                (
                    stock_code,
                    result["modelVersion"],
                    result["asOf"],
                    article_count,
                    len(result["issues"]),
                    Jsonb(result),
                ),
            )
            cursor.execute(
                """
                insert into public.stock_analysis_state (
                  stock_code, status, pending_article_count, last_analyzed_at,
                  last_model_version, retry_count, error_message, updated_at
                ) values (%s, 'ready', 0, now(), %s, 0, null, now())
                on conflict (stock_code) do update set
                  status = 'ready', pending_article_count = 0,
                  last_analyzed_at = now(), last_model_version = excluded.last_model_version,
                  retry_count = 0, error_message = null, updated_at = now()
                """,
                (stock_code, result["modelVersion"]),
            )
        connection.commit()
    return result


def enqueue_stock(stock_code: str, reason: str, priority: int = 100) -> int | None:
    with connect() as connection:
        upsert_supported_stocks(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "select status from public.stock_analysis_state where stock_code = %s",
                (stock_code,),
            )
            current = cursor.fetchone()
            if current and current[0] in {"queued", "running"}:
                connection.commit()
                return None
            cursor.execute(
                "select * from pgmq.send(%s, %s)",
                (QUEUE_NAME, Jsonb({"stock_code": stock_code, "reason": reason, "priority": priority})),
            )
            message_id = int(cursor.fetchone()[0])
            cursor.execute(
                """
                insert into public.stock_analysis_state (stock_code, status, reason, updated_at)
                values (%s, 'queued', %s, now())
                on conflict (stock_code) do update set
                  status = 'queued', reason = excluded.reason,
                  error_message = null, updated_at = now()
                """,
                (stock_code, reason),
            )
        connection.commit()
    return message_id
