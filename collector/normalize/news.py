"""NAVER 검색 결과 뉴스 정규화."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from collector.models.news import NormalizedNewsArticle


TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "ref",
    "sc",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def normalize_url(value: str | None) -> str:
    if not value:
        return ""
    parts = urlsplit(value.strip())
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(query), "")
    )


def parse_published_at(value: str | None) -> str:
    if not value:
        return ""
    return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_item(item: dict, *, source: str = "naver") -> NormalizedNewsArticle:
    title = clean_text(item.get("title"))
    summary = clean_text(item.get("description"))
    original_url = normalize_url(item.get("originallink"))
    source_url = normalize_url(item.get("link"))
    canonical_url = original_url or source_url
    published_at = parse_published_at(item.get("pubDate"))
    identity = canonical_url or f"{title}|{published_at}"
    content_hash = _sha256(f"{title}\n{summary}")

    return NormalizedNewsArticle(
        document_id=f"news_{_sha256(identity)[:20]}",
        source=source,
        title=title,
        summary=summary,
        published_at=published_at,
        canonical_url=canonical_url,
        original_url=original_url,
        source_url=source_url,
        content_hash=content_hash,
    )


def normalize_items(
    items: list[dict],
    *,
    source: str = "naver",
) -> list[NormalizedNewsArticle]:
    articles: list[NormalizedNewsArticle] = []
    seen_identities: set[str] = set()

    for item in items:
        article = normalize_item(item, source=source)
        identity = article.canonical_url or article.content_hash
        if not article.title or identity in seen_identities:
            continue
        seen_identities.add(identity)
        articles.append(article)

    return articles
