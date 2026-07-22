"""정규화 뉴스 model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedNewsArticle:
    document_id: str
    source: str
    title: str
    summary: str
    published_at: str
    canonical_url: str
    original_url: str
    source_url: str
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelevanceResult:
    relation_type: str
    confidence: float
    evidence: tuple[str, ...]
    status: str = "eligible"
    rule_version: str = "relevance-v2"
