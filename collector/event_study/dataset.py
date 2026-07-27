"""Event 단위의 결정적이고 누수 방지된 학습 행을 생성한다."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from collector.event_study.reactions import calculate_market_adjusted_reaction
from collector.historical_events.price_reaction import HORIZONS


DATASET_SCHEMA_VERSION = "event-study-dataset-v1"
MATERIAL_DOWNSIDE_THRESHOLD_PERCENT = -3.0


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _article_rows(event: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [
        dict(article)
        for article in list(event.get("articles") or [])
        if isinstance(article, Mapping)
    ]
    representative = event.get("representative_article")
    if isinstance(representative, Mapping):
        representative_row = dict(representative)
        document_id = representative_row.get("document_id")
        if not any(row.get("document_id") == document_id for row in rows):
            rows.append(representative_row)
    return rows


def _feature_documents(
    event: Mapping[str, Any],
) -> tuple[datetime, list[dict[str, Any]]]:
    articles = _article_rows(event)
    dated = [
        (published_at, article)
        for article in articles
        if (published_at := _parse_datetime(article.get("published_at")))
    ]
    explicit_cutoff = _parse_datetime(event.get("feature_cutoff_at"))
    cutoff = explicit_cutoff or (
        min(value for value, _article in dated) if dated else None
    )
    if cutoff is None:
        event_date = date.fromisoformat(str(event["event_date"]))
        cutoff = datetime(
            event_date.year,
            event_date.month,
            event_date.day,
            tzinfo=timezone.utc,
        )

    eligible = [
        article
        for published_at, article in dated
        if published_at <= cutoff
    ]
    eligible.sort(
        key=lambda article: (
            str(article.get("published_at", "")),
            str(article.get("document_id", "")),
        )
    )
    return cutoff, eligible


def _feature_text(articles: Sequence[Mapping[str, Any]]) -> str:
    parts = []
    for article in articles:
        text = " ".join(
            value.strip()
            for value in (
                str(article.get("title") or ""),
                str(article.get("summary") or ""),
            )
            if value.strip()
        )
        if text:
            parts.append(text)
    return "\n".join(parts)


def _label(value: float | None, threshold: float) -> int | None:
    if value is None:
        return None
    return int(value < threshold)


def build_event_study_rows(
    events: Sequence[Mapping[str, Any]],
    *,
    stock_prices: Mapping[str, Sequence[dict[str, Any]]],
    benchmark_prices: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """한 Event를 한 행으로 만들고 입력 cutoff와 미래 label을 분리한다."""

    rows: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    for event in sorted(events, key=lambda row: str(row.get("event_id", ""))):
        event_id = str(event.get("event_id") or "").strip()
        stock_code = str(event.get("stock_code") or "").strip()
        event_date_value = date.fromisoformat(str(event["event_date"]))
        if not event_id or not stock_code:
            raise ValueError("event_id와 stock_code가 필요합니다.")
        if event_id in seen_event_ids:
            raise ValueError(f"중복 Event ID입니다: {event_id}")
        seen_event_ids.add(event_id)

        cutoff, feature_articles = _feature_documents(event)
        representative = event.get("representative_article") or {}
        reaction = calculate_market_adjusted_reaction(
            stock_prices.get(stock_code, []),
            benchmark_prices,
            event_date=event_date_value,
            representative_published_at=(
                feature_articles[0].get("published_at")
                if feature_articles
                else representative.get("published_at")
            ),
        )
        returns = dict(reaction["returns"])
        abnormal_returns = dict(reaction["abnormalReturns"])
        feature_document_ids = [
            str(article.get("document_id"))
            for article in feature_articles
            if article.get("document_id")
        ]

        row: dict[str, Any] = {
            "dataset_schema_version": DATASET_SCHEMA_VERSION,
            "event_id": event_id,
            "stock_code": stock_code,
            "event_date": event_date_value.isoformat(),
            "feature_cutoff_at": cutoff.isoformat(),
            "feature_document_ids": feature_document_ids,
            "feature_text": _feature_text(feature_articles),
            "topic_id": str(event.get("topic_id") or ""),
            "event_name": str(event.get("name") or ""),
            "event_category": str(
                event.get("event_category")
                or event.get("category")
                or "사업·전략"
            ),
            "impact_direction": str(
                event.get("impact_direction")
                or event.get("impact")
                or "unknown"
            ),
            "source_count": int(event.get("source_count") or 0),
            "article_count": int(event.get("article_count") or len(_article_rows(event))),
            "base_date": reaction["baseDate"],
            "baseline_policy": reaction.get("baselinePolicy"),
            "price_status": reaction["status"],
            "benchmark_status": reaction["benchmarkStatus"],
            "abnormal_return_method": reaction["abnormalReturnMethod"],
        }
        for horizon in HORIZONS:
            key = f"d{horizon}"
            raw_return = returns.get(key)
            abnormal_return = abnormal_returns.get(key)
            row[f"return_{key}"] = raw_return
            row[f"benchmark_return_{key}"] = reaction[
                "benchmarkReturns"
            ].get(key)
            row[f"abnormal_return_{key}"] = abnormal_return
            row[f"loss_label_{key}"] = _label(raw_return, 0.0)
            row[f"material_downside_label_{key}"] = _label(
                abnormal_return,
                MATERIAL_DOWNSIDE_THRESHOLD_PERCENT,
            )
            row[f"comparison_date_{key}"] = reaction[
                "comparisonDates"
            ].get(key)
        rows.append(row)
    return rows


def dataset_hash(rows: Iterable[Mapping[str, Any]]) -> str:
    normalized = sorted(
        (dict(row) for row in rows),
        key=lambda row: str(row.get("event_id", "")),
    )
    serialized = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def temporal_split(
    rows: Sequence[Mapping[str, Any]],
    *,
    train_end: date,
    validation_end: date,
) -> dict[str, list[dict[str, Any]]]:
    """Event 날짜 기준의 순방향 train/validation/test 분할."""

    if train_end >= validation_end:
        raise ValueError("train_end는 validation_end보다 앞서야 합니다.")
    result: dict[str, list[dict[str, Any]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    seen: set[str] = set()
    for original in sorted(
        rows,
        key=lambda row: (
            str(row.get("event_date", "")),
            str(row.get("event_id", "")),
        ),
    ):
        row = dict(original)
        event_id = str(row.get("event_id", ""))
        if not event_id or event_id in seen:
            raise ValueError("분할 입력의 Event ID는 고유해야 합니다.")
        seen.add(event_id)
        event_date = date.fromisoformat(str(row["event_date"]))
        if event_date <= train_end:
            split = "train"
        elif event_date <= validation_end:
            split = "validation"
        else:
            split = "test"
        row["split"] = split
        result[split].append(row)
    return result
