"""Supabase 연결 전 사용하는 원자적 로컬 저장소."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from collector.models.news import NormalizedNewsArticle


@dataclass
class QueryCheckpoint:
    last_seen_published_at: str = ""
    recent_urls: list[str] | None = None
    payload_hash: str = ""

    def __post_init__(self) -> None:
        if self.recent_urls is None:
            self.recent_urls = []


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


NaverCheckpoint = QueryCheckpoint


def load_checkpoint(path: Path) -> QueryCheckpoint:
    if not path.exists():
        return QueryCheckpoint()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return QueryCheckpoint(
        last_seen_published_at=payload.get("last_seen_published_at", ""),
        recent_urls=list(payload.get("recent_urls", [])),
        payload_hash=payload.get("payload_hash", ""),
    )


def save_checkpoint(path: Path, checkpoint: QueryCheckpoint) -> None:
    _atomic_write_text(
        path,
        json.dumps(asdict(checkpoint), ensure_ascii=False, indent=2),
    )


def payload_items_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        payload.get("items", []),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def select_new_articles(
    articles: Iterable[NormalizedNewsArticle],
    checkpoint: QueryCheckpoint,
) -> list[NormalizedNewsArticle]:
    known_urls = set(checkpoint.recent_urls or [])
    return [
        article
        for article in articles
        if not article.canonical_url or article.canonical_url not in known_urls
    ]


def updated_checkpoint(
    articles: list[NormalizedNewsArticle],
    previous: QueryCheckpoint,
    payload_hash: str,
    *,
    recent_url_limit: int = 500,
) -> QueryCheckpoint:
    current_urls = [article.canonical_url for article in articles if article.canonical_url]
    merged_urls = list(dict.fromkeys(current_urls + list(previous.recent_urls or [])))
    published_values = [
        article.published_at for article in articles if article.published_at
    ]
    latest = max(
        [previous.last_seen_published_at, *published_values],
        default="",
    )
    return QueryCheckpoint(
        last_seen_published_at=latest,
        recent_urls=merged_urls[:recent_url_limit],
        payload_hash=payload_hash,
    )


def write_raw_gzip(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with gzip.open(temporary_path, "wt", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False)
    temporary_path.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json_atomic(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    content = "".join(
        f"{json.dumps(row, ensure_ascii=False)}\n" for row in rows
    )
    _atomic_write_text(path, content)


def merge_jsonl(
    path: Path,
    rows: Iterable[dict[str, Any]],
    *,
    key_fields: tuple[str, ...],
) -> int:
    existing: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in read_jsonl(path):
        existing[tuple(row[field] for field in key_fields)] = row

    before = len(existing)
    for row in rows:
        existing[tuple(row[field] for field in key_fields)] = row

    content = "".join(
        f"{json.dumps(row, ensure_ascii=False)}\n" for row in existing.values()
    )
    _atomic_write_text(path, content)
    return len(existing) - before


def merge_processed_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    return merge_jsonl(path, rows, key_fields=("document_id",))
