"""BERTopic assignment를 영구 저장 가능한 Topic/Event 결과로 변환한다."""

from __future__ import annotations

import hashlib
import math
import re
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


SCHEMA_VERSION = "topic-result-v1"
STOCKECHO_NAMESPACE = uuid.UUID("aa4aac93-5584-4bc5-8a00-120973a36fea")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _local_date(value: str, timezone_name: str) -> date:
    return _parse_datetime(value).astimezone(ZoneInfo(timezone_name)).date()


def _stable_uuid(kind: str, *parts: str) -> str:
    key = "|".join((kind, *parts))
    return str(uuid.uuid5(STOCKECHO_NAMESPACE, key))


def _article_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": row["document_id"],
        "source": row.get("source", ""),
        "title": row.get("title", ""),
        "summary": row.get("summary", ""),
        "published_at": row.get("published_at", ""),
        "canonical_url": row.get("canonical_url", ""),
        "source_url": row.get("source_url", ""),
        "relevance_confidence": float(row.get("relevance_confidence", 0.0)),
    }


def _representative(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    # 모델 점수가 같거나 없는 경우에도 매 실행에서 같은 기사를 선택한다.
    selected = max(
        rows,
        key=lambda row: (
            float(row.get("_representation_score", 0.0)),
            float(row.get("relevance_confidence", 0.0)),
            row.get("published_at", ""),
            row["document_id"],
        ),
    )
    return _article_projection(selected)


def _ordered_articles(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            float(row.get("_representation_score", 0.0)),
            float(row.get("relevance_confidence", 0.0)),
            row.get("published_at", ""),
            row["document_id"],
        ),
        reverse=True,
    )
    return [_article_projection(row) for row in ordered]


def _source_count(rows: Iterable[dict[str, Any]]) -> int:
    sources = set()
    for row in rows:
        url = row.get("canonical_url") or row.get("source_url", "")
        host = urlparse(url).hostname
        sources.add(
            host.removeprefix("www.")
            if host
            else row.get("source", "unknown")
        )
    return len(sources)


def _fallback_keywords(rows: Sequence[dict[str, Any]], limit: int = 5) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        for value in row.get("matched_queries", []):
            keyword = value.replace(row.get("company_name", ""), "").strip()
            if keyword:
                counts[keyword] += 1
    return [item[0] for item in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _event_keywords(
    rows: Sequence[dict[str, Any]],
    tokenizer: Callable[[str], list[str]] | None,
    *,
    company_name: str,
    fallback: Sequence[str],
    limit: int = 5,
) -> list[str]:
    """같은 날짜 Event의 제목들에서 반복 출현한 핵심어를 고른다."""

    if tokenizer is None:
        return list(fallback[:limit])

    company_tokens = set(tokenizer(company_name))
    for suffix in ("전자", "그룹", "홀딩스", "주식회사"):
        if company_name.endswith(suffix) and len(company_name) > len(suffix):
            company_tokens.update(tokenizer(company_name[: -len(suffix)]))
    noise = company_tokens | {"단독", "르포", "종합", "속보", "사진", "영상"}

    document_counts: Counter[str] = Counter()
    total_counts: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    position = 0
    for row in rows:
        tokens = [token for token in tokenizer(row.get("title", "")) if token not in noise]
        document_counts.update(set(tokens))
        total_counts.update(tokens)
        for token in tokens:
            first_seen.setdefault(token, position)
            position += 1

    ordered = sorted(
        document_counts,
        key=lambda token: (
            -document_counts[token],
            -total_counts[token],
            first_seen[token],
            token,
        ),
    )
    return ordered[:limit] or list(fallback[:limit])


def _issue_title_tokens(title: str, company_name: str) -> set[str]:
    normalized = title.casefold().replace(company_name.casefold(), " ")
    return {
        token
        for token in re.findall(r"[가-힣a-z0-9]+", normalized)
        if len(token) >= 2
    }


def _same_issue_title(left: str, right: str, company_name: str) -> bool:
    left_tokens = _issue_title_tokens(left, company_name)
    right_tokens = _issue_title_tokens(right, company_name)
    if not left_tokens or not right_tokens:
        return False
    overlap = left_tokens & right_tokens
    union = left_tokens | right_tokens
    # 뉴스 제목은 같은 사건도 "로봇사업"/"로봇 사업"처럼 합성어가 갈리므로
    # 공통 핵심어가 충분하면 다소 낮은 Jaccard 비율도 같은 이슈로 본다.
    return len(overlap) >= 3 and len(overlap) / len(union) >= 0.35


def build_topic_records(
    articles: Sequence[dict[str, Any]],
    assignments: Sequence[int],
    keywords_by_runtime_topic: dict[int, Sequence[str]],
    *,
    model_version: str,
    timezone_name: str = "Asia/Seoul",
    event_keyword_tokenizer: Callable[[str], list[str]] | None = None,
) -> list[dict[str, Any]]:
    """BERTopic 숫자 ID를 실행 진단값으로만 보관하고 UUID Topic/Event를 만든다."""

    if len(articles) != len(assignments):
        raise ValueError("articles와 assignments 길이가 다릅니다.")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    runtime_ids: dict[str, int] = {}
    for article, runtime_topic_id in zip(articles, assignments):
        # BERTopic -1은 하나의 의미 군집이 아니므로 문서별 singleton으로 분리한다.
        group_key = (
            f"outlier:{article['document_id']}"
            if runtime_topic_id == -1
            else f"topic:{runtime_topic_id}"
        )
        grouped[group_key].append(dict(article))
        runtime_ids[group_key] = runtime_topic_id

    records: list[dict[str, Any]] = []
    for group_key, rows in grouped.items():
        rows.sort(key=lambda row: (row.get("published_at", ""), row["document_id"]))
        runtime_topic_id = runtime_ids[group_key]
        stock_code = rows[0]["stock_code"]
        document_ids = sorted(row["document_id"] for row in rows)
        document_fingerprint = hashlib.sha256(
            "\n".join(document_ids).encode("utf-8")
        ).hexdigest()[:20]
        topic_id = _stable_uuid(
            "topic", model_version, stock_code, document_fingerprint
        )
        keywords = [
            keyword.strip()
            for keyword in keywords_by_runtime_topic.get(runtime_topic_id, [])
            if keyword.strip()
        ][:10]
        if runtime_topic_id == -1 or not keywords:
            keywords = _fallback_keywords(rows) or [rows[0].get("company_name", "이슈")]

        event_groups: dict[date, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            event_groups[_local_date(row["published_at"], timezone_name)].append(row)
        events = []
        for event_date, event_rows in sorted(event_groups.items(), reverse=True):
            event_document_ids = sorted(row["document_id"] for row in event_rows)
            event_fingerprint = hashlib.sha256(
                "\n".join(event_document_ids).encode("utf-8")
            ).hexdigest()[:20]
            event_articles = _ordered_articles(event_rows)
            event_representation = next(
                (
                    row.get("_event_representation")
                    for row in event_rows
                    if row.get("_event_representation")
                ),
                None,
            )
            event_keywords = (
                list(event_representation["keywords"])
                if event_representation
                else _event_keywords(
                    event_rows,
                    event_keyword_tokenizer,
                    company_name=rows[0].get("company_name", ""),
                    fallback=keywords,
                )
            )
            event_name = (
                event_representation["name"]
                if event_representation
                else " · ".join(event_keywords[:3])
            )
            events.append(
                {
                    "event_id": _stable_uuid(
                        "event",
                        model_version,
                        stock_code,
                        topic_id,
                        event_date.isoformat(),
                        event_fingerprint,
                    ),
                    "event_date": event_date.isoformat(),
                    "article_count": len(event_rows),
                    "source_count": _source_count(event_rows),
                    "name": event_name,
                    "keywords": event_keywords,
                    "label_method": (
                        event_representation.get("label_method", "kiwi-frequency-v1")
                        if event_representation
                        else "kiwi-frequency-v1"
                    ),
                    "document_ids": event_document_ids,
                    "representative_article": event_articles[0],
                    "articles": event_articles,
                }
            )

        representative = _representative(rows)
        topic_name = " · ".join(keywords[:3]) if keywords else representative["title"]
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "model_version": model_version,
                "stock_code": stock_code,
                "company_name": rows[0].get("company_name", ""),
                "topic_id": topic_id,
                "runtime_topic_id": runtime_topic_id,
                "is_outlier": runtime_topic_id == -1,
                "name": topic_name,
                "keywords": keywords,
                "article_count": len(rows),
                "source_count": _source_count(rows),
                "period_start": rows[0]["published_at"],
                "period_end": rows[-1]["published_at"],
                "document_ids": document_ids,
                "representative_article": representative,
                "events": events,
                "major_issue": None,
            }
        )
    return sorted(records, key=lambda row: (-row["article_count"], row["topic_id"]))


def _latest_event(
    topic: dict[str, Any], *, as_of: date, window_days: int
) -> dict[str, Any] | None:
    start = as_of - timedelta(days=window_days - 1)
    events = [
        event
        for event in topic["events"]
        if start <= date.fromisoformat(event["event_date"]) <= as_of
    ]
    if not events:
        return None
    return max(events, key=lambda event: event["event_date"])


def _score_event(
    event: dict[str, Any], *, as_of: date, window_days: int
) -> float:
    latest = date.fromisoformat(event["event_date"])
    recency = 1.0 - min((as_of - latest).days / max(window_days, 1), 1.0)
    score = (
        event["article_count"]
        + 0.35 * math.log1p(event["source_count"])
        + 0.5 * recency
    )
    return round(score, 6)


def select_major_issues(
    topics: Sequence[dict[str, Any]],
    *,
    as_of: date,
    windows: Sequence[int] = (7, 14, 30),
    limit: int = 3,
    min_articles: int = 2,
) -> tuple[list[dict[str, Any]], int | None]:
    """7일에서 시작해 부족한 서로 다른 Topic을 14일, 30일로 보충한다."""

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    used_window: int | None = None
    for window_days in windows:
        candidates = []
        for topic in topics:
            if topic["topic_id"] in selected_ids or topic.get("is_outlier"):
                continue
            event = _latest_event(topic, as_of=as_of, window_days=window_days)
            if not event or event["article_count"] < min_articles:
                continue
            score = _score_event(event, as_of=as_of, window_days=window_days)
            candidates.append((score, event["article_count"], event["source_count"], topic, event))
        candidates.sort(
            key=lambda item: (-item[0], -item[1], -item[2], item[3]["topic_id"])
        )
        for score, article_count, source_count, topic, event in candidates:
            representative = event["representative_article"]
            if any(
                _same_issue_title(
                    representative["title"],
                    issue["representative_article"]["title"],
                    topic["company_name"],
                )
                for issue in selected
            ):
                continue
            selected.append(
                {
                    "schema_version": topic["schema_version"],
                    "model_version": topic["model_version"],
                    "stock_code": topic["stock_code"],
                    "company_name": topic["company_name"],
                    "topic_id": topic["topic_id"],
                    "event_id": event["event_id"],
                    "event_date": event["event_date"],
                    "label_method": event.get("label_method", "kiwi-frequency-v1"),
                    "name": event.get("name") or topic["name"],
                    "topic_name": event.get("name") or topic["name"],
                    "keywords": event.get("keywords") or topic["keywords"],
                    "as_of": as_of.isoformat(),
                    "selection_window_days": window_days,
                    "score": score,
                    "article_count_in_window": article_count,
                    "source_count_in_window": source_count,
                    "representative_article": representative,
                    "articles": event["articles"],
                }
            )
            selected_ids.add(topic["topic_id"])
            used_window = window_days
            if len(selected) == limit:
                break
        if len(selected) == limit:
            break

    for rank, issue in enumerate(selected, start=1):
        issue["rank"] = rank
    return selected, used_window


def annotate_major_issues(
    topics: list[dict[str, Any]], issues: Sequence[dict[str, Any]]
) -> None:
    issue_by_id = {issue["topic_id"]: issue for issue in issues}
    for topic in topics:
        issue = issue_by_id.get(topic["topic_id"])
        if issue:
            topic["major_issue"] = {
                key: issue[key]
                for key in (
                    "rank",
                    "event_id",
                    "selection_window_days",
                    "score",
                    "article_count_in_window",
                    "source_count_in_window",
                )
            }
