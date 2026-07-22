"""현재 이슈 키워드로 자사·공통·동종기업 과거 뉴스를 단계적으로 수집한다."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from collector.companies import get_company
from collector.historical_news.planner import build_issue_news_query_plan
from collector.jobs.collect_news_query import load_source
from collector.jobs.collect_news_query import run as collect_query
from collector.repositories.local import write_json_atomic
from collector.sources.base import NewsSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "issue-news-backfill-v1"
KST = ZoneInfo("Asia/Seoul")


def _search_id(stock_code: str, phrases: Sequence[str], before: date) -> str:
    value = "|".join((stock_code, before.isoformat(), *phrases))
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"issue_search_{digest}"


def _local_date(value: str) -> date:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(KST).date()


def _source_key(url: str) -> str:
    host = urlparse(url).hostname
    return host or "unknown"


def _summary_path(project_root: Path, search_id: str) -> Path:
    return (
        project_root
        / "data"
        / "processed"
        / "historical_search"
        / f"{search_id}.json"
    )


def _proxy_events(
    event_sources: dict[tuple[str, date], set[str]],
    event_documents: dict[tuple[str, date], set[str]],
    *,
    target_stock_code: str,
    minimum_sources: int,
) -> list[dict[str, Any]]:
    rows = []
    for (stock_code, event_date), sources in event_sources.items():
        if len(sources) < minimum_sources:
            continue
        rows.append(
            {
                "stock_code": stock_code,
                "scope": (
                    "own_company"
                    if stock_code == target_stock_code
                    else "other_company"
                ),
                "event_date": event_date.isoformat(),
                "article_count": len(event_documents[(stock_code, event_date)]),
                "source_count": len(sources),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["scope"] != "own_company",
            -row["article_count"],
            -row["source_count"],
            row["event_date"],
            row["stock_code"],
        ),
    )


def run(
    *,
    stock_code: str,
    keywords: Sequence[str],
    before: date,
    extra_variants: Sequence[str] = (),
    source_name: str = "naver",
    display: int = 100,
    max_pages_per_query: int = 3,
    max_total_calls: int = 12,
    result_limit: int = 3,
    minimum_sources: int = 2,
    max_peers: int = 3,
    refresh: bool = False,
    source: NewsSource | None = None,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """필요한 과거 사례 수가 채워질 때까지만 NAVER ``sort=sim``을 호출한다."""

    if not 1 <= display <= 100:
        raise ValueError("display는 1~100이어야 합니다.")
    if max_pages_per_query < 1:
        raise ValueError("max_pages_per_query는 1 이상이어야 합니다.")
    if max_total_calls < 1:
        raise ValueError("max_total_calls는 1 이상이어야 합니다.")
    if result_limit < 1:
        raise ValueError("result_limit은 1 이상이어야 합니다.")
    if minimum_sources < 1:
        raise ValueError("minimum_sources는 1 이상이어야 합니다.")

    company = get_company(stock_code)
    plan = build_issue_news_query_plan(
        company,
        keywords,
        extra_variants=extra_variants,
        max_peers=max_peers,
    )
    search_id = _search_id(stock_code, plan.phrases, before)
    output_path = _summary_path(project_root, search_id)
    if output_path.exists() and not refresh:
        cached = json.loads(output_path.read_text(encoding="utf-8"))
        return {**cached, "cache_hit": True}

    source = source or load_source(source_name)
    event_sources: dict[tuple[str, date], set[str]] = defaultdict(set)
    event_documents: dict[tuple[str, date], set[str]] = defaultdict(set)
    collection_calls: list[dict[str, Any]] = []
    exhausted_query_ids: set[str] = set()

    def qualifying_events() -> list[dict[str, Any]]:
        return _proxy_events(
            event_sources,
            event_documents,
            target_stock_code=stock_code,
            minimum_sources=minimum_sources,
        )

    def own_ready() -> bool:
        return any(row["scope"] == "own_company" for row in qualifying_events())

    def external_company_count() -> int:
        return len(
            {
                row["stock_code"]
                for row in qualifying_events()
                if row["scope"] == "other_company"
            }
        )

    def external_required() -> int:
        return result_limit - (1 if own_ready() else 0)

    def ingest(result: dict[str, Any]) -> None:
        for article in result["eligible_articles"]:
            article_date = _local_date(article["published_at"])
            if article_date >= before:
                continue
            key = (article["stock_code"], article_date)
            event_documents[key].add(article["document_id"])
            event_sources[key].add(
                _source_key(article.get("canonical_url", ""))
            )

    def collect_phase(
        phase: str,
        queries: Sequence,
        stop_when: Callable[[], bool],
    ) -> None:
        for page_index in range(max_pages_per_query):
            start = 1 + page_index * display
            if start > 1000:
                return
            for query in queries:
                if len(collection_calls) >= max_total_calls or stop_when():
                    return
                if query.query_id in exhausted_query_ids:
                    continue
                result = collect_query(
                    query=query,
                    source_name=source_name,
                    display=display,
                    start=start,
                    sort="sim",
                    source=source,
                    project_root=project_root,
                )
                ingest(result)
                exhausted = result["received_count"] < display
                if exhausted:
                    exhausted_query_ids.add(query.query_id)
                collection_calls.append(
                    {
                        "phase": phase,
                        "query_id": query.query_id,
                        "query": query.text,
                        "start": start,
                        "sort": "sim",
                        "received_count": result["received_count"],
                        "new_count": result["new_count"],
                        "eligible_count": len(result["eligible_articles"]),
                        "reported_total": result["reported_total"],
                        "exhausted": exhausted,
                    }
                )

    collect_phase("own_company", plan.own_queries, own_ready)
    collect_phase(
        "common_industry",
        plan.common_queries,
        lambda: external_company_count() >= external_required(),
    )
    if external_company_count() < external_required():
        collect_phase(
            "peer_company",
            plan.peer_queries,
            lambda: external_company_count() >= external_required(),
        )

    events = qualifying_events()
    result = {
        "schema_version": SCHEMA_VERSION,
        "search_id": search_id,
        "cache_hit": False,
        "stock_code": stock_code,
        "company_name": company.name,
        "keywords": list(plan.keywords),
        "phrases": list(plan.phrases),
        "before": before.isoformat(),
        "selection_goal": {
            "result_limit": result_limit,
            "own_company_max": 1,
            "other_companies_required": external_required(),
            "minimum_sources_per_date": minimum_sources,
        },
        "peer_stock_codes": list(plan.peer_stock_codes),
        "query_plan": {
            "own_company": [query.text for query in plan.own_queries],
            "common_industry": [query.text for query in plan.common_queries],
            "peer_company": [query.text for query in plan.peer_queries],
        },
        "call_count": len(collection_calls),
        "max_total_calls": max_total_calls,
        "calls": collection_calls,
        "qualifying_event_proxies": events,
        "own_company_ready": own_ready(),
        "other_company_count": external_company_count(),
        "goal_met": (
            len(events) >= result_limit
            and external_company_count() >= external_required()
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "next_step": "관련도 재평가 후 종목별 BERTopic/Event 산출물을 다시 생성하세요.",
        "output_path": str(output_path.relative_to(project_root)),
    }
    write_json_atomic(output_path, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", required=True)
    parser.add_argument("--keyword", action="append", required=True)
    parser.add_argument("--before", type=date.fromisoformat, required=True)
    parser.add_argument("--variant", action="append", default=[])
    parser.add_argument("--source", default="naver")
    parser.add_argument("--display", type=int, default=100)
    parser.add_argument("--max-pages-per-query", type=int, default=3)
    parser.add_argument("--max-total-calls", type=int, default=12)
    parser.add_argument("--result-limit", type=int, default=3)
    parser.add_argument("--minimum-sources", type=int, default=2)
    parser.add_argument("--max-peers", type=int, default=3)
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run(
        stock_code=args.stock_code,
        keywords=args.keyword,
        before=args.before,
        extra_variants=args.variant,
        source_name=args.source,
        display=args.display,
        max_pages_per_query=args.max_pages_per_query,
        max_total_calls=args.max_total_calls,
        result_limit=args.result_limit,
        minimum_sources=args.minimum_sources,
        max_peers=args.max_peers,
        refresh=args.refresh,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
