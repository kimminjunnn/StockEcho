"""StockEcho 제품 데이터 최신성과 운영 gate를 점검한다."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from psycopg.rows import dict_row

from collector.historical_events.service import SCHEMA_VERSION
from collector.repositories.supabase import connect


def health_snapshot() -> dict[str, object]:
    with connect() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                with latest as (
                  select distinct on (event_id, horizon)
                         status, stale_after, as_of
                  from public.event_risk_forecasts
                  order by event_id, horizon, as_of desc
                )
                select
                  count(*) as total,
                  count(*) filter (where status = 'available') as available,
                  count(*) filter (where stale_after <= now()) as stale,
                  max(as_of) as latest
                from latest
                """
            )
            forecasts = dict(cursor.fetchone())
            cursor.execute(
                """
                select
                  count(*) as total,
                  count(*) filter (where status = 'ready') as ready,
                  count(*) filter (where status = 'failed') as failed,
                  max(updated_at) as latest
                from public.historical_issue_analyses
                """
            )
            analyses = dict(cursor.fetchone())
            cursor.execute("select count(*) as total from public.market_daily")
            market_daily = int(cursor.fetchone()["total"])
            cursor.execute("select count(*) as total from public.market_index_daily")
            market_index_daily = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                with latest_stock as (
                  select distinct on (stock_code) stock_code, result
                  from public.stock_analysis_results
                  order by stock_code, analyzed_at desc
                ),
                current_issues as (
                  select issue.value->>'eventId' as event_id
                  from latest_stock stock
                  cross join lateral jsonb_array_elements(
                    coalesce(stock.result->'issues', '[]'::jsonb)
                  ) issue
                ),
                ready_analysis as (
                  select distinct on (current_event_id)
                         current_event_id, result
                  from public.historical_issue_analyses
                  where status = 'ready'
                    and result->>'schemaVersion' = %s
                  order by current_event_id, updated_at desc
                ),
                latest_d5_forecast as (
                  select distinct on (event_id)
                         event_id, status, result
                  from public.event_risk_forecasts
                  where horizon = 'd5'
                  order by event_id, as_of desc
                )
                select
                  count(distinct issue.event_id) as total,
                  count(distinct analysis.current_event_id) as analysis_ready,
                  count(distinct analysis.current_event_id) filter (
                    where jsonb_array_length(analysis.result->'events') > 0
                  ) as with_evidence,
                  count(distinct forecast.event_id) as forecast_ready,
                  count(distinct forecast.event_id) filter (
                    where forecast.status = 'available'
                      and forecast.result #>> '{forecast,returnPercentiles,p50}'
                          is not null
                  ) as forecast_available,
                  count(distinct forecast.event_id) filter (
                    where coalesce(
                      (forecast.result #>> '{forecast,productionEligible}')::boolean,
                      false
                    )
                  ) as production_eligible
                from current_issues issue
                left join ready_analysis analysis
                  on analysis.current_event_id = issue.event_id
                left join latest_d5_forecast forecast
                  on forecast.event_id = issue.event_id
                """,
                (SCHEMA_VERSION,),
            )
            current_issues = dict(cursor.fetchone())
    for payload in (forecasts, analyses):
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = value.astimezone(timezone.utc).isoformat()
    total = int(forecasts["total"])
    stale_ratio = int(forecasts["stale"]) / total if total else 1.0
    current_issue_total = int(current_issues["total"])
    current_issue_coverage = (
        int(current_issues["analysis_ready"]) / current_issue_total
        if current_issue_total
        else 0.0
    )
    current_evidence_coverage = (
        int(current_issues["with_evidence"]) / current_issue_total
        if current_issue_total
        else 0.0
    )
    current_forecast_coverage = (
        int(current_issues["forecast_available"]) / current_issue_total
        if current_issue_total
        else 0.0
    )
    status = (
        "healthy"
        if (
            total > 0
            and market_daily > 0
            and market_index_daily > 0
            and stale_ratio < 0.5
            and current_issue_coverage >= 0.8
            and current_evidence_coverage >= 0.5
            and current_forecast_coverage >= 0.5
        )
        else "degraded"
    )
    return {
        "schemaVersion": "stockecho-health-v1",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "forecasts": {**forecasts, "staleRatio": round(stale_ratio, 6)},
        "historicalAnalyses": analyses,
        "currentIssues": {
            **current_issues,
            "analysisCoverageRatio": round(current_issue_coverage, 6),
            "evidenceCoverageRatio": round(current_evidence_coverage, 6),
            "d5ForecastCoverageRatio": round(current_forecast_coverage, 6),
        },
        "marketDailyRows": market_daily,
        "marketIndexDailyRows": market_index_daily,
    }


def main() -> None:
    print(json.dumps(health_snapshot(), ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
