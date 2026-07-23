"""저장 Event 우선 검색, NAVER 보충, KIS 거래일 수익률을 하나로 연결한다."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from collector.clients.kis import KisApiError, KisDailyPriceClient, load_kis_client
from collector.companies import SUPPORTED_COMPANIES, get_company
from collector.historical_events.keywords import (
    extract_core_keywords,
    extract_search_keywords,
)
from collector.historical_events.price_reaction import calculate_trading_day_returns
from collector.historical_events.search import search_historical_events
from collector.jobs.backfill_issue_news import run as backfill_issue_news
from collector.repositories.local import read_jsonl
from collector.repositories.supabase import PROJECT_ROOT, connect, upsert_supported_stocks


SCHEMA_VERSION = "historical-issue-analysis-v6"
RESULT_LIMIT = 4
OTHER_COMPANY_RESULT_LIMIT = 3
MINIMUM_SOURCES = 2
MINIMUM_SIMILARITY = 0.4
PRICE_LOOKAHEAD_DAYS = 90
CURRENT_EVENT_COOLDOWN_DAYS = 2


def _limit_result_mix(
    matches: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """자사 최대 1건과 유사 종목 최대 3건만 사용자 결과로 선택한다."""

    own = [match for match in matches if match["scope"] == "own_company"][:1]
    external = [
        match for match in matches if match["scope"] == "other_company"
    ][:OTHER_COMPANY_RESULT_LIMIT]
    selected = [*own, *external]
    for rank, match in enumerate(selected, start=1):
        match["rank"] = rank
    return selected


def _external_match_count(matches: Sequence[dict[str, Any]]) -> int:
    return sum(match["scope"] == "other_company" for match in matches)


@dataclass(frozen=True)
class HistoricalIssueRequest:
    stock_code: str
    topic_id: str
    event_id: str
    event_date: date
    name: str
    topic_label: str
    keywords: tuple[str, ...]

    def validate(self) -> None:
        get_company(self.stock_code)
        if not self.event_id.strip():
            raise ValueError("event_id가 필요합니다.")
        if not self.topic_id.strip():
            raise ValueError("topic_id가 필요합니다.")
        if not self.name.strip():
            raise ValueError("현재 Event 이름이 필요합니다.")
        if not any(keyword.strip() for keyword in self.keywords):
            raise ValueError("현재 Event 키워드가 하나 이상 필요합니다.")


def _cache_key(
    request: HistoricalIssueRequest,
    core_keywords: Sequence[str],
    search_keywords: Sequence[str],
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stock_code": request.stock_code,
        "topic_id": request.topic_id,
        "event_id": request.event_id,
        "event_date": request.event_date.isoformat(),
        "name": request.name.strip(),
        "topic_label": request.topic_label.strip(),
        "core_keywords": list(core_keywords),
        "search_keywords": list(search_keywords),
        "minimum_sources": MINIMUM_SOURCES,
        "minimum_similarity": MINIMUM_SIMILARITY,
        "result_limit": RESULT_LIMIT,
        "other_company_result_limit": OTHER_COMPANY_RESULT_LIMIT,
        "current_event_cooldown_days": CURRENT_EVENT_COOLDOWN_DAYS,
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"historical_issue_{digest}"


def _source_name(article: dict[str, Any]) -> str:
    url_value = (
        article.get("canonical_url")
        or article.get("original_url")
        or article.get("source_url")
        or ""
    )
    hostname = (urlparse(url_value).hostname or "").removeprefix("www.")
    return hostname or "원문 기사"


def _article_for_api(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "documentId": article.get("document_id", ""),
        "source": article.get("source", ""),
        "title": article.get("title", ""),
        "summary": article.get("summary", ""),
        "publishedAt": article.get("published_at", ""),
        "canonicalUrl": article.get("canonical_url", ""),
        "sourceUrl": article.get("source_url", ""),
        "sourceName": _source_name(article),
        "relevanceConfidence": float(
            article.get("relevance_confidence")
            or article.get("confidence")
            or 0
        ),
    }


def _event_upsert_values(
    event: dict[str, Any],
    *,
    stock_code: str,
    topic_id: str,
    model_version: str,
    origin: str,
) -> tuple[Any, ...]:
    articles = list(event.get("articles") or [])
    representative = event.get("representative_article") or (
        articles[0] if articles else {}
    )
    return (
        str(event["event_id"]),
        stock_code,
        topic_id,
        event["event_date"],
        event.get("name") or representative.get("title") or "과거 이슈",
        Jsonb(list(event.get("keywords") or [])),
        int(event.get("article_count") or len(articles)),
        int(event.get("source_count") or 0),
        Jsonb(representative),
        Jsonb(articles),
        model_version,
        origin,
    )


def _upsert_event_rows(connection, values: Sequence[tuple[Any, ...]]) -> None:
    if not values:
        return
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into public.historical_events (
              event_id, stock_code, topic_id, event_date, name, keywords,
              article_count, source_count, representative_article, articles,
              model_version, origin
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (event_id) do update set
              stock_code = excluded.stock_code,
              topic_id = excluded.topic_id,
              event_date = excluded.event_date,
              name = excluded.name,
              keywords = excluded.keywords,
              article_count = excluded.article_count,
              source_count = excluded.source_count,
              representative_article = excluded.representative_article,
              articles = excluded.articles,
              model_version = excluded.model_version,
              origin = excluded.origin,
              updated_at = now()
            """,
            values,
        )


def sync_saved_events(connection, *, project_root: Path = PROJECT_ROOT) -> int:
    """로컬 Topic 전체와 Supabase 분석 snapshot의 Event를 검색 테이블에 합친다."""

    values: list[tuple[Any, ...]] = []
    topics_root = project_root / "data" / "processed" / "topics"
    for path in sorted(topics_root.glob("*_topics.jsonl")):
        for topic in read_jsonl(path):
            if topic.get("is_outlier"):
                continue
            for event in topic.get("events", []):
                if int(event.get("source_count", 0)) < MINIMUM_SOURCES:
                    continue
                values.append(
                    _event_upsert_values(
                        event,
                        stock_code=str(topic["stock_code"]),
                        topic_id=str(topic.get("topic_id", "")),
                        model_version=str(topic.get("model_version", "")),
                        origin="topic_model",
                    )
                )

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select stock_code, model_version, result
            from public.stock_analysis_results
            order by analyzed_at
            """
        )
        snapshot_rows = cursor.fetchall()
    for row in snapshot_rows:
        for issue in row["result"].get("issues", []):
            source_count = int(issue.get("sourceCount", 0))
            if source_count < MINIMUM_SOURCES:
                continue
            articles = [
                {
                    "document_id": article.get("documentId", ""),
                    "source": article.get("source", ""),
                    "title": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "published_at": article.get("publishedAt", ""),
                    "canonical_url": article.get("canonicalUrl", ""),
                    "source_url": article.get("sourceUrl", ""),
                    "relevance_confidence": article.get(
                        "relevanceConfidence", 0
                    ),
                }
                for article in issue.get("articles", [])
            ]
            representative_value = issue.get("representativeArticle") or {}
            representative = {
                "document_id": representative_value.get("documentId", ""),
                "source": representative_value.get("source", ""),
                "title": representative_value.get("title", ""),
                "summary": representative_value.get("summary", ""),
                "published_at": representative_value.get("publishedAt", ""),
                "canonical_url": representative_value.get("canonicalUrl", ""),
                "source_url": representative_value.get("sourceUrl", ""),
                "relevance_confidence": representative_value.get(
                    "relevanceConfidence", 0
                ),
            }
            event = {
                "event_id": issue.get("eventId"),
                "event_date": issue.get("eventDate"),
                "name": issue.get("name"),
                "keywords": issue.get("keywords", []),
                "article_count": issue.get("articleCount", len(articles)),
                "source_count": source_count,
                "representative_article": representative,
                "articles": articles or [representative],
            }
            if not event["event_id"] or not event["event_date"]:
                continue
            values.append(
                _event_upsert_values(
                    event,
                    stock_code=str(row["stock_code"]),
                    topic_id=str(issue.get("topicId", "")),
                    model_version=str(row["model_version"]),
                    origin="analysis_snapshot",
                )
            )

    _upsert_event_rows(connection, values)
    return len(values)


def _load_saved_topics(connection, *, before: date) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select event.*, stock.name as company_name
            from public.historical_events event
            join public.stocks stock using (stock_code)
            where event.event_date < %s
              and event.source_count >= %s
              and (
                event.origin <> 'naver_backfill'
                or event.model_version = %s
              )
            order by event.event_date desc, event.source_count desc
            """,
            (before, MINIMUM_SOURCES, SCHEMA_VERSION),
        )
        rows = cursor.fetchall()
    return [
        {
            "stock_code": row["stock_code"],
            "company_name": row["company_name"],
            "topic_id": row["topic_id"] or f"event-topic:{row['event_id']}",
            "name": row["name"],
            "keywords": list(row["keywords"] or []),
            "is_outlier": False,
            "origin": row["origin"],
            "events": [
                {
                    "event_id": row["event_id"],
                    "event_date": row["event_date"].isoformat(),
                    "name": row["name"],
                    "keywords": list(row["keywords"] or []),
                    "article_count": row["article_count"],
                    "source_count": row["source_count"],
                    "representative_article": row["representative_article"],
                    "articles": list(row["articles"] or []),
                    "origin": row["origin"],
                }
            ],
        }
        for row in rows
    ]


def _upsert_backfill_articles(connection, events: Sequence[dict[str, Any]]) -> None:
    article_rows: dict[str, dict[str, Any]] = {}
    links: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for event in events:
        for article in event.get("articles", []):
            document_id = str(article.get("document_id", ""))
            if not document_id:
                continue
            article_rows[document_id] = article
            key = (
                document_id,
                str(article.get("stock_code", event["stock_code"])),
                str(article.get("query_id", "")),
                str(article.get("rule_version", "relevance-v2")),
            )
            links[key] = article
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
                    document_id,
                    article.get("source", "naver"),
                    article.get("title", ""),
                    article.get("summary", ""),
                    article["published_at"],
                    article.get("canonical_url", ""),
                    article.get("original_url", ""),
                    article.get("source_url", ""),
                    article.get("content_hash", ""),
                )
                for document_id, article in article_rows.items()
            ],
        )
        cursor.executemany(
            """
            insert into public.article_stocks (
              document_id, stock_code, query_id, query_text, query_type,
              relation_type, confidence, status, evidence, rule_version,
              evaluated_at
            ) values (%s, %s, %s, %s, %s, %s, %s, 'eligible', %s, %s, %s)
            on conflict (document_id, stock_code, query_id, rule_version)
            do update set
              confidence = excluded.confidence,
              status = 'eligible',
              evidence = excluded.evidence,
              evaluated_at = excluded.evaluated_at
            """,
            [
                (
                    document_id,
                    stock_code,
                    query_id,
                    article.get("query_text", ""),
                    article.get("query_type", "event"),
                    article.get("relation_type", "industry"),
                    float(article.get("relevance_confidence", 0)),
                    Jsonb(article.get("relevance_evidence", [])),
                    rule_version,
                    article.get("evaluated_at")
                    or datetime.now(timezone.utc).isoformat(),
                )
                for (
                    document_id,
                    stock_code,
                    query_id,
                    rule_version,
                ), article in links.items()
                if query_id
            ],
        )


def _save_backfill_events(
    connection, events: Sequence[dict[str, Any]]
) -> None:
    _upsert_backfill_articles(connection, events)
    values = [
        _event_upsert_values(
            event,
            stock_code=str(event["stock_code"]),
            topic_id=f"naver-search:{event['event_id']}",
            model_version=SCHEMA_VERSION,
            origin="naver_backfill",
        )
        for event in events
    ]
    _upsert_event_rows(connection, values)


def _load_market_rows(
    connection, *, stock_code: str, start_date: date, end_date: date
) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select trading_date, close_price
            from public.market_daily
            where stock_code = %s
              and trading_date between %s and %s
            order by trading_date
            """,
            (stock_code, start_date, end_date),
        )
        return list(cursor.fetchall())


def _upsert_market_rows(
    connection, *, stock_code: str, rows: Sequence[dict[str, Any]]
) -> None:
    if not rows:
        return
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into public.market_daily (
              stock_code, trading_date, close_price, source, fetched_at
            ) values (%s, %s, %s, 'KIS', now())
            on conflict (stock_code, trading_date) do update set
              close_price = excluded.close_price,
              source = excluded.source,
              fetched_at = now()
            """,
            [
                (stock_code, row["trading_date"], row["close_price"])
                for row in rows
            ],
        )


def _price_reaction(
    connection,
    event: dict[str, Any],
    *,
    kis_client: KisDailyPriceClient | None,
) -> tuple[dict[str, Any], KisDailyPriceClient | None]:
    event_date = date.fromisoformat(event["event_date"])
    today = datetime.now(timezone.utc).date()
    end_date = min(event_date + timedelta(days=PRICE_LOOKAHEAD_DAYS), today)
    representative = event.get("representative_article") or {}
    published_at = representative.get("published_at")
    rows = _load_market_rows(
        connection,
        stock_code=event["stock_code"],
        start_date=event_date - timedelta(days=7),
        end_date=end_date,
    )
    reaction = calculate_trading_day_returns(
        rows,
        event_date=event_date,
        representative_published_at=published_at,
    )
    if reaction["status"] == "complete" or end_date < event_date:
        return reaction, kis_client

    try:
        client = kis_client or load_kis_client()
        fetched = client.daily_closes(
            event["stock_code"],
            start_date=event_date - timedelta(days=7),
            end_date=end_date,
        )
        _upsert_market_rows(
            connection, stock_code=event["stock_code"], rows=fetched
        )
        rows = _load_market_rows(
            connection,
            stock_code=event["stock_code"],
            start_date=event_date - timedelta(days=7),
            end_date=end_date,
        )
        return (
            calculate_trading_day_returns(
                rows,
                event_date=event_date,
                representative_published_at=published_at,
            ),
            client,
        )
    except (KisApiError, ValueError) as error:
        if reaction["status"] == "unavailable":
            reaction["reason"] = str(error)
        else:
            reaction["reason"] = (
                f"{reaction.get('reason') or ''} KIS 보충 조회를 완료하지 못했습니다."
            ).strip()
        return reaction, kis_client


def _cached_result(connection, cache_key: str) -> dict[str, Any] | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select result
            from public.historical_issue_analyses
            where cache_key = %s and status = 'ready' and result is not null
            """,
            (cache_key,),
        )
        row = cursor.fetchone()
    return dict(row["result"]) if row else None


def _mark_processing(
    connection,
    *,
    cache_key: str,
    request: HistoricalIssueRequest,
    core_keywords: Sequence[str],
    search_keywords: Sequence[str],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into public.historical_issue_analyses (
              cache_key, stock_code, current_event_id, current_event_date,
              request_context, status, result, error_code, updated_at
            ) values (%s, %s, %s, %s, %s, 'processing', null, null, now())
            on conflict (cache_key) do update set
              request_context = excluded.request_context,
              status = 'processing',
              result = null,
              error_code = null,
              updated_at = now()
            """,
            (
                cache_key,
                request.stock_code,
                request.event_id,
                request.event_date,
                Jsonb(
                    {
                        "topicId": request.topic_id,
                        "name": request.name,
                        "topicLabel": request.topic_label,
                        "keywords": list(request.keywords),
                        "coreKeywords": list(core_keywords),
                        "searchKeywords": list(search_keywords),
                    }
                ),
            ),
        )


def _store_result(connection, cache_key: str, result: dict[str, Any]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update public.historical_issue_analyses
            set status = 'ready', result = %s, error_code = null, updated_at = now()
            where cache_key = %s
            """,
            (Jsonb(result), cache_key),
        )


def analyze_historical_issue(
    request: HistoricalIssueRequest,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """동일 요청을 영속 캐시하고 실제 Event·가격 반응만 반환한다."""

    request.validate()
    company = get_company(request.stock_code)
    core_keywords = extract_core_keywords(
        name=request.name,
        topic_label=request.topic_label,
        keywords=request.keywords,
        company_name=company.name,
    )
    if not core_keywords:
        raise ValueError("과거 검색에 사용할 핵심 키워드를 만들 수 없습니다.")
    search_keywords = extract_search_keywords(
        keywords=request.keywords,
        core_keywords=core_keywords,
        company_name=company.name,
    )
    cache_key = _cache_key(request, core_keywords, search_keywords)
    candidate_before = request.event_date - timedelta(
        days=CURRENT_EVENT_COOLDOWN_DAYS
    )

    with connect() as connection:
        cached = _cached_result(connection, cache_key)
        if cached:
            connection.commit()
            return {**cached, "cacheHit": True}

        with connection.cursor() as cursor:
            cursor.execute(
                "select pg_advisory_lock(hashtext(%s))",
                (cache_key,),
            )
        try:
            cached = _cached_result(connection, cache_key)
            if cached:
                connection.commit()
                return {**cached, "cacheHit": True}

            upsert_supported_stocks(connection)
            _mark_processing(
                connection,
                cache_key=cache_key,
                request=request,
                core_keywords=core_keywords,
                search_keywords=search_keywords,
            )
            sync_saved_events(connection, project_root=project_root)
            connection.commit()

            saved_topics = _load_saved_topics(
                connection, before=candidate_before
            )
            initial_search = search_historical_events(
                saved_topics,
                target_stock_code=request.stock_code,
                keywords=search_keywords,
                before=candidate_before,
                current_event_id=request.event_id,
                limit=RESULT_LIMIT,
                minimum_score=MINIMUM_SIMILARITY,
                minimum_sources=MINIMUM_SOURCES,
            )
            matches = _limit_result_mix(initial_search["matches"])
            backfill_result: dict[str, Any] | None = None
            if _external_match_count(matches) < OTHER_COMPANY_RESULT_LIMIT:
                backfill_result = backfill_issue_news(
                    stock_code=request.stock_code,
                    keywords=search_keywords,
                    before=candidate_before,
                    result_limit=RESULT_LIMIT,
                    external_result_limit=OTHER_COMPANY_RESULT_LIMIT,
                    minimum_sources=MINIMUM_SOURCES,
                    project_root=project_root,
                )
                _save_backfill_events(
                    connection,
                    backfill_result.get("qualifying_event_proxies", []),
                )
                connection.commit()
                saved_topics = _load_saved_topics(
                    connection, before=candidate_before
                )
                matches = _limit_result_mix(
                    search_historical_events(
                        saved_topics,
                        target_stock_code=request.stock_code,
                        keywords=search_keywords,
                        before=candidate_before,
                        current_event_id=request.event_id,
                        limit=RESULT_LIMIT,
                        minimum_score=MINIMUM_SIMILARITY,
                        minimum_sources=MINIMUM_SOURCES,
                    )["matches"]
                )

            kis_client: KisDailyPriceClient | None = None
            api_events: list[dict[str, Any]] = []
            for match in matches:
                reaction, kis_client = _price_reaction(
                    connection, match, kis_client=kis_client
                )
                api_events.append(
                    {
                        "rank": match["rank"],
                        "eventId": match["event_id"],
                        "topicId": match["topic_id"],
                        "stockCode": match["stock_code"],
                        "companyName": match["company_name"],
                        "scope": match["scope"],
                        "eventDate": match["event_date"],
                        "name": match["name"],
                        "keywords": list(match["keywords"]),
                        "similarityScore": match["similarity_score"],
                        "matchedKeywords": list(match["matched_keywords"]),
                        "similarityReasons": list(
                            match["similarity_reasons"]
                        ),
                        "articleCount": match["article_count"],
                        "sourceCount": match["source_count"],
                        "origin": match["origin"],
                        "representativeArticle": _article_for_api(
                            match["representative_article"]
                        ),
                        "articles": [
                            _article_for_api(article)
                            for article in match["articles"][:5]
                        ],
                        "priceReaction": reaction,
                    }
                )
            connection.commit()

            has_partial_prices = any(
                event["priceReaction"]["status"] != "complete"
                for event in api_events
            )
            if not api_events:
                completeness = "insufficient"
            elif (
                _external_match_count(matches) < OTHER_COMPANY_RESULT_LIMIT
                or has_partial_prices
            ):
                completeness = "partial"
            else:
                completeness = "complete"

            result = {
                "schemaVersion": SCHEMA_VERSION,
                "cacheKey": cache_key,
                "cacheHit": False,
                "completeness": completeness,
                "target": {
                    "stockCode": request.stock_code,
                    "companyName": company.name,
                    "topicId": request.topic_id,
                    "eventId": request.event_id,
                    "eventDate": request.event_date.isoformat(),
                    "name": request.name,
                    "topicLabel": request.topic_label,
                    "keywords": list(request.keywords),
                    "coreKeywords": core_keywords,
                    "searchKeywords": search_keywords,
                },
                "search": {
                    "storedEventCount": len(saved_topics),
                    "storedMatchCount": len(initial_search["matches"]),
                    "naverBackfillUsed": backfill_result is not None,
                    "naverCacheHit": (
                        bool(backfill_result.get("cache_hit"))
                        if backfill_result
                        else False
                    ),
                    "naverCallCount": (
                        int(backfill_result.get("call_count", 0))
                        if backfill_result
                        else 0
                    ),
                    "minimumSources": MINIMUM_SOURCES,
                    "minimumSimilarity": MINIMUM_SIMILARITY,
                    "candidateBefore": candidate_before.isoformat(),
                    "currentEventCooldownDays": CURRENT_EVENT_COOLDOWN_DAYS,
                },
                "events": api_events,
                "dataCoverageNotice": (
                    "NAVER 검색 및 StockEcho가 수집한 뉴스 범위에서 분석한 "
                    "결과입니다. 전체 언론 보도를 포함하지 않을 수 있습니다."
                ),
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            _store_result(connection, cache_key, result)
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    update public.historical_issue_analyses
                    set status = 'failed', result = null,
                        error_code = 'analysis_failed', updated_at = now()
                    where cache_key = %s
                    """,
                    (cache_key,),
                )
            connection.commit()
            raise
        finally:
            with connection.cursor() as cursor:
                cursor.execute(
                    "select pg_advisory_unlock(hashtext(%s))",
                    (cache_key,),
                )
            connection.commit()
