"""저장된 유사사건 분석을 제품용 경험분포 forecast로 materialize한다."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from collector.repositories.supabase import connect
from collector.companies import get_company
from collector.event_study.reactions import calculate_market_adjusted_reaction
from collector.historical_events.search import search_historical_events
from collector.historical_events.service import _load_saved_topics
from collector.risk_model.empirical import empirical_risk_forecast


def _dataset_version(events: list[dict[str, Any]]) -> str:
    evidence = [
        {
            "eventId": event.get("eventId"),
            "eventDate": event.get("eventDate"),
            "similarityScore": event.get("similarityScore"),
            "priceReaction": event.get("priceReaction"),
        }
        for event in events
    ]
    digest = hashlib.sha256(
        json.dumps(
            evidence,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"historical-evidence-{digest}"


def _enrich_abnormal_returns(
    events: list[dict[str, Any]],
    *,
    stock_prices: dict[str, list[dict[str, Any]]],
    benchmark_prices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched = []
    for source in events:
        event = dict(source)
        stock_code = str(event.get("stockCode") or "")
        event_date_value = str(event.get("eventDate") or "")
        representative = (
            event.get("representativeArticle")
            or event.get("representative_article")
            or {}
        )
        if stock_code in stock_prices and event_date_value:
            reaction = calculate_market_adjusted_reaction(
                stock_prices[stock_code],
                benchmark_prices,
                event_date=date.fromisoformat(event_date_value),
                representative_published_at=(
                    representative.get("publishedAt")
                    or representative.get("published_at")
                ),
            )
            event["priceReaction"] = {
                **dict(event.get("priceReaction") or {}),
                **reaction,
            }
        enriched.append(event)
    return enriched


def _forecast_evidence_events(
    result: dict[str, Any],
    *,
    saved_topics: list[dict[str, Any]],
    limit: int = 20,
    minimum_event_date: date = date(2021, 1, 1),
) -> list[dict[str, Any]]:
    target = dict(result.get("target") or {})
    stock_code = str(target.get("stockCode") or "")
    event_date_value = str(target.get("eventDate") or "")
    keywords = list(target.get("searchKeywords") or target.get("keywords") or [])
    if not stock_code or not event_date_value or not keywords:
        return list(result.get("events") or [])
    company = get_company(stock_code)
    search = search_historical_events(
        saved_topics,
        target_stock_code=stock_code,
        keywords=keywords,
        context_keywords=list(target.get("coreKeywords") or []),
        target_sector=company.sector,
        target_category=str(target.get("category") or ""),
        target_impact=str(target.get("impact") or "unknown"),
        before=date.fromisoformat(event_date_value) - timedelta(days=2),
        current_event_id=str(target.get("eventId") or ""),
        limit=max(limit * 5, 100),
        minimum_score=0.4,
        minimum_sources=2,
    )
    searched = [
        {
            "eventId": match["event_id"],
            "stockCode": match["stock_code"],
            "eventDate": match["event_date"],
            "similarityScore": match["similarity_score"],
            "sourceCount": match["source_count"],
            "representativeArticle": match["representative_article"],
        }
        for match in search["matches"]
        if date.fromisoformat(str(match["event_date"])) >= minimum_event_date
    ]
    original = [
        dict(event)
        for event in list(result.get("events") or [])
        if event.get("eventDate")
        and date.fromisoformat(str(event["eventDate"])) >= minimum_event_date
    ]
    combined: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in [*original, *searched]:
        event_id = str(event.get("eventId") or "")
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        combined.append(event)
        if len(combined) == limit:
            break
    return combined


def materialize(*, stale_hours: int = 24 * 7) -> dict[str, Any]:
    if stale_hours < 1:
        raise ValueError("stale_hours는 1 이상이어야 합니다.")
    now = datetime.now(timezone.utc)
    written = 0
    unavailable = 0
    with connect() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                select distinct on (current_event_id)
                       current_event_id, stock_code, result, updated_at
                from public.historical_issue_analyses
                where status = 'ready' and result is not null
                order by current_event_id, updated_at desc
                """
            )
            analyses = list(cursor.fetchall())
            cursor.execute(
                """
                select stock_code, trading_date, close_price
                from public.market_daily
                order by stock_code, trading_date
                """
            )
            market_rows = list(cursor.fetchall())
            cursor.execute(
                """
                select trading_date, close_price
                from public.market_index_daily
                where index_code = 'KOSPI'
                order by trading_date
                """
            )
            benchmark_prices = list(cursor.fetchall())
            saved_topics = _load_saved_topics(
                connection,
                before=datetime.now(timezone.utc).date() + timedelta(days=1),
            )
        stock_prices: dict[str, list[dict[str, Any]]] = {}
        for row in market_rows:
            stock_prices.setdefault(str(row["stock_code"]), []).append(row)
        with connection.cursor() as cursor:
            for analysis in analyses:
                result = dict(analysis["result"])
                events = _enrich_abnormal_returns(
                    _forecast_evidence_events(
                        result,
                        saved_topics=saved_topics,
                    ),
                    stock_prices=stock_prices,
                    benchmark_prices=benchmark_prices,
                )
                forecast = empirical_risk_forecast(events)
                dataset_version = _dataset_version(events)
                evidence_ids = [
                    str(event.get("eventId"))
                    for event in events
                    if event.get("eventId")
                ]
                for horizon, horizon_result in forecast["horizons"].items():
                    status = str(horizon_result["status"])
                    unavailable += int(status == "unavailable")
                    payload = {
                        "eventId": str(analysis["current_event_id"]),
                        "stockCode": str(analysis["stock_code"]),
                        "horizon": horizon,
                        "asOf": now.isoformat(),
                        "staleAfter": (now + timedelta(hours=stale_hours)).isoformat(),
                        "stale": False,
                        "forecast": {
                            "lossProbability": horizon_result["loss_probability"],
                            "returnPercentiles": horizon_result["return_percentiles"],
                            "observedEventCount": horizon_result["observed_event_count"],
                            "effectiveSampleSize": horizon_result["effective_sample_size"],
                            "confidence": horizon_result["confidence"],
                            "productionEligible": horizon_result["production_eligible"],
                            "returnBasis": horizon_result["return_basis"],
                            "modelVersion": forecast["model_version"],
                            "datasetVersion": dataset_version,
                        },
                        "observedHistory": {
                            "events": events,
                            "sampleCount": horizon_result["observed_event_count"],
                        },
                        "limitations": [
                            forecast["disclaimer"],
                            (
                                "medium 이상 신뢰도에서만 확률을 제품 판단 보조값으로 "
                                "사용합니다."
                            ),
                        ],
                    }
                    cursor.execute(
                        """
                        insert into public.event_risk_forecasts (
                          event_id, stock_code, horizon, as_of, stale_after,
                          status, confidence, model_version, dataset_version,
                          result, evidence_event_ids, updated_at
                        ) values (
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
                        )
                        on conflict (
                          event_id, horizon, model_version, dataset_version
                        ) do update set
                          as_of = excluded.as_of,
                          stale_after = excluded.stale_after,
                          status = excluded.status,
                          confidence = excluded.confidence,
                          result = excluded.result,
                          evidence_event_ids = excluded.evidence_event_ids,
                          updated_at = now()
                        """,
                        (
                            analysis["current_event_id"],
                            analysis["stock_code"],
                            horizon,
                            now,
                            now + timedelta(hours=stale_hours),
                            status,
                            horizon_result["confidence"],
                            forecast["model_version"],
                            dataset_version,
                            Jsonb(payload),
                            Jsonb(evidence_ids),
                        ),
                    )
                    written += 1
        connection.commit()
    return {
        "analysisCount": len(analyses),
        "forecastRowsWritten": written,
        "unavailableRows": unavailable,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stale-hours", type=int, default=24 * 7)
    args = parser.parse_args()
    print(json.dumps(materialize(stale_hours=args.stale_hours), ensure_ascii=False))


if __name__ == "__main__":
    main()
